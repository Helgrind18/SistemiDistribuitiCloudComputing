from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal, InvalidOperation

import requests
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalogo_titoli import CATALOGO_TITOLI
from app.modelli import (
    Portafoglio,
    QuotazioneCorrente,
    TitoloPosseduto,
)

load_dotenv()

URL_API_TWELVE_DATA = os.getenv(
    "URL_API_TWELVE_DATA",
    "https://api.twelvedata.com",
).rstrip("/")

TIMEOUT_SECONDI = 10


class ErroreConfigurazioneQuotazioni(Exception):
    """Errore sollevato quando manca la chiave API."""


class ErroreServizioQuotazioni(Exception):
    """Errore sollevato quando Twelve Data restituisce un errore."""


class ErrorePortafoglioNonTrovato(Exception):
    """Errore sollevato quando il portafoglio richiesto non esiste."""


def ottieni_chiave_api() -> str:
    """Restituisce la chiave API di Twelve Data."""

    chiave_api = os.getenv(
        "CHIAVE_API_TWELVE_DATA"
    )

    if not chiave_api:
        raise ErroreConfigurazioneQuotazioni(
            "La variabile CHIAVE_API_TWELVE_DATA non è configurata."
        )

    return chiave_api


def cerca_titoli_nel_catalogo_locale(
        testo: str,
        limite: int = 10,
) -> list[dict[str, str]]:
    """Cerca titoli nel catalogo locale usato come fallback."""

    testo_normalizzato = testo.strip().lower()

    if not testo_normalizzato:
        return []

    risultati = []

    for titolo in CATALOGO_TITOLI:
        ticker = titolo["ticker"]
        nome = titolo["nome"]

        if (
                testo_normalizzato in ticker.lower()
                or testo_normalizzato in nome.lower()
        ):
            risultati.append(
                {
                    "ticker": ticker,
                    "nome": nome,
                    "mercato": titolo["mercato"],
                    "paese": "United States",
                    "tipo_strumento": "Azione",
                    "settore": titolo["settore"],
                }
            )

    return risultati[:limite]


def crea_risposta_ricerca_locale(
        testo: str,
        limite: int,
        messaggio: str,
) -> dict[str, object]:
    """Restituisce i risultati locali quando Twelve Data non è disponibile."""

    return {
        "origine": "catalogo_locale",
        "messaggio": messaggio,
        "risultati": cerca_titoli_nel_catalogo_locale(
            testo=testo,
            limite=limite,
        ),
    }


def calcola_priorita_risultato_ricerca(
        risultato: dict[str, str],
        testo: str,
        ticker_catalogo: set[str],
) -> tuple:
    """Definisce l'ordine dei risultati mostrati all'utente."""

    testo_normalizzato = testo.strip().lower()

    ticker = risultato["ticker"].strip().upper()
    nome = risultato["nome"].strip().lower()
    paese = risultato["paese"].strip().lower()
    mercato = risultato["mercato"].strip().upper()
    tipo_strumento = risultato["tipo_strumento"].strip().lower()

    return (
        0 if ticker.lower() == testo_normalizzato else 1,
        0 if ticker in ticker_catalogo else 1,
        0 if nome == testo_normalizzato else 1,
        0 if nome.startswith(testo_normalizzato) else 1,
        0 if tipo_strumento in {"common stock", "azione"} else 1,
        0 if paese == "united states" else 1,
        0 if mercato in {"NASDAQ", "NYSE"} else 1,
        ticker,
    )


def unisci_e_ordina_risultati_ricerca(
        risultati_online: list[dict[str, str]],
        risultati_locali: list[dict[str, str]],
        testo: str,
        limite: int,
) -> list[dict[str, str]]:
    """Unisce i risultati online e locali evitando duplicati."""

    risultati_per_ticker = {}

    for risultato_online in risultati_online:
        ticker = risultato_online["ticker"]

        if ticker not in risultati_per_ticker:
            risultati_per_ticker[ticker] = risultato_online

    for risultato_locale in risultati_locali:
        ticker = risultato_locale["ticker"]

        if ticker not in risultati_per_ticker:
            risultati_per_ticker[ticker] = risultato_locale
            continue

        risultato = risultati_per_ticker[
            ticker
        ]

        risultato["nome"] = risultato_locale[
            "nome"
        ]

        risultato["mercato"] = risultato_locale[
            "mercato"
        ]

        risultato["paese"] = risultato_locale[
            "paese"
        ]

        risultato["tipo_strumento"] = risultato_locale[
            "tipo_strumento"
        ]

        risultato["settore"] = risultato_locale[
            "settore"
        ]

    ticker_catalogo = {
        risultato["ticker"]
        for risultato in risultati_locali
    }

    return sorted(
        risultati_per_ticker.values(),
        key=lambda risultato: (
            calcola_priorita_risultato_ricerca(
                risultato=risultato,
                testo=testo,
                ticker_catalogo=ticker_catalogo,
            )
        ),
    )[:limite]


