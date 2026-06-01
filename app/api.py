from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dipendenze import ottieni_sessione
from app.modelli import (
    ErroreImportazione,
    Portafoglio,
    TitoloPosseduto,
)
from app.schemi import (
    PortafoglioInCreazione,
    TitoloPossedutoInIngresso,
)
from app.servizio_importazione import (
    ErroreFormatoFileNonSupportato,
    ErrorePortafoglioNonTrovato,
    importa_file_in_portafoglio,
)
from app.servizio_portafogli import (
    ErrorePortafoglioNonTrovato as ErrorePortafoglioTitoloNonTrovato,
    ErroreTickerGiaPresente,
    aggiungi_titolo_manualmente,
    crea_portafoglio,
)


applicazione = FastAPI(
    title="Gestione portafogli finanziari",
    description=(
        "API per creare portafogli e importare titoli "
        "da file CSV oppure JSON."
    ),
    version="0.1.0",
)

SessioneDatabase = Annotated[
    Session,
    Depends(ottieni_sessione),
]


@applicazione.get("/verifica-salute")
def verifica_salute() -> dict[str, str]:
    """Verifica che l'applicazione sia attiva."""

    return {
        "stato": "ok",
    }


@applicazione.post(
    "/portafogli",
    status_code=201,
)
def crea_nuovo_portafoglio(
    dati: PortafoglioInCreazione,
    sessione: SessioneDatabase,
) -> dict:
    """Crea un nuovo portafoglio."""

    portafoglio = crea_portafoglio(
        sessione=sessione,
        nome=dati.nome,
        descrizione=dati.descrizione,
    )

    return {
        "id": portafoglio.id,
        "nome": portafoglio.nome,
        "descrizione": portafoglio.descrizione,
    }


@applicazione.get("/portafogli")
def elenca_portafogli(
    sessione: SessioneDatabase,
) -> list[dict]:
    """Restituisce tutti i portafogli salvati."""

    portafogli = sessione.scalars(
        select(Portafoglio).order_by(Portafoglio.id)
    ).all()

    return [
        {
            "id": portafoglio.id,
            "nome": portafoglio.nome,
            "descrizione": portafoglio.descrizione,
        }
        for portafoglio in portafogli
    ]

@applicazione.post(
    "/portafogli/{portafoglio_id}/titoli",
    status_code=201,
)
def inserisci_titolo_manualmente(
    portafoglio_id: int,
    dati: TitoloPossedutoInIngresso,
    sessione: SessioneDatabase,
) -> dict:
    """Inserisce manualmente un titolo all'interno di un portafoglio."""

    try:
        titolo = aggiungi_titolo_manualmente(
            sessione=sessione,
            portafoglio_id=portafoglio_id,
            dati=dati,
        )
    except ErrorePortafoglioTitoloNonTrovato as errore:
        raise HTTPException(
            status_code=404,
            detail=str(errore),
        ) from errore
    except ErroreTickerGiaPresente as errore:
        raise HTTPException(
            status_code=409,
            detail=str(errore),
        ) from errore

    return {
        "id": titolo.id,
        "ticker": titolo.ticker,
        "quantita": str(titolo.quantita),
        "prezzo_medio_acquisto": str(
            titolo.prezzo_medio_acquisto
        ),
        "data_acquisto": titolo.data_acquisto,
        "settore": titolo.settore,
        "mercato": titolo.mercato,
    }
@applicazione.get("/portafogli/{portafoglio_id}/titoli")
def elenca_titoli_posseduti(
    portafoglio_id: int,
    sessione: SessioneDatabase,
) -> list[dict]:
    """Restituisce i titoli contenuti in un portafoglio."""

    portafoglio = sessione.get(
        Portafoglio,
        portafoglio_id,
    )

    if portafoglio is None:
        raise HTTPException(
            status_code=404,
            detail="Il portafoglio richiesto non esiste.",
        )

    titoli = sessione.scalars(
        select(TitoloPosseduto)
        .where(
            TitoloPosseduto.portafoglio_id
            == portafoglio_id
        )
        .order_by(TitoloPosseduto.ticker)
    ).all()

    return [
        {
            "id": titolo.id,
            "ticker": titolo.ticker,
            "quantita": str(titolo.quantita),
            "prezzo_medio_acquisto": str(
                titolo.prezzo_medio_acquisto
            ),
            "data_acquisto": titolo.data_acquisto,
            "settore": titolo.settore,
            "mercato": titolo.mercato,
        }
        for titolo in titoli
    ]


@applicazione.post(
    "/portafogli/{portafoglio_id}/importazioni",
)
async def carica_file_portafoglio(
    portafoglio_id: int,
    file: Annotated[
        UploadFile,
        File(description="File CSV oppure JSON da importare"),
    ],
    sessione: SessioneDatabase,
) -> dict:
    """Carica un file CSV oppure JSON all'interno di un portafoglio."""

    nome_file = file.filename or "file_senza_nome"
    contenuto_file = await file.read()

    dimensione_massima = 2 * 1024 * 1024

    if len(contenuto_file) > dimensione_massima:
        raise HTTPException(
            status_code=413,
            detail="Il file supera la dimensione massima di 2 MB.",
        )

    try:
        importazione = importa_file_in_portafoglio(
            sessione=sessione,
            portafoglio_id=portafoglio_id,
            nome_file=nome_file,
            contenuto_file=contenuto_file,
        )
    except ErrorePortafoglioNonTrovato as errore:
        raise HTTPException(
            status_code=404,
            detail=str(errore),
        ) from errore
    except ErroreFormatoFileNonSupportato as errore:
        raise HTTPException(
            status_code=400,
            detail=str(errore),
        ) from errore

    sessione.flush()

    errori = sessione.scalars(
        select(ErroreImportazione)
        .where(
            ErroreImportazione.importazione_id
            == importazione.id
        )
        .order_by(ErroreImportazione.id)
    ).all()

    return {
        "importazione_id": importazione.id,
        "nome_file": importazione.nome_file_originale,
        "formato_file": importazione.formato_file,
        "stato": importazione.stato,
        "righe_totali": importazione.righe_totali,
        "righe_importate": importazione.righe_importate,
        "errori": [
            {
                "numero_riga": errore.numero_riga,
                "nome_campo": errore.nome_campo,
                "messaggio": errore.messaggio,
            }
            for errore in errori
        ],
    }