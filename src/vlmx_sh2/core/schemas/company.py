"""
Database schemas and entity models for company database.

Contains the CompanyDatabase schemas definition and all company-related
entity models including CompanyEntity, MetadataEntity, BrandEntity,
OfferingEntity, TargetEntity, and ValuesEntity.
"""

# src/vlmx_sh2/schemas/company.py

from datetime import date, datetime
from typing import ClassVar, List, Optional, Type

from sqlmodel import Field

from ..enums import (
    Cardinality,
    CompetitorSize,
    ContextLevel,
    Country,
    Currency,
    Legal,
    Model,
    NewsCategory,
    Phase,
    Round,
    Sector,
    Stage,
    TypeOrg,
    Unit,
)
from .base import EntityModel, SchemaModel

# ============================================
# COMPANY ENTITY created at the same time as the database
# ============================================


class OrganizationEntity(EntityModel, table=True):
    """Organization information - can be company, fund, holding, etc."""

    # ==================== CLASS METADATA ====================
    context: ClassVar[ContextLevel] = ContextLevel.SYS
    module: ClassVar[str] = "core"

    # ==================== PRIMARY KEY ====================
    id: Optional[int] = Field(default=None, primary_key=True)

    # ==================== USER FIELDS ====================
    name: str = Field(..., description="Company name")
    type: TypeOrg = Field(default=TypeOrg.COMPANY, description="Organization type")
    legal: Optional[Legal] = Field(description="Legal entity type")
    currency: Optional[Currency] = Field(
        default=Currency.USD, description="Operating currency"
    )
    unit: Optional[Unit] = Field(default=Unit.THOUSANDS, description="Financial units")
    closing: Optional[int] = Field(default=12, description="Fiscal year end month")
    incorporation: Optional[date] = Field(
        default=None, description="Date of incorporation"
    )

    # ==================== SYSTEM FIELDS ====================
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    source_db: Optional[str] = Field(default=None)
    last_synced_at: Optional[datetime] = Field(default=None)

    @classmethod
    def table_name(cls) -> str:
        return "company"

    @classmethod
    def get_entity_aliases(cls) -> List[str]:
        """Organization can be referred to as org or o."""
        return ["org", "o"]


# ============================================
# ADDRESS ENTITY
# ============================================


class AddressEntity(EntityModel, table=True):
    """
    Python Model: AddressEntity
    SQL Table: company address
    Description: company address elements
    """

    module: ClassVar[str] = "core"

    # ==================== KEYS ======================
    id: Optional[int] = Field(default=None, primary_key=True)
    co_id: int = Field(default=1, description="Reference to company.id")

    # ==================== USER FIELDS ====================
    street: Optional[str] = Field(description="Street name")
    number: Optional[int] = Field(description="Street number")
    zip: Optional[int] = Field(description="Postal code")
    city: Optional[str] = Field(description="City name")
    country: Optional[Country] = Field(description="Country")
    website: Optional[str] = Field(description="Website URL")
    headquarter: bool = Field(
        default=True, description="Is this the headquarter of the company?"
    )

    # ==================== SYSTEM FIELDS ====================
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def table_name(cls) -> str:
        return "address"


# ============================================
# METADATA ENTITY (company metadata extension)
# ============================================


class MetadataEntity(EntityModel, table=True):
    """
    Python Model: MetadataEntity
    SQL Table: metadata
    Description: Relational
    """

    module: ClassVar[str] = "core"

    # ==================== KEYS ======================
    id: Optional[int] = Field(default=None, primary_key=True)
    co_id: int = Field(default=1, description="Reference to company.id")

    # ==================== USER FIELDS ====================
    stage: Optional[Stage] = Field(description="Stage of the company")
    round: Optional[Round] = Field(description="Round of the company")
    phase: Optional[Phase] = Field(description="Phase of the company")
    sector: Optional[Sector] = Field(description="Sector of the company")
    sector2: Optional[Sector] = Field(description="Secondary sector of the company")
    sector3: Optional[Sector] = Field(description="Tertiary sector of the company")
    model: Optional[Model] = Field(description="Model of the company")
    model2: Optional[Model] = Field(description="Secondary model of the company")

    # ==================== SYSTEM FIELDS ====================
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def table_name(cls) -> str:
        return "metadata"


# ============================================
# BRAND ENTITY (Parent - Core brand info only)
# ============================================


class BrandEntity(EntityModel, table=True):
    """
    Python Model: BrandEntity
    SQL Table: brand
    Description: Core company brand identity (vision, mission, personality, promise)

    Note: offering, target, and values moved to separate tables:
    - OfferingModel → brand_offerings table
    - TargetModel → brand_targets table
    - ValueModel → brand_values table
    """

    module: ClassVar[str] = "branding"

    # ==================== KEYS ======================
    id: Optional[int] = Field(default=None, primary_key=True)
    co_id: int = Field(default=1, description="Reference to company.id")

    # ==================== USER FIELDS ====================
    vision: Optional[str] = Field(description="Company vision statement")
    mission: Optional[str] = Field(description="Company mission statement")
    personality: Optional[str] = Field(description="Brand personality description")
    promise: Optional[str] = Field(description="Brand promise to customers")
    positioning: Optional[str] = Field(description="Brand unique positioning")

    # ==================== SYSTEM FIELDS ====================
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def table_name(cls) -> str:
        return "brand"


