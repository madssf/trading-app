import smtplib
import config
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# The mail addresses and password
sender_address = f'{config.GMAIL_SENDER}@gmail.com'
sender_pass = config.GMAIL_SENDER_PW
receiver_address = config.MAIL_RECIEVER


def send_mail(type, mail_content):
    if type == "trade alert":
        subject = 'Trade condition alert! | cloud.trading.app'
        content = "Instructions:"+'\n'
        for order in mail_content:

            content += f"{order['side']} {order['symbol']}  {order['coins']} tokens - ({round(order['usd_amt'],2)} $)"+'\n'
    else:
        raise ValueError('unknown mail type')
    message = MIMEMultipart()
    message['From'] = sender_address
    message['To'] = receiver_address
    # The subject line
    message['Subject'] = subject
    # The body and the attachments for the mail
    message.attach(MIMEText(str(content), 'plain'))
    # Create SMTP session for sending the mail
    session = smtplib.SMTP('smtp.gmail.com', 587)  # use gmail with port
    session.starttls()  # enable security
    # login with mail_id and password
    session.login(sender_address, sender_pass)
    text = message.as_string()
    session.sendmail(sender_address, receiver_address, text)
    session.quit()
    print(
        f'sent mail! | from: {sender_address} | to: {receiver_address} | subject: {subject}| content: {mail_content}|')
