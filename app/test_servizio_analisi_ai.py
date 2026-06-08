from app.servizio_analisi_ai import genera_testo


def esegui_test() -> None:
    """Verifica il collegamento con Gemini."""

    richiesta = (
        "Scrivi una frase molto breve in italiano "
        "per confermare che il servizio AI funziona."
    )

    risposta = genera_testo(
        richiesta=richiesta
    )

    print("Risposta ricevuta da Gemini:")
    print(risposta)


if __name__ == "__main__":
    esegui_test()
