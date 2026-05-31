from sqlalchemy import text

from app.connessione_database import motore_database


def esegui_test_connessione() -> None:
    """Verifica che Python riesca a collegarsi al database MySQL."""
    with motore_database.connect() as connessione:
        nome_database = connessione.execute(
            text("SELECT DATABASE()")
        ).scalar_one()

        versione_mysql = connessione.execute(
            text("SELECT VERSION()")
        ).scalar_one()

    print("Connessione al database riuscita.")
    print(f"Database selezionato: {nome_database}")
    print(f"Versione MySQL: {versione_mysql}")


if __name__ == "__main__":
    esegui_test_connessione()