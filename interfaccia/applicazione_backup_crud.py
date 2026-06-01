from __future__ import annotations

import os
from datetime import date
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()

URL_API = os.getenv(
    "URL_API",
    "http://127.0.0.1:8000",
).rstrip("/")

TIMEOUT_SECONDI = 10


def invia_richiesta(
    metodo: str,
    percorso: str,
    **parametri: Any,
) -> requests.Response | None:
    """Invia una richiesta HTTP al backend FastAPI."""

    try:
        return requests.request(
            method=metodo,
            url=f"{URL_API}{percorso}",
            timeout=TIMEOUT_SECONDI,
            **parametri,
        )
    except requests.RequestException as errore:
        st.error(
            "Impossibile comunicare con il backend FastAPI. "
            f"Dettaglio: {errore}"
        )

        return None


def mostra_errore_api(
    risposta: requests.Response,
) -> None:
    """Mostra un errore restituito dal backend."""

    try:
        contenuto = risposta.json()
        dettaglio = contenuto.get(
            "detail",
            contenuto,
        )
    except ValueError:
        dettaglio = risposta.text

    st.error(
        f"Errore restituito dal backend "
        f"({risposta.status_code}): {dettaglio}"
    )


def verifica_backend() -> bool:
    """Controlla che FastAPI sia raggiungibile."""

    risposta = invia_richiesta(
        metodo="GET",
        percorso="/verifica-salute",
    )

    return risposta is not None and risposta.ok


def ottieni_portafogli() -> list[dict]:
    """Recupera i portafogli salvati."""

    risposta = invia_richiesta(
        metodo="GET",
        percorso="/portafogli",
    )

    if risposta is None:
        return []

    if not risposta.ok:
        mostra_errore_api(risposta)
        return []

    return risposta.json()


def ottieni_titoli(
    portafoglio_id: int,
) -> list[dict]:
    """Recupera i titoli di un portafoglio."""

    risposta = invia_richiesta(
        metodo="GET",
        percorso=f"/portafogli/{portafoglio_id}/titoli",
    )

    if risposta is None:
        return []

    if not risposta.ok:
        mostra_errore_api(risposta)
        return []

    return risposta.json()


def crea_portafoglio(
    nome: str,
    descrizione: str | None,
) -> None:
    """Richiede al backend la creazione di un portafoglio."""

    risposta = invia_richiesta(
        metodo="POST",
        percorso="/portafogli",
        json={
            "nome": nome,
            "descrizione": descrizione,
        },
    )

    if risposta is None:
        return

    if risposta.status_code != 201:
        mostra_errore_api(risposta)
        return

    portafoglio = risposta.json()

    st.session_state["messaggio_successo"] = (
        "Portafoglio creato correttamente: "
        f"{portafoglio['nome']}."
    )

    st.rerun()


def inserisci_titolo_manualmente(
    portafoglio_id: int,
    ticker: str,
    quantita: float,
    prezzo_medio_acquisto: float,
    data_acquisto: date,
    settore: str,
    mercato: str,
) -> None:
    """Invia al backend un titolo inserito manualmente."""

    risposta = invia_richiesta(
        metodo="POST",
        percorso=f"/portafogli/{portafoglio_id}/titoli",
        json={
            "ticker": ticker,
            "quantita": quantita,
            "prezzo_medio_acquisto": prezzo_medio_acquisto,
            "data_acquisto": data_acquisto.isoformat(),
            "settore": settore,
            "mercato": mercato,
        },
    )

    if risposta is None:
        return

    if risposta.status_code != 201:
        mostra_errore_api(risposta)
        return

    titolo = risposta.json()

    st.session_state["messaggio_successo"] = (
        f"Titolo {titolo['ticker']} inserito correttamente."
    )

    st.rerun()


def importa_file(
    portafoglio_id: int,
    file_caricato,
) -> None:
    """Invia al backend un file CSV oppure JSON."""

    risposta = invia_richiesta(
        metodo="POST",
        percorso=f"/portafogli/{portafoglio_id}/importazioni",
        files={
            "file": (
                file_caricato.name,
                file_caricato.getvalue(),
                file_caricato.type or "application/octet-stream",
            )
        },
    )

    if risposta is None:
        return

    if not risposta.ok:
        mostra_errore_api(risposta)
        return

    risultato = risposta.json()

    if risultato["stato"] == "completata":
        st.session_state["messaggio_successo"] = (
            "Importazione completata: "
            f"{risultato['righe_importate']} titoli inseriti."
        )

        st.rerun()

    st.error("Importazione fallita. Nessun titolo è stato inserito.")

    errori = risultato.get("errori", [])

    if errori:
        st.dataframe(
            errori,
            hide_index=True,
            use_container_width=True,
        )


