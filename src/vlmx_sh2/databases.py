"""
Database schema definitions for VLMX DSL.

Defines database schemas and table structures for different entity types.
Maps database tables to their corresponding Pydantic models and provides
schema validation and organization capabilities.
"""

from pydantic import BaseModel
from typing import List, Type
from .entities import OrganizationEntity, MetadataEntity, BrandEntity, OfferingEntity

class DatabaseSchema(BaseModel):
    """Base class for database schemas"""
    name: str
    description: str
    tables: List[Type[BaseModel]]  # Which entities/tables this database has
    
class CompanyDatabase(DatabaseSchema):
    name: str = "company"
    description: str = "Single company database"
    tables: List[Type[BaseModel]] = [
        OrganizationEntity,
        MetadataEntity,
        BrandEntity,
        OfferingEntity,
        # ... all company-related tables
    ]

class FundDatabase(DatabaseSchema):
    name: str = "fund"
    description: str = "Investment fund portfolio database"
    #tables: List[Type[BaseModel]] = []