# Serve a controllare i dati in ingresso PRIMA di inserirli nel db. Della validazione se ne occupa pydantic

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PortafoglioInCreazione(BaseModel):
    """Dati necessari per creare un nuovo portafoglio."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    nome: Annotated[
        str,
        Field(min_length=1, max_length=100),
    ]

    descrizione: Annotated[
        str | None,
        Field(max_length=500),
    ] = None


class TitoloPossedutoInIngresso(BaseModel):
    """Dati di un titolo inserito manualmente oppure importato da un file."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    ticker: Annotated[
        str,
        Field(min_length=1, max_length=15),
    ]

    quantita: Annotated[
        Decimal,
        Field(gt=0, max_digits=18, decimal_places=6),
    ]

    prezzo_medio_acquisto: Annotated[
        Decimal,
        Field(ge=0, max_digits=18, decimal_places=6),
    ]

    data_acquisto: date

    settore: Annotated[
        str,
        Field(min_length=1, max_length=100),
    ]

    mercato: Annotated[
        str,
        Field(min_length=1, max_length=50),
    ]

    @field_validator("ticker", "mercato", mode="before")
    @classmethod
    def normalizza_testo_maiuscolo(cls, valore: object) -> object:
        """Elimina gli spazi esterni e converte il testo in maiuscolo."""
        if isinstance(valore, str):
            return valore.strip().upper()

        return valore

    @field_validator("data_acquisto")
    @classmethod
    def verifica_data_acquisto(cls, valore: date) -> date:
        """Impedisce di inserire una data di acquisto futura."""
        if valore > date.today():
            raise ValueError(
                "La data di acquisto non può essere successiva alla data odierna."
            )

        return valore