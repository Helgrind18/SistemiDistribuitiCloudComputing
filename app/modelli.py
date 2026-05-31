from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.connessione_database import BaseModelli


class Portafoglio(BaseModelli):
    """Portafoglio personale contenente uno o più titoli."""

    __tablename__ = "portafogli"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    nome: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    descrizione: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    creato_il: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    aggiornato_il: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    titoli_posseduti: Mapped[list[TitoloPosseduto]] = relationship(
        back_populates="portafoglio",
        cascade="all, delete-orphan",
    )

    importazioni: Mapped[list[Importazione]] = relationship(
        back_populates="portafoglio",
        cascade="all, delete-orphan",
    )


class TitoloPosseduto(BaseModelli):
    """Titolo azionario presente in un portafoglio."""

    __tablename__ = "titoli_posseduti"

    __table_args__ = (
        UniqueConstraint(
            "portafoglio_id",
            "ticker",
            name="uq_titoli_posseduti_portafoglio_ticker",
        ),
        CheckConstraint(
            "quantita > 0",
            name="ck_titoli_posseduti_quantita_positiva",
        ),
        CheckConstraint(
            "prezzo_medio_acquisto >= 0",
            name="ck_titoli_posseduti_prezzo_non_negativo",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    portafoglio_id: Mapped[int] = mapped_column(
        ForeignKey("portafogli.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    ticker: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
    )

    quantita: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        nullable=False,
    )

    prezzo_medio_acquisto: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        nullable=False,
    )

    data_acquisto: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    settore: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    mercato: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    creato_il: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    aggiornato_il: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    portafoglio: Mapped[Portafoglio] = relationship(
        back_populates="titoli_posseduti",
    )


class Importazione(BaseModelli):
    """Caricamento di un file CSV oppure JSON."""

    __tablename__ = "importazioni"

    __table_args__ = (
        CheckConstraint(
            "formato_file IN ('csv', 'json')",
            name="ck_importazioni_formato_file",
        ),
        CheckConstraint(
            "stato IN ('in_attesa', 'completata', 'fallita')",
            name="ck_importazioni_stato",
        ),
        CheckConstraint(
            "righe_totali >= 0",
            name="ck_importazioni_righe_totali_non_negative",
        ),
        CheckConstraint(
            "righe_importate >= 0",
            name="ck_importazioni_righe_importate_non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    portafoglio_id: Mapped[int] = mapped_column(
        ForeignKey("portafogli.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    nome_file_originale: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    formato_file: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    percorso_archiviazione: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    stato: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="in_attesa",
    )

    righe_totali: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    righe_importate: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    creato_il: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    portafoglio: Mapped[Portafoglio] = relationship(
        back_populates="importazioni",
    )

    errori: Mapped[list[ErroreImportazione]] = relationship(
        back_populates="importazione",
        cascade="all, delete-orphan",
    )


class ErroreImportazione(BaseModelli):
    """Problema rilevato durante la validazione di una riga importata."""

    __tablename__ = "errori_importazione"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    importazione_id: Mapped[int] = mapped_column(
        ForeignKey("importazioni.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    numero_riga: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    nome_campo: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    messaggio: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    dati_originali: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    creato_il: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    importazione: Mapped[Importazione] = relationship(
        back_populates="errori",
    )