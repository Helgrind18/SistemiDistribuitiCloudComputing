from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.schemi import TitoloPossedutoInIngresso

CAMPI_OBBLIGATORI = {
    "ticker",
    "quantita",
    "prezzo_medio_acquisto",
    "data_acquisto",
    "settore",
    "mercato",
}


@dataclass(slots=True)
class ErroreLettura:
    """Errore rilevato durante la lettura o la validazione del file."""

    numero_riga: int | None
    nome_campo: str | None
    messaggio: str
    dati_originali: Any = None


@dataclass(slots=True)
class RisultatoLettura:
    """Risultato complessivo della lettura di un file."""

    titoli_validi: list[TitoloPossedutoInIngresso] = field(
        default_factory=list
    )

    errori: list[ErroreLettura] = field(
        default_factory=list
    )

    @property
    def valido(self) -> bool:
        """Indica se il file può essere importato integralmente."""
        return not self.errori


def leggi_file_portafoglio(
        nome_file: str,
        contenuto_file: bytes,
) -> RisultatoLettura:
    """Legge un file CSV oppure JSON e valida tutti i titoli contenuti."""

    if not contenuto_file:
        return RisultatoLettura(
            errori=[
                ErroreLettura(
                    numero_riga=None,
                    nome_campo=None,
                    messaggio="Il file è vuoto.",
                )
            ]
        )

    try:
        testo = contenuto_file.decode("utf-8-sig")
    except UnicodeDecodeError:
        return RisultatoLettura(
            errori=[
                ErroreLettura(
                    numero_riga=None,
                    nome_campo=None,
                    messaggio="Il file deve utilizzare la codifica UTF-8.",
                )
            ]
        )

    estensione = Path(nome_file).suffix.lower()

    if estensione == ".csv":
        righe, errori = _leggi_righe_csv(testo)
    elif estensione == ".json":
        righe, errori = _leggi_righe_json(testo)
    else:
        return RisultatoLettura(
            errori=[
                ErroreLettura(
                    numero_riga=None,
                    nome_campo=None,
                    messaggio="Sono accettati soltanto file CSV oppure JSON.",
                )
            ]
        )

    if errori:
        return RisultatoLettura(errori=errori)

    return _valida_righe(righe)


def _leggi_righe_csv(
        testo: str,
) -> tuple[list[tuple[int, dict[str, Any]]], list[ErroreLettura]]:
    """Legge le righe di un CSV e controlla le intestazioni."""

    lettore = csv.DictReader(StringIO(testo))

    if lettore.fieldnames is None:
        return [], [
            ErroreLettura(
                numero_riga=None,
                nome_campo=None,
                messaggio="Il file CSV non contiene le intestazioni.",
            )
        ]

    intestazioni = [
        intestazione.strip().lower()
        for intestazione in lettore.fieldnames
    ]

    if len(intestazioni) != len(set(intestazioni)):
        return [], [
            ErroreLettura(
                numero_riga=1,
                nome_campo=None,
                messaggio="Il file CSV contiene intestazioni duplicate.",
            )
        ]

    lettore.fieldnames = intestazioni

    campi_presenti = set(intestazioni)
    campi_mancanti = CAMPI_OBBLIGATORI - campi_presenti
    campi_inattesi = campi_presenti - CAMPI_OBBLIGATORI

    errori: list[ErroreLettura] = []

    if campi_mancanti:
        errori.append(
            ErroreLettura(
                numero_riga=1,
                nome_campo=None,
                messaggio=(
                        "Mancano le seguenti colonne obbligatorie: "
                        + ", ".join(sorted(campi_mancanti))
                ),
            )
        )

    if campi_inattesi:
        errori.append(
            ErroreLettura(
                numero_riga=1,
                nome_campo=None,
                messaggio=(
                        "Sono presenti colonne non riconosciute: "
                        + ", ".join(sorted(campi_inattesi))
                ),
            )
        )

    if errori:
        return [], errori

    righe: list[tuple[int, dict[str, Any]]] = []

    for numero_riga, dati_riga in enumerate(lettore, start=2):
        if None in dati_riga:
            errori.append(
                ErroreLettura(
                    numero_riga=numero_riga,
                    nome_campo=None,
                    messaggio="La riga contiene più valori del previsto.",
                    dati_originali=dati_riga,
                )
            )

            continue

        if not any(
                str(valore).strip()
                for valore in dati_riga.values()
                if valore is not None
        ):
            continue

        righe.append((numero_riga, dati_riga))

    if not righe and not errori:
        errori.append(
            ErroreLettura(
                numero_riga=None,
                nome_campo=None,
                messaggio="Il file CSV non contiene titoli.",
            )
        )

    return righe, errori


def _leggi_righe_json(
        testo: str,
) -> tuple[list[tuple[int, dict[str, Any]]], list[ErroreLettura]]:
    """Legge una lista JSON contenente uno o più titoli."""

    try:
        dati = json.loads(testo)
    except json.JSONDecodeError as errore:
        return [], [
            ErroreLettura(
                numero_riga=errore.lineno,
                nome_campo=None,
                messaggio=f"Il contenuto JSON non è valido: {errore.msg}.",
            )
        ]

    if not isinstance(dati, list):
        return [], [
            ErroreLettura(
                numero_riga=None,
                nome_campo=None,
                messaggio="Il file JSON deve contenere una lista di titoli.",
            )
        ]

    if not dati:
        return [], [
            ErroreLettura(
                numero_riga=None,
                nome_campo=None,
                messaggio="Il file JSON non contiene titoli.",
            )
        ]

    righe: list[tuple[int, dict[str, Any]]] = []
    errori: list[ErroreLettura] = []

    for posizione, dati_titolo in enumerate(dati, start=1):
        if not isinstance(dati_titolo, dict):
            errori.append(
                ErroreLettura(
                    numero_riga=posizione,
                    nome_campo=None,
                    messaggio="Ogni elemento JSON deve essere un oggetto.",
                    dati_originali=dati_titolo,
                )
            )

            continue

        righe.append((posizione, dati_titolo))

    return righe, errori


def _valida_righe(
        righe: list[tuple[int, dict[str, Any]]],
) -> RisultatoLettura:
    """Valida i titoli e individua eventuali ticker duplicati."""

    risultato = RisultatoLettura()
    ticker_gia_presenti: set[str] = set()

    for numero_riga, dati_riga in righe:
        try:
            titolo = TitoloPossedutoInIngresso.model_validate(
                dati_riga
            )
        except ValidationError as errore:
            for dettaglio in errore.errors():
                percorso_campo = ".".join(
                    str(parte)
                    for parte in dettaglio["loc"]
                )

                risultato.errori.append(
                    ErroreLettura(
                        numero_riga=numero_riga,
                        nome_campo=percorso_campo or None,
                        messaggio=dettaglio["msg"],
                        dati_originali=dati_riga,
                    )
                )

            continue

        if titolo.ticker in ticker_gia_presenti:
            risultato.errori.append(
                ErroreLettura(
                    numero_riga=numero_riga,
                    nome_campo="ticker",
                    messaggio=(
                        f"Il ticker '{titolo.ticker}' "
                        "compare più volte nello stesso file."
                    ),
                    dati_originali=dati_riga,
                )
            )

            continue

        ticker_gia_presenti.add(titolo.ticker)
        risultato.titoli_validi.append(titolo)

    return risultato
