from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modelli import Portafoglio, TitoloPosseduto
from app.schemi import (
    PortafoglioInCreazione,
    TitoloPossedutoInIngresso,
)


class ErrorePortafoglioNonTrovato(Exception):
    """Errore sollevato quando il portafoglio richiesto non esiste."""


class ErroreTickerGiaPresente(Exception):
    """Errore sollevato quando un ticker è già presente nel portafoglio."""


def crea_portafoglio(
    sessione: Session,
    nome: str,
    descrizione: str | None = None,
) -> Portafoglio:
    """Crea un portafoglio e lo aggiunge alla sessione corrente."""

    dati_validati = PortafoglioInCreazione(
        nome=nome,
        descrizione=descrizione,
    )

    portafoglio = Portafoglio(
        nome=dati_validati.nome,
        descrizione=dati_validati.descrizione,
    )

    sessione.add(portafoglio)
    sessione.flush()

    return portafoglio


def aggiungi_titolo_manualmente(
    sessione: Session,
    portafoglio_id: int,
    dati: TitoloPossedutoInIngresso,
) -> TitoloPosseduto:
    """Inserisce manualmente un titolo all'interno di un portafoglio."""

    portafoglio = sessione.get(
        Portafoglio,
        portafoglio_id,
    )

    if portafoglio is None:
        raise ErrorePortafoglioNonTrovato(
            f"Il portafoglio con id={portafoglio_id} non esiste."
        )

    titolo_esistente = sessione.scalar(
        select(TitoloPosseduto).where(
            TitoloPosseduto.portafoglio_id == portafoglio_id,
            TitoloPosseduto.ticker == dati.ticker,
        )
    )

    if titolo_esistente is not None:
        raise ErroreTickerGiaPresente(
            f"Il ticker '{dati.ticker}' è già presente nel portafoglio."
        )

    titolo = TitoloPosseduto(
        portafoglio_id=portafoglio_id,
        ticker=dati.ticker,
        quantita=dati.quantita,
        prezzo_medio_acquisto=dati.prezzo_medio_acquisto,
        data_acquisto=dati.data_acquisto,
        settore=dati.settore,
        mercato=dati.mercato,
    )

    sessione.add(titolo)
    sessione.flush()

    return titolo