st.set_page_config(
    page_title="Gestione portafogli finanziari",
    page_icon="📈",
    layout="wide",
)

st.title("Gestione portafogli finanziari")
st.caption("Interfaccia Streamlit collegata al backend FastAPI.")

messaggio_successo = st.session_state.pop(
    "messaggio_successo",
    None,
)

if messaggio_successo:
    st.success(messaggio_successo)

if verifica_backend():
    st.success("Backend FastAPI raggiungibile.")
else:
    st.error("Backend FastAPI non raggiungibile.")
    st.stop()

scheda_portafogli, scheda_gestione = st.tabs(
    [
        "Portafogli",
        "Gestione titoli",
    ]
)

with scheda_portafogli:
    st.header("Crea un nuovo portafoglio")

    with st.form("creazione_portafoglio"):
        nome = st.text_input(
            "Nome del portafoglio",
            max_chars=100,
        )

        descrizione = st.text_area(
            "Descrizione facoltativa",
            max_chars=500,
        )

        conferma_creazione = st.form_submit_button(
            "Crea portafoglio"
        )

        if conferma_creazione:
            if not nome.strip():
                st.warning(
                    "Inserire un nome per il portafoglio."
                )
            else:
                crea_portafoglio(
                    nome=nome.strip(),
                    descrizione=(
                        descrizione.strip()
                        if descrizione.strip()
                        else None
                    ),
                )

    st.header("Portafogli presenti")

    portafogli = ottieni_portafogli()

    if portafogli:
        st.dataframe(
            portafogli,
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info(
            "Non sono ancora presenti portafogli."
        )


with scheda_gestione:
    st.header("Gestione dei titoli posseduti")

    portafogli = ottieni_portafogli()

    if not portafogli:
        st.info(
            "Creare almeno un portafoglio prima di inserire titoli."
        )
    else:
        portafoglio_id = st.selectbox(
            "Seleziona un portafoglio",
            options=[
                portafoglio["id"]
                for portafoglio in portafogli
            ],
            format_func=lambda identificativo: next(
                (
                    f"{portafoglio['nome']} "
                    f"(id={portafoglio['id']})"
                    for portafoglio in portafogli
                    if portafoglio["id"] == identificativo
                ),
                str(identificativo),
            ),
        )

        st.subheader("Titoli presenti")

        titoli = ottieni_titoli(
            portafoglio_id=portafoglio_id,
        )

        if titoli:
            st.dataframe(
                titoli,
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info(
                "Il portafoglio selezionato non contiene ancora titoli."
            )

        colonna_inserimento, colonna_importazione = st.columns(2)

        with colonna_inserimento:
            st.subheader("Inserimento manuale")

            with st.form("inserimento_manuale"):
                ticker = st.text_input(
                    "Ticker",
                    max_chars=15,
                    placeholder="Esempio: NVDA",
                )

                quantita = st.number_input(
                    "Quantità acquistata",
                    min_value=0.000001,
                    value=1.0,
                    step=1.0,
                    format="%.6f",
                )

                prezzo_medio_acquisto = st.number_input(
                    "Prezzo medio di acquisto",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                )

                data_acquisto = st.date_input(
                    "Data di acquisto",
                    value=date.today(),
                    max_value=date.today(),
                )

                settore = st.text_input(
                    "Settore",
                    placeholder="Esempio: Technology",
                )

                mercato = st.text_input(
                    "Mercato",
                    placeholder="Esempio: NASDAQ",
                )

                conferma_inserimento = st.form_submit_button(
                    "Inserisci titolo"
                )

                if conferma_inserimento:
                    if not ticker.strip():
                        st.warning("Inserire il ticker.")
                    elif not settore.strip():
                        st.warning("Inserire il settore.")
                    elif not mercato.strip():
                        st.warning("Inserire il mercato.")
                    else:
                        inserisci_titolo_manualmente(
                            portafoglio_id=portafoglio_id,
                            ticker=ticker.strip(),
                            quantita=quantita,
                            prezzo_medio_acquisto=(
                                prezzo_medio_acquisto
                            ),
                            data_acquisto=data_acquisto,
                            settore=settore.strip(),
                            mercato=mercato.strip(),
                        )

        with colonna_importazione:
            st.subheader("Importazione da file")

            file_caricato = st.file_uploader(
                "Seleziona un file CSV oppure JSON",
                type=[
                    "csv",
                    "json",
                ],
            )

            if file_caricato is not None:
                st.write(
                    f"File selezionato: `{file_caricato.name}`"
                )

                if st.button(
                    "Importa file",
                    type="primary",
                ):
                    importa_file(
                        portafoglio_id=portafoglio_id,
                        file_caricato=file_caricato,
                    )