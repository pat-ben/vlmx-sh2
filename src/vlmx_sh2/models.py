""" This files includes pydantic models that should match
1:1 SQL tables. Each model represents a table in the database.
Operational models may differ from the database schema.
    
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from vlmx_sh2.enum import Entity, Currency, Unit
import datetime

from pydantic.types import date



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
        orm_mode = True
        use_enum_values = True
        
    @classmethod
    def table_name(cls) -> str:
        """Returns the SQL table name for this model"""
        raise NotImplementedError


# ============================================
# TABLE MODELS (1:1 with SQL tables)
# ============================================

class CompanyModel(DatabaseModel):
    """
    Python Model: CompanyModel
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
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def table_name(cls) -> str:
        return "company"


class MetadataModel(DatabaseModel):
    """
    Python Model: MetadataModel
    SQL Table: metadata
    Description: Extended company metadata (key-value pairs)
    """
    id: Optional[int] = None
    company_id: int = Field(..., description="Reference to company.id")
    key: str = Field(..., description="Metadata key")
    value: str = Field(..., description="Metadata value")
    data_type: Literal["string", "number", "boolean", "date"] = Field(default="string")
    description: Optional[str] = Field(None, description="Description of this metadata")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @classmethod
    def table_name(cls) -> str:
        return "metadata"


class BrandModel(DatabaseModel):
    """
    Python Model: BrandModel
    SQL Table: brand
    Description: Company brand identity (vision, mission, values, promise)
    """
    id: Optional[int] = None
    company_id: int = Field(..., description="Reference to company.id")
    vision: Optional[str] = Field(None, description="Company vision")
    mission: Optional[str] = Field(None, description="Company mission")
    values: Optional[str] = Field(None, description="Company values (JSON or text)")
    promise: Optional[str] = Field(None, description="Brand promise")
    tagline: Optional[str] = Field(None, description="Company tagline")
    positioning: Optional[str] = Field(None, description="Market positioning")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @classmethod
    def table_name(cls) -> str:
        return "brand"


class DocsModel(DatabaseModel):
    """
    Python Model: DocsModel
    SQL Table: docs
    Description: Document references (Microsoft files + PDF)
    """
    id: Optional[int] = None
    company_id: int = Field(..., description="Reference to company.id")
    file_name: str = Field(..., description="Document filename")
    file_path: str = Field(..., description="Path to document")
    file_type: DocumentType = Field(..., description="Document type")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    description: Optional[str] = Field(None, description="Document description")
    category: Optional[str] = Field(None, description="Document category")
    tags: Optional[str] = Field(None, description="Tags (comma-separated or JSON)")
    uploaded_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @classmethod
    def table_name(cls) -> str:
        return "docs"


class JsonModel(DatabaseModel):
    """
    Python Model: JsonModel
    SQL Table: json
    Description: Standardized JSON data (accounting, budget, planning)
    """
    id: Optional[int] = None
    company_id: int = Field(..., description="Reference to company.id")
    data_type: JsonDataType = Field(..., description="Type of JSON data")
    json_content: str = Field(..., description="JSON content as string")
    period_date: Optional[date] = Field(None, description="Period this data relates to")
    fiscal_year: Optional[int] = Field(None, description="Fiscal year")
    status: Literal["DRAFT", "FINAL", "ARCHIVED"] = Field(default="DRAFT")
    description: Optional[str] = Field(None, description="Description of this JSON data")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @classmethod
    def table_name(cls) -> str:
        return "json"


class DataModel(DatabaseModel):
    """
    Python Model: DataModel
    SQL Table: data
    Description: Key financial data (fundamentals)
    """
    id: Optional[int] = None
    company_id: int = Field(..., description="Reference to company.id")
    period_date: date = Field(..., description="Period end date")
    fiscal_year: int = Field(..., description="Fiscal year")
    status: Literal["ACTUAL", "PLAN", "FORECAST", "BUDGET"] = Field(default="ACTUAL")
    
    # Financial metrics
    revenue: Optional[float] = Field(None, description="Revenue")
    ebitda: Optional[float] = Field(None, description="EBITDA")
    equity: Optional[float] = Field(None, description="Equity")
    debt: Optional[float] = Field(None, description="Debt")
    cash: Optional[float] = Field(None, description="Cash")
    grants: Optional[float] = Field(None, description="Grants")
    
    # Metadata
    notes: Optional[str] = Field(None, description="Notes about this period")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @classmethod
    def table_name(cls) -> str:
        return "data"


class MetricsModel(DatabaseModel):
    """
    Python Model: MetricsModel
    SQL Table: metrics
    Description: Company metrics (KPIs, performance indicators)
    """
    id: Optional[int] = None
    company_id: int = Field(..., description="Reference to company.id")
    metric_name: str = Field(..., description="Name of the metric")
    metric_value: float = Field(..., description="Metric value")
    metric_unit: Optional[str] = Field(None, description="Unit of measurement")
    period_date: date = Field(..., description="Period this metric relates to")
    category: Optional[str] = Field(None, description="Metric category")
    description: Optional[str] = Field(None, description="Metric description")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @classmethod
    def table_name(cls) -> str:
        return "metrics"


class MilestonesModel(DatabaseModel):
    """
    Python Model: MilestonesModel
    SQL Table: milestones
    Description: Company milestones
    """
    id: Optional[int] = None
    company_id: int = Field(..., description="Reference to company.id")
    title: str = Field(..., description="Milestone title")
    description: Optional[str] = Field(None, description="Milestone description")
    target_date: Optional[date] = Field(None, description="Target completion date")
    actual_date: Optional[date] = Field(None, description="Actual completion date")
    status: MilestoneStatus = Field(default=MilestoneStatus.ACTIVE, description="Milestone status")
    priority: Literal["HIGH", "MEDIUM", "LOW"] = Field(default="MEDIUM")
    category: Optional[str] = Field(None, description="Milestone category")
    progress: Optional[int] = Field(None, ge=0, le=100, description="Progress percentage")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @classmethod
    def table_name(cls) -> str:
        return "milestones"


class NewsModel(DatabaseModel):
    """
    Python Model: NewsModel
    SQL Table: news
    Description: Company news and announcements
    """
    id: Optional[int] = None
    company_id: int = Field(..., description="Reference to company.id")
    date: date = Field(..., description="News date")
    headline: str = Field(..., description="News headline")
    content: Optional[str] = Field(None, description="Full news content")
    source: Optional[str] = Field(None, description="News source")
    url: Optional[str] = Field(None, description="URL to original news")
    category: Optional[str] = Field(None, description="News category")
    tags: Optional[str] = Field(None, description="Tags (comma-separated or JSON)")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @classmethod
    def table_name(cls) -> str:
        return "news"
