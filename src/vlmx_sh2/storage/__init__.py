"""
Data persistence layer.

Public API:
  - StorageInterface        — single facade for all storage operations
  - StorageBackend          — protocol that backends implement
  - StorageBackendType      — enum: JSON | SQLITE
  - set_backend / get_backend — switch or inspect the active backend
  - get_company_folder_path — shared path utility
  - find_company_candidates — company search helper

SQLite engine utilities and legacy free functions are also re-exported
for backward compatibility.
"""

# Backend protocol and configuration
from .backend import StorageBackend, StorageBackendType
from .database import StorageInterface, set_backend, get_backend

# Shared path utilities
from .paths import get_data_directory_path, get_company_folder_path

# Result helpers
from .result_helpers import success_result, error_result

# SQLite engine utilities
from .engine import get_engine, create_tables, get_session, get_company_db_path

# Legacy SQLite free functions (predate the backend protocol)
from .sqlite_backend import (
    sqlite_create_entity,
    sqlite_load_entity,
    sqlite_save_entity,
    sqlite_delete_entity,
    sqlite_load_all_entities,
    sqlite_list_companies,
    sqlite_entity_exists,
)
