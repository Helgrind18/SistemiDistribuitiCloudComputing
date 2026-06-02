from pathlib import Path

from app.lettore_file import leggi_file


def esegui_test() -> None:
    cartella_progetto = Path(__file__).resolve().parent.parent

    percorso = (
        cartella_progetto
        / "esempi"
        / "portafoglio_valido.json"
    )

    righe = leggi_file(
        nome_file=percorso.name,
        contenuto_file=percorso.read_bytes(),
    )

    for riga in righe:
        print(riga)


if __name__ == "__main__":
    esegui_test()