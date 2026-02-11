"""
Data persistence layer.

Public API:
  - StorageInterface        — single facade for all storage operations
  - StorageBackend          — protocol that backends implement
  - StorageBackendType      — enum: JSON | SQLITE
  - set_backend / get_backend — switch or inspect the active backend
  - get_company_folder_path — shared path utility
  - find_company_candidates — company search helper

SQLite utilities (engine, legacy functions) are importable from their
respective modules but NOT eagerly loaded here to avoid pulling in
sqlmodel/sqlalchemy at startup.
"""

# Backend protocol and configuration
from .backend import StorageBackend, StorageBackendType
from .database import StorageInterface, set_backend, get_backend

# Shared path utilities (no SQLite dependency)
from .paths import get_data_directory_path, get_company_folder_path

# Result helpers (no SQLite dependency)
from .result_helpers import success_result, error_result

# NOTE: SQLite engine utilities and legacy free functions are NOT
# imported here to keep startup fast.  Import directly when needed:
#
#   from vlmx_sh2.storage.engine import get_engine, create_tables
#   from vlmx_sh2.storage.sqlite_backend import sqlite_create_entity
