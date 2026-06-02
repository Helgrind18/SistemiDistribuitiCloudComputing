# Controlla ogni dizionario e restituisce una lista di titoli validi
from pydantic import ValidationError

from app.schemi import TitoloPossedutoInIngresso


def valida_titoli(righe: list[dict]) -> list[TitoloPossedutoInIngresso]:
    titoli_validi = []
    ticker_letti = set() # Impedisco che lo stesso ticker sia due volte dentro lo stesso file
    for numero_riga, riga in enumerate(righe,start=1):
        try:
            titolo = TitoloPossedutoInIngresso.model_validate(riga) # Lascio a pydantic la validazione della riga passata in ingresso
        except ValidationError as errore:
            raise ValueError(
                f"La riga {numero_riga} non è valida."
            ) from errore
        # Controllo se sia già presente il ticker
        if titolo.ticker in ticker_letti:
            raise ValueError(
                f"Il ticker '{titolo.ticker}' "
                f"compare più volte nel file."
            )
        titoli_validi.append(titolo)
        ticker_letti.add(titolo.ticker)
    return titoli_validi

# La logica è la seguente:
# Legge la riga: se è corretta, continua e la aggiunge alla lista finale. Se non è valida, allora, la funzione termina immediatamente
