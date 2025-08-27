from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# --- Flask app + db ---
from flask import current_app
from app import create_app            # your factory
from models import db                 # SQLAlchemy() instance comes from models/__init__.py

# Alembic Config object
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Create Flask app & push context so we can read config/DB url
flask_app = create_app()
flask_app.app_context().push()

# Pull DB URL from Flask config and ESCAPE % for ConfigParser
db_url = str(current_app.config.get("SQLALCHEMY_DATABASE_URI", ""))
config.set_main_option("sqlalchemy.url", db_url.replace("%", "%%"))

# Metadata for autogenerate
target_metadata = db.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode'."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode'."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()