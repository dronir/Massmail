
# Simple mass emailer

This is a simple tool to send an email to multiple people.

It requires you to have an SMTP server for the sending.
If you have a Gmail account, you can use the Gmail SMTP
service, which should let you send 500 emails per day.

**Caveat:** If you send too much mail, you might end up in trouble anyway due to automatic anti-spam systems, and even get your Gmail account suspended.

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
3. Generate a new app password. You can name it whatever you want.
4. Fill in your full Gmail address and the new app password in the config file.

### Get a list of recipients to send to

The email list must be a CSV file with the following properties:

- The first non-empty line contains the column names.
- The columns `Firstname`, `Lastname` and `email` are present. These are used to construct the "To:" line.
- One line per recipient.
- Lines whose `email` field does not match the regular expression `[^@]+@[^@]+\.[^@]+` are ignored (not a proper email address).

### Write your email

1. Copy `example_message.toml` to `message.toml`
2. Edit the subject line, from field and message body in the file.
3. Optionally, add a "reply-to" field.
4. Optionally, add filters to only send the mail to some of your recipients.

#### Templating

You can use [Jinja2 templating](https://jinja.palletsprojects.com/en/3.0.x/templates/) in your email body. The column names of your recipients
file (see below) can be used to customize the email per recipient.
The variable `recipient` will be a Python dictionary with the column names of your CSV file
as keys.

For example, you could start your email with `Dear {{ recipient["Firstname"] }}`,
or do conditional things on your recipients' data:

```text
{{% if recipient["language"] == "fi" %}}
<Finnish text>
{{% else %}}
<Default text>
{{% endif %}}
```

#### Filtering

Under `[filters]` in the email file, you can currently add two lists named `drop_empty` and `drop_nonempty`. These lists can contain column names of your recipients file.

- If a column is in `drop_empty` and a recipient has _no value_ in that column, that recipient is ignored.
- If a column is in `drop_nonempty` and a recipient has _any non-whitespace value_ in that column, that recipient is ignored.

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
