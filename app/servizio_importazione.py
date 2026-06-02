from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.lettore_file import (
    ErroreLettura,
    RisultatoLettura,
    leggi_file_portafoglio,
)
from app.modelli import (
    ErroreImportazione,
    Importazione,
    Portafoglio,
    TitoloPosseduto,
)
from app.schemi import TitoloPossedutoInIngresso


class ErrorePortafoglioNonTrovato(Exception):
    """Errore sollevato quando il portafoglio richiesto non esiste."""


class ErroreFormatoFileNonSupportato(Exception):
    """Errore sollevato quando il file non è CSV oppure JSON."""


def importa_file_in_portafoglio(
        sessione: Session,
        portafoglio_id: int,
        nome_file: str,
        contenuto_file: bytes,
) -> Importazione:
    """
    Registra un'importazione e salva i titoli soltanto se il file
    è completamente valido.
    """

    portafoglio = sessione.get(
        Portafoglio,
        portafoglio_id,
    )

    if portafoglio is None:
        raise ErrorePortafoglioNonTrovato(
            f"Il portafoglio con id={portafoglio_id} non esiste."
        )

    formato_file = Path(nome_file).suffix.lower().removeprefix(".")

    if formato_file not in {"csv", "json"}:
        raise ErroreFormatoFileNonSupportato(
            "Sono accettati soltanto file CSV oppure JSON."
        )

    risultato = leggi_file_portafoglio(
        nome_file=nome_file,
        contenuto_file=contenuto_file,
    )

    errori = list(risultato.errori)

    if not errori:
        errori.extend(
            _trova_ticker_gia_presenti(
                sessione=sessione,
                portafoglio_id=portafoglio_id,
                titoli=risultato.titoli_validi,
            )
        )

    importazione = Importazione(
        portafoglio_id=portafoglio_id,
        nome_file_originale=nome_file,
        formato_file=formato_file,
        stato="fallita" if errori else "completata",
        righe_totali=_calcola_righe_totali(
            risultato=risultato,
            errori=errori,
        ),
        righe_importate=0,
    )

    sessione.add(importazione)
    sessione.flush()

    if errori:
        _salva_errori_importazione(
            sessione=sessione,
            importazione_id=importazione.id,
            errori=errori,
        )

        return importazione

    _salva_titoli(
        sessione=sessione,
        portafoglio_id=portafoglio_id,
        titoli=risultato.titoli_validi,
    )

    importazione.righe_importate = len(
        risultato.titoli_validi
    )

    return importazione


def _trova_ticker_gia_presenti(
        sessione: Session,
        portafoglio_id: int,
        titoli: list[TitoloPossedutoInIngresso],
) -> list[ErroreLettura]:
    """Individua i ticker già salvati nello stesso portafoglio."""

    ticker_da_importare = [
        titolo.ticker
        for titolo in titoli
    ]

    if not ticker_da_importare:
        return []

    ticker_esistenti = set(
        sessione.scalars(
            select(TitoloPosseduto.ticker).where(
                TitoloPosseduto.portafoglio_id == portafoglio_id,
                TitoloPosseduto.ticker.in_(ticker_da_importare),
            )
        ).all()
    )

    return [
        ErroreLettura(
            numero_riga=None,
            nome_campo="ticker",
            messaggio=(
                f"Il ticker '{ticker}' è già presente "
                "nel portafoglio."
            ),
            dati_originali={"ticker": ticker},
        )
        for ticker in sorted(ticker_esistenti)
    ]


def _salva_titoli(
        sessione: Session,
        portafoglio_id: int,
        titoli: list[TitoloPossedutoInIngresso],
) -> None:
    """Aggiunge alla sessione tutti i titoli validati."""

    for titolo in titoli:
        sessione.add(
            TitoloPosseduto(
                portafoglio_id=portafoglio_id,
                ticker=titolo.ticker,
                quantita=titolo.quantita,
                prezzo_medio_acquisto=(
                    titolo.prezzo_medio_acquisto
                ),
                data_acquisto=titolo.data_acquisto,
                settore=titolo.settore,
                mercato=titolo.mercato,
            )
        )


def _salva_errori_importazione(
        sessione: Session,
        importazione_id: int,
        errori: list[ErroreLettura],
) -> None:
    """Registra nel database gli errori trovati nel file."""

    for errore in errori:
        sessione.add(
            ErroreImportazione(
                importazione_id=importazione_id,
                numero_riga=errore.numero_riga,
                nome_campo=errore.nome_campo,
                messaggio=errore.messaggio,
                dati_originali=_converti_in_testo_json(
                    errore.dati_originali
                ),
            )
        )


def _calcola_righe_totali(
        risultato: RisultatoLettura,
        errori: list[ErroreLettura],
) -> int:
    """Calcola il numero complessivo di righe analizzate."""

    righe_errate = {
        errore.numero_riga
        for errore in errori
        if errore.numero_riga is not None
    }

    return len(risultato.titoli_validi) + len(righe_errate)


def _converti_in_testo_json(dati: object) -> str | None:
    """Converte i dati originali in testo JSON."""

    if dati is None:
        return None

    return json.dumps(
        dati,
        ensure_ascii=False,
        default=str,
    )
