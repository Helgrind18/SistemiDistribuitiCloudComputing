from app.connessione_database import SessioneLocale
from app.servizio_quotazioni import aggiorna_quotazione_corrente


def esegui_test() -> None:
    """Recupera una quotazione e la salva nel database."""

    with SessioneLocale.begin() as sessione:
        quotazione = aggiorna_quotazione_corrente(
            sessione=sessione,
            ticker="MSFT",
        )

        print("Quotazione salvata correttamente.")
        print(f"Ticker: {quotazione.ticker}")
        print(f"Prezzo corrente: {quotazione.prezzo_corrente}")
        print(f"Recuperata il: {quotazione.recuperata_il}")


if __name__ == "__main__":
    esegui_test()
