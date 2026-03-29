import os
import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv


# === CONFIGURAZIONE ===
load_dotenv()

EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASS = os.getenv("EMAIL_PASS")
raw_email_to = os.getenv("EMAIL_TO", "")

# Estrae gli indirizzi pulendo eventuali parentesi quadre o spazi
lista_email = [e.strip() for e in raw_email_to.replace("[", "").replace("]", "").split(",") if e.strip()]


def invia_email(testo_report):
    if not lista_email:
        print("⚠️ Nessuna email di destinazione configurata nel parametro EMAIL_TO!")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "🩰 Report Audizioni Ballerini"
    msg["From"] = EMAIL_FROM
    # Unisce le email in un'unica stringa separata da virgola, in conformità allo standard MIME
    msg["To"] = ", ".join(lista_email)

    msg.attach(MIMEText(testo_report, "html"))
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASS)
            server.send_message(msg)
    except Exception as e:
        print("⚠️ Errore durante l'invio dell'email:", e)