import csv
import json
from io import StringIO
from pathlib import Path


def leggi_csv(contenuto: str) -> list[dict]:
    """Legge un CSV e restituisce una lista di righe."""
    lettore = csv.DictReader(
        StringIO(contenuto)
    )
    # Recupero l'intestazione del file
    if lettore.fieldnames is None:
        raise ValueError("Il file csv non contiene le intestazioni")
    return list(lettore)


def leggi_json(contenuto: str) -> list[dict]:
    """Legge un JSON e restituisce il suo contenuto."""
    try:
        return json.loads(contenuto)
    except json.JSONDecodeError as errore:
        raise ValueError(
            "Il contenuto del file JSON non è valido."
        ) from errore


def leggi_file(nome_file: str,contenuto_file: bytes,) -> list[dict]:
    """Sceglie il lettore corretto in base all'estensione del file."""

    if not contenuto_file:
        raise ValueError("Il file è vuoto")

    contenuto = contenuto_file.decode("utf-8")

    estensione = Path(nome_file).suffix.lower()

    if estensione == ".csv":
        return leggi_csv(contenuto)

    if estensione == ".json":
        return leggi_json(contenuto)

    raise ValueError("Formato non supportato. Usare un file CSV oppure JSON.")
