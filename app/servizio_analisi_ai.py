import logging
import os

from dotenv import load_dotenv
from google import genai


logger = logging.getLogger(__name__)

load_dotenv()


class ErroreConfigurazioneAnalisiAI(Exception):
    """Errore sollevato quando manca una variabile di configurazione."""


class ErroreServizioAnalisiAI(Exception):
    """Errore sollevato quando Gemini non risponde correttamente."""


def ottieni_variabile_ambiente_obbligatoria(
    nome: str,
) -> str:
    """Restituisce una variabile d'ambiente obbligatoria."""

    valore = os.getenv(
        nome
    )

    if not valore:
        raise ErroreConfigurazioneAnalisiAI(
            f"La variabile d'ambiente '{nome}' non è configurata."
        )

    return valore


def genera_testo(
    richiesta: str,
) -> str:
    """Invia una richiesta testuale a Gemini e restituisce la risposta."""

    chiave_api = ottieni_variabile_ambiente_obbligatoria(
        "GEMINI_API_KEY"
    )

    modello = os.getenv(
        "MODELLO_GEMINI",
        "gemini-2.5-flash-lite",
    )

    client = genai.Client(
        api_key=chiave_api
    )

    try:
        risposta = client.models.generate_content(
            model=modello,
            contents=richiesta,
        )
    except Exception as errore:
        logger.exception(
            "Errore durante la richiesta inviata a Gemini."
        )

        raise ErroreServizioAnalisiAI(
            "Non è stato possibile ottenere una risposta da Gemini."
        ) from errore

    if not risposta.text:
        raise ErroreServizioAnalisiAI(
            "Gemini non ha restituito alcun testo."
        )

    return risposta.text


def formatta_numero_locale(
    valore: str | float | int | None,
) -> str:
    """Formatta un numero secondo la convenzione italiana."""

    if valore is None:
        return "non disponibile"

    numero = float(
        valore
    )

    return (
        f"{numero:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def genera_analisi_portafoglio_locale(
    riepilogo: dict,
) -> str:
    """Genera un report locale quando Gemini non è disponibile."""

    righe = [
        (
            f'Il portafoglio "{riepilogo["nome_portafoglio"]}" '
            "presenta un capitale investito totale di "
            f'{formatta_numero_locale(
                riepilogo["capitale_investito_totale"]
            )} euro e un valore corrente totale di '
            f'{formatta_numero_locale(
                riepilogo["valore_corrente_totale"]
            )} euro.'
        ),
        (
            "Il guadagno o la perdita complessiva è pari a "
            f'{formatta_numero_locale(
                riepilogo["guadagno_perdita_totale"]
            )} euro, con una variazione percentuale del '
            f'{formatta_numero_locale(
                riepilogo["variazione_percentuale_totale"]
            )}%.'
        ),
    ]

    titoli_con_variazione = [
        titolo
        for titolo in riepilogo["titoli"]
        if titolo["variazione_percentuale"] is not None
    ]

    if titoli_con_variazione:
        titolo_piu_rilevante = max(
            titoli_con_variazione,
            key=lambda titolo: abs(
                float(
                    titolo["variazione_percentuale"]
                )
            ),
        )

        righe.extend(
            [
                "",
                (
                    "Il titolo con la variazione percentuale "
                    "più rilevante è "
                    f'{titolo_piu_rilevante["ticker"]}, '
                    "con una variazione del "
                    f'{formatta_numero_locale(
                        titolo_piu_rilevante[
                            "variazione_percentuale"
                        ]
                    )}%.'
                ),
            ]
        )

    righe.extend(
        [
            "",
            (
                "L'analisi è stata generata localmente perché "
                "il servizio AI non è temporaneamente disponibile."
            ),
            (
                "Il testo ha finalità informative e non "
                "costituisce consulenza finanziaria."
            ),
        ]
    )

    return "\n".join(
        righe
    )


def genera_analisi_portafoglio(
    riepilogo: dict,
) -> str:
    """Genera una breve analisi descrittiva del portafoglio."""

    dettagli_titoli = []

    for titolo in riepilogo["titoli"]:
        dettagli_titoli.append(
            "- "
            f"{titolo['ticker']}: "
            f"capitale investito {titolo['capitale_investito']} euro, "
            f"valore corrente {titolo['valore_corrente']} euro, "
            f"guadagno o perdita {titolo['guadagno_perdita']} euro, "
            f"variazione {titolo['variazione_percentuale']}%."
        )

    elenco_titoli = "\n".join(
        dettagli_titoli
    )

    richiesta = (
        "Genera una breve analisi descrittiva in italiano di questo "
        "portafoglio finanziario.\n"
        "Usa un linguaggio chiaro e sintetico.\n"
        "Usa la virgola come separatore decimale e il punto come "
        "separatore delle migliaia.\n"
        "Evidenzia l'andamento complessivo e il titolo con la variazione "
        "percentuale più rilevante.\n"
        "Non fornire consigli di acquisto o vendita.\n"
        "Concludi specificando che il testo ha finalità informative e "
        "non costituisce consulenza finanziaria.\n\n"
        f"Nome del portafoglio: {riepilogo['nome_portafoglio']}\n"
        f"Capitale investito totale: "
        f"{riepilogo['capitale_investito_totale']} euro\n"
        f"Valore corrente totale: "
        f"{riepilogo['valore_corrente_totale']} euro\n"
        f"Guadagno o perdita totale: "
        f"{riepilogo['guadagno_perdita_totale']} euro\n"
        f"Variazione percentuale totale: "
        f"{riepilogo['variazione_percentuale_totale']}%\n\n"
        "Dettaglio dei titoli:\n"
        f"{elenco_titoli}"
    )

    try:
        return genera_testo(
            richiesta=richiesta
        )

    except (
        ErroreConfigurazioneAnalisiAI,
        ErroreServizioAnalisiAI,
    ):
        return genera_analisi_portafoglio_locale(
            riepilogo=riepilogo
        )
