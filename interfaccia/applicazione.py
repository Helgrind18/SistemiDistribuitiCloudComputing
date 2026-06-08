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
TIMEOUT_ANALISI_AI_SECONDI = 30


def invia_richiesta(
    metodo: str,
    percorso: str,
    timeout: int = TIMEOUT_SECONDI,
    **parametri: Any,
) -> requests.Response | None:
    """Invia una richiesta HTTP al backend FastAPI."""

    try:
        return requests.request(
            method=metodo,
            url=f"{URL_API}{percorso}",
            timeout=timeout,
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


def salva_messaggio_successo(
    messaggio: str,
) -> None:
    """Salva un messaggio e aggiorna la pagina."""

    st.session_state["messaggio_successo"] = messaggio
    st.rerun()


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
    """Recupera i titoli contenuti in un portafoglio."""

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


def aggiorna_quotazioni_portafoglio(
    portafoglio_id: int,
) -> dict | None:
    """Richiede al backend l'aggiornamento delle quotazioni."""

    risposta = invia_richiesta(
        metodo="POST",
        percorso=(
            f"/portafogli/{portafoglio_id}"
            "/aggiorna-quotazioni"
        ),
    )

    if risposta is None:
        return None

    if not risposta.ok:
        mostra_errore_api(risposta)
        return None

    return risposta.json()


def ottieni_riepilogo_portafoglio(
    portafoglio_id: int,
) -> dict | None:
    """Recupera il riepilogo finanziario di un portafoglio."""

    risposta = invia_richiesta(
        metodo="GET",
        percorso=(
            f"/portafogli/{portafoglio_id}"
            "/riepilogo"
        ),
    )

    if risposta is None:
        return None

    if not risposta.ok:
        mostra_errore_api(risposta)
        return None

    return risposta.json()


def genera_analisi_ai_portafoglio(
    portafoglio_id: int,
) -> str | None:
    """Richiede al backend un'analisi AI del portafoglio."""

    risposta = invia_richiesta(
        metodo="POST",
        percorso=(
            f"/portafogli/{portafoglio_id}"
            "/analisi-ai"
        ),
        timeout=TIMEOUT_ANALISI_AI_SECONDI,
    )

    if risposta is None:
        return None

    if not risposta.ok:
        mostra_errore_api(risposta)
        return None

    risultato = risposta.json()

    return risultato["analisi"]


def genera_suggerimenti_ai_titoli(
    portafoglio_id: int,
    titolo_id: int,
) -> dict | None:
    """Richiede al backend titoli simili per settore."""

    risposta = invia_richiesta(
        metodo="POST",
        percorso=(
            f"/portafogli/{portafoglio_id}"
            f"/titoli/{titolo_id}"
            "/suggerimenti-ai"
        ),
        timeout=TIMEOUT_ANALISI_AI_SECONDI,
    )

    if risposta is None:
        return None

    if not risposta.ok:
        mostra_errore_api(risposta)
        return None

    return risposta.json()


def ottieni_chiave_analisi_ai(
    portafoglio_id: int,
) -> str:
    """Restituisce la chiave usata per salvare l'analisi nella sessione."""

    return f"analisi_ai_portafoglio_{portafoglio_id}"


def elimina_analisi_ai_salvata(
    portafoglio_id: int,
) -> None:
    """Elimina l'analisi AI salvata quando cambiano i dati del portafoglio."""

    st.session_state.pop(
        ottieni_chiave_analisi_ai(
            portafoglio_id=portafoglio_id,
        ),
        None,
    )


def ottieni_chiave_suggerimenti_ai(
    portafoglio_id: int,
    titolo_id: int,
) -> str:
    """Restituisce la chiave usata per salvare i suggerimenti."""

    return (
        f"suggerimenti_ai_portafoglio_{portafoglio_id}"
        f"_titolo_{titolo_id}"
    )


def elimina_suggerimenti_ai_salvati(
    portafoglio_id: int,
) -> None:
    """Elimina i suggerimenti salvati quando cambiano i titoli."""

    prefisso = (
        f"suggerimenti_ai_portafoglio_{portafoglio_id}"
        "_titolo_"
    )

    chiavi_da_eliminare = [
        chiave
        for chiave in st.session_state
        if chiave.startswith(prefisso)
    ]

    for chiave in chiavi_da_eliminare:
        st.session_state.pop(
            chiave,
            None,
        )


def elimina_risultati_ai_salvati(
    portafoglio_id: int,
) -> None:
    """Elimina analisi e suggerimenti salvati per un portafoglio."""

    elimina_analisi_ai_salvata(
        portafoglio_id=portafoglio_id,
    )

    elimina_suggerimenti_ai_salvati(
        portafoglio_id=portafoglio_id,
    )


def prepara_tabella_suggerimenti(
    suggerimenti: list[dict],
) -> list[dict]:
    """Prepara i suggerimenti per la tabella Streamlit."""

    return [
        {
            "Ticker": titolo["ticker"],
            "Nome": titolo["nome"],
            "Settore": titolo["settore"],
            "Mercato": titolo["mercato"],
        }
        for titolo in suggerimenti
    ]


def formatta_numero(
    valore: str | float | int | None,
) -> str:
    """Formatta un numero con due cifre decimali."""

    if valore is None:
        return "Non disponibile"

    numero = float(valore)

    return (
        f"{numero:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def formatta_percentuale(
    valore: str | float | int | None,
) -> str:
    """Formatta un valore percentuale."""

    if valore is None:
        return "Non disponibile"

    return f"{formatta_numero(valore)}%"


def prepara_tabella_riepilogo(
    titoli: list[dict],
) -> list[dict]:
    """Prepara i dettagli dei titoli per la tabella Streamlit."""

    return [
        {
            "Ticker": titolo["ticker"],
            "Quantità": formatta_numero(
                titolo["quantita"]
            ),
            "Prezzo medio di acquisto": formatta_numero(
                titolo["prezzo_medio_acquisto"]
            ),
            "Capitale investito": formatta_numero(
                titolo["capitale_investito"]
            ),
            "Prezzo corrente": formatta_numero(
                titolo["prezzo_corrente"]
            ),
            "Valore corrente": formatta_numero(
                titolo["valore_corrente"]
            ),
            "Guadagno / perdita": formatta_numero(
                titolo["guadagno_perdita"]
            ),
            "Variazione": formatta_percentuale(
                titolo["variazione_percentuale"]
            ),
            "Quotazione recuperata il": titolo["recuperata_il"],
        }
        for titolo in titoli
    ]


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

    salva_messaggio_successo(
        "Portafoglio creato correttamente: "
        f"{portafoglio['nome']}."
    )


def elimina_portafoglio(
    portafoglio_id: int,
) -> None:
    """Richiede al backend l'eliminazione di un portafoglio."""

    risposta = invia_richiesta(
        metodo="DELETE",
        percorso=f"/portafogli/{portafoglio_id}",
    )

    if risposta is None:
        return

    if risposta.status_code != 204:
        mostra_errore_api(risposta)
        return

    elimina_risultati_ai_salvati(
        portafoglio_id=portafoglio_id,
    )

    salva_messaggio_successo(
        "Portafoglio eliminato correttamente."
    )


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

    elimina_risultati_ai_salvati(
        portafoglio_id=portafoglio_id,
    )

    salva_messaggio_successo(
        f"Titolo {titolo['ticker']} inserito correttamente."
    )


def modifica_titolo(
    portafoglio_id: int,
    titolo_id: int,
    ticker: str,
    quantita: float,
    prezzo_medio_acquisto: float,
    data_acquisto: date,
    settore: str,
    mercato: str,
) -> None:
    """Richiede al backend la modifica di un titolo."""

    risposta = invia_richiesta(
        metodo="PUT",
        percorso=(
            f"/portafogli/{portafoglio_id}"
            f"/titoli/{titolo_id}"
        ),
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

    if risposta.status_code != 200:
        mostra_errore_api(risposta)
        return

    titolo = risposta.json()

    elimina_risultati_ai_salvati(
        portafoglio_id=portafoglio_id,
    )

    salva_messaggio_successo(
        f"Titolo {titolo['ticker']} modificato correttamente."
    )


def elimina_titolo(
    portafoglio_id: int,
    titolo_id: int,
) -> None:
    """Richiede al backend l'eliminazione di un titolo."""

    risposta = invia_richiesta(
        metodo="DELETE",
        percorso=(
            f"/portafogli/{portafoglio_id}"
            f"/titoli/{titolo_id}"
        ),
    )

    if risposta is None:
        return

    if risposta.status_code != 204:
        mostra_errore_api(risposta)
        return

    elimina_risultati_ai_salvati(
        portafoglio_id=portafoglio_id,
    )

    salva_messaggio_successo(
        "Titolo eliminato correttamente."
    )


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
                file_caricato.type
                or "application/octet-stream",
            )
        },
    )

    if risposta is None:
        return

    if not risposta.ok:
        mostra_errore_api(
            risposta
        )
        return

    risultato = risposta.json()

    elimina_risultati_ai_salvati(
        portafoglio_id=portafoglio_id,
    )

    salva_messaggio_successo(
        "Importazione completata: "
        f"{risultato['righe_importate']} titoli inseriti."
    )


