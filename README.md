# Ricerca Annunci Danza 🩰

Script Python che cerca annunci di lavoro e audizioni nel mondo della danza (ballerini e insegnanti),
riassume i risultati con l’AI e invia un report via email.

## Come funziona
- Cerca annunci da Indeed, LinkedIn, Subito, ecc.
- Riassume con GPT-4o-mini
- Invia report giornaliero via email

## Configurazione
Crea un file `.env` con:

EMAIL_FROM=tuamail@gmail.com
EMAIL_PASS=tuapasswordapp
EMAIL_TO=destinatario@gmail.com
OPENAI_API_KEY=chiave_api_openai

