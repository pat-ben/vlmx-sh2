"""
Form and UI ENUMs.

Contains all ENUMs that are visible to users in forms, dropdowns,
and other UI components. These represent user choices and business
domain values that users directly interact with.

Categories:
- Company/Business ENUMs: Legal, Currency, Country, TypeOrg, Unit
- Investment/Finance ENUMs: Stage, Phase, Round, Sector, Model  
- Content ENUMs: NewsCategory, CompetitorSize

All ENUMs in this file should be user-facing and appear in UI elements.
"""

from enum import Enum


# ==================== COMPANY/BUSINESS ENUMs ====================

class Legal(str, Enum):
    """Company legal entity types for user selection."""
    SA = "SA"
    SARL = "SARL"
    SAS = "SAS"
    LLC = "LLC"
    INC = "INC"
    LTD = "LTD"
    GMBH = "GMBH"


class Currency(str, Enum):
    """Supported currencies for financial data."""
    EUR = "EUR"
    USD = "USD"
    GBP = "GBP"
    CHF = "CHF"
    CAD = "CAD"


class Country(str, Enum):
    """Countries for company registration and operations."""
    SWITZERLAND = "Switzerland"
    FRANCE = "France"
    GERMANY = "Germany"
    USA = "USA"
    UK = "UK"
    CANADA = "Canada"
    AUSTRALIA = "Australia"
    NEW_ZEALAND = "New Zealand"
    PORTUGAL = "Portugal"


class TypeOrg(str, Enum):
    """Types of organization allowed in VLMX."""
    COMPANY = "company"  # the most common type of organization
    HOLDING = "holding"  # a holding is a parent company of multiple companies
    SUBSIDIARY = "subsidiary"  # a subsidiary is a company owned by another company
    FUND = "fund"  # a fund is a cluster of multiple companies
    FOUNDATION = "foundation"  # a foundation is a non-profit organization


class Unit(str, Enum):
    """Financial units for displaying monetary amounts."""
    UNITS = "UNITS"
    THOUSANDS = "THOUSANDS"
    MILLIONS = "MILLIONS"


# ==================== INVESTMENT/FINANCE ENUMs ====================

class Stage(str, Enum):
    """Company development stage."""
    EARLY = "early"
    LATE = "late"


class Phase(str, Enum):
    """Company funding/development phase."""
    PREPRODUCT = "pre-product"
    PRETRACTION = "pre-traction"
    PREREVENUE = "pre-revenue"
    PREEBITDA = "pre-ebitda"
    PRECASHFLOW = "pre-cashflow"
    CASHFLOW = "cashflow"


class Round(str, Enum):
    """Investment funding rounds."""
    PRESEED = "pre-seed"
    SEED = "seed"
    SERIESA = "Series A"


class Sector(str, Enum):
    """Business sectors/industries."""
    BIOTECH = "biotech"
    AI = "ai"
    ROBOTICS = "robotics"


class Model(str, Enum):
    """Business models."""
    B2B = "b2b"
    B2C = "b2c"
    B2G = "b2g"


# ==================== CONTENT ENUMs ====================

class NewsCategory(str, Enum):
    """Categories for company news and announcements."""
    PRODUCT = "product"
    MARKET = "market"
    TEAM = "team"


class CompetitorSize(str, Enum):
    """Size categories for competitor analysis."""
    CORPORATE = "corporate"
    SMB = "smb"
    STARTUP = "start-up"