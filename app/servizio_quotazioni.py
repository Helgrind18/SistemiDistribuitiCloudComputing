from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation

import requests
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.modelli import (
    Portafoglio,
    QuotazioneCorrente,
    TitoloPosseduto,
)
from sqlalchemy import select
load_dotenv()

URL_API_TWELVE_DATA = os.getenv(
    "URL_API_TWELVE_DATA",
    "https://api.twelvedata.com",
).rstrip("/")

TIMEOUT_SECONDI = 10


class ErroreConfigurazioneQuotazioni(Exception):
    """Errore sollevato quando manca la chiave API."""


class ErroreServizioQuotazioni(Exception):
    """Errore sollevato quando il servizio esterno non risponde correttamente."""


def ottieni_chiave_api() -> str:
    """Restituisce la chiave API necessaria per contattare Twelve Data."""

    chiave_api = os.getenv(
        "CHIAVE_API_TWELVE_DATA"
    )

    if not chiave_api:
        raise ErroreConfigurazioneQuotazioni(
            "La variabile CHIAVE_API_TWELVE_DATA non è configurata."
        )

    return chiave_api


def ottieni_prezzo_corrente(
    ticker: str,
) -> Decimal:
    """Recupera il prezzo corrente di un ticker tramite Twelve Data."""

    ticker_normalizzato = ticker.strip().upper()

    if not ticker_normalizzato:
        raise ValueError(
            "Il ticker non può essere vuoto."
        )

    try:
        risposta = requests.get(
            f"{URL_API_TWELVE_DATA}/price",
            params={
                "symbol": ticker_normalizzato,
                "apikey": ottieni_chiave_api(),
            },
            timeout=TIMEOUT_SECONDI,
        )
    except requests.RequestException as errore:
        raise ErroreServizioQuotazioni(
            "Impossibile contattare il servizio Twelve Data."
        ) from errore

    try:
        contenuto = risposta.json()
    except requests.JSONDecodeError as errore:
        raise ErroreServizioQuotazioni(
            "Twelve Data ha restituito una risposta non valida."
        ) from errore

    if not risposta.ok:
        messaggio = contenuto.get(
            "message",
            "Errore non specificato.",
        )

        raise ErroreServizioQuotazioni(
            f"Twelve Data ha restituito un errore: {messaggio}"
        )

    if "price" not in contenuto:
        messaggio = contenuto.get(
            "message",
            "Prezzo non disponibile.",
        )

        raise ErroreServizioQuotazioni(
            f"Prezzo non recuperato per {ticker_normalizzato}: "
            f"{messaggio}"
        )

    try:
        return Decimal(
            str(contenuto["price"])
        )
    except InvalidOperation as errore:
        raise ErroreServizioQuotazioni(
            "Il prezzo restituito da Twelve Data non è numerico."
        ) from errore

def aggiorna_quotazione_corrente(
    sessione: Session,
    ticker: str,
) -> QuotazioneCorrente:
    """Recupera e salva l'ultima quotazione disponibile di un ticker."""

    ticker_normalizzato = ticker.strip().upper()

    prezzo_corrente = ottieni_prezzo_corrente(
        ticker=ticker_normalizzato,
    )

    quotazione = sessione.get(
        QuotazioneCorrente,
        ticker_normalizzato,
    )

    if quotazione is None:
        quotazione = QuotazioneCorrente(
            ticker=ticker_normalizzato,
            prezzo_corrente=prezzo_corrente,
        )

        sessione.add(quotazione)
    else:
        quotazione.prezzo_corrente = prezzo_corrente

    sessione.flush()

    return quotazione

class ErrorePortafoglioNonTrovato(Exception):
    """Errore sollevato quando il portafoglio richiesto non esiste."""


def aggiorna_quotazioni_portafoglio(
    sessione: Session,
    portafoglio_id: int,
) -> dict:
    """
    Aggiorna le quotazioni di tutti i titoli presenti in un portafoglio.

    Se un ticker non può essere aggiornato, gli altri vengono comunque
    elaborati e l'errore viene restituito nel riepilogo.
    """

    portafoglio = sessione.get(
        Portafoglio,
        portafoglio_id,
    )

    if portafoglio is None:
        raise ErrorePortafoglioNonTrovato(
            f"Il portafoglio con id={portafoglio_id} non esiste."
        )

    titoli = sessione.scalars(
        select(TitoloPosseduto)
        .where(
            TitoloPosseduto.portafoglio_id
            == portafoglio_id
        )
        .order_by(TitoloPosseduto.ticker)
    ).all()

    ticker_aggiornati: list[str] = []
    errori: list[dict[str, str]] = []

    for titolo in titoli:
        try:
            aggiorna_quotazione_corrente(
                sessione=sessione,
                ticker=titolo.ticker,
            )

            ticker_aggiornati.append(
                titolo.ticker
            )
        except (
            ErroreConfigurazioneQuotazioni,
            ErroreServizioQuotazioni,
        ) as errore:
            errori.append(
                {
                    "ticker": titolo.ticker,
                    "messaggio": str(errore),
                }
            )

    return {
        "portafoglio_id": portafoglio_id,
        "ticker_totali": len(titoli),
        "ticker_aggiornati": ticker_aggiornati,
        "errori": errori,
    }
