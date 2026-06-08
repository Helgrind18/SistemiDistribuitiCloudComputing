from app.servizio_suggerimenti_ai import (
    genera_suggerimenti_titoli_simili,
)


def esegui_test() -> None:
    """Verifica i suggerimenti per settore e la spiegazione di Gemini."""

    risultato = genera_suggerimenti_titoli_simili(
        ticker_riferimento="AAPL",
        settore_riferimento="Technology",
        ticker_posseduti=[
            "AAPL",
            "MSFT",
            "NVDA",
        ],
    )

    print("Titolo di riferimento:")
    print(
        risultato["ticker_riferimento"]
    )

    print("\nSettore:")
    print(
        risultato["settore"]
    )

    print("\nTitoli simili:")
    for titolo in risultato["suggerimenti"]:
        print(
            f"  {titolo['ticker']}: "
            f"{titolo['nome']} "
            f"({titolo['mercato']})"
        )

    print("\nSpiegazione generata da Gemini:")
    print(
        risultato["spiegazione"]
    )


if __name__ == "__main__":
    esegui_test()
