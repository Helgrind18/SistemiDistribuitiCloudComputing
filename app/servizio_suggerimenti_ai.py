from app.catalogo_titoli import trova_titoli_simili_per_settore
from app.servizio_analisi_ai import genera_testo


def genera_suggerimenti_titoli_simili(
    ticker_riferimento: str,
    settore_riferimento: str,
    ticker_posseduti: list[str],
) -> dict[str, object]:
    """Suggerisce titoli dello stesso settore e genera una spiegazione."""

    ticker_da_escludere = {
        ticker.upper()
        for ticker in ticker_posseduti
    }

    suggerimenti = trova_titoli_simili_per_settore(
        settore=settore_riferimento,
        ticker_da_escludere=ticker_da_escludere,
    )

    if not suggerimenti:
        return {
            "ticker_riferimento": ticker_riferimento,
            "settore": settore_riferimento,
            "suggerimenti": [],
            "spiegazione": (
                "Non sono disponibili altri titoli dello stesso settore "
                "nel catalogo dimostrativo."
            ),
        }

    elenco_suggerimenti = "\n".join(
        (
            f"- {titolo['ticker']}: "
            f"{titolo['nome']}, "
            f"settore {titolo['settore']}, "
            f"mercato {titolo['mercato']}."
        )
        for titolo in suggerimenti
    )

    richiesta = (
        "Scrivi una breve spiegazione in italiano dei titoli simili "
        "elencati di seguito.\n"
        "I titoli sono stati selezionati dall'applicazione perché "
        "appartengono allo stesso settore del titolo di riferimento.\n"
        "Non aggiungere altri ticker.\n"
        "Non inventare dati finanziari, rendimenti o previsioni.\n"
        "Non fornire consigli di acquisto o vendita.\n"
        "Concludi specificando che i suggerimenti hanno finalità "
        "esplorative e non costituiscono consulenza finanziaria.\n\n"
        f"Titolo di riferimento: {ticker_riferimento}\n"
        f"Settore: {settore_riferimento}\n\n"
        "Titoli simili:\n"
        f"{elenco_suggerimenti}"
    )

    spiegazione = genera_testo(
        richiesta=richiesta
    )

    return {
        "ticker_riferimento": ticker_riferimento,
        "settore": settore_riferimento,
        "suggerimenti": suggerimenti,
        "spiegazione": spiegazione,
    }
