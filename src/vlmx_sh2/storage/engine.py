"""
SQLite engine management.

Provides engine creation, table initialization, session management,
and database path resolution for per-company SQLite databases.
"""

from pathlib import Path
from typing import Dict

from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import Engine

from ..models.context import Context
from .paths import get_company_folder_path


# Engine cache: reuse engines for the same database path
_engine_cache: Dict[str, Engine] = {}


def get_engine(db_path: Path) -> Engine:
    """Create or retrieve a cached SQLAlchemy engine for a SQLite database file."""
    key = str(db_path)
    if key not in _engine_cache:
        _engine_cache[key] = create_engine(f"sqlite:///{db_path}")
    return _engine_cache[key]


def create_tables(engine: Engine) -> None:
    """Create all tables defined by EntityModel subclasses (via SQLModel metadata)."""
    SQLModel.metadata.create_all(engine)  # type: ignore[attr-defined]


def get_session(engine: Engine) -> Session:
    """Return a new SQLModel Session bound to the given engine."""
    return Session(engine)


def get_company_db_path(company_name: str, context: Context) -> Path:
    """Get the path to a company's SQLite database file (e.g., data/acme/acme.db)."""
    company_folder = get_company_folder_path(company_name, context)
    return company_folder / f"{company_name.lower()}.db"
