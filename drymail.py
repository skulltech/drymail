from smtplib import SMTP, SMTP_SSL, SMTPServerDisconnected
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from email import encoders, message_from_bytes
import mimetypes

from bs4 import BeautifulSoup
import mistune 


class SMTPMailer:
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
        self.user = user
        self.password = password
        self.connected = False

    def connect(self):
        self.client = SMTP(self.host, self.port) if not self.ssl else SMTP_SSL(self.host, self.port, **self.__ssloptions)
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
        if not message.prepared:
            message.prepare()
        if not self.connected:
            self.connect()
        self.client.send_message(message.message, from_addr=sender, to_addrs=receivers)


class Message:
    def __init__(self, sender, receivers, subject=None, authors=None, cc=None, bcc=None, replyto=None, headers=None, text=None, html=None, prepared_message=None):
        self.subject = subject or ''
        self.sender = sender
        self.receivers = receivers
        self.authors = authors
        self.cc = cc
        self.bcc = bcc
        self.replyto = replyto
        self.text = text or ''
        self.html = html or ''
        self.__attachments = []
        self.prepared_message = prepared_message
        self.prepared = False

    def __str__(self):
        return self.message.as_string()

    @property
    def attachments(self):
        return self.__attachments

    def attach(self, data, filename, mimetype=None):
        if self.prepared_message:

        if not mimetype:
            mimetype, encoding = mimetypes.guess_type(path)
            if mimetype is None or encoding is not None:
                mimetype = 'application/octet-stream'
        maintype, subtype = mimetype.split('/', 1)
        attachment = MIMEBase(maintype, subtype)
        attachment.set_payload(data)
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', 'attachment', filename=filename)
        self.message.attach(attachment)
        self.__attachments.append(filename)

    def __addresses(self, addresses):
        if isinstance(addresses, list):
            addresses = [self.__address(address) for address in addresses] 
            return ', '.join(addresses)
        else:
            return self.__address(addresses)

    def __address(self, address):
        address = ('', address) if isinstance(address, str) else address
        return formataddr((str(Header(address[0], 'utf-8')), address[1]))

    def prepare(self):
        if self.prepared_message:
            self.message = message_from_bytes(self.prepared_message)
            self.prepared = True
            return

        self.message = MIMEMultipart('mixed')
        self.text = self.text or BeautifulSoup(self.html, 'html.parser').get_text(strip=True)
        self.html = self.html or mistune.markdown(self.text)

        self.message['Sender'] = self.__address(self.sender)
        self.message['From'] = self.__addresses(self.authors) if self.authors else self.__address(self.sender)
        self.message['To'] = self.__addresses(self.receivers)
        self.message['Subject'] = self.subject
        if self.cc:
            self.message['CC'] = self.__addresses(self.cc)
        if self.bcc:
            self.message['BCC'] = self.__addresses(self.bcc)
        if self.replyto:
            self.message['Reply-To'] = self.__addresses(self.replyto)

        body = MIMEMultipart('alternative')
        plaintext_part = MIMEText(self.text, 'plain')
        html_part = MIMEText(self.html, 'html')
        body.attach(plaintext_part)
        body.attach(html_part)
        self.message.attach(body)
        self.prepared = True


'''
payload = [
{
    'SMTP': {
        'Host': 'smtp.gmail.com',
        'Port': '587',
        'SSL': False,
        'TLS': True,
        'User': 'bulletproof.sumit@gmail.com',
        'Password': '__password__'
    },
    'Message': {
        'Subject': 'Testing API',
        'Sender': ['Sumit', 'bulletproof.sumit@gmail.com'],
        'Receivers': [
            ['John', 'john@place.com'],
            'jane@doe.com'
        ],
        'Authors': [
            'bulletproof.sumit@gmail.com',
            ['SkullTech', 'sumit.ghosh32@gmail.com']
        ],
        'CC': [],
        'BCC': [],
        'Reply-To': [],
        'Text': '',
        'HTML': '',
        'Headers': [
            'Header 1',
            'Header 2'
        ],
        'Attachments': [
            {
                'Filename': 'Resume.pdf',
                'Data': 'qwerty',
                'MIMEType': 'application/pdf'
            },
            {
                'Filename': 'Resume.pdf',
                'Data': 'qwerty',  # Base64 encoded
                'MIMEType': 'application/pdf'
            }
        ]
    }
},
{
    ...
}
]

'''

def mailer(message):
    print('[*] Message received.')
    smtp_options = {
        'host': message['SMTP']['Host'],
        'port': message['SMTP'].get('Port', None),
        'user': message['SMTP'].get('User', None),
        'password': message['SMTP'].get('Password', None),
        'tls': message['SMTP'].get('TLS', None),
        'SSL': message['SMTP'].get('SSL', None)
    }
    client = SMTPMailer(**smtp_options)
    print('[*] SMTP connection created.')
    message_options = {
        'sender': message['Message']['Sender'],
        'receivers': message['Message']['Receivers'],
        'subject': message['Message'].get('Subject', None),
        'authors': message['Message'].get('Authors', None),
        'cc': message['Message'].get('CC', None),
        'bcc': message['Message'].get('BCC', None),
        'replyto': message['Message'].get('Reply-To', None),
        'headers': message['Message'].get('Headers', None),
        'text': message['Message'].get('Text', None),
        'html': message['Message'].get('HTML', None),
        'prepared_message': message['Message'].get('PreparedMessage', None)
    }
    msg = Message(**message_options)
    for attachment in message['Message'].get('Attachments', []):
        msg.attach(filename=attachment['Filename'], data=attachment['Data'], mimetype=attachment.get('MIMEType', None))
    msg.prepare()
    print('[*] Message prepared : >')
    print(msg)
    client.send(msg)
    print('[*] Message sent!')


def send_request():
    payload = {"param_1": "value_1", "param_2": "value_2"}
    files = {
         'json': (None, json.dumps(payload), 'application/json'),
         'file': (os.path.basename(file), open(file, 'rb'), 'application/octet-stream')
    }

    r = requests.post(url, files=files)
    print(r.content)

'''

client = SMTPMailer(host='smtp.gmail.com', user='bulletproof.sumit@gmail.com', password='__password__', tls=True)
message = Message(subject='Testing my lib.', sender=('Sumit Ghosh', 'bulletproof.sumit@gmail.com'), authors=[('Sumit Ghosh', 'bulletproof.sumit@gmail.com'), ('Sumit IIT', 'cs5160400@cse.iitd.ac.in')], receivers=[('SkullTech', 'sumit.ghosh32@gmail.com'), ('Dank SkullTech', 'bulletproof.sumit@gmail.com')])
message.attach(filename='testing.py', data=open('testing.py', 'rb').read(), mimetype='application/program')
print(message)
client.send(message)
'''