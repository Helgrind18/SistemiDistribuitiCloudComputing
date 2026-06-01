from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()

URL_API = os.getenv(
    "URL_API",
    "http://127.0.0.1:8000",
).rstrip("/")

TIMEOUT_SECONDI = 5


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
    """Mostra un messaggio leggibile quando il backend restituisce un errore."""

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

    if risposta is None:
        return False

    if not risposta.ok:
        mostra_errore_api(risposta)
        return False

    return True


def ottieni_portafogli() -> list[dict]:
    """Recupera i portafogli presenti nel database."""

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
    st.stop()

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

    conferma = st.form_submit_button(
        "Crea portafoglio"
    )

    if conferma:
        if not nome.strip():
            st.warning(
                "Inserire un nome per il portafoglio."
            )
        else:
            risposta = invia_richiesta(
                metodo="POST",
                percorso="/portafogli",
                json={
                    "nome": nome,
                    "descrizione": (
                        descrizione
                        if descrizione.strip()
                        else None
                    ),
                },
            )

            if risposta is not None:
                if risposta.status_code == 201:
                    portafoglio = risposta.json()

                    st.session_state[
                        "messaggio_successo"
                    ] = (
                        "Portafoglio creato correttamente: "
                        f"{portafoglio['nome']}."
                    )

                    st.rerun()
                else:
                    mostra_errore_api(risposta)

st.header("Portafogli presenti")

portafogli = ottieni_portafogli()

if portafogli:
    st.dataframe(
        portafogli,
        hide_index=True,
    )
else:
    st.info(
        "Non sono ancora presenti portafogli."
    )
