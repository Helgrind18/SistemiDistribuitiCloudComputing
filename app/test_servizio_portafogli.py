from datetime import date
from decimal import Decimal

from app.connessione_database import SessioneLocale
from app.schemi import TitoloPossedutoInIngresso
from app.servizio_portafogli import (
    ErroreTickerGiaPresente,
    aggiungi_titolo_manualmente,
    crea_portafoglio,
    elimina_portafoglio,
    elimina_titolo,
    modifica_titolo,
)


def esegui_test() -> None:
    """Verifica le operazioni principali sui portafogli e sui titoli."""

    with SessioneLocale.begin() as sessione:
        # 1. Crea un portafoglio temporaneo.
        portafoglio = crea_portafoglio(
            sessione=sessione,
            nome="Portafoglio temporaneo",
            descrizione="Creato soltanto per il test.",
        )

        print(
            f"Portafoglio creato con id={portafoglio.id}"
        )

        # 2. Inserisce manualmente un titolo.
        dati_titolo = TitoloPossedutoInIngresso(
            ticker="MSFT",
            quantita=Decimal("4"),
            prezzo_medio_acquisto=Decimal("390.50"),
            data_acquisto=date(2026, 2, 10),
            settore="Technology",
            mercato="NASDAQ",
        )

        titolo = aggiungi_titolo_manualmente(
            sessione=sessione,
            portafoglio_id=portafoglio.id,
            dati=dati_titolo,
        )

        print(
            f"Titolo inserito: {titolo.ticker}, "
            f"quantita={titolo.quantita}"
        )

        # 3. Verifica che un ticker duplicato venga rifiutato.
        try:
            aggiungi_titolo_manualmente(
                sessione=sessione,
                portafoglio_id=portafoglio.id,
                dati=dati_titolo,
            )
        except ErroreTickerGiaPresente as errore:
            print(
                f"Duplicato rifiutato correttamente: {errore}"
            )
        else:
            raise RuntimeError(
                "Errore: il ticker duplicato è stato accettato."
            )

        # 4. Modifica il titolo già presente.
        dati_modificati = TitoloPossedutoInIngresso(
            ticker="MSFT",
            quantita=Decimal("6"),
            prezzo_medio_acquisto=Decimal("400.00"),
            data_acquisto=date(2026, 2, 10),
            settore="Technology",
            mercato="NASDAQ",
        )

        titolo_modificato = modifica_titolo(
            sessione=sessione,
            portafoglio_id=portafoglio.id,
            titolo_id=titolo.id,
            dati=dati_modificati,
        )

        print(
            f"Titolo modificato: {titolo_modificato.ticker}, "
            f"quantita={titolo_modificato.quantita}, "
            f"prezzo={titolo_modificato.prezzo_medio_acquisto}"
        )

        # 5. Elimina il titolo.
        elimina_titolo(
            sessione=sessione,
            portafoglio_id=portafoglio.id,
            titolo_id=titolo.id,
        )

        print("Titolo eliminato correttamente.")

        # 6. Elimina il portafoglio temporaneo.
        elimina_portafoglio(
            sessione=sessione,
            portafoglio_id=portafoglio.id,
        )

        print("Portafoglio eliminato correttamente.")

    print("Test completato correttamente.")


if __name__ == "__main__":
    esegui_test()