def formatta_portafoglio(
    portafoglio_id: int,
    portafogli: list[dict],
) -> str:
    """Genera l'etichetta mostrata nel menu dei portafogli."""

    for portafoglio in portafogli:
        if portafoglio["id"] == portafoglio_id:
            return (
                f"{portafoglio['nome']} "
                f"(id={portafoglio['id']})"
            )

    return str(portafoglio_id)


def formatta_titolo(
    titolo_id: int,
    titoli: list[dict],
) -> str:
    """Genera l'etichetta mostrata nel menu dei titoli."""

    for titolo in titoli:
        if titolo["id"] == titolo_id:
            return (
                f"{titolo['ticker']} "
                f"(id={titolo['id']})"
            )

    return str(titolo_id)


st.set_page_config(
    page_title="Gestione portafogli finanziari",
    page_icon="📈",
    layout="wide",
)

st.title("Gestione portafogli finanziari")
st.caption(
    "Interfaccia Streamlit collegata al backend FastAPI."
)

messaggio_successo = st.session_state.pop(
    "messaggio_successo",
    None,
)

if messaggio_successo:
    st.success(
        messaggio_successo
    )

if verifica_backend():
    st.success(
        "Backend FastAPI raggiungibile."
    )
else:
    st.error(
        "Backend FastAPI non raggiungibile."
    )
    st.stop()