def cerca_titoli_per_nome_o_ticker(
        testo: str,
        limite: int = 10,
) -> dict[str, object]:
    """Cerca titoli tramite Twelve Data e integra il catalogo locale."""

    testo = testo.strip()

    if len(testo) < 2:
        raise ValueError(
            "Inserire almeno 2 caratteri per cercare un titolo."
        )

    if limite < 1 or limite > 10:
        raise ValueError(
            "Il numero massimo di risultati deve essere compreso tra 1 e 10."
        )

    risultati_locali = cerca_titoli_nel_catalogo_locale(
        testo=testo,
        limite=limite,
    )

    try:
        risposta = requests.get(
            f"{URL_API_TWELVE_DATA}/symbol_search",
            params={
                "symbol": testo,
                "outputsize": 30,
                "apikey": ottieni_chiave_api(),
            },
            timeout=TIMEOUT_SECONDI,
        )
    except (
            requests.RequestException,
            ErroreConfigurazioneQuotazioni,
    ):
        return crea_risposta_ricerca_locale(
            testo=testo,
            limite=limite,
            messaggio=(
                "Twelve Data non è temporaneamente disponibile. "
                "Sono mostrati i risultati del catalogo locale."
            ),
        )

    try:
        contenuto = risposta.json()
    except ValueError:
        return crea_risposta_ricerca_locale(
            testo=testo,
            limite=limite,
            messaggio=(
                "Twelve Data ha restituito una risposta non valida. "
                "Sono mostrati i risultati del catalogo locale."
            ),
        )

    if (
            not risposta.ok
            or not isinstance(
        contenuto,
        dict,
    )
            or contenuto.get(
        "status"
    ) == "error"
    ):
        return crea_risposta_ricerca_locale(
            testo=testo,
            limite=limite,
            messaggio=(
                "La ricerca online non è temporaneamente disponibile. "
                "Sono mostrati i risultati del catalogo locale."
            ),
        )

    dati = contenuto.get(
        "data",
        [],
    )

    if not isinstance(
            dati,
            list,
    ):
        return crea_risposta_ricerca_locale(
            testo=testo,
            limite=limite,
            messaggio=(
                "Twelve Data ha restituito una risposta non valida. "
                "Sono mostrati i risultati del catalogo locale."
            ),
        )

    settori_per_ticker = {
        titolo["ticker"].upper(): titolo["settore"]
        for titolo in CATALOGO_TITOLI
    }

    risultati_online = []

    for elemento in dati:
        if not isinstance(
                elemento,
                dict,
        ):
            continue

        ticker = str(
            elemento.get(
                "symbol",
                "",
            )
        ).strip().upper()

        if not ticker:
            continue

        nome = str(
            elemento.get(
                "instrument_name",
                ticker,
            )
        ).strip()

        mercato = str(
            elemento.get(
                "exchange",
                elemento.get(
                    "mic_code",
                    "",
                ),
            )
        ).strip()

        paese = str(
            elemento.get(
                "country",
                "",
            )
        ).strip()

        tipo_strumento = str(
            elemento.get(
                "instrument_type",
                "",
            )
        ).strip()

        risultati_online.append(
            {
                "ticker": ticker,
                "nome": nome or ticker,
                "mercato": mercato,
                "paese": paese,
                "tipo_strumento": tipo_strumento,
                "settore": settori_per_ticker.get(
                    ticker,
                    "",
                ),
            }
        )

    risultati = unisci_e_ordina_risultati_ricerca(
        risultati_online=risultati_online,
        risultati_locali=risultati_locali,
        testo=testo,
        limite=limite,
    )

    return {
        "origine": "twelve_data",
        "messaggio": None,
        "risultati": risultati,
    }


