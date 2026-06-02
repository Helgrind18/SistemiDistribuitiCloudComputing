from pathlib import Path

from sqlalchemy import select

from app.connessione_database import SessioneLocale
from app.modelli import (
    Importazione,
    Portafoglio,
    TitoloPosseduto,
)
from app.servizio_importazione import importa_file_in_portafoglio


NOME_PORTAFOGLIO_TEST = "Portafoglio test importazione semplice"


def leggi_file_esempio(
    nome_file: str,
) -> bytes:
    """Legge un file dalla cartella esempi."""

    cartella_progetto = (
        Path(__file__)
        .resolve()
        .parent
        .parent
    )

    percorso_file = (
        cartella_progetto
        / "esempi"
        / nome_file
    )

    return percorso_file.read_bytes()


def elimina_vecchi_dati_test() -> None:
    """Elimina eventuali portafogli creati da test precedenti."""

    with SessioneLocale.begin() as sessione:
        portafogli = sessione.scalars(
            select(Portafoglio).where(
                Portafoglio.nome == NOME_PORTAFOGLIO_TEST
            )
        ).all()

        for portafoglio in portafogli:
            sessione.delete(
                portafoglio
            )


def crea_portafoglio_test() -> int:
    """Crea un portafoglio vuoto e restituisce il suo id."""

    with SessioneLocale.begin() as sessione:
        portafoglio = Portafoglio(
            nome=NOME_PORTAFOGLIO_TEST,
            descrizione="Portafoglio temporaneo usato per il test.",
        )

        sessione.add(
            portafoglio
        )

        sessione.flush()

        return portafoglio.id


def prova_importazione_valida(
    portafoglio_id: int,
) -> None:
    """Importa un CSV corretto."""

    with SessioneLocale.begin() as sessione:
        importazione = importa_file_in_portafoglio(
            sessione=sessione,
            portafoglio_id=portafoglio_id,
            nome_file="portafoglio_valido.csv",
            contenuto_file=leggi_file_esempio(
                "portafoglio_valido.csv"
            ),
        )

        print("\nImportazione valida:")
        print(f"  stato={importazione.stato}")
        print(f"  righe_importate={importazione.righe_importate}")


def prova_importazione_non_valida(
    portafoglio_id: int,
) -> None:
    """Verifica che un CSV errato venga rifiutato."""

    print("\nImportazione non valida:")

    try:
        with SessioneLocale.begin() as sessione:
            importa_file_in_portafoglio(
                sessione=sessione,
                portafoglio_id=portafoglio_id,
                nome_file="portafoglio_non_valido.csv",
                contenuto_file=leggi_file_esempio(
                    "portafoglio_non_valido.csv"
                ),
            )
    except ValueError as errore:
        print(f"  rifiutata correttamente: {errore}")
        return

    raise RuntimeError(
        "Errore: il file non valido è stato accettato."
    )


def prova_importazione_duplicata(
    portafoglio_id: int,
) -> None:
    """Verifica che i ticker già salvati non vengano inseriti nuovamente."""

    print("\nSeconda importazione dello stesso CSV:")

    try:
        with SessioneLocale.begin() as sessione:
            importa_file_in_portafoglio(
                sessione=sessione,
                portafoglio_id=portafoglio_id,
                nome_file="portafoglio_valido.csv",
                contenuto_file=leggi_file_esempio(
                    "portafoglio_valido.csv"
                ),
            )
    except ValueError as errore:
        print(f"  rifiutata correttamente: {errore}")
        return

    raise RuntimeError(
        "Errore: i ticker duplicati sono stati accettati."
    )


def stampa_dati_salvati(
    portafoglio_id: int,
) -> None:
    """Mostra i titoli e le importazioni salvati nel database."""

    with SessioneLocale() as sessione:
        titoli = sessione.scalars(
            select(TitoloPosseduto)
            .where(
                TitoloPosseduto.portafoglio_id
                == portafoglio_id
            )
            .order_by(
                TitoloPosseduto.ticker
            )
        ).all()

        importazioni = sessione.scalars(
            select(Importazione)
            .where(
                Importazione.portafoglio_id
                == portafoglio_id
            )
            .order_by(
                Importazione.id
            )
        ).all()

        print("\nTitoli salvati nel database:")
        print(f"  totale={len(titoli)}")

        for titolo in titoli:
            print(
                f"  {titolo.ticker}: "
                f"quantita={titolo.quantita}, "
                f"prezzo={titolo.prezzo_medio_acquisto}"
            )

        print("\nImportazioni salvate nel database:")
        print(f"  totale={len(importazioni)}")

        for importazione in importazioni:
            print(
                f"  id={importazione.id}, "
                f"stato={importazione.stato}, "
                f"righe_importate={importazione.righe_importate}"
            )


def esegui_test() -> None:
    """Esegue tutte le verifiche del servizio di importazione."""

    elimina_vecchi_dati_test()

    portafoglio_id = crea_portafoglio_test()

    print(
        f"Portafoglio di test creato con id={portafoglio_id}"
    )

    prova_importazione_valida(
        portafoglio_id
    )

    prova_importazione_non_valida(
        portafoglio_id
    )

    prova_importazione_duplicata(
        portafoglio_id
    )

    stampa_dati_salvati(
        portafoglio_id
    )

    elimina_vecchi_dati_test()

    print("\nTest completato correttamente.")


if __name__ == "__main__":
    esegui_test()