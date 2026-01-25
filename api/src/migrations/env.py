# -----------------------------------------------
# Append the API lib package to the system path
# -----------------------------------------------
import sys
from pathlib import Path

app_lib_path = str(Path(__file__).joinpath("../../").resolve())
print(f"Appending lib path: {app_lib_path}")
sys.path.append(app_lib_path)
# -----------------------------------------------

# -----------------------------------------------
# Alembic imports
# -----------------------------------------------
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# -----------------------------------------------
# Custom imports
# -----------------------------------------------
from lib.config import Config
from lib.models import BaseModel

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# if config.config_file_name is not None:
#     fileConfig(config.config_file_name)

# Needed for auto-migrations
target_metadata = BaseModel.metadata

app_config = Config()
print(f"SQL URL: {app_config.db_url}")
config.set_main_option("sqlalchemy.url", app_config.db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
