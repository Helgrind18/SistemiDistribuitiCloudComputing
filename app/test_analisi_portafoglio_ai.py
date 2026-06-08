from app.servizio_analisi_ai import genera_analisi_portafoglio


def esegui_test() -> None:
    """Verifica la generazione del report finanziario tramite Gemini."""

    riepilogo = {
        "nome_portafoglio": "Portafoglio dimostrativo",
        "capitale_investito_totale": "3000.00",
        "valore_corrente_totale": "3400.00",
        "guadagno_perdita_totale": "400.00",
        "variazione_percentuale_totale": "13.33",
        "titoli": [
            {
                "ticker": "MSFT",
                "capitale_investito": "1500.00",
                "valore_corrente": "1650.00",
                "guadagno_perdita": "150.00",
                "variazione_percentuale": "10.00",
            },
            {
                "ticker": "NVDA",
                "capitale_investito": "1500.00",
                "valore_corrente": "1750.00",
                "guadagno_perdita": "250.00",
                "variazione_percentuale": "16.67",
            },
        ],
    }

    analisi = genera_analisi_portafoglio(
        riepilogo=riepilogo
    )

    print("Analisi generata da Gemini:")
    print()
    print(analisi)


if __name__ == "__main__":
    esegui_test()
