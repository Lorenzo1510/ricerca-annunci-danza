from config import SEARCH_URLS_CASTING, SEARCH_URLS_INSEGNANTE, KEYWORDS_INCLUDE, KEYWORDS_INSEGNANTE, INSTAGRAM_QUERIES_CASTING, INSTAGRAM_QUERIES_INSEGNANTE
from search_and_find import trova_annunci
from ai import crea_report
from mail_sender import invia_email

def call():
    annunci_casting = trova_annunci(
        categoria="casting",
        urls=SEARCH_URLS_CASTING,
        keywords=KEYWORDS_INCLUDE,
        hashtags=INSTAGRAM_QUERIES_CASTING
    )

    annunci_insegnante = trova_annunci(
        categoria="insegnante",
        urls=SEARCH_URLS_INSEGNANTE,
        keywords=KEYWORDS_INSEGNANTE,
        hashtags=INSTAGRAM_QUERIES_INSEGNANTE
    )

    tutti_annunci = annunci_casting + annunci_insegnante
    report = crea_report(tutti_annunci)

    invia_email(report)


# === MAIN ===
if __name__ == "__main__":
    print("🚀 Avvio ricerca annunci...")
    call()
    print("✅ Report inviato con successo!")
