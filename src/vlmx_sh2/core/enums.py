
"""
Enum definitions for the VLMX DSL.

Defines word types, operation levels, entity types, currencies, and other
enumerated values used throughout the command parsing and execution system.
"""

from enum import Enum, IntEnum

### ENUM for words


class WordType(Enum):
    ACTION = "action"  # verbs only (eg. create, update, delete)
    ENTITY = "entity"  # noun only :An entity is an Pydantic model which corresponds to a SQL table (eg. MetadataModel => metadata table)
    FIELD = "field"  # noun or adjective: Pydantic model's fields which correspond to SQL table columns (eg. currency field => currency column)
    

### ENUM for operations

class OperationLevel(str, Enum):
    """Level at which an action operates"""
    DATABASE = "database"  # e.g., backup, restore
    ENTITY = "entity"        # e.g., create table, drop table
    ATTRIBUTE = "attribute"  # e.g., update, delete attribute
    

class CRUDOperation(str, Enum):
    """ Specific CRUD operation type."""    
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    NONE = "none"


class ActionCategory(str, Enum):
    """ Broad category of what an action does. """
    CRUD = "crud"
    NAVIGATION = "navigation"
    SYSTEM = "system"
    ANALYSIS = "analysis"
    IMPORT_EXPORT = "import_export"


class TokenType(str, Enum):
    """Type classification for parsed tokens"""
    WORD = "word"        # Token that matches a Word in the registry
    VALUE = "value"      # Token representing a value (company name, etc.)
    UNKNOWN = "unknown"  # Token that doesn't match any known pattern

class ContextLevel(IntEnum):
    SYS = 0 # system / root level
    ORG = 1 # organization level (most of the time company)
    APP = 2 # application level (could be plugin)


### ENUM for requirements

class RequirementType(Enum):
    """Defines whether a word/attribute is required in a command"""
    REQUIRED = "required"           # Must be present
    OPTIONAL = "optional"           # Can be omitted
    CONDITIONAL = "conditional"     # Required under certain conditions


### Company Enums


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


class Type(str, Enum):
    """Types of organization allowed in VLMX"""
    COMPANY = "company"  # the most common type of organization
    FUND = "fund"  # a fund is a cluster of multiple companies
    FOUNDATION = "individual"  # an individual is a person


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