scheda_dashboard, scheda_portafogli, scheda_gestione = st.tabs(
    [
        "Dashboard",
        "Portafogli",
        "Gestione titoli",
    ]
)

with scheda_dashboard:
    st.header(
        "Dashboard finanziaria"
    )

    st.write(
        "Visualizza il riepilogo del portafoglio utilizzando "
        "le ultime quotazioni salvate nel database."
    )

    portafogli_dashboard = ottieni_portafogli()

    if not portafogli_dashboard:
        st.info(
            "Creare almeno un portafoglio prima di visualizzare "
            "la dashboard."
        )
    else:
        portafoglio_dashboard_id = st.selectbox(
            "Seleziona un portafoglio",
            options=[
                portafoglio["id"]
                for portafoglio in portafogli_dashboard
            ],
            format_func=lambda identificativo: (
                formatta_portafoglio(
                    identificativo,
                    portafogli_dashboard,
                )
            ),
            key="portafoglio_dashboard",
        )

        st.caption(
            "Le quotazioni vengono richieste a Twelve Data soltanto "
            "quando premi il pulsante di aggiornamento."
        )

        if st.button(
            "Aggiorna quotazioni",
            type="primary",
            key=(
                "aggiorna_quotazioni_"
                f"{portafoglio_dashboard_id}"
            ),
        ):
            with st.spinner(
                "Recupero delle quotazioni in corso..."
            ):
                risultato_aggiornamento = (
                    aggiorna_quotazioni_portafoglio(
                        portafoglio_id=portafoglio_dashboard_id,
                    )
                )

            if risultato_aggiornamento is not None:
                numero_aggiornati = len(
                    risultato_aggiornamento[
                        "ticker_aggiornati"
                    ]
                )

                elimina_risultati_ai_salvati(
                    portafoglio_id=portafoglio_dashboard_id,
                )

                st.success(
                    "Quotazioni aggiornate correttamente: "
                    f"{numero_aggiornati} ticker aggiornati."
                )

        riepilogo = ottieni_riepilogo_portafoglio(
            portafoglio_id=portafoglio_dashboard_id,
        )

        if riepilogo is not None:
            st.subheader(
                f"Riepilogo: {riepilogo['nome_portafoglio']}"
            )

            (
                colonna_capitale,
                colonna_valore,
                colonna_guadagno,
                colonna_variazione,
            ) = st.columns(
                4
            )

            with colonna_capitale:
                st.metric(
                    "Capitale investito",
                    formatta_numero(
                        riepilogo[
                            "capitale_investito_totale"
                        ]
                    ),
                )

            with colonna_valore:
                st.metric(
                    "Valore corrente",
                    formatta_numero(
                        riepilogo[
                            "valore_corrente_totale"
                        ]
                    ),
                )

            with colonna_guadagno:
                st.metric(
                    "Guadagno / perdita",
                    formatta_numero(
                        riepilogo[
                            "guadagno_perdita_totale"
                        ]
                    ),
                )

            with colonna_variazione:
                st.metric(
                    "Variazione percentuale",
                    formatta_percentuale(
                        riepilogo[
                            "variazione_percentuale_totale"
                        ]
                    ),
                )

            st.subheader(
                "Dettaglio dei titoli"
            )

            dettagli_titoli = prepara_tabella_riepilogo(
                riepilogo["titoli"]
            )

            if dettagli_titoli:
                st.dataframe(
                    dettagli_titoli,
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.info(
                    "Il portafoglio non contiene ancora titoli."
                )

            st.divider()
            st.subheader(
                "Analisi AI del portafoglio"
            )

            st.caption(
                "Gemini genera una breve analisi descrittiva usando "
                "i dati del riepilogo. Il testo ha finalità informative."
            )

            if dettagli_titoli:
                if st.button(
                    "Genera analisi AI",
                    key=(
                        "genera_analisi_ai_"
                        f"{portafoglio_dashboard_id}"
                    ),
                ):
                    with st.spinner(
                        "Generazione dell'analisi AI in corso..."
                    ):
                        analisi_ai = genera_analisi_ai_portafoglio(
                            portafoglio_id=portafoglio_dashboard_id,
                        )

                    if analisi_ai is not None:
                        st.session_state[
                            ottieni_chiave_analisi_ai(
                                portafoglio_id=portafoglio_dashboard_id,
                            )
                        ] = analisi_ai

                analisi_ai_salvata = st.session_state.get(
                    ottieni_chiave_analisi_ai(
                        portafoglio_id=portafoglio_dashboard_id,
                    )
                )

                if analisi_ai_salvata:
                    st.markdown(
                        analisi_ai_salvata
                    )
            else:
                st.info(
                    "Aggiungere almeno un titolo prima di generare "
                    "l'analisi AI."
                )

        st.divider()
        st.subheader(
            "Titoli simili per settore"
        )

        st.caption(
            "L'applicazione seleziona titoli dello stesso settore da "
            "un catalogo controllato. Gemini genera una breve "
            "spiegazione descrittiva dei risultati."
        )

        titoli_dashboard = ottieni_titoli(
            portafoglio_id=portafoglio_dashboard_id,
        )

        if titoli_dashboard:
            titolo_riferimento_id = st.selectbox(
                "Seleziona un titolo di riferimento",
                options=[
                    titolo["id"]
                    for titolo in titoli_dashboard
                ],
                format_func=lambda identificativo: (
                    formatta_titolo(
                        identificativo,
                        titoli_dashboard,
                    )
                ),
                key=(
                    "titolo_riferimento_suggerimenti_"
                    f"{portafoglio_dashboard_id}"
                ),
            )

            if st.button(
                "Genera suggerimenti AI",
                key=(
                    "genera_suggerimenti_ai_"
                    f"{portafoglio_dashboard_id}_"
                    f"{titolo_riferimento_id}"
                ),
            ):
                with st.spinner(
                    "Generazione dei suggerimenti AI in corso..."
                ):
                    risultato_suggerimenti = (
                        genera_suggerimenti_ai_titoli(
                            portafoglio_id=portafoglio_dashboard_id,
                            titolo_id=titolo_riferimento_id,
                        )
                    )

                if risultato_suggerimenti is not None:
                    st.session_state[
                        ottieni_chiave_suggerimenti_ai(
                            portafoglio_id=portafoglio_dashboard_id,
                            titolo_id=titolo_riferimento_id,
                        )
                    ] = risultato_suggerimenti

            suggerimenti_salvati = st.session_state.get(
                ottieni_chiave_suggerimenti_ai(
                    portafoglio_id=portafoglio_dashboard_id,
                    titolo_id=titolo_riferimento_id,
                )
            )

            if suggerimenti_salvati:
                suggerimenti = suggerimenti_salvati[
                    "suggerimenti"
                ]

                if suggerimenti:
                    st.dataframe(
                        prepara_tabella_suggerimenti(
                            suggerimenti
                        ),
                        hide_index=True,
                        use_container_width=True,
                    )
                else:
                    st.info(
                        "Non sono disponibili altri titoli dello stesso "
                        "settore nel catalogo dimostrativo."
                    )

                st.markdown(
                    suggerimenti_salvati["spiegazione"]
                )
        else:
            st.info(
                "Aggiungere almeno un titolo prima di generare "
                "suggerimenti."
            )


with scheda_portafogli:
    st.header(
        "Crea un nuovo portafoglio"
    )

    with st.form(
        "creazione_portafoglio"
    ):
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

    st.header(
        "Portafogli presenti"
    )

    portafogli = ottieni_portafogli()

    if portafogli:
        st.dataframe(
            portafogli,
            hide_index=True,
            use_container_width=True,
        )

        with st.expander(
            "Elimina un portafoglio",
            expanded=False,
        ):
            st.warning(
                "L'eliminazione rimuove anche i titoli associati."
            )

            portafoglio_da_eliminare_id = st.selectbox(
                "Portafoglio da eliminare",
                options=[
                    portafoglio["id"]
                    for portafoglio in portafogli
                ],
                format_func=lambda identificativo: (
                    formatta_portafoglio(
                        identificativo,
                        portafogli,
                    )
                ),
                key="portafoglio_da_eliminare",
            )

            conferma_eliminazione_portafoglio = st.checkbox(
                "Confermo di voler eliminare il portafoglio.",
                key=(
                    "conferma_eliminazione_portafoglio_"
                    f"{portafoglio_da_eliminare_id}"
                ),
            )

            if st.button(
                "Elimina portafoglio",
                disabled=(
                    not conferma_eliminazione_portafoglio
                ),
                type="primary",
            ):
                elimina_portafoglio(
                    portafoglio_id=portafoglio_da_eliminare_id,
                )
    else:
        st.info(
            "Non sono ancora presenti portafogli."
        )

with scheda_gestione:
    st.header(
        "Gestione dei titoli posseduti"
    )

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
            format_func=lambda identificativo: (
                formatta_portafoglio(
                    identificativo,
                    portafogli,
                )
            ),
            key="portafoglio_selezionato",
        )

        st.subheader(
            "Titoli presenti"
        )

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
                "Il portafoglio selezionato "
                "non contiene ancora titoli."
            )

        colonna_inserimento, colonna_importazione = st.columns(
            2
        )

        with colonna_inserimento:
            st.subheader(
                "Inserimento manuale"
            )

            with st.form(
                f"inserimento_manuale_{portafoglio_id}"
            ):
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
                        st.warning(
                            "Inserire il ticker."
                        )
                    elif not settore.strip():
                        st.warning(
                            "Inserire il settore."
                        )
                    elif not mercato.strip():
                        st.warning(
                            "Inserire il mercato."
                        )
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
            st.subheader(
                "Importazione da file"
            )

            file_caricato = st.file_uploader(
                "Seleziona un file CSV oppure JSON",
                type=[
                    "csv",
                    "json",
                ],
                key=f"file_importazione_{portafoglio_id}",
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

        if titoli:
            st.divider()
            st.subheader(
                "Modifica o elimina un titolo"
            )

            titolo_id = st.selectbox(
                "Seleziona un titolo",
                options=[
                    titolo["id"]
                    for titolo in titoli
                ],
                format_func=lambda identificativo: (
                    formatta_titolo(
                        identificativo,
                        titoli,
                    )
                ),
                key="titolo_selezionato",
            )

            titolo_selezionato = next(
                titolo
                for titolo in titoli
                if titolo["id"] == titolo_id
            )

            colonna_modifica, colonna_eliminazione = st.columns(
                [
                    2,
                    1,
                ]
            )

            with colonna_modifica:
                with st.form(
                    f"modifica_titolo_{titolo_id}"
                ):
                    ticker_modificato = st.text_input(
                        "Ticker da modificare",
                        value=titolo_selezionato["ticker"],
                        max_chars=15,
                        key=f"ticker_modificato_{titolo_id}",
                    )

                    quantita_modificata = st.number_input(
                        "Quantità aggiornata",
                        min_value=0.000001,
                        value=float(
                            titolo_selezionato["quantita"]
                        ),
                        step=1.0,
                        format="%.6f",
                        key=f"quantita_modificata_{titolo_id}",
                    )

                    prezzo_modificato = st.number_input(
                        "Prezzo medio aggiornato",
                        min_value=0.0,
                        value=float(
                            titolo_selezionato[
                                "prezzo_medio_acquisto"
                            ]
                        ),
                        step=0.01,
                        format="%.2f",
                        key=f"prezzo_modificato_{titolo_id}",
                    )

                    data_modificata = st.date_input(
                        "Data di acquisto aggiornata",
                        value=date.fromisoformat(
                            titolo_selezionato[
                                "data_acquisto"
                            ]
                        ),
                        max_value=date.today(),
                        key=f"data_modificata_{titolo_id}",
                    )

                    settore_modificato = st.text_input(
                        "Settore aggiornato",
                        value=titolo_selezionato["settore"],
                        key=f"settore_modificato_{titolo_id}",
                    )

                    mercato_modificato = st.text_input(
                        "Mercato aggiornato",
                        value=titolo_selezionato["mercato"],
                        key=f"mercato_modificato_{titolo_id}",
                    )

                    conferma_modifica = st.form_submit_button(
                        "Salva modifiche"
                    )

                    if conferma_modifica:
                        if not ticker_modificato.strip():
                            st.warning(
                                "Inserire il ticker."
                            )
                        elif not settore_modificato.strip():
                            st.warning(
                                "Inserire il settore."
                            )
                        elif not mercato_modificato.strip():
                            st.warning(
                                "Inserire il mercato."
                            )
                        else:
                            modifica_titolo(
                                portafoglio_id=portafoglio_id,
                                titolo_id=titolo_id,
                                ticker=ticker_modificato.strip(),
                                quantita=quantita_modificata,
                                prezzo_medio_acquisto=(
                                    prezzo_modificato
                                ),
                                data_acquisto=data_modificata,
                                settore=settore_modificato.strip(),
                                mercato=mercato_modificato.strip(),
                            )

            with colonna_eliminazione:
                st.warning(
                    "L'eliminazione del titolo è definitiva."
                )

                conferma_eliminazione_titolo = st.checkbox(
                    "Confermo di voler eliminare il titolo.",
                    key=(
                        "conferma_eliminazione_titolo_"
                        f"{titolo_id}"
                    ),
                )

                if st.button(
                    "Elimina titolo",
                    disabled=(
                        not conferma_eliminazione_titolo
                    ),
                    type="primary",
                ):
                    elimina_titolo(
                        portafoglio_id=portafoglio_id,
                        titolo_id=titolo_id,
                    )