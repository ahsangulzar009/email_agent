import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

smtp_server = os.getenv("SMTP_HOST")
smtp_port = os.getenv("SMTP_PORT")
sender_email = os.getenv("SMTP_FROM")
app_password = os.getenv("SMTP_PASS")

def send_email(recipient_email, subject, body):
  msg = EmailMessage()  
  msg["From"] = sender_email
  msg["To"] = recipient_email
  msg["Subject"] = subject
  msg.set_content(body)

  try:
    with smtplib.SMTP_SSL(smtp_server, int(smtp_port)) as server:
      server.login(sender_email, app_password)
      server.send_message(msg)
    return "Email sent successfully!"
  except Exception as e:
    return f"Failed to send email: {e}"