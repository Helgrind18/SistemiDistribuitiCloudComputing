from typing import Annotated

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dipendenze import ottieni_sessione
from app.modelli import (
    Portafoglio,
    TitoloPosseduto,
)
from app.schemi import (
    PortafoglioInCreazione,
    TitoloPossedutoInIngresso,
)
from app.servizio_analisi_ai import (
    ErroreConfigurazioneAnalisiAI,
    ErroreServizioAnalisiAI,
    genera_analisi_portafoglio,
)
from app.servizio_importazione import (
    ErroreFormatoFileNonSupportato,
    ErrorePortafoglioNonTrovato as ErrorePortafoglioImportazioneNonTrovato,
    importa_file_in_portafoglio,
)
from app.servizio_portafogli import (
    ErrorePortafoglioNonTrovato as ErrorePortafoglioGestioneNonTrovato,
    ErroreTickerGiaPresente,
    ErroreTitoloNonTrovato,
    aggiungi_titolo_manualmente,
    crea_portafoglio,
    elimina_portafoglio,
    elimina_titolo,
    modifica_titolo,
)
from app.servizio_quotazioni import (
    ErroreConfigurazioneQuotazioni,
    ErrorePortafoglioNonTrovato as ErrorePortafoglioQuotazioniNonTrovato,
    ErroreServizioQuotazioni,
    aggiorna_quotazioni_portafoglio,
    calcola_riepilogo_portafoglio,
)
from app.servizio_suggerimenti_ai import genera_suggerimenti_titoli_simili

applicazione = FastAPI(
    title="Gestione portafogli finanziari",
    description=(
        "API per creare e gestire portafogli finanziari, "
        "inserire manualmente titoli e importare file CSV oppure JSON."
    ),
    version="0.3.0",
)


SessioneDatabase = Annotated[
    Session,
    Depends(ottieni_sessione),
]


def converti_portafoglio_in_dizionario(
    portafoglio: Portafoglio,
) -> dict[str, object]:
    """Converte un portafoglio in una risposta JSON."""

    return {
        "id": portafoglio.id,
        "nome": portafoglio.nome,
        "descrizione": portafoglio.descrizione,
    }


def converti_titolo_in_dizionario(
    titolo: TitoloPosseduto,
) -> dict[str, object]:
    """Converte un titolo posseduto in una risposta JSON."""

    return {
        "id": titolo.id,
        "ticker": titolo.ticker,
        "quantita": str(
            titolo.quantita
        ),
        "prezzo_medio_acquisto": str(
            titolo.prezzo_medio_acquisto
        ),
        "data_acquisto": titolo.data_acquisto,
        "settore": titolo.settore,
        "mercato": titolo.mercato,
    }


@applicazione.get("/")
def mostra_messaggio_iniziale() -> dict[str, str]:
    """Mostra un messaggio quando viene aperta la pagina principale."""

    return {
        "messaggio": (
            "API per la gestione dei portafogli finanziari attiva. "
            "Aprire /docs per utilizzare la documentazione interattiva."
        )
    }


@applicazione.get("/verifica-salute")
def verifica_salute() -> dict[str, str]:
    """Verifica che l'applicazione sia attiva."""

    return {
        "stato": "ok",
    }


@applicazione.post(
    "/portafogli",
    status_code=status.HTTP_201_CREATED,
)
def crea_nuovo_portafoglio(
    dati: PortafoglioInCreazione,
    sessione: SessioneDatabase,
) -> dict[str, object]:
    """Crea un nuovo portafoglio."""

    portafoglio = crea_portafoglio(
        sessione=sessione,
        nome=dati.nome,
        descrizione=dati.descrizione,
    )

    return converti_portafoglio_in_dizionario(
        portafoglio
    )


@applicazione.get("/portafogli")
def elenca_portafogli(
    sessione: SessioneDatabase,
) -> list[dict[str, object]]:
    """Restituisce tutti i portafogli salvati."""

    portafogli = sessione.scalars(
        select(
            Portafoglio
        ).order_by(
            Portafoglio.id
        )
    ).all()

    return [
        converti_portafoglio_in_dizionario(
            portafoglio
        )
        for portafoglio in portafogli
    ]


