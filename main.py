import os
import json
import smtplib
import requests
from datetime import datetime, timedelta
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
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
GIORNI_MASSIMI = 7

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

# === CERCA SU SITI WEB ===
def cerca_siti_web(urls, keywords, categoria):
    risultati = []
    for url in urls:
        try:
            html = requests.get(url, headers=HEADERS, timeout=15).text
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                text = a.get_text().strip().lower()
                if any(k in text for k in keywords) and not any(x in text for x in KEYWORDS_EXCLUDE):
                    link = a["href"]
                    if not link.startswith("http"):
                        link = requests.compat.urljoin(url, link)
                    risultati.append({
                        "titolo": text,
                        "url": link,
                        "fonte": "web",
                        "categoria": categoria,
                        "data": datetime.now().isoformat()
                    })
        except Exception as e:
            print(f"⚠️ Errore su {url}: {e}")
    return risultati

# === CERCA SU INSTAGRAM (via SerpAPI) ===
def cerca_instagram_via_serpapi(query_list, categoria, max_results=10):
    risultati = []
    for query in query_list:
        try:
            print(f"🔍 Cerco su Instagram (via Google): {query}")
            params = {
                "engine": "google",
                "q": f"site:instagram.com {query}",
                "num": max_results,
                "api_key": SERPAPI_KEY
            }
            r = requests.get("https://serpapi.com/search.json", params=params)
            data = r.json()
            for item in data.get("organic_results", []):
                titolo = item.get("title", "")
                link = item.get("link", "")
                if any(k in titolo.lower() for k in ["danza", "audizione", "ballet", "insegnante"]):
                    risultati.append({
                        "titolo": titolo[:120],
                        "url": link,
                        "fonte": f"instagram (via serpapi: {query})",
                        "categoria": categoria,
                        "data": datetime.now().isoformat()
                    })
        except Exception as e:
            print(f"⚠️ Errore SerpAPI {query}: {e}")
    return risultati

# === TROVA ANNUNCI COMPLETI ===
def trova_annunci(categoria, urls, keywords, hashtags):
    vecchi_annunci = carica_database()
    nuovi = []

    nuovi += cerca_siti_web(urls, keywords, categoria)
    nuovi += cerca_instagram_via_serpapi(hashtags, categoria)

    unici = []
    urls_esistenti = {a["url"] for a in vecchi_annunci}
    for a in nuovi:
        if a["url"] not in urls_esistenti:
            unici.append(a)
            urls_esistenti.add(a["url"])

    if unici:
        salva_database(vecchi_annunci + unici)

    return unici

# === GPT: RIASSUNTO ANNUNCIO ===
def riassumi_annuncio(testo, url, categoria):
    prompt = f"""
        Sei un assistente che analizza annunci di lavoro nel settore della danza.
        Categoria: {categoria}

        Riassumi in modo sintetico:
        - Ruolo o posizione offerta
        - Requisiti o competenze
        - Luogo o ente
        - Scadenza o modalità di candidatura (se presenti)

        Annuncio:
        {testo}

        Link: {url}

        Rispondi in massimo 4 righe, tono professionale, senza inventare dati mancanti.
    """
    try:
        risposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt.strip()}],
            max_tokens=150,
            temperature=0.6,
        )
        return risposta.choices[0].message.content.strip()
    except Exception as e:
        print("⚠️ Errore GPT:", e)
        return testo

# === CREA REPORT ===
def crea_report(annunci):
    if not annunci:
        return "Nessuna nuova audizione trovata negli ultimi giorni."

    report = f"🎭 **Report Audizioni (ultimi {GIORNI_MASSIMI} giorni)**\n\n"
    annunci_per_categoria = {"casting": [], "insegnante": []}

    for a in annunci:
        categoria = a.get("categoria", "casting")
        annunci_per_categoria.setdefault(categoria, []).append(a)

    for categoria, lista in annunci_per_categoria.items():
        if lista:
            report += f"### 🩰 Sezione: {categoria.upper()}\n\n"
            for a in lista:
                breve = riassumi_annuncio(a["titolo"], a["url"], categoria)
                data_str = datetime.fromisoformat(a["data"]).strftime("%d/%m/%Y")
                report += f"- {breve}\n📅 {data_str} | 👉 {a['url']} ({a.get('fonte')})\n\n"

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
    SEARCH_URLS_CASTING = [
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

    KEYWORDS_CASTING = [
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

    print("🚀 Avvio ricerca annunci...")

    annunci_casting = trova_annunci(
        categoria="casting",
        urls=SEARCH_URLS_CASTING,
        keywords=KEYWORDS_CASTING,
        hashtags=["audizione", "balletaudition", "castingdanzatori", "danza"]
    )

    annunci_insegnante = trova_annunci(
        categoria="insegnante",
        urls=SEARCH_URLS_INSEGNANTE,
        keywords=KEYWORDS_INSEGNANTE,
        hashtags=["insegnantedidanza", "danceteacher", "lezionididanza"]
    )

    tutti_annunci = annunci_casting + annunci_insegnante
    report = crea_report(tutti_annunci)

    print(report)
    invia_email(report)

    print("✅ Report inviato con successo!")
