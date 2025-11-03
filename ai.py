import os
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

# configurazione
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GIORNI_MASSIMI = int(os.getenv("GIORNI_MASSIMI", 7))

client = OpenAI(api_key=OPENAI_API_KEY)


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
