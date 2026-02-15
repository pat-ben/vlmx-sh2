# File: src/vlmx_sh2/storage/sqlite_backend.py
"""
SQLite storage backend.

Provides both:
- ``SqliteBackend`` class implementing the ``StorageBackend`` protocol,
  delegating to the legacy free functions below.
- Legacy free functions (``sqlite_create_entity``, etc.) that predate
  the backend protocol and are kept for backward compatibility.
"""

from typing import Any, Dict, List, Optional, Type

from sqlmodel import Session, select

from ..core.models.context import Context
from ..core.schemas.base import EntityModel
from ..core.schemas.company import CompanyDatabase
from vlmx_sh2.core.enums import Cardinality
from .paths import get_company_folder_path, get_data_directory_path
from .engine import get_engine, create_tables, get_session, get_company_db_path
from .result_helpers import error_result, success_result


# ==================== HELPERS ====================


def _get_entity_class(entity_type: str) -> Optional[Type[EntityModel]]:
    """Resolve an entity_type string to its SQLModel class.

    Handles the special case where entity_type 'company' maps to
    OrganizationEntity (whose get_entity_word_id() returns 'organization').
    """
    for entity_class in CompanyDatabase.tables:
        word_id = entity_class.get_entity_word_id()
        # Match by word ID (e.g., "brand" → BrandEntity)
        if word_id == entity_type:
            return entity_class
        # Special case: "company" matches OrganizationEntity via table_name()
        if entity_type == "company" and entity_class.table_name() == "company":
            return entity_class
    return None


# ==================== SQLITE BACKEND (protocol) ====================


class SqliteBackend:
    """SQLite storage backend.

    Satisfies the ``StorageBackend`` protocol via structural subtyping.
    Delegates to the legacy free functions (``sqlite_create_entity``, etc.)
    defined in this module. Methods without a legacy equivalent raise
    ``NotImplementedError``.
    """

    def create_entity(
        self,
        entity_type: str,
        data: Dict[str, Any],
        context: Context,
    ) -> Dict[str, Any]:
        return sqlite_create_entity(entity_type, data, context)

    def load_entity(
        self,
        entity_type: str,
        company_name: str,
        context: Context,
    ) -> Optional[Dict[str, Any]]:
        return sqlite_load_entity(entity_type, company_name, context)

    def save_entity(
        self,
        entity_type: str,
        data: Dict[str, Any],
        company_name: str,
        context: Context,
    ) -> Dict[str, Any]:
        return sqlite_save_entity(entity_type, data, company_name, context)

    def delete_entity(
        self,
        entity_type: str,
        entity_name: str,
        context: Context,
    ) -> Dict[str, Any]:
        return sqlite_delete_entity(entity_type, entity_name, context)

    def load_all_entities(
        self,
        entity_type: str,
        company_name: str,
        context: Context,
    ) -> List[Dict[str, Any]]:
        return sqlite_load_all_entities(entity_type, company_name, context)

    def save_entity_array(
        self,
        entity_type: str,
        entity_array: List[Dict[str, Any]],
        company_name: str,
        context: Context,
    ) -> Dict[str, Any]:
        raise NotImplementedError("SqliteBackend.save_entity_array not yet implemented")

    def update_dynamic_entity_record(
        self,
        entity_type: str,
        record_id: str,
        updated_fields: Dict[str, Any],
        company_name: str,
        context: Context,
    ) -> Dict[str, Any]:
        raise NotImplementedError("SqliteBackend.update_dynamic_entity_record not yet implemented")

    def list_companies(
        self,
        context: Context,
    ) -> Dict[str, Any]:
        return sqlite_list_companies(context)

    def entity_exists(
        self,
        entity_name: str,
        company_name: str,
        context: Context,
    ) -> bool:
        return sqlite_entity_exists(entity_type=entity_name, company_name=company_name, context=context)

    def find_company_by_name(
        self,
        search_name: str,
        context: Context,
    ) -> Optional[str]:
        raise NotImplementedError("SqliteBackend.find_company_by_name not yet implemented")

    def find_company_candidates(
        self,
        search_name: str,
        context: Context,
    ) -> List[str]:
        raise NotImplementedError("SqliteBackend.find_company_candidates not yet implemented")


# ==================== LEGACY FREE FUNCTIONS ====================
# These predate the StorageBackend protocol and are kept so that
# existing code importing them continues to work.


def sqlite_create_entity(entity_type: str, data: Dict[str, Any],
                         context: Context) -> Dict[str, Any]:
    """Insert a new entity row. For 'company', also creates the .db file and tables."""
    try:
        entity_class = _get_entity_class(entity_type)
        if entity_class is None:
            return error_result(f"Unknown entity type: {entity_type}")

        if entity_type == "company":
            company_name = data.get("name")
            if not company_name:
                return error_result("Company name is required")

            db_path = get_company_db_path(company_name, context)

            # Ensure company folder exists
            db_path.parent.mkdir(parents=True, exist_ok=True)

            engine = get_engine(db_path)
            create_tables(engine)

            instance = entity_class(**data)
            with get_session(engine) as session:
                session.add(instance)
                session.commit()
                session.refresh(instance)
                result_data = instance.model_dump()

            return success_result(
                f"Successfully created company '{company_name}'",
                company=result_data,
                db_path=str(db_path),
            )
        else:
            # Non-company entities require an org context
            from ..core.utils.context_helpers import is_sys
            if is_sys(context) or not context.org_name:
                return error_result(
                    "Must be in organization context to create non-company entities"
                )

            db_path = get_company_db_path(context.org_name, context)
            if not db_path.exists():
                return error_result(
                    f"Database not found for company '{context.org_name}'"
                )

            engine = get_engine(db_path)
            instance = entity_class(**data)
            with get_session(engine) as session:
                session.add(instance)
                session.commit()
                session.refresh(instance)
                result_data = instance.model_dump()

            return success_result(
                f"Successfully created {entity_type}",
                data=result_data,
            )

    except Exception as e:
        return error_result(f"Failed to create {entity_type}: {str(e)}")


def sqlite_load_entity(entity_type: str, company_name: str,
                       context: Context) -> Optional[Dict[str, Any]]:
    """Load a single entity record and return as dict."""
    try:
        entity_class = _get_entity_class(entity_type)
        if entity_class is None:
            return None

        db_path = get_company_db_path(company_name, context)
        if not db_path.exists():
            return None

        engine = get_engine(db_path)
        with get_session(engine) as session:
            statement = select(entity_class)
            result = session.exec(statement).first()
            if result is None:
                return None
            return result.model_dump()

    except Exception:
        return None


def sqlite_save_entity(entity_type: str, data: Dict[str, Any],
                       company_name: str,
                       context: Context) -> Dict[str, Any]:
    """Update an existing entity record."""
    try:
        entity_class = _get_entity_class(entity_type)
        if entity_class is None:
            return error_result(f"Unknown entity type: {entity_type}")

        db_path = get_company_db_path(company_name, context)
        if not db_path.exists():
            return error_result(f"Database not found for company '{company_name}'")

        engine = get_engine(db_path)
        with get_session(engine) as session:
            # For SINGLE cardinality, get the first (only) row
            # For MULTIPLE, require an 'id' in data to locate the record
            if (hasattr(entity_class, 'cardinality')
                    and entity_class.cardinality == Cardinality.MULTIPLE):
                record_id = data.get("id")
                if record_id is None:
                    return error_result(f"Record 'id' required to update {entity_type}")
                existing = session.get(entity_class, record_id)
            else:
                statement = select(entity_class)
                existing = session.exec(statement).first()

            if existing is None:
                return error_result(f"{entity_type} record not found for '{company_name}'")

            # Apply updates
            for key, value in data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)

            session.add(existing)
            session.commit()
            session.refresh(existing)
            result_data = existing.model_dump()

        return success_result(
            f"Successfully updated {entity_type} for '{company_name}'",
            data=result_data,
        )

    except Exception as e:
        return error_result(f"Failed to save {entity_type}: {str(e)}")


def sqlite_delete_entity(entity_type: str, entity_name: str,
                         context: Context) -> Dict[str, Any]:
    """Delete an entity record or all entity data."""
    try:
        entity_class = _get_entity_class(entity_type)
        if entity_class is None:
            return error_result(f"Unknown entity type: {entity_type}")

        if entity_type == "company":
            db_path = get_company_db_path(entity_name, context)
            if not db_path.exists():
                return error_result(f"Database not found for company '{entity_name}'")

            # Remove the .db file (company folder cleanup is handled by JSON backend)
            db_path.unlink()
            return success_result(
                f"Successfully deleted SQLite database for '{entity_name}'",
                db_path=str(db_path),
            )
        else:
            if not context.org_name:
                return error_result("Must be in organization context to delete entities")

            db_path = get_company_db_path(context.org_name, context)
            if not db_path.exists():
                return error_result(
                    f"Database not found for company '{context.org_name}'"
                )

            engine = get_engine(db_path)
            with get_session(engine) as session:
                # Delete all rows for the entity type
                statement = select(entity_class)
                results = session.exec(statement).all()
                for row in results:
                    session.delete(row)
                session.commit()

            return success_result(f"Successfully deleted {entity_type} data")

    except Exception as e:
        return error_result(f"Failed to delete {entity_type}: {str(e)}")


def sqlite_load_all_entities(entity_type: str, company_name: str,
                             context: Context) -> List[Dict[str, Any]]:
    """Load all records for a multi-cardinality entity."""
    try:
        entity_class = _get_entity_class(entity_type)
        if entity_class is None:
            return []

        db_path = get_company_db_path(company_name, context)
        if not db_path.exists():
            return []

        engine = get_engine(db_path)
        with get_session(engine) as session:
            statement = select(entity_class)
            results = session.exec(statement).all()
            return [row.model_dump() for row in results]

    except Exception:
        return []


def sqlite_list_companies(context: Context) -> Dict[str, Any]:
    """List all companies by scanning for .db files in the data directory."""
    try:
        data_dir = get_data_directory_path(context)
        companies: List[Dict[str, Any]] = []

        if data_dir.exists():
            for folder in data_dir.iterdir():
                if not folder.is_dir():
                    continue
                # Look for a .db file matching the folder name
                db_file = folder / f"{folder.name}.db"
                if not db_file.exists():
                    continue

                # Load organization data from SQLite
                org_data = sqlite_load_entity("company", folder.name, context)
                if org_data:
                    companies.append(org_data)

        return success_result(
            f"Found {len(companies)} companies",
            companies=companies,
            count=len(companies),
            data_directory=str(data_dir),
        )

    except Exception as e:
        return error_result(f"Failed to list companies: {str(e)}")


def sqlite_entity_exists(entity_type: str, company_name: str,
                         context: Context) -> bool:
    """Check if a table has any data for the given entity type."""
    try:
        entity_class = _get_entity_class(entity_type)
        if entity_class is None:
            return False

        db_path = get_company_db_path(company_name, context)
        if not db_path.exists():
            return False

        engine = get_engine(db_path)
        with get_session(engine) as session:
            statement = select(entity_class)
            result = session.exec(statement).first()
            return result is not None

    except Exception:
        return False