def ottieni_prezzo_corrente(
        ticker: str,
) -> Decimal:
    """Recupera il prezzo corrente di un ticker da Twelve Data."""

    ticker = ticker.strip().upper()

    if not ticker:
        raise ValueError(
            "Il ticker non può essere vuoto."
        )

    try:
        risposta = requests.get(
            f"{URL_API_TWELVE_DATA}/price",
            params={
                "symbol": ticker,
                "apikey": ottieni_chiave_api(),
            },
            timeout=TIMEOUT_SECONDI,
        )
    except requests.RequestException as errore:
        raise ErroreServizioQuotazioni(
            "Impossibile contattare Twelve Data."
        ) from errore

    try:
        contenuto = risposta.json()
    except ValueError as errore:
        raise ErroreServizioQuotazioni(
            "Twelve Data ha restituito una risposta non valida."
        ) from errore

    if not isinstance(
            contenuto,
            dict,
    ):
        raise ErroreServizioQuotazioni(
            "Twelve Data ha restituito una risposta non valida."
        )

    if not risposta.ok:
        messaggio = contenuto.get(
            "message",
            "Errore non specificato.",
        )

        raise ErroreServizioQuotazioni(
            f"Twelve Data ha restituito un errore: {messaggio}"
        )

    if "price" not in contenuto:
        raise ErroreServizioQuotazioni(
            f"Il prezzo del ticker '{ticker}' non è disponibile."
        )

    try:
        return Decimal(
            str(
                contenuto["price"]
            )
        )
    except InvalidOperation as errore:
        raise ErroreServizioQuotazioni(
            "Il prezzo restituito da Twelve Data non è numerico."
        ) from errore

def ottieni_andamento_storico_titolo(
    ticker: str,
    giorni: int = 30,
) -> dict[str, object]:
    """Recupera i prezzi di chiusura giornalieri di un titolo."""

    ticker = ticker.strip().upper()

    if not ticker:
        raise ValueError("Il ticker non può essere vuoto.")

    if giorni < 5 or giorni > 365:
        raise ValueError(
            "Il numero di giorni deve essere compreso tra 5 e 365."
        )

    try:
        risposta = requests.get(
            f"{URL_API_TWELVE_DATA}/time_series",
            params={
                "symbol": ticker,
                "interval": "1day",
                "outputsize": giorni,
                "apikey": ottieni_chiave_api(),
            },
            timeout=TIMEOUT_SECONDI,
        )
    except requests.RequestException as errore:
        raise ErroreServizioQuotazioni(
            "Impossibile contattare Twelve Data."
        ) from errore

    try:
        contenuto = risposta.json()
    except ValueError as errore:
        raise ErroreServizioQuotazioni(
            "Twelve Data ha restituito una risposta non valida."
        ) from errore

    if not isinstance(contenuto, dict):
        raise ErroreServizioQuotazioni(
            "Twelve Data ha restituito una risposta non valida."
        )

    if not risposta.ok or contenuto.get("status") == "error":
        messaggio = contenuto.get(
            "message",
            "Errore non specificato.",
        )

        raise ErroreServizioQuotazioni(
            f"Twelve Data ha restituito un errore: {messaggio}"
        )

    valori = contenuto.get("values", [])

    if not isinstance(valori, list) or not valori:
        raise ErroreServizioQuotazioni(
            f"Lo storico del ticker '{ticker}' non è disponibile."
        )

    punti = []

    for valore in reversed(valori):
        if not isinstance(valore, dict):
            continue

        data = str(
            valore.get("datetime", "")
        ).strip()

        prezzo_chiusura = valore.get("close")
        volume = valore.get("volume")

        if not data or prezzo_chiusura is None:
            continue

        try:
            prezzo_chiusura_numerico = Decimal(
                str(prezzo_chiusura)
            )
        except InvalidOperation as errore:
            raise ErroreServizioQuotazioni(
                "Twelve Data ha restituito un prezzo storico non valido."
            ) from errore
        try:
            volume_numerico = (
                int(
                    Decimal(
                        str(
                            volume
                        )
                    )
                )
                if volume is not None
                else None
            )
        except InvalidOperation as errore:
            raise ErroreServizioQuotazioni(
                "Twelve Data ha restituito un volume storico non valido."
            ) from errore

        punti.append(
            {
                "data": data,
                "prezzo_chiusura": float(
                    prezzo_chiusura_numerico
                ),
                "volume": volume_numerico,
            }
        )

    if not punti:
        raise ErroreServizioQuotazioni(
            f"Lo storico del ticker '{ticker}' non è disponibile."
        )

    return {
        "ticker": ticker,
        "intervallo": "1day",
        "giorni_richiesti": giorni,
        "punti": punti,
    }

