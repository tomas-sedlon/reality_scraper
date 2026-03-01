import smtplib
import ssl
import yaml
import os
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List


class EmailSender:

    def __init__(self, client_config):
        self.email_cfg = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "..", 'email.yml')))

        self.sender_email = self.email_cfg['sender_email']
        self.sender_email_password = self.email_cfg['sender_email_password']
        self.receiver_emails: List[str] = client_config['receiver_emails']
        self.subject = f'reality_report_{str(datetime.date.today())}'

        self.port = 465  # For SSL
        self.smtp_server = "smtp.gmail.com"
        self.context = ssl.create_default_context()

    def send_message_to_all(self, message_content: Optional[str]):
        for recipient in self.receiver_emails:
            self.send_message(message_content, recipient)

    def send_message(self, message_content: Optional[str], receiver_email):
        if message_content is not None:
            message = MIMEMultipart("alternative")
            message["Subject"] = self.subject
            message["From"] = self.sender_email
            message["To"] = receiver_email

            part1 = MIMEText(message_content, "plain")
            message.attach(part1)

            try:
                with smtplib.SMTP_SSL(self.smtp_server, self.port, context=self.context, timeout=15) as server:
                    server.login(self.sender_email, self.sender_email_password)
                    server.sendmail(self.sender_email, receiver_email, message.as_string())
                    print(f"Sent message to email {receiver_email}")
            except Exception as e:
                print(f"Error sending email to {receiver_email}: {repr(e)}")
        else:
            print(f"Received an empty message, will not send anything")