@applicazione.delete(
    "/portafogli/{portafoglio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def rimuovi_portafoglio(
    portafoglio_id: int,
    sessione: SessioneDatabase,
) -> Response:
    """Elimina un portafoglio e tutti i titoli associati."""

    try:
        elimina_portafoglio(
            sessione=sessione,
            portafoglio_id=portafoglio_id,
        )
    except ErrorePortafoglioGestioneNonTrovato as errore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(
                errore
            ),
        ) from errore

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


@applicazione.post(
    "/portafogli/{portafoglio_id}/titoli",
    status_code=status.HTTP_201_CREATED,
)
def inserisci_titolo_manualmente(
    portafoglio_id: int,
    dati: TitoloPossedutoInIngresso,
    sessione: SessioneDatabase,
) -> dict[str, object]:
    """Inserisce manualmente un titolo in un portafoglio."""

    try:
        titolo = aggiungi_titolo_manualmente(
            sessione=sessione,
            portafoglio_id=portafoglio_id,
            dati=dati,
        )
    except ErrorePortafoglioGestioneNonTrovato as errore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(
                errore
            ),
        ) from errore
    except ErroreTickerGiaPresente as errore:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(
                errore
            ),
        ) from errore

    return converti_titolo_in_dizionario(
        titolo
    )


@applicazione.get(
    "/portafogli/{portafoglio_id}/titoli"
)
def elenca_titoli_posseduti(
    portafoglio_id: int,
    sessione: SessioneDatabase,
) -> list[dict[str, object]]:
    """Restituisce i titoli contenuti in un portafoglio."""

    portafoglio = sessione.get(
        Portafoglio,
        portafoglio_id,
    )

    if portafoglio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Il portafoglio richiesto non esiste.",
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

    return [
        converti_titolo_in_dizionario(
            titolo
        )
        for titolo in titoli
    ]


@applicazione.put(
    "/portafogli/{portafoglio_id}/titoli/{titolo_id}",
)
def aggiorna_titolo(
    portafoglio_id: int,
    titolo_id: int,
    dati: TitoloPossedutoInIngresso,
    sessione: SessioneDatabase,
) -> dict[str, object]:
    """Modifica integralmente i dati di un titolo già presente."""

    try:
        titolo = modifica_titolo(
            sessione=sessione,
            portafoglio_id=portafoglio_id,
            titolo_id=titolo_id,
            dati=dati,
        )
    except ErrorePortafoglioGestioneNonTrovato as errore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(
                errore
            ),
        ) from errore
    except ErroreTitoloNonTrovato as errore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(
                errore
            ),
        ) from errore
    except ErroreTickerGiaPresente as errore:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(
                errore
            ),
        ) from errore

    return converti_titolo_in_dizionario(
        titolo
    )


@applicazione.delete(
    "/portafogli/{portafoglio_id}/titoli/{titolo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def rimuovi_titolo(
    portafoglio_id: int,
    titolo_id: int,
    sessione: SessioneDatabase,
) -> Response:
    """Elimina un titolo da un portafoglio."""

    try:
        elimina_titolo(
            sessione=sessione,
            portafoglio_id=portafoglio_id,
            titolo_id=titolo_id,
        )
    except ErrorePortafoglioGestioneNonTrovato as errore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(
                errore
            ),
        ) from errore
    except ErroreTitoloNonTrovato as errore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(
                errore
            ),
        ) from errore

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


@applicazione.post(
    "/portafogli/{portafoglio_id}/importazioni",
)
async def carica_file_portafoglio(
    portafoglio_id: int,
    file_caricato: Annotated[
        UploadFile,
        File(
            alias="file",
            description="File CSV oppure JSON da importare",
        ),
    ],
    sessione: SessioneDatabase,
) -> dict[str, object]:
    """Carica un file CSV oppure JSON in un portafoglio."""

    nome_file = (
        file_caricato.filename
        or "file_senza_nome"
    )

    contenuto_file = await file_caricato.read()

    dimensione_massima = 2 * 1024 * 1024

    if len(
        contenuto_file
    ) > dimensione_massima:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Il file supera la dimensione massima di 2 MB.",
        )

    try:
        numero_titoli_importati = importa_file_in_portafoglio(
            sessione=sessione,
            portafoglio_id=portafoglio_id,
            nome_file=nome_file,
            contenuto_file=contenuto_file,
        )
    except ErrorePortafoglioImportazioneNonTrovato as errore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(
                errore
            ),
        ) from errore
    except ErroreFormatoFileNonSupportato as errore:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(
                errore
            ),
        ) from errore
    except ValueError as errore:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(
                errore
            ),
        ) from errore

    return {
        "nome_file": nome_file,
        "stato": "completata",
        "righe_importate": numero_titoli_importati,
    }


