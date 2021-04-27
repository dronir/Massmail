
# Simple mass emailer

This is a simple tool to send an email to multiple people.

It requires you to have an SMTP server for the sending.
If you have a Gmail account, you can use the Gmail SMTP
service, which lets you send 300 emails per day.

## Installation

You need Python 3.6+.

If running a normal Python distribution, preferably start by making a new `virtualenv`, 
but in any case install the dependencies that are found in `requirements.txt`.
With `pip` this is probably easiest:

```shell
pip install -r requirements.txt
```

## Setting up for sending

### Set up Google SMTP

1. Copy `example_config.toml` to `config.toml`.
2. Go to your Google security settings.
3. Generate a a new app password. You can name it whatever you want.
4. Fill in your full Gmail address and the new app password in the config file.

### Write your email

1. Copy `example_message.toml` to `message.toml`
2. Edit the subject line, from field and message body in the file.

### Get a list of recipients to send to

The email list must be a CSV file with the following properties:

- The first non-empty line contains the column names.
- The column names `Firstname`, `Lastname` and `email` are present.
- One line per recipient.
- Any lines with a `N/A` or empty value in any of these three columns gets ignored.

## Sending the message

If `address_list.csv` is your list of recipients, run the following on the command line:

```shell
python massmail.py address_list.csv message.toml
```

The first parameter after the name of the script is the path to your list of recipients.
The second parameter is the path to the TOML file containing the message.

The script will print out the message and ask for your confirmation before sending.

### Config file

The script will use `config.toml` by default, but if you want a different file, you can add the argument `--config FILENAME` to the command line.
