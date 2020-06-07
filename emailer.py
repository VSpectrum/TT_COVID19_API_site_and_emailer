from config import *
import smtplib
from os import listdir, path
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

def send_email(recipient, subject, text_body = None, html_body = None, attachments = None):

    gmail_user = emailer_ad
    gmail_pwd = emailer_pass

    FROM = emailer_ad
    TO = recipient if type(recipient) is list else [recipient]
    SUBJECT = subject

    msg = MIMEMultipart('alternative')
    msg['Subject'] = SUBJECT
    msg['From'] = FROM
    msg['To'] = 'veydh@reticence.net'
    msg.add_header('List-Unsubscribe', 'https://covid.reticence.net/unsubscribe')

    msg.preamble = 'Multipart massage.\n'
    if (text_body): msg.attach(MIMEText(text_body, 'plain'))
    if (html_body): msg.attach(MIMEText(html_body, 'html'))

    if attachments:
        for graphpic in listdir('graphs'):
            ImgFileName = 'graphs/'+graphpic
            img_data = open(ImgFileName, 'rb').read()
            image = MIMEImage(img_data, name=path.basename(ImgFileName))
            msg.attach(image)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_pwd)
        server.sendmail(FROM, TO, msg.as_string())
        server.quit()
        print("Success")
    except:
        print("Failed")