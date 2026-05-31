import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()


def ottieni_variabile_ambiente_obbligatoria(nome: str) -> str:
    """Restituisce una variabile d'ambiente oppure interrompe l'avvio."""
    valore = os.getenv(nome)

    if not valore:
        raise RuntimeError(
            f"La variabile d'ambiente obbligatoria '{nome}' non è definita."
        )

    return valore


url_database = URL.create(
    drivername="mysql+pymysql",
    username=ottieni_variabile_ambiente_obbligatoria("MYSQL_USER"),
    password=ottieni_variabile_ambiente_obbligatoria("MYSQL_PASSWORD"),
    host=os.getenv("MYSQL_HOST", "127.0.0.1"),
    port=int(os.getenv("MYSQL_PORT", "3306")),
    database=ottieni_variabile_ambiente_obbligatoria("MYSQL_DATABASE"),
    query={"charset": "utf8mb4"},
)

motore_database = create_engine(
    url_database,
    pool_pre_ping=True,
)

SessioneLocale = sessionmaker(
    bind=motore_database,
    autoflush=False,
    autocommit=False,
)


class BaseModelli(DeclarativeBase):
    """Classe di base condivisa da tutti i modelli SQLAlchemy."""

    pass