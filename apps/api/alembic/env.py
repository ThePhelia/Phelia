from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path
import os
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

config = context.config

DEFAULT_ENV_VARS = {
    "APP_SECRET": "development-secret",
    "DATABASE_URL": config.get_main_option("sqlalchemy.url"),
    "REDIS_URL": "redis://localhost:6379/0",
    "CELERY_BROKER_URL": "redis://localhost:6379/0",
    "CELERY_RESULT_BACKEND": "redis://localhost:6379/0",
    "QB_URL": "http://localhost:8080",
    "QB_USER": "admin",
    "QB_PASS": "adminadmin",
}

for key, value in DEFAULT_ENV_VARS.items():
    os.environ.setdefault(key, value)

from app.db.session import Base  # noqa: E402
from app.core.config import settings  # noqa: E402
import app.db.models  # noqa: F401,E402

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
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
