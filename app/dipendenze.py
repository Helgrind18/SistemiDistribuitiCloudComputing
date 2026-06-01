from collections.abc import Generator

from sqlalchemy.orm import Session

from app.connessione_database import SessioneLocale


def ottieni_sessione() -> Generator[Session, None, None]:
    """
    Crea una sessione del database per ogni richiesta HTTP.

    Se la richiesta termina correttamente, salva le modifiche.
    In caso di errore, annulla la transazione.
    """

    with SessioneLocale() as sessione:
        try:
            yield sessione
            sessione.commit()
        except Exception:
            sessione.rollback()
            raise