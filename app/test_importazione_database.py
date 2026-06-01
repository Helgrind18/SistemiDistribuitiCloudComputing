from pathlib import Path

from sqlalchemy import select

from app.connessione_database import SessioneLocale
from app.modelli import (
    ErroreImportazione,
    Importazione,
    Portafoglio,
    TitoloPosseduto,
)
from app.servizio_importazione import importa_file_in_portafoglio
from app.servizio_portafogli import crea_portafoglio


NOME_PORTAFOGLIO_TEST = "Portafoglio dimostrativo"


def leggi_file_esempio(nome_file: str) -> bytes:
    """Legge un file dalla cartella esempi."""

    cartella_progetto = Path(__file__).resolve().parent.parent
    percorso_file = cartella_progetto / "esempi" / nome_file

    return percorso_file.read_bytes()


def elimina_dati_test_precedenti() -> None:
    """Elimina il portafoglio generato da esecuzioni precedenti."""

    with SessioneLocale.begin() as sessione:
        portafogli = sessione.scalars(
            select(Portafoglio).where(
                Portafoglio.nome == NOME_PORTAFOGLIO_TEST
            )
        ).all()

        for portafoglio in portafogli:
            sessione.delete(portafoglio)


def esegui_test() -> None:
    """Verifica il salvataggio atomico delle importazioni."""

    elimina_dati_test_precedenti()

    with SessioneLocale.begin() as sessione:
        portafoglio = crea_portafoglio(
            sessione=sessione,
            nome=NOME_PORTAFOGLIO_TEST,
            descrizione="Portafoglio usato per il test.",
        )

        portafoglio_id = portafoglio.id

        print(
            f"Portafoglio creato con id={portafoglio_id}"
        )

    with SessioneLocale.begin() as sessione:
        importazione_valida = importa_file_in_portafoglio(
            sessione=sessione,
            portafoglio_id=portafoglio_id,
            nome_file="portafoglio_valido.csv",
            contenuto_file=leggi_file_esempio(
                "portafoglio_valido.csv"
            ),
        )

        print(
            "Importazione valida:"
            f" stato={importazione_valida.stato},"
            f" righe_importate="
            f"{importazione_valida.righe_importate}"
        )

    with SessioneLocale.begin() as sessione:
        importazione_errata = importa_file_in_portafoglio(
            sessione=sessione,
            portafoglio_id=portafoglio_id,
            nome_file="portafoglio_non_valido.csv",
            contenuto_file=leggi_file_esempio(
                "portafoglio_non_valido.csv"
            ),
        )

        importazione_errata_id = importazione_errata.id

        print(
            "Importazione errata:"
            f" stato={importazione_errata.stato},"
            f" righe_importate="
            f"{importazione_errata.righe_importate}"
        )

    with SessioneLocale() as sessione:
        titoli_salvati = sessione.scalars(
            select(TitoloPosseduto).where(
                TitoloPosseduto.portafoglio_id
                == portafoglio_id
            )
        ).all()

        errori_salvati = sessione.scalars(
            select(ErroreImportazione).where(
                ErroreImportazione.importazione_id
                == importazione_errata_id
            )
        ).all()

        print(
            f"Titoli presenti nel database: "
            f"{len(titoli_salvati)}"
        )

        for titolo in titoli_salvati:
            print(
                f"  {titolo.ticker}:"
                f" quantita={titolo.quantita},"
                f" prezzo_medio="
                f"{titolo.prezzo_medio_acquisto}"
            )

        print(
            f"Errori salvati nel database: "
            f"{len(errori_salvati)}"
        )

        for errore in errori_salvati:
            print(
                f"  riga={errore.numero_riga},"
                f" campo={errore.nome_campo},"
                f" messaggio={errore.messaggio}"
            )


if __name__ == "__main__":
    esegui_test()