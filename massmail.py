import argparse
import toml
import asyncio
import aiosmtplib
import pandas as pd
import re
from email.message import EmailMessage
from sys import argv, exit

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

def valid_address(s):
    """Crudely validate an email."""
    return re.match("[^@]+@[^@]+\.[^@]+", s)

def get_name(row):
    """Turn DataFrame row tuple into string for email recepient."""
    first = row[1].strip()
    last = row[2].strip()
    address = row[3].strip()
    if not valid_address(address):
        print(f"<{address}> was not a valid address. Skipped.")
        return None
    return f"{first} {last} <{address}>"




async def send_email(config, recipient, message):
    """Send given message to a particular recipient, using given server config."""
    mail = EmailMessage()
    mail["From"] = message["from"]
    mail["To"] = recipient
    mail["Subject"] = message["title"]
    mail.set_content(message["body"])

    try:
        print(f"Sending to {recipient}...")
        await aiosmtplib.send(
            mail,
            hostname=config["hostname"],
            port=config["port"],
            username=config["username"],
            password=config["password"],
            start_tls=True
        )
    except Exception as E:
        print(f"Error sending to {recipient}:\n{E}")
        return False
    else:
        return True

async def iterate_recipients(addr):
    """Iterator over rows DataFrame, converting info to strings."""
    for line in addr.itertuples():
        recipient = get_name(line)
        if recipient is None:
            continue
        yield recipient

async def do_sending(config, addresses, message):
    """Iterate over all recipients and send the email to each."""
    async for recipient in iterate_recipients(addresses):
        await send_email(config, recipient, message)



parser = argparse.ArgumentParser()
parser.add_argument("receipients", help="A CSV file with the receipients's data")
parser.add_argument("message", help="A TOML file with the message")
parser.add_argument("--config", default="config.toml", help="A TOML file with config variables, defaults to 'config.toml'.")

if __name__=="__main__":
    # Parse command line arguments
    args = parser.parse_args()

    # Load config, message contents and address book from files
    config = load_toml(args.config)
    message = load_toml(args.message)
    addr = load_addresses(args.receipients)

    # Print message and confirmation request
    print(f"==== BEGIN MESSAGE ====")
    print(f"Subject: {message['title']}")
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

