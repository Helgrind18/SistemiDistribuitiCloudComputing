from logging.config import fileConfig

from alembic import context

from app import modelli  # Import necessario per registrare le tabelle.
from app.connessione_database import BaseModelli, motore_database

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

url_connessione = motore_database.url.render_as_string(
    hide_password=False,
)

config.set_main_option(
    "sqlalchemy.url",
    url_connessione.replace("%", "%%"),
)

metadati_destinazione = BaseModelli.metadata


def esegui_migrazioni_modalita_offline() -> None:
    """Genera istruzioni SQL senza collegarsi direttamente al database."""
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=metadati_destinazione,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def esegui_migrazioni_modalita_online() -> None:
    """Applica le migrazioni collegandosi al database."""
    with motore_database.connect() as connessione:
        context.configure(
            connection=connessione,
            target_metadata=metadati_destinazione,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    esegui_migrazioni_modalita_offline()
else:
    esegui_migrazioni_modalita_online()