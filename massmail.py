import argparse
import re
import toml
import asyncio
import pandas as pd
from aiosmtplib import SMTP
from email.message import EmailMessage
from sys import exit

def load_toml(filename):
    """Load a TOML file with given filename."""
    with open(filename, 'r') as f:
        return toml.loads(f.read())

def load_addresses(filename):
    """Load CSV file into DataFrame, then drop all lines with N/A values."""
    df = pd.read_csv(
        filename, 
        header=0, 
        usecols=["Firstname", "Lastname", "email"], 
        skip_blank_lines=True        
    )
    return df.dropna()

def valid_message(message):
    return ("subject" in message
        and "from" in message
        and "body" in message
    )

def valid_config(config):
    return ("hostname" in config
        and "port" in config
        and "username" in config
        and "password" in config
    )

def valid_address(s):
    """Crudely validate an email."""
    return re.match("[^@]+@[^@]+\.[^@]+", s)



def get_recipient(row):
    """Turn DataFrame row tuple into string for email recipient."""
    first = row[1].strip()
    last = row[2].strip()
    address = row[3].strip()
    if not valid_address(address):
        print(f"<{address}> was not a valid address. Skipped.")
        return None
    return f"{first} {last} <{address}>"

async def iterate_recipients(addr):
    """Iterator over rows DataFrame, converting info to strings."""
    for line in addr.itertuples():
        recipient = get_recipient(line)
        if recipient is None:
            continue
        yield recipient

async def queue_recipients(queue, addresses):
    """Get recipients from the DataFrame, turn them into strings,
    add them to the queue, and finally add a None."""
    async for recipient in iterate_recipients(addresses):
        await queue.put(recipient)
    await queue.put(None)




def get_client(config):
    return SMTP(
            hostname=config["hostname"],
            port=config["port"],
            username=config["username"],
            password=config["password"], 
            start_tls=True
        )

async def do_sending(config, addresses, message):
    """Main task. Create queue to share work, and workers to send out messages."""
    tasks = []
    queue = asyncio.Queue(maxsize=100)
    tasks.append(queue_recipients(queue, addresses))
    
    N = config.get("parallel_workers", 1)
    print(f"Starting {N} worker tasks...")
    for n in range(N):
        tasks.append(worker_send(config, queue, message, n+1))
    results = await asyncio.gather(*tasks)

async def worker_send(config, queue, message, n):
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
            print(f"Worker {n} sending to {recipient}...")
            await send_email(client, recipient, message)

async def send_email(client, recipient, message):
    """Use the client to send the message to the recipient."""
    mail = EmailMessage()
    mail["From"] = message["from"]
    mail["To"] = recipient
    mail["Subject"] = message["subject"]
    mail.set_content(message["body"])

    try:
        await client.send_message(mail)
    except Exception as E:
        print(f"Error sending to {recipient}:\n{E}")
        return False
    else:
        return True




parser = argparse.ArgumentParser()
parser.add_argument("recipients", help="A CSV file with the recipients's data")
parser.add_argument("message", help="A TOML file with the message")
parser.add_argument("--config", default="config.toml", help="A TOML file with config variables, defaults to 'config.toml'.")

if __name__=="__main__":
    # Parse command line arguments
    args = parser.parse_args()

    # Load config, message contents and address book from files
    config = load_toml(args.config)
    if not valid_config(config):
        print("Error: some key missing from config file (either 'hostname', 'port', 'username' or 'password').")
        exit()
    message = load_toml(args.message)
    if not valid_message(message):
        print("Error: some value missing from message (either 'subject', 'from' or 'body').")
        exit()
    addr = load_addresses(args.recipients)

    # Print message and confirmation request
    print(f"==== BEGIN MESSAGE ====")
    print(f"Subject: {message['subject']}")
    print(f"From: {message['from']}")
    print()
    print(message["body"])
    print("==== END MESSAGE ====")
    answer = input(f"Send the above message to the {len(addr)} people found in the address list? [y/N] ").upper()
    if answer == "Y":
        asyncio.run(do_sending(config, addr, message))
    else:
        print("Cancelled.")
        exit