def calcola_riepilogo_portafoglio(
    sessione: Session,
    portafoglio_id: int,
) -> dict:
    """
    Calcola il riepilogo finanziario utilizzando le ultime quotazioni
    disponibili nel database.
    """

    portafoglio = sessione.get(
        Portafoglio,
        portafoglio_id,
    )

    if portafoglio is None:
        raise ErrorePortafoglioNonTrovato(
            f"Il portafoglio con id={portafoglio_id} non esiste."
        )

    titoli = sessione.scalars(
        select(TitoloPosseduto)
        .where(
            TitoloPosseduto.portafoglio_id
            == portafoglio_id
        )
        .order_by(TitoloPosseduto.ticker)
    ).all()

    capitale_investito_totale = Decimal("0")
    capitale_investito_quotato = Decimal("0")
    valore_corrente_totale = Decimal("0")

    dettagli_titoli: list[dict] = []
    quotazioni_mancanti: list[str] = []

    for titolo in titoli:
        capitale_investito = (
            titolo.quantita
            * titolo.prezzo_medio_acquisto
        )

        capitale_investito_totale += capitale_investito

        quotazione = sessione.get(
            QuotazioneCorrente,
            titolo.ticker,
        )

        if quotazione is None:
            quotazioni_mancanti.append(
                titolo.ticker
            )

            dettagli_titoli.append(
                {
                    "ticker": titolo.ticker,
                    "quantita": str(titolo.quantita),
                    "prezzo_medio_acquisto": str(
                        titolo.prezzo_medio_acquisto
                    ),
                    "capitale_investito": str(
                        capitale_investito
                    ),
                    "prezzo_corrente": None,
                    "valore_corrente": None,
                    "guadagno_perdita": None,
                    "variazione_percentuale": None,
                    "recuperata_il": None,
                }
            )

            continue

        capitale_investito_quotato += capitale_investito

        valore_corrente = (
            titolo.quantita
            * quotazione.prezzo_corrente
        )

        valore_corrente_totale += valore_corrente

        guadagno_perdita = (
            valore_corrente
            - capitale_investito
        )

        if capitale_investito == 0:
            variazione_percentuale = None
        else:
            variazione_percentuale = (
                guadagno_perdita
                / capitale_investito
                * Decimal("100")
            )

        dettagli_titoli.append(
            {
                "ticker": titolo.ticker,
                "quantita": str(titolo.quantita),
                "prezzo_medio_acquisto": str(
                    titolo.prezzo_medio_acquisto
                ),
                "capitale_investito": str(
                    capitale_investito
                ),
                "prezzo_corrente": str(
                    quotazione.prezzo_corrente
                ),
                "valore_corrente": str(
                    valore_corrente
                ),
                "guadagno_perdita": str(
                    guadagno_perdita
                ),
                "variazione_percentuale": (
                    str(variazione_percentuale)
                    if variazione_percentuale is not None
                    else None
                ),
                "recuperata_il": (
                    quotazione.recuperata_il.isoformat()
                    if quotazione.recuperata_il is not None
                    else None
                ),
            }
        )

    guadagno_perdita_totale = (
        valore_corrente_totale
        - capitale_investito_quotato
    )

    if capitale_investito_quotato == 0:
        variazione_percentuale_totale = None
    else:
        variazione_percentuale_totale = (
            guadagno_perdita_totale
            / capitale_investito_quotato
            * Decimal("100")
        )

    return {
        "portafoglio_id": portafoglio.id,
        "nome_portafoglio": portafoglio.nome,
        "riepilogo_completo": not quotazioni_mancanti,
        "quotazioni_mancanti": quotazioni_mancanti,
        "capitale_investito_totale": str(
            capitale_investito_totale
        ),
        "capitale_investito_quotato": str(
            capitale_investito_quotato
        ),
        "valore_corrente_totale": str(
            valore_corrente_totale
        ),
        "guadagno_perdita_totale": str(
            guadagno_perdita_totale
        ),
        "variazione_percentuale_totale": (
            str(variazione_percentuale_totale)
            if variazione_percentuale_totale is not None
            else None
        ),
        "titoli": dettagli_titoli,
    }