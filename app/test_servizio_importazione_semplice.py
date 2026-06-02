from pathlib import Path

from sqlalchemy import select

from app.connessione_database import SessioneLocale
from app.modelli import (
    Portafoglio,
    TitoloPosseduto,
)
from app.servizio_importazione import importa_file_in_portafoglio


NOME_PORTAFOGLIO_TEST = "Portafoglio test servizio importazione"


def leggi_file_esempio(
    nome_file: str,
) -> bytes:
    """Legge un file presente nella cartella esempi."""

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


def elimina_portafogli_test() -> None:
    """Elimina i portafogli creati da eventuali test precedenti."""

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
            descrizione="Usato soltanto per il test.",
        )

        sessione.add(
            portafoglio
        )

        sessione.flush()

        return portafoglio.id

def esegui_test() -> None:
    """Verifica importazione valida, file errato e ticker duplicati."""

    with SessioneLocale.begin() as sessione:
        portafoglio = Portafoglio(
            nome=NOME_PORTAFOGLIO_TEST,
            descrizione="Creato soltanto per il test.",
        )

        sessione.add(
            portafoglio
        )

        sessione.flush()

        portafoglio_id = portafoglio.id

    # Prima prova: file valido.
    with SessioneLocale.begin() as sessione:
        numero_titoli = importa_file_in_portafoglio(
            sessione=sessione,
            portafoglio_id=portafoglio_id,
            nome_file="portafoglio_valido.csv",
            contenuto_file=leggi_file_esempio(
                "portafoglio_valido.csv"
            ),
        )

        print(
            f"Titoli importati dal file valido: {numero_titoli}"
        )

    # Seconda prova: file non valido.
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
        print(
            f"File non valido rifiutato correttamente: {errore}"
        )

    # Terza prova: importazione ripetuta dello stesso file.
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
        print(
            f"Duplicati rifiutati correttamente: {errore}"
        )

    # Controlla quanti titoli sono rimasti nel database.
    with SessioneLocale.begin() as sessione:
        titoli = sessione.scalars(
            select(TitoloPosseduto)
            .where(
                TitoloPosseduto.portafoglio_id == portafoglio_id
            )
            .order_by(
                TitoloPosseduto.ticker
            )
        ).all()

        print(
            f"Titoli presenti nel database: {len(titoli)}"
        )

        for titolo in titoli:
            print(
                f"  {titolo.ticker}: "
                f"quantita={titolo.quantita}, "
                f"prezzo={titolo.prezzo_medio_acquisto}"
            )

        if len(titoli) != 3:
            raise RuntimeError(
                "Il database contiene un numero inatteso di titoli."
            )

        portafoglio = sessione.get(
            Portafoglio,
            portafoglio_id,
        )

        sessione.delete(
            portafoglio
        )

    print("Test completato correttamente.")
if __name__ == "__main__":
    esegui_test()