# ============================================
# OFFERING ENTITY RELATED TO BRAND (Key-Value Pairs)
# ============================================


class OfferingEntity(EntityModel, table=True):
    """
    Python Model: OfferingEntity
    SQL Table: brand_offerings
    Description: Company product/service offerings (key-value pairs)

    Examples:
        key="Core Product", value="AI-powered financial analytics platform"
        key="Premium Service", value="White-label solutions for enterprises"
        key="Consulting", value="Strategic advisory for digital transformation"
    """

    # ==================== CLASS METADATA ====================
    cardinality: ClassVar[Cardinality] = Cardinality.MULTIPLE
    module: ClassVar[str] = "branding"

    # ==================== KEYS ==========================
    id: Optional[int] = Field(default=None, primary_key=True)
    brand_id: int = Field(default=1, description="Reference to brand.id")

    # ==================== USER FIELDS Key-Value  ====================
    title: str = Field(..., description="Offering title/category")
    description: str = Field(default="", description="Offering description")

    # ==================== SYSTEM FIELDS ====================
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def table_name(cls) -> str:
        return "brand_offerings"


# ============================================
# TARGET ENTITY RELATED TO BRAND (Key-Value Pairs)
# ============================================


class TargetEntity(EntityModel, table=True):
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

    # ==================== CLASS METADATA ====================
    cardinality: ClassVar[Cardinality] = Cardinality.MULTIPLE
    module: ClassVar[str] = "branding"

    # ==================== KEYS ==========================
    id: Optional[int] = Field(default=None, primary_key=True)
    brand_id: int = Field(default=1, description="Reference to brand.id")

    # ==================== USER FIELDS Key-Value  ====================
    title: str = Field(..., description="Target segment title")
    description: str = Field(default="", description="Target segment description")

    # ==================== SYSTEM FIELDS ====================
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def table_name(cls) -> str:
        return "brand_targets"


# ============================================
# VALUE ENTITY RELATED TO BRAND (Key-Value Pairs)
# ============================================


class ValuesEntity(EntityModel, table=True):
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

    # ==================== CLASS METADATA ====================
    cardinality: ClassVar[Cardinality] = Cardinality.MULTIPLE
    module: ClassVar[str] = "branding"

    # ==================== KEYS ==========================
    id: Optional[int] = Field(default=None, primary_key=True)
    brand_id: int = Field(default=1, description="Reference to brand.id")

    # ==================== USER FIELDS Key-Value  ====================
    key: str = Field(..., description="Value name/title")
    value: str = Field(default="", description="Value description/explanation)")

    # ==================== SYSTEM FIELDS ====================
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def table_name(cls) -> str:
        return "brand_values"


# ============================================
# NEWS ENTITY
# ============================================


class NewsEntity(EntityModel, table=True):
    """
    Python Model: NewsEntity
    SQL Table: news
    Description: news
    """

    # ==================== CLASS METADATA ====================
    cardinality: ClassVar[Cardinality] = Cardinality.MULTIPLE
    module: ClassVar[str] = "market"

    # ==================== KEYS ==========================
    id: Optional[int] = Field(default=None, primary_key=True)
    co_id: int = Field(default=1, description="Reference to company.id")

    # ==================== USER FIELDS ====================
    news_date: date = Field(
        default_factory=date.today, description="Date of the news article"
    )
    headline: str = Field(default="", description="Headline of the news article")
    category: Optional[NewsCategory] = Field(description="Category of the news article")
    content: str = Field(default="", description="News article content")
    link: Optional[str] = Field(description="Link to the news article")

    # ==================== SYSTEM FIELDS ====================
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def table_name(cls) -> str:
        return "news"


# ============================================
# COMPETITOR ENTITY
# ============================================


class CompetitorsEntity(EntityModel, table=True):
    """
    Python Model: CompetitorsEntity
    SQL Table: competitors
    Description: competitors
    """

    # ==================== CLASS METADATA ====================
    cardinality: ClassVar[Cardinality] = Cardinality.MULTIPLE
    module: ClassVar[str] = "market"

    # ==================== KEYS ==========================
    id: Optional[int] = Field(default=None, primary_key=True)
    co_id: int = Field(default=1, description="Reference to company.id")

    # ==================== USER FIELDS ====================
    name: Optional[str] = Field(description="Name of the competitor")
    similarity: Optional[float] = Field(
        default=0.0, description="Similarity score between the two companies"
    )
    comment: Optional[str] = Field(description="Comment about the competitor")
    link: Optional[str] = Field(description="Link to the competitor's website")
    size: Optional[CompetitorSize] = Field(description="Size of the competitor")
    leader: Optional[bool] = Field(
        default=False, description="Is the competitor a leader in the industry"
    )

    # ==================== SYSTEM FIELDS ====================
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def table_name(cls) -> str:
        return "competitors"


# ============================================
# DATABASE MODEL
# ============================================


class CompanyDatabase(SchemaModel):
    name: str = "company"
    description: str = "Single company database"
    tables: ClassVar[List[Type[EntityModel]]] = [
        OrganizationEntity,
        AddressEntity,
        MetadataEntity,
        BrandEntity,
        OfferingEntity,
        TargetEntity,
        ValuesEntity,
        NewsEntity,
        CompetitorsEntity,
    ]
