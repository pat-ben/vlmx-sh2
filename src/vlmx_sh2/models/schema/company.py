"""
Database schema and entity models for company database.

Contains the CompanyDatabase schema definition and all company-related
entity models including CompanyEntity, MetadataEntity, BrandEntity,
OfferingEntity, TargetEntity, and ValuesEntity.
"""

from datetime import date, datetime
from typing import Optional
from sqlmodel import Field
from .enums import Legal, Currency, Unit, Type
from .base import DatabaseSchema, DatabaseModel


# ============================================
# DATABASE SCHEMA
# ============================================

class CompanyDatabase(DatabaseSchema):
    name: str = "company"
    description: str = "Single company database"
    # tables: List[Type[SQLModel]] = []


# ============================================
# COMPANY ENTITY created at the same time as the database
# ============================================


class CompanyEntity(DatabaseModel, table=True):
    """
    Python Model: CompanyEntity
    Database: Company's name
    SQL Table: company
    Description: Core company information (one record per company database)
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    legal: Legal
    type: Type = Type.COMPANY
    currency: Currency
    unit: Unit = Unit.THOUSANDS
    closing: int = 12
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


class MetadataEntity(DatabaseModel, table=True):
    """
    Python Model: MetadataEntity
    SQL Table: metadata
    Description: Extended company metadata (key-value pairs)
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    co_id: int = Field(..., description="Reference to company.id")
    key: str = Field(..., description="Metadata key")
    value: Optional[str] = Field(..., description="Metadata value stored as JSON string")
    
    # timestamp
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def table_name(cls) -> str:
        return "metadata"


# ============================================
# BRAND ENTITY (Parent - Core brand info only)
# ============================================

class BrandEntity(DatabaseModel, table=True):
    """
    Python Model: BrandEntity
    SQL Table: brand
    Description: Core company brand identity (vision, mission, personality, promise)
    
    Note: offering, target, and values moved to separate tables:
    - OfferingModel → brand_offerings table
    - TargetModel → brand_targets table
    - ValueModel → brand_values table
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    co_id: int = Field(default=1, description="Reference to company.id")
    
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

class OfferingEntity(DatabaseModel, table=True):
    """
    Python Model: OfferingEntity
    SQL Table: brand_offerings
    Description: Company product/service offerings (key-value pairs)
    
    Examples:
        key="Core Product", value="AI-powered financial analytics platform"
        key="Premium Service", value="White-label solutions for enterprises"
        key="Consulting", value="Strategic advisory for digital transformation"
    """
    id: Optional[int] = Field(default=None, primary_key=True)
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

class TargetEntity(DatabaseModel, table=True):
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
    id: Optional[int] = Field(default=None, primary_key=True)
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

class ValuesEntity(DatabaseModel, table=True):
    """
    Python Model: ValuesEntity
    SQL Table: brand_values
    Description: Company core values (key-value pairs)
    
    Examples:
        key="Innovation", value="We constantly push boundaries and embrace new technologies"
        key="Integrity", value="We act with honesty and transparency in all our dealings"
        key="Impact", value="We measure success by the positive change we create"
        key="Inclusivity", value="We build products that serve everyone, regardless of background"
    """
    id: Optional[int] = Field(default=None, primary_key=True)
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