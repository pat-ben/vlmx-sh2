"""
Enum definitions for VLMX schema.

"""

from enum import Enum


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


class Unit(str, Enum):
    """Financial units"""

    THOUSANDS = "THOUSANDS"
    MILLIONS = "MILLIONS"


class Type(str, Enum):
    """Types of organization allowed in VLMX"""
    COMPANY = "company"  # the most common type of organization
    FUND = "fund"  # a fund is a cluster of multiple companies
    FOUNDATION = "individual"  # an individual is a person