def aggiorna_quotazione_corrente(
        sessione: Session,
        ticker: str,
) -> QuotazioneCorrente:
    """Recupera e salva il prezzo corrente di un ticker."""

    ticker = ticker.strip().upper()

    prezzo_corrente = ottieni_prezzo_corrente(
        ticker=ticker,
    )

    quotazione = sessione.get(
        QuotazioneCorrente,
        ticker,
    )

    if quotazione is None:
        quotazione = QuotazioneCorrente(
            ticker=ticker,
            prezzo_corrente=prezzo_corrente,
        )

        sessione.add(
            quotazione
        )
    else:
        quotazione.prezzo_corrente = prezzo_corrente

    quotazione.recuperata_il = datetime.now()

    sessione.flush()

    return quotazione


def aggiorna_quotazioni_portafoglio(
        sessione: Session,
        portafoglio_id: int,
) -> dict:
    """
    Aggiorna le quotazioni di tutti i titoli presenti nel portafoglio.

    Se una quotazione non può essere recuperata, la funzione termina
    immediatamente.
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
        select(
            TitoloPosseduto
        )
        .where(
            TitoloPosseduto.portafoglio_id
            == portafoglio_id
        )
        .order_by(
            TitoloPosseduto.ticker
        )
    ).all()

    ticker_aggiornati = []

    for titolo in titoli:
        aggiorna_quotazione_corrente(
            sessione=sessione,
            ticker=titolo.ticker,
        )

        ticker_aggiornati.append(
            titolo.ticker
        )

    return {
        "portafoglio_id": portafoglio_id,
        "ticker_totali": len(
            titoli
        ),
        "ticker_aggiornati": ticker_aggiornati,
        "errori": [],
    }


def calcola_riepilogo_portafoglio(
        sessione: Session,
        portafoglio_id: int,
) -> dict:
    """Calcola il riepilogo finanziario di un portafoglio."""

    portafoglio = sessione.get(
        Portafoglio,
        portafoglio_id,
    )

    if portafoglio is None:
        raise ErrorePortafoglioNonTrovato(
            f"Il portafoglio con id={portafoglio_id} non esiste."
        )

    titoli = sessione.scalars(
        select(
            TitoloPosseduto
        )
        .where(
            TitoloPosseduto.portafoglio_id
            == portafoglio_id
        )
        .order_by(
            TitoloPosseduto.ticker
        )
    ).all()

    capitale_investito_totale = Decimal(
        "0"
    )

    valore_corrente_totale = Decimal(
        "0"
    )

    dettagli_titoli = []

    for titolo in titoli:
        quotazione = sessione.get(
            QuotazioneCorrente,
            titolo.ticker,
        )

        if quotazione is None:
            raise ErroreServizioQuotazioni(
                f"La quotazione del ticker '{titolo.ticker}' "
                "non è disponibile. Aggiornare prima le quotazioni."
            )

        capitale_investito = (
                titolo.quantita
                * titolo.prezzo_medio_acquisto
        )

        valore_corrente = (
                titolo.quantita
                * quotazione.prezzo_corrente
        )

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

        capitale_investito_totale += (
            capitale_investito
        )

        valore_corrente_totale += (
            valore_corrente
        )

        dettagli_titoli.append(
            {
                "ticker": titolo.ticker,
                "quantita": str(
                    titolo.quantita
                ),
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
                    str(
                        variazione_percentuale
                    )
                    if variazione_percentuale is not None
                    else None
                ),
                "recuperata_il": (
                    quotazione.recuperata_il.isoformat()
                ),
            }
        )

    guadagno_perdita_totale = (
            valore_corrente_totale
            - capitale_investito_totale
    )

    if capitale_investito_totale == 0:
        variazione_percentuale_totale = None
    else:
        variazione_percentuale_totale = (
                guadagno_perdita_totale
                / capitale_investito_totale
                * Decimal("100")
        )

    return {
        "portafoglio_id": portafoglio.id,
        "nome_portafoglio": portafoglio.nome,
        "riepilogo_completo": True,
        "quotazioni_mancanti": [],
        "capitale_investito_totale": str(
            capitale_investito_totale
        ),
        "capitale_investito_quotato": str(
            capitale_investito_totale
        ),
        "valore_corrente_totale": str(
            valore_corrente_totale
        ),
        "guadagno_perdita_totale": str(
            guadagno_perdita_totale
        ),
        "variazione_percentuale_totale": (
            str(
                variazione_percentuale_totale
            )
            if variazione_percentuale_totale is not None
            else None
        ),
        "titoli": dettagli_titoli,
    }
