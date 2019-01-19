# drymail
Makes sending emails easy and DRY — For Python 3.  

[![PyPI version](https://badge.fury.io/py/drymail.svg)](https://badge.fury.io/py/drymail)

__Drymail__ is a minimalist wrapper over Python’s existing [smtplib](https://docs.python.org/3/library/smtplib.html) and [email](https://docs.python.org/3/library/email.html) libraries, designed to be friendly but unrestrictive. Here’s how you might send a simple email with an attachment using _drymail_.

```python
from drymail import SMTPMailer, Message

client = SMTPMailer(host='smtp.email.com', user='johndoe', password='password', tls=True)
message = Message(subject='Congrats on the new job!', sender=('John Doe', 'john@email.com'), 
                  receivers=[('Jane Doe', 'jane@message.com'), 'jane.doe@mail.io'])
with open('congrats.pdf', 'rb') as pdf_file:
    message.attach(filename='congrats.pdf', data=pdf_file.read(), mimetype='application/pdf')

client.send(message)
```

## Features

- Supports creating email with HTML content, plaintext content, or both!
- Supports mentioning contacts in the `“John Doe" <john@email.com>` format.
- Support standard headers like `CC`, `BCC`, `Reply-To` and `Authors`.
- Supports injecting custom headers.
- Supports adding attachments.
- And most importantly — the library being minimalist, it doesn’t restrict you in any way like some of the most fancier email frameworks do.

## Installation

Install `drymail` by running —

```console
$ pip3 install drymail
```

## Documentation

Documentation is available at https://drymail.readthedocs.io/

## Contribute

All kinds of contribution are welcome.

- Issue Tracker — https://github.com/drymail/issues
- Source Code — https://github.com/drymail

## License

This project is licensed under the MIT license.

