from pathlib import Path

from app.lettore_file import leggi_file_portafoglio


def stampa_risultato(nome_file: str) -> None:
    """Legge un file di esempio e stampa il risultato."""

    cartella_progetto = Path(__file__).resolve().parent.parent
    percorso_file = cartella_progetto / "esempi" / nome_file

    risultato = leggi_file_portafoglio(
        nome_file=percorso_file.name,
        contenuto_file=percorso_file.read_bytes(),
    )

    print(f"\nFile: {percorso_file.name}")
    print(f"File valido: {risultato.valido}")
    print(f"Titoli validi trovati: {len(risultato.titoli_validi)}")
    print(f"Errori trovati: {len(risultato.errori)}")

    for titolo in risultato.titoli_validi:
        print(f"  Titolo valido: {titolo.model_dump()}")

    for errore in risultato.errori:
        print(
            "  Errore:"
            f" riga={errore.numero_riga},"
            f" campo={errore.nome_campo},"
            f" messaggio={errore.messaggio}"
        )


if __name__ == "__main__":
    stampa_risultato("portafoglio_valido.csv")
    stampa_risultato("portafoglio_valido.json")
    stampa_risultato("portafoglio_non_valido.csv")