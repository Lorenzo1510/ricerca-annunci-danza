import os
import time
from datetime import datetime

from dotenv import load_dotenv
import google.generativeai as genai

# configurazione
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GIORNI_MASSIMI = int(os.getenv("GIORNI_MASSIMI", 7))

genai.configure(api_key=GOOGLE_API_KEY)


def riassumi_annuncio(testo, url, categoria):
    oggi = datetime.now().strftime("%d/%m/%Y")
    prompt = f"""
        Sei un assistente che analizza annunci di lavoro nel settore della danza.
        Categoria: {categoria}
        Data di oggi: {oggi}

        ANALISI CRITICA:
        Verifica attentamente se l'annuncio o l'audizione indicata nel testo è GIA' SCADUTA, PASSATA o CHIUSA. 
        Tieni conto della data di oggi ({oggi}). Se i termini per candidarsi sono superati, o l'audizione si è già tenuta e non ha senso candidarsi, RISPONDI ESATTAMENTE e SOLTANTO con la parola: SCARTARE

        Se invece l'annuncio è ancora valido o non c'è una data di scadenza chiara, riassumi in modo sintetico:
        - Ruolo o posizione offerta
        - Requisiti o competenze
        - Luogo o ente
        - Scadenza o modalità di candidatura (se presenti)

        IMPORTANTE ZONA MILANO: Se il luogo del lavoro o dell'audizione si trova a Milano (e provincia) o in generale in Lombardia, INIZIA la tua sintesi ASSOLUTAMENTE con il tag esatto: [MILANO]. Se la zona non è Milano/Lombardia, NON includere questo tag.

        Annuncio:
        {testo}

        Link: {url}

        Se l'annuncio è valido, rispondi in massimo 4 righe, tono professionale, senza inventare dati mancanti.
    """
    max_retries = 3
    base_delay = 14 # tempo di attesa base per non sforare le 5 RPM del tier free

    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            risposta = model.generate_content(
                prompt.strip(),
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=150,
                    temperature=0.6,
                )
            )
            time.sleep(2) # Pausa di 2 sec per ammorbidire un po' i rate limit sul lungo termine
            return risposta.text.strip()
        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "quota" in error_msg:
                wait_time = base_delay * (2 ** attempt)
                print(f"⏳ Quota Gemini (429) superata. Attendo {wait_time} secondi (tentativo {attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
            else:
                print("⚠️ Errore Gemini:", e)
                return testo

    print("❌ Impossibile analizzare questo annuncio per ripetuti errori di quota API.")
    return testo

# === CREA REPORT ===
def crea_report(annunci):
    if not annunci:
        return "<h3>Nessuna nuova audizione trovata negli ultimi giorni.</h3>"

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.6; max-width: 800px; margin: 0 auto; }}
            h2 {{ color: #4A90E2; border-bottom: 2px solid #4A90E2; padding-bottom: 5px; }}
            h3 {{ color: #D0021B; margin-top: 30px; }}
            .annuncio {{ background: #f9f9f9; padding: 15px; margin-bottom: 20px; border-radius: 8px; border-left: 5px solid #F5A623; }}
            .annuncio-meta {{ font-size: 0.9em; color: #777; margin-top: 10px; }}
            a {{ color: #4A90E2; text-decoration: none; font-weight: bold; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <h2>🎭 Report Audizioni & Casting (ultimi {GIORNI_MASSIMI} giorni)</h2>
    """

    annunci_per_categoria = {"casting": [], "insegnante": []}

    for a in annunci:
        categoria = a.get("categoria", "casting")
        annunci_per_categoria.setdefault(categoria, []).append(a)

    annunci_validi_totali = 0

    for categoria, lista in annunci_per_categoria.items():
        milano_html = ""
        altri_html = ""
        for a in lista:
            breve = riassumi_annuncio(a["titolo"], a["url"], categoria)
            if "SCARTARE" in breve.upper() and len(breve.strip()) < 20:
                print(f"🗑️ Scartato: {a['titolo']}")
                continue
                
            annunci_validi_totali += 1
            data_str = datetime.fromisoformat(a["data"]).strftime("%d/%m/%Y")
            
            is_milano = "[MILANO]" in breve.upper()
            breve_pulito = breve.replace("[MILANO]", "").replace("[Milano]", "").replace("[milano]", "").strip()
            
            # format the summary nicely if it has newlines
            breve_html = breve_pulito.replace('\n', '<br>')
            
            annuncio_html = f"""
            <div class="annuncio">
                <p>{breve_html}</p>
                <div class="annuncio-meta">
                    📅 Trovato il: {data_str} | 🔍 Fonte: {a.get('fonte')}<br>
                    👉 <a href="{a['url']}">Vai all'annuncio originale</a>
                </div>
            </div>
            """
            
            if is_milano:
                milano_html += annuncio_html
            else:
                altri_html += annuncio_html
            
        if milano_html or altri_html:
            html += f"<h3>🩰 Sezione: {categoria.upper()}</h3>"
            if milano_html:
                html += "<h4>📌 In evidenza (Zona Milano / Dintorni)</h4>"
                html += milano_html
            if altri_html:
                if milano_html:
                    html += "<h4>🌍 Altre Zone</h4>"
                html += altri_html

    if annunci_validi_totali == 0:
        return "<h3>Tutte le audizioni trovate risultano troppo vecchie o scadute. Nessun nuovo annuncio valido.</h3>"

    html += "</body></html>"
    return html
