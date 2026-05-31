from pydantic import ValidationError

from app.schemi import TitoloPossedutoInIngresso


def verifica_titolo_valido() -> None:
    """Controlla la normalizzazione di un titolo corretto."""
    titolo = TitoloPossedutoInIngresso.model_validate(
        {
            "ticker": "  msft ",
            "quantita": "4",
            "prezzo_medio_acquisto": "390.50",
            "data_acquisto": "2026-02-10",
            "settore": "Technology",
            "mercato": " nasdaq ",
        }
    )

    print("Titolo valido:")
    print(titolo.model_dump())


def verifica_titolo_non_valido() -> None:
    """Controlla il rifiuto di una quantità negativa."""
    try:
        TitoloPossedutoInIngresso.model_validate(
            {
                "ticker": "AAPL",
                "quantita": "-3",
                "prezzo_medio_acquisto": "205.30",
                "data_acquisto": "2026-03-05",
                "settore": "Technology",
                "mercato": "NASDAQ",
            }
        )
    except ValidationError as errore:
        print("\nTitolo non valido:")
        print(errore)


if __name__ == "__main__":
    verifica_titolo_valido()
    verifica_titolo_non_valido()