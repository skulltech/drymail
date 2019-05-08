import mimetypes
from email import encoders, message_from_bytes
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from smtplib import SMTP, SMTP_SSL, SMTPServerDisconnected

import mistune
from bs4 import BeautifulSoup


class SMTPMailer:
    """
    Wrapper around `smtplib.SMTP` class, for managing a SMTP client.

    Parameters
    ----------
    host : str
        The hostname of the SMTP server to connect to.
    port : int, optional
        The port number of the SMTP server to connect to.
    user : str, optional
        The username to be used for authentication to the SMTP server.
    password : str, optional
        The password to be used for authentication to the SMTP server.
    ssl : bool, optional
        Whether to use SSL for the SMTP connection.
    tls : bool, optional
        Whether to use TLS // `starttls` for the SMTP connection.
    keyfile : str, optional
        File containing the SSL private key.
    certfile : str, optional
        File containing the SSL certificate in PEM format.
    context: `ssl.SSLContext` object
        The SSL context to be used in the SSL connection.

    Attributes
    ----------
    client: `smtplib.SMTP` object
        The SMTP client that'd be used to send emails.
    connected: bool
        Whether there is an active SMTP connection.
    host : str
        The hostname of the SMTP server to connect to.
    port : int
        The port number of the SMTP server to connect to.
    user : str
        The username to be used for authentication to the SMTP server.
    password : str
        The password to be used for authentication to the SMTP server.
    ssl : bool
        Whether to use SSL for the SMTP connection.
    tls : bool
        Whether to use TLS // `starttls` for the SMTP connection.
    """

    def __init__(self, host, port=None, user=None, password=None, ssl=False, tls=False, **kwargs):
        self.host = host
        self.ssl = ssl
        self.tls = tls
        if ssl:
            self.port = port or 465
            self.__ssloptions = dict()
            for key in ['keyfile', 'certfile', 'context']:
                self.__ssloptions[key] = kwargs.get(key, None)
        elif tls:
            self.port = port or 587
        else:
            self.port = port or 25
        self.user = user
        self.password = password
        self.connected = False
        self.client = None

    def connect(self):
        """
        Create the SMTP connection.
        """
        self.client = SMTP(self.host, self.port) if not self.ssl else SMTP_SSL(self.host, self.port,
                                                                               **self.__ssloptions)
        self.client.ehlo()
        if self.tls:
            self.client.starttls()
            self.client.ehlo()
        if self.user and self.password:
            self.client.login(self.user, self.password)
        self.connected = True

    def __enter__(self):
        return self

    def close(self):
        """
        Close the SMTP connection and `quit` the `self.client` object.
        """
        if self.connected:
            try:
                self.client.quit()
            except SMTPServerDisconnected:
                pass
        self.connected = False

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __del__(self):
        self.close()

    def send(self, message, sender=None, receivers=None):
        """
        Send an email through this SMTP client.

        Parameters
        ----------
        message : `drymail.Message` object
            The message to be sent.
        sender : str, optional
            The email address of the sender.
        receivers : list of str, optional
            The email addresses of the receivers // recipients.
        """
        if not message.prepared:
            message.prepare()
        if not self.connected:
            self.connect()
        self.client.send_message(message.message, from_addr=sender, to_addrs=receivers)


def stringify_address(address):
    """
    Converts an address into a string in the `"John Doe" <john@example.com>"` format, which can be directly used in the
    headers of an email.

    Parameters
    ----------
    address : str or (str, str)
        An address. Can be either the email address or a tuple of the name
        and the email address.

    Returns
    -------
    str
        Address as a single string, in the `"John Doe" <john@example.com>"` format. Returns
        `address` unchanged if it's a single string.
    """
    address = ('', address) if isinstance(address, str) else address
    return formataddr((str(Header(address[0], 'utf-8')), address[1]))


def stringify_addresses(addresses):
    """
    Converts a list of addresses into a string in the
    `"John Doe" <john@example.com>, "Jane" <jane@example.com>"` format,
    which can be directly used in the headers of an email.

    Parameters
    ----------
    addresses : (str or (str, str)) or list of (str or (str, str))
        A single address or a list of addresses which is to be converted into a single string. Each element can be
        either an email address or a tuple of a name and an email address.

    Returns
    -------
    str
        The address(es) as a single string which can be directly used in the headers of an email.
    """
    if isinstance(addresses, list):
        addresses = [stringify_address(address) for address in addresses]
        return ', '.join(addresses)
    else:
        return stringify_address(addresses)