@applicazione.post(
    "/portafogli/{portafoglio_id}/aggiorna-quotazioni",
)
def aggiorna_quotazioni(
    portafoglio_id: int,
    sessione: SessioneDatabase,
) -> dict:
    """Aggiorna le quotazioni dei titoli presenti in un portafoglio."""

    try:
        return aggiorna_quotazioni_portafoglio(
            sessione=sessione,
            portafoglio_id=portafoglio_id,
        )
    except ErrorePortafoglioQuotazioniNonTrovato as errore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(
                errore
            ),
        ) from errore
    except ErroreConfigurazioneQuotazioni as errore:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(
                errore
            ),
        ) from errore
    except ErroreServizioQuotazioni as errore:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(
                errore
            ),
        ) from errore


@applicazione.get(
    "/portafogli/{portafoglio_id}/riepilogo",
)
def ottieni_riepilogo_portafoglio(
    portafoglio_id: int,
    sessione: SessioneDatabase,
) -> dict:
    """Restituisce il riepilogo finanziario di un portafoglio."""

    try:
        return calcola_riepilogo_portafoglio(
            sessione=sessione,
            portafoglio_id=portafoglio_id,
        )
    except ErrorePortafoglioQuotazioniNonTrovato as errore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(
                errore
            ),
        ) from errore

@applicazione.post(
    "/portafogli/{portafoglio_id}/analisi-ai",
)
def genera_analisi_ai_portafoglio(
    portafoglio_id: int,
    sessione: SessioneDatabase,
) -> dict[str, str]:
    """Genera una breve analisi descrittiva del portafoglio tramite Gemini."""

    try:
        riepilogo = calcola_riepilogo_portafoglio(
            sessione=sessione,
            portafoglio_id=portafoglio_id,
        )

        analisi = genera_analisi_portafoglio(
            riepilogo=riepilogo,
        )
    except ErrorePortafoglioQuotazioniNonTrovato as errore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(
                errore
            ),
        ) from errore
    except ErroreServizioQuotazioni as errore:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(
                errore
            ),
        ) from errore
    except ErroreConfigurazioneAnalisiAI as errore:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(
                errore
            ),
        ) from errore
    except ErroreServizioAnalisiAI as errore:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(
                errore
            ),
        ) from errore

    return {
        "analisi": analisi,
    }

@applicazione.post(
    "/portafogli/{portafoglio_id}/titoli/{titolo_id}/suggerimenti-ai",
)
def ottieni_suggerimenti_titoli_ai(
    portafoglio_id: int,
    titolo_id: int,
    sessione: SessioneDatabase,
) -> dict[str, object]:
    """Suggerisce titoli simili per settore."""

    portafoglio = sessione.get(
        Portafoglio,
        portafoglio_id,
    )

    if portafoglio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Il portafoglio richiesto non esiste.",
        )

    titolo_riferimento = sessione.get(
        TitoloPosseduto,
        titolo_id,
    )

    if (
        titolo_riferimento is None
        or titolo_riferimento.portafoglio_id != portafoglio_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Il titolo richiesto non esiste nel portafoglio.",
        )

    titoli_posseduti = sessione.scalars(
        select(
            TitoloPosseduto
        ).where(
            TitoloPosseduto.portafoglio_id
            == portafoglio_id
        )
    ).all()

    try:
        return genera_suggerimenti_titoli_simili(
            ticker_riferimento=titolo_riferimento.ticker,
            settore_riferimento=titolo_riferimento.settore,
            ticker_posseduti=[
                titolo.ticker
                for titolo in titoli_posseduti
            ],
        )
    except ErroreConfigurazioneAnalisiAI as errore:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(
                errore
            ),
        ) from errore
    except ErroreServizioAnalisiAI as errore:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(
                errore
            ),
        ) from errore
