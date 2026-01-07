"""
Enum definitions for VLMX schema.

"""

from enum import Enum


class Cardinality(str, Enum):
    """Entity cardinality types"""
    
    SINGLE = "single"
    MULTIPLE = "multiple"


class Legal(str, Enum):
    """Company legal entity types"""

    SA = "SA"
    SARL = "SARL"
    SAS = "SAS"
    HOLDING = "HOLDING"
    OPERATING = "OPERATING"
    LLC = "LLC"
    INC = "INC"
    LTD = "LTD"
    GMBH = "GMBH"
    
class Currency(str, Enum):
    """Supported currencies"""

    EUR = "EUR"
    USD = "USD"
    GBP = "GBP"
    CHF = "CHF"
    CAD = "CAD"

class Country(str, Enum):
    """Company legal entity types"""

    SWITZERLAND = "Switzerland"
    FRANCE = "France"
    GERMANY = "Germany"
    USA = "USA"
    UK = "UK"
    CANADA = "Canada"
    AUSTRALIA = "Australia"
    NEW_ZEALAND = "New Zealand"
    PORTUGAL = "Portugal"

class Stage(str, Enum):
    """Company legal entity types"""

    early = "early"
    LATE = "late"

class Phase(str, Enum):
    """Company legal entity types"""

    PREPRODUCT = "pre-product"
    PRETRACTION = "pre-traction"
    PREREVENUE = "pre-revenue"
    PREEBITDA = "pre-ebitda"
    PRECASHFLOW = "pre-cashflow"
    CASHFLOW = "cashflow"

class NewsCategory(str, Enum):
    """Company legal entity types"""

    PRODUCT = "product"
    MARKET = "market"
    TEAM = "team"

class CompetitorSize(str, Enum):
    """Company legal entity types"""

    CORPORATE = "corporate"
    SMB = "smb"
    STARTUP = "start-up"

class Sector(str, Enum):
    """Company legal entity types"""

    BIOTECH = "biotech"
    AI = "ai"
    ROBOTICS = "robotics"

class Model(str, Enum):
    """Company legal entity types"""

    B2B = "b2b"
    B2C = "b2c"
    B2G = "b2g"

class Round(str, Enum):
    """Company legal entity types"""

    PRESEED = "pre-seed"
    SEED = "seed"
    SERIESA = "Series A"


class Unit(str, Enum):
    """Financial units"""

    THOUSANDS = "THOUSANDS"
    MILLIONS = "MILLIONS"


class TypeOrg(str, Enum):
    """Types of organization allowed in VLMX"""
    COMPANY = "company"  # the most common type of organization
    FUND = "fund"  # a fund is a cluster of multiple companies
    FOUNDATION = "individual"  # an individual is a person
