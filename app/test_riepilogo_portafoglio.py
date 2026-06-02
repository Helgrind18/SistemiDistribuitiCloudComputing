from app.connessione_database import SessioneLocale
from app.servizio_quotazioni import (
    aggiorna_quotazioni_portafoglio,
    calcola_riepilogo_portafoglio,
)


PORTAFOGLIO_ID = 2


def esegui_test() -> None:
    """Aggiorna le quotazioni e calcola il riepilogo di un portafoglio."""

    with SessioneLocale.begin() as sessione:
        risultato_aggiornamento = aggiorna_quotazioni_portafoglio(
            sessione=sessione,
            portafoglio_id=PORTAFOGLIO_ID,
        )

        print("Aggiornamento quotazioni completato.")
        print(risultato_aggiornamento)

    with SessioneLocale() as sessione:
        riepilogo = calcola_riepilogo_portafoglio(
            sessione=sessione,
            portafoglio_id=PORTAFOGLIO_ID,
        )

        print("\nRiepilogo portafoglio:")
        print(
            "Capitale investito totale:",
            riepilogo["capitale_investito_totale"],
        )
        print(
            "Valore corrente totale:",
            riepilogo["valore_corrente_totale"],
        )
        print(
            "Guadagno o perdita totale:",
            riepilogo["guadagno_perdita_totale"],
        )
        print(
            "Variazione percentuale totale:",
            riepilogo["variazione_percentuale_totale"],
        )

        print("\nDettaglio titoli:")

        for titolo in riepilogo["titoli"]:
            print(titolo)


if __name__ == "__main__":
    esegui_test()
