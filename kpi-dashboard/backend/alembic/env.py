"""
Alembic migration environment for CS Pulse.

Reads DATABASE_URL from environment (same as app_v3_minimal.py and the MCP server).
Imports all SQLAlchemy models so autogenerate can diff against them.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add backend/ to path so model imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import the shared db instance and ALL models
from extensions import db

# Import models so they register with db.metadata
import models  # noqa: F401 — registers all tables

try:
    import models_action_interface  # noqa: F401
except ImportError:
    pass

config = context.config

# Override sqlalchemy.url from DATABASE_URL env var (same as Flask app)
database_url = os.environ.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL')
if database_url:
    config.set_main_option('sqlalchemy.url', database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point autogenerate at our models' metadata
target_metadata = db.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL without connecting)."""
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
    """Run migrations in 'online' mode (connects to DB and applies)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