class Message:
    """
    Class representing an email message.

    Parameters
    ----------
    sender : str or (str, str)
        The address of the sender. Can be either the email address or a tuple of the name and the email address.
    receivers : list of (str or (str, str))
        The list of receivers // recipients. Each element can be either an email address or a tuple of a name and an
        email address.
    subject : str, optional
        The subject of the email
    authors : list of (str or (str, str)), optional
        The list of authors, to be mentioned in the `Authors` header. Each
        element can be either an email address or a tuple of a name and an email address.
    cc : list of (str or (str, str)), optional
        The list of addresses to CC to. Each element can be either an email
        address or a tuple of a name and an email address.
    bcc : list of (str or (str, str)), optional
        The list of addresses to BCC to. Each element can be either an email address or a tuple of a name and an email
        address.
    reply_to : list of (str or (str, str)), optional
        The list of addresses to mention in the `Reply-To` header. Each element can be either an email address or a
        tuple of a name and an email address.
    headers : dict, optional
        Custom headers as key-value pairs, to be injected into the email.
    text: str, optional
        The body of the message, as plaintext. At least one among `text` and `html`
        must be provided.
    html: str, optional
        The body of the message, as HTML. At least one among `text` and `html`
        must be provided.
    prepared_message: bytes, optional
        A prepared email as bytes. If this is provided, all the other optional parameters will be ignored.

    Attributes
    ----------
    message: `email.message.Message` object or `email.mime.multipart.MIMEMultipart` object
        The prepared message object.
    prepared: bool
        Whether the message is prepared, in other words whether `self.message` is available and proper.
    sender : str or (str, str)
        The address of the sender. Can be either the email address or a tuple of the name and the email address.
    receivers : list of (str or (str, str))
        The list of receivers // recipients. Each element can be either an email address or a tuple of a name and an
        email address.
    subject : str
        The subject of the email
    authors : list of (str or (str, str))
        The list of authors, to be mentioned in the `Authors` header. Each element can be either an email address or a
        tuple of a name and an email address.
    cc : list of (str or (str, str))
        The list of addresses to CC to. Each element can be either an email address or a tuple of a name and an email
        address.
    bcc : list of (str or (str, str))
        The list of addresses to BCC to. Each element can be either an email address or a tuple of a name and an email
        address.
    reply_to : list of (str or (str, str))
        The list of addresses to mention in the `Reply-To` header. Each element can be either an email address or a
        tuple of a name and an email address.
    headers : dict
        Custom headers as key-value pairs, to be injected into the email.
    text: str
        The body of the message, as plaintext.
    html: str
        The body of the message, as HTML.
    prepared_message: bytes
        A prepared email as bytes.
    """

    def __init__(self, sender, receivers, subject=None, authors=None, cc=None, bcc=None, reply_to=None, headers=None,
                 text=None, html=None, prepared_message=None):
        self.subject = subject or ''
        self.sender = sender
        self.receivers = receivers
        self.authors = authors
        self.cc = cc
        self.bcc = bcc
        self.headers = headers
        self.reply_to = reply_to
        self.text = text or ''
        self.html = html or ''
        self.__attachments = []
        self.prepared_message = prepared_message
        self.prepared = False
        self.message = MIMEMultipart('mixed')

    def __str__(self):
        if not self.prepared:
            self.prepare()
        return self.message.as_string()

    @property
    def attachments(self):
        """
        All the attachments attached to the message.

        Returns
        -------
        list of str
            The filenames of the attachments attached.
        """
        return self.__attachments

    def attach(self, data, filename, mimetype=None):
        """
        Add a file as attachment to the email.

        Parameters
        ----------
        data: bytes
            The raw content of the file to be attached.
        filename : str
            The name of the file to be attached.
        mimetype : str, optional
            The MIMEType of the file to be attached.
        """
        if self.prepared_message:
            return

        if not mimetype:
            mimetype, encoding = mimetypes.guess_type(filename)
            if mimetype is None or encoding is not None:
                mimetype = 'application/octet-stream'
        maintype, subtype = mimetype.split('/', 1)
        attachment = MIMEBase(maintype, subtype)
        attachment.set_payload(data)
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', 'attachment', filename=filename)
        self.message.attach(attachment)
        self.__attachments.append(filename)

    def prepare(self):
        """
        Prepare the `self.message` object.
        """
        if self.prepared_message:
            self.message = message_from_bytes(self.prepared_message)
            self.prepared = True
            return

        self.text = self.text or BeautifulSoup(self.html, 'html.parser').get_text(strip=True)
        self.html = self.html or mistune.markdown(self.text)

        self.message['Sender'] = stringify_address(self.sender)
        self.message['From'] = stringify_addresses(self.authors) if self.authors else stringify_address(self.sender)
        self.message['To'] = stringify_addresses(self.receivers)
        self.message['Subject'] = self.subject
        if self.cc:
            self.message['CC'] = stringify_addresses(self.cc)
        if self.bcc:
            self.message['BCC'] = stringify_addresses(self.bcc)
        if self.reply_to:
            self.message['Reply-To'] = stringify_addresses(self.reply_to)
        if self.headers:
            for key, value in self.headers.items():
                self.message[key] = value

        body = MIMEMultipart('alternative')
        plaintext_part = MIMEText(self.text, 'plain')
        html_part = MIMEText(self.html, 'html')
        body.attach(plaintext_part)
        body.attach(html_part)
        self.message.attach(body)
        self.prepared = True
