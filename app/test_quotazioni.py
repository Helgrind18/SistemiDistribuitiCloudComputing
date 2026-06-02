from app.servizio_quotazioni import (
    ErroreConfigurazioneQuotazioni,
    ErroreServizioQuotazioni,
    ottieni_prezzo_corrente,
)


def esegui_test() -> None:
    """Verifica il recupero del prezzo corrente di un titolo."""

    ticker = "MSFT"

    try:
        prezzo = ottieni_prezzo_corrente(
            ticker=ticker,
        )
    except (
        ErroreConfigurazioneQuotazioni,
        ErroreServizioQuotazioni,
    ) as errore:
        print(
            f"Errore durante il recupero della quotazione: {errore}"
        )

        return

    print("Quotazione recuperata correttamente.")
    print(f"Ticker: {ticker}")
    print(f"Prezzo corrente: {prezzo}")


if __name__ == "__main__":
    esegui_test()
