import os
import requests
from datetime import datetime

from bs4 import BeautifulSoup
from dotenv import load_dotenv

from utils import carica_database, salva_database
from config import KEYWORDS_EXCLUDE

# === CONFIGURAZIONE ===
load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

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
