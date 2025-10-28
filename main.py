import os
import json
import smtplib
import requests
from datetime import datetime, timedelta
import locale
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

# === CONFIGURAZIONE ===
load_dotenv()

EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

SEARCH_URLS = [
    # 👯‍♂️ Ballerini e danzatori
    "https://it.indeed.com/jobs?q=ballerina+danza&sort=date",
    "https://it.indeed.com/jobs?q=danzatore&sort=date",
    "https://www.subito.it/annunci-italia/offerte-lavoro/?q=danza",
    "https://www.subito.it/annunci-italia/offerte-lavoro/?q=ballerina",
    "https://www.profilcultura.it/annuncio/Lavoro-Arti-Spettacolo",
    "https://danceeurope.net/auditions/",
    "https://www.onedanceuk.org/jobs/",
]

SEARCH_URLS_INSEGNANTE = [
    # 👩‍🏫 Insegnanti di danza
    "https://it.indeed.com/jobs?q=insegnante+di+danza&sort=date",
    "https://it.indeed.com/jobs?q=dance+teacher&l=Italy&sort=date",
    "https://it.linkedin.com/jobs/insegnante-di-danza-offerte-di-lavoro",
    "https://it.jooble.org/SearchResult?ukw=insegnante+danza",
    "https://www.profilcultura.it/annuncio/Lavoro-Arti-Spettacolo",
    "https://www.onedanceuk.org/jobs/?category=teaching",
    "https://www.tes.com/en-us/jobs/browse/performing-arts-teaching-and-lecturing",
]

# === PAROLE CHIAVE ===

KEYWORDS_INCLUDE = [
    "ballerino", "ballerina", "danzatore", "danzatrice", "danza", "compagnia di danza",
    "coreografo", "coreografa", "spettacolo di danza", "audizione danza", "balletto",
    "danza contemporanea", "danza moderna", "danza classica", "performer di danza",
    "dancer", "ballet", "ballet dancer", "contemporary dance", "modern dance",
    "choreographer", "dance company", "dance audition", "dance performance", "dance project", "dance casting"
]

KEYWORDS_EXCLUDE = [
    "attore", "attrice", "recitazione", "teatro", "film", "cinema", "cantante", "voce",
    "vocalist", "musicista", "comparse", "figurante", "modello", "modella", "pubblicità",
    "spot", "speaker", "actor", "actress", "acting", "theatre", "theater", "film", "movie",
    "singer", "vocal", "musician", "extra", "figurant", "model", "commercial", "advertisement", "casting call for actors"
]

KEYWORDS_INSEGNANTE = [
    "insegnante di danza", "insegnante danza", "docente di danza", "maestro di danza", "maestra di danza",
    "professore di danza", "professoressa di danza", "coreografo insegnante", "lezioni di danza",
    "scuola di danza cerca insegnante", "accademia di danza cerca docente",
    "insegnamento danza classica", "insegnamento danza moderna", "insegnamento hip hop",
    "insegnamento contemporaneo", "dance teacher", "dance instructor", "ballet teacher",
    "modern dance teacher", "contemporary dance teacher", "hip hop dance teacher",
    "dance school hiring", "looking for dance teacher", "dance academy hiring",
    "teach dance", "dance teaching position"
]


DB_FILE = "annunci_salvati.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# utils
def carica_database():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def salva_database(dati):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, indent=2)

def trova_annunci(keywords_include: list, urls: list, keywords_exclude: list = KEYWORDS_EXCLUDE):
    try:
        locale.setlocale(locale.LC_TIME, "it_IT.UTF-8")
    except:
        pass

    vecchi_annunci = carica_database()
    nuovi_annunci = []
    limite = datetime.now() - timedelta(days=14)  # ultimi 14 giorni

    for url in urls:
        try:
            print(f"🔍 Scansione: {url}")
            try:
                html = requests.get(url, headers=HEADERS, timeout=30).text
            except requests.exceptions.SSLError:
                html = requests.get(url, headers=HEADERS, timeout=30, verify=False).text

            soup = BeautifulSoup(html, "html.parser")

            for a in soup.find_all("a", href=True):
                text = a.get_text().strip().lower()

                if not any(k in text for k in keywords_include):
                    continue
                if any(bad in text for bad in keywords_exclude):
                    continue

                link = a["href"]
                if not link.startswith("http"):
                    link = requests.compat.urljoin(url, link)

                if link not in [x["url"] for x in vecchi_annunci]:
                    nuovi_annunci.append({
                        "titolo": text,
                        "url": link,
                        "categoria": "Insegnante" if keywords_include == KEYWORDS_INSEGNANTE else "Ballerino"
                    })

        except Exception as e:
            print(f"⚠️ Errore su {url}: {e}")

    if nuovi_annunci:
        salva_database(vecchi_annunci + nuovi_annunci)

    return nuovi_annunci

# === FUNZIONE: riassunto AI ===
def riassumi_annuncio(testo, url, categoria):
    """
    Usa GPT per creare un riassunto breve ma informativo di un annuncio.
    Evidenzia ruolo, requisiti, luogo, scadenza e contatto (se presenti).
    """
    prompt = f"""
        Sei un assistente che analizza annunci di lavoro nel settore della danza.
        Riassumi in modo sintetico e chiaro il seguente annuncio di categoria: {categoria}.

        👉 Fornisci:
        - Ruolo o posizione offerta
        - Tipo di contratto o durata (se presente)
        - Requisiti o competenze richieste
        - Luogo o ente che offre l’opportunità
        - Scadenza o modalità di candidatura (se indicata)

        Annuncio:
        {testo}

        Link: {url}

        Scrivi la risposta in massimo **4 righe**, in tono professionale, evitando ripetizioni o frasi generiche.
        Se mancano informazioni, non inventare.
        """
    try:
        risposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt.strip()}],
            max_tokens=160,
            temperature=0.6,
        )
        return risposta.choices[0].message.content.strip()
    except Exception as e:
        print("⚠️ Errore GPT:", e)
        return testo

def crea_report(annunci):
    if not annunci:
        return "Nessuna nuova audizione trovata oggi."

    report = "🎭 **Report Audizioni trovate oggi**\n\n"
    for a in annunci:
        breve = riassumi_annuncio(a["titolo"], a["url"], a["categoria"])
        report += f"- {breve}\n👉 {a['url']}\n\n"
    return report

def invia_email(testo_report):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "🩰 Report Audizioni Ballerini"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    msg.attach(MIMEText(testo_report, "plain"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_FROM, EMAIL_PASS)
        server.send_message(msg)

# === MAIN ===
if __name__ == "__main__":
    print("Avvio ricerca annunci...")
    annunci = trova_annunci(KEYWORDS_INCLUDE, SEARCH_URLS) + trova_annunci(KEYWORDS_INSEGNANTE, SEARCH_URLS_INSEGNANTE)
    report = crea_report(annunci)
    invia_email(report)
    print("Report inviato con successo!")
