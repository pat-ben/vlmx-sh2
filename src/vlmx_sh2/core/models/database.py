"""
Database schema definitions for VLMX DSL.

Defines database schemas and table structures for different entity types.
Maps database tables to their corresponding SQLModel models and provides
schema validation and organization capabilities.
"""

from sqlmodel import SQLModel
from typing import List, Type


class DatabaseSchema(SQLModel):
    """Base class for database schemas"""
    name: str
    description: str
    tables: List[Type[SQLModel]]  # Which entities/tables this database has
    
class CompanyDatabase(DatabaseSchema):
    name: str = "company"
    description: str = "Single company database"
    # tables: List[Type[SQLModel]] = []


class FundDatabase(DatabaseSchema):
    name: str = "fund"
    description: str = "Investment fund portfolio database"
    #tables: List[Type[BaseModel]] = []