"""This files includes an example of pydantic models that should match
1:1 SQL tables. Each model represents a table in the database.
Operational models may differ from the database schema.
This file is also helpful to design the DSL grammar which should correspond ... to the database.

"""

from datetime import date, datetime
from typing import Optional, Union
from pydantic import BaseModel, Field
from .enums import (Entity, Currency, Unit)
 

# File: src/vlmx_sh2/models/database.py
"""
Database models - Each model maps 1:1 to a SQL table.
All models follow the pattern: PythonModel → sql_table

Architecture:
- create company ACME → creates acme.db file
- Inside acme.db → tables: company, metadata, brand, docs, json, data, metrics, milestones, news
"""


# ============================================
# BASE MODEL
# ============================================


class DatabaseModel(BaseModel):
    """Base class for all database models"""

    class Config:
        from_attributes = True
        use_enum_values = True

    @classmethod
    def table_name(cls) -> str:
        """Returns the SQL table name for this model"""
        raise NotImplementedError


# ============================================
# COMPANY ENTITY created at the same time as the database
# ============================================


class CompanyEntity(DatabaseModel):
    """
    Python Model: CompanyEntity
    Database: Company's name
    SQL Table: company
    Description: Core company information (one record per company database)
    """

    id: Optional[int] = None
    name: str
    entity: Entity
    currency: Currency
    unit: Unit
    fiscal_month: int = 12
    incorporation: Optional[date] = None
    
    # timestamp
    created_at: datetime = Field(default_factory=datetime.now)    
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # track where the source database file is located and when it was last synced
    source_db: Optional[str] = Field(None, description="Source database file (portfolio only)")
    last_synced_at: Optional[datetime] = Field(None, description="Last sync timestamp (portfolio only)")

    @classmethod
    def table_name(cls) -> str:
        return "company"



# ============================================
# METADATA ENTITY (company metadata extension)
# ============================================


class MetadataEntity(DatabaseModel):
    """
    Python Model: MetadataEntity
    SQL Table: metadata
    Description: Extended company metadata (key-value pairs)
    """

    id: Optional[int] = None
    org_id: int = Field(..., description="Reference to organization.id")
    key: str = Field(..., description="Metadata key")
    value: Union[str, int, float, bool, date, list, dict, None] = Field(..., description="Metadata value (automatically typed and validated)")
    
    # timestamp
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def table_name(cls) -> str:
        return "metadata"


# ============================================
# BRAND ENTITY (Parent - Core brand info only)
# ============================================

class BrandEntity(DatabaseModel):
    """
    Python Model: BrandEntity
    SQL Table: brand
    Description: Core company brand identity (vision, mission, personality, promise)
    
    Note: offering, target, and values moved to separate tables:
    - OfferingModel → brand_offerings table
    - TargetModel → brand_targets table
    - ValueModel → brand_values table
    """
    id: Optional[int] = None
    org_id: int = Field(default=1, description="Reference to organization.id")
    
    # Core brand elements (single text fields)
    vision: Optional[str] = Field(None, description="Company vision statement")
    mission: Optional[str] = Field(None, description="Company mission statement")
    personality: Optional[str] = Field(None, description="Brand personality description")
    promise: Optional[str] = Field(None, description="Brand promise to customers")
    brand: Optional[str] = Field(None, description="Brand name")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @classmethod
    def table_name(cls) -> str:
        return "brand"


# ============================================
# OFFERING ENTITY RELATED TO BRAND (Key-Value Pairs)
# ============================================

class OfferingEntity(DatabaseModel):
    """
    Python Model: OfferingEntity
    SQL Table: brand_offerings
    Description: Company product/service offerings (key-value pairs)
    
    Examples:
        key="Core Product", value="AI-powered financial analytics platform"
        key="Premium Service", value="White-label solutions for enterprises"
        key="Consulting", value="Strategic advisory for digital transformation"
    """
    id: Optional[int] = None
    brand_id: int = Field(..., description="Reference to brand.id")
    key: str = Field(..., description="Offering title/category")
    value: str = Field(
        ..., 
        description="Offering description (automatically typed and validated)"
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @classmethod
    def table_name(cls) -> str:
        return "brand_offerings"


# ============================================
# TARGET ENTITY RELATED TO BRAND (Key-Value Pairs)
# ============================================

class TargetEntity(DatabaseModel):
    """
    Python Model: TargetEntity
    SQL Table: brand_targets
    Description: Target audience/market segments (key-value pairs)
    
    Examples:
        key="Primary Segment", value="Fintech startups with 10-50 employees"
        key="Secondary Segment", value="Mid-market financial institutions"
        key="Geographic Focus", value="European Union and Switzerland"
        key="Customer Profile", value="CFOs and finance teams"
    """
    id: Optional[int] = None
    brand_id: int = Field(..., description="Reference to brand.id")
    key: str = Field(..., description="Target segment title/category")
    value: str = Field(
        ..., 
        description="Target segment description (automatically typed and validated)"
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @classmethod
    def table_name(cls) -> str:
        return "brand_targets"


# ============================================
# VALUE ENTITY RELATED TO BRAND (Key-Value Pairs)
# ============================================

class ValueEntity(DatabaseModel):
    """
    Python Model: ValueEntity
    SQL Table: brand_values
    Description: Company core values (key-value pairs)
    
    Examples:
        key="Innovation", value="We constantly push boundaries and embrace new technologies"
        key="Integrity", value="We act with honesty and transparency in all our dealings"
        key="Impact", value="We measure success by the positive change we create"
        key="Inclusivity", value="We build products that serve everyone, regardless of background"
    """
    id: Optional[int] = None
    brand_id: int = Field(..., description="Reference to brand.id")
    key: str = Field(..., description="Value name/title")
    value: str = Field(
        ..., 
        description="Value description/explanation (automatically typed and validated)"
    )    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @classmethod
    def table_name(cls) -> str:
        return "brand_values"

