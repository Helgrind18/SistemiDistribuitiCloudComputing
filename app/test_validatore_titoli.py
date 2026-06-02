from pathlib import Path

from app.lettore_file import leggi_file
from app.validazione_titoli import valida_titoli


def prova_file(
    nome_file: str,
) -> None:
    """Legge e valida un file di esempio."""

    cartella_progetto = (
        Path(__file__)
        .resolve()
        .parent
        .parent
    )

    percorso = (
        cartella_progetto
        / "esempi"
        / nome_file
    )

    print(f"\nFile: {nome_file}")

    try:
        righe = leggi_file(
            nome_file=percorso.name,
            contenuto_file=percorso.read_bytes(),
        )

        titoli = valida_titoli(
            righe
        )
    except ValueError as errore:
        print(
            f"Validazione fallita: {errore}"
        )

        return

    print(
        f"Validazione riuscita: {len(titoli)} titoli corretti."
    )

    for titolo in titoli:
        print(
            f"  {titolo.ticker}: "
            f"quantita={titolo.quantita}, "
            f"prezzo={titolo.prezzo_medio_acquisto}"
        )


if __name__ == "__main__":
    prova_file(
        "portafoglio_valido.csv"
    )

    prova_file(
        "portafoglio_non_valido.csv"
    )