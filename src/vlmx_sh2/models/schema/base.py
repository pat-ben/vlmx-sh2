"""
Base classes for database schemas and models.

Defines common base classes that all database schemas and entity models inherit from.
Provides shared functionality for table naming, configuration, and schema organization.
"""

from typing import List, Type
from sqlmodel import SQLModel


# ============================================
# DATABASE SCHEMA
# ============================================

class DatabaseSchema(SQLModel):
    """Base class for database schemas"""
    name: str
    description: str
    tables: List[Type[SQLModel]]  # Which entities/tables this database has



# ============================================
# BASE MODEL
# ============================================


class DatabaseModel(SQLModel):
    """Base class for all database models"""

    
    model_config = { # type: ignore[assignment]
        "from_attributes": True,
        "use_enum_values": True
    }

    @classmethod
    def table_name(cls) -> str:
        """Returns the SQL table name for this model"""
        raise NotImplementedError