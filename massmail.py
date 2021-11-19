import argparse
import re

import aiosmtplib
import toml
import asyncio
import csv
import logging
from aiosmtplib.smtp import SMTP
from email.message import EmailMessage
from sys import exit
from jinja2 import Template
from typing import Any, Optional, Match, List

logging.basicConfig(level=logging.DEBUG)


def load_toml(filename: str) -> dict[str, Any]:
    """Load a TOML file with given filename."""
    with open(filename, "r") as f:
        return dict(toml.loads(f.read()))


def valid_message(message: dict[str, Any]) -> bool:
    return "subject" in message and "from" in message and "body" in message


def valid_config(config: dict[str, Any]) -> bool:
    return (
        "hostname" in config and "port" in config and "username" in config and "password" in config
    )


def valid_address(s: str) -> Optional[Match[str]]:
    """Crudely validate an email."""
    return re.match(r"[^@]+@[^@]+\.[^@]+", s)


def load_addresses(filename: str, filters: dict) -> List[dict]:
    """Load CSV file into list of dicts."""
    recipients = []
    with open(filename, "r") as f:
        for line in csv.DictReader(f):
            t = clean_recipient(line, filters)
            if t is not None:
                recipients.append(t)
    return recipients


def clean_recipient(line: dict[str, str], filters: dict) -> Optional[dict]:
    """Ensure email address is valid and filter if filters are given."""
    if not valid_address(line["email"]):
        logging.warning(f"Not a valid-looking email address: '{line['email']}'. Skipping.")
        return None

    if filters is None:
        return line

    for col in filters["drop_empty"]:
        if col in line.keys():
            if line[col].strip() == "":
                logging.debug(f"Dropping {line['email']} because {col} = {line[col]} empty.")
                return None
        else:
            logging.warning(f"{col} not in keys {line.keys()}")

    for col in filters["drop_nonempty"]:
        if col in line.keys():
            if line[col].strip() != "":
                logging.debug(f"Dropping {line['email']} because {col} = {line[col]} nonempty.")
                return None
        else:
            logging.warning(f"{col} not in keys {line.keys()}")
    return line


async def queue_recipients(queue: asyncio.Queue, recipients: List) -> None:
    """Get recipients from the list, add them to the queue, and finally add a None."""
    for recipient in recipients:
        await queue.put(recipient)
    await queue.put(None)


async def do_sending(
    config: dict[str, Any], recipients: List[dict], message: dict[str, Any]
) -> None:
    """Main task. Create queue to share work, and workers to send out messages."""
    tasks = []
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    tasks.append(queue_recipients(queue, recipients))

    N = config.get("parallel_workers", 1)
    print(f"Starting {N} worker tasks...")
    for n in range(N):
        tasks.append(worker(config, queue, message, n + 1))
    _ = await asyncio.gather(*tasks)


def get_client(config: dict) -> SMTP:
    """Create SMTP client object from config dict."""
    return SMTP(
        hostname=config["hostname"],
        port=config["port"],
        username=config["username"],
        password=config["password"],
        start_tls=True,
    )


async def worker(config: dict, queue: asyncio.Queue, message: dict, n: int) -> None:
    """Create a client, get recipients from queue, and send the message to each."""
    async with get_client(config) as client:
        while True:
            recipient = await queue.get()
            if recipient is None:
                # If we get a None, all addresses have been processed.
                # Put None back in the queue for the next worker to find, and return.
                print(f"Worker {n} finished.")
                await queue.put(None)
                return
            print(f"Worker {n} sending to {recipient['email']}...")
            await send_email(client, recipient, message)


async def send_email(client: SMTP, recipient: dict, message: dict) -> bool:
    """Use the client to send the message to the recipient."""
    mail = EmailMessage()
    mail["To"] = recipient["email"]
    mail["From"] = message["from"]
    mail["Subject"] = message["subject"]
    if "reply_to" in message.keys():
        mail["reply-to"] = message["reply_to"]

    # Render message template based on recipient dict
    message_body = await message["template"].render_async(recipient=recipient)
    mail.set_content(message_body)

    # TODO better exeption handling
    try:
        await client.send_message(mail)
    except Exception as E:
        logging.error(f"Error sending to {recipient}:\n{E}")
        return False
    else:
        return True


parser = argparse.ArgumentParser()
parser.add_argument("recipients", help="A CSV file with the recipients's data")
parser.add_argument("message", help="A TOML file with the message")
parser.add_argument(
    "--config",
    default="config.toml",
    help="A TOML file with config variables, defaults to 'config.toml'.",
)

if __name__ == "__main__":
    # Parse command line arguments
    args = parser.parse_args()

    # Load config, message contents and address book from files
    raw_config = load_toml(args.config)
    if not valid_config(raw_config):
        print(
            "Error: some key missing from config file (either 'hostname', 'port', 'username' or 'password')."
        )
        exit()
    message = load_toml(args.message)
    if not valid_message(message):
        print("Error: some value missing from message (either 'subject', 'from' or 'body').")
        exit()

    # Create Jinja2 template from message body string
    message["template"] = Template(message["body"], enable_async=True)

    # Load recipients and filter them if filters are provided in the message file
    addr = load_addresses(args.recipients, message.get("filters", None))

    # Print message and confirmation request
    print("==== BEGIN MESSAGE ====")
    print(f"Subject: {message['subject']}")
    print(f"From: {message['from']}")
    print()
    print(message["body"])
    print("==== END MESSAGE ====")
    answer = input(
        f"Send the above message to the {len(addr)} people found in the address list? [y/N] "
    ).upper()
    if answer == "Y":
        asyncio.run(do_sending(raw_config, addr, message))
    else:
        print("Cancelled.")
        exit
