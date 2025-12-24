from enum import Enum, IntEnum

### ENUM for words


class WordType(Enum):
    ACTION = "action"  # verbs only (eg. create, update, delete)
    MODIFIER = "modifier"  # adjectives or nouns that modify an entity (only one adjective per entity). Additional filers can be added with where"
    ENTITY = "entity"  # noun only :An entity is an Pydantic model which corresponds to a SQL table (eg. MetadataModel => metadata table)
    ATTRIBUTE = "attribute"  # noun or adjective: attributes are Pydantic model's fields which correspond to SQL table columns (eg. currency field => currency column)
    FILTER = "filter"  # preposition: Filters are used to filter entities (eg. where id=5)


### ENUM for operations

class OperationLevel(str, Enum):
    """Level at which an action operates"""
    DATABASE = "database"  # e.g., backup, restore
    TABLE = "table"        # e.g., create table, drop table
    ATTRIBUTE = "attribute"  # e.g., update, delete attribute
    ROW = "row"            # e.g., create, update, delete record
    QUERY = "query"        # e.g., show, filter
    SYSTEM = "system"      # e.g., create, update, delete record

class ActionCategory(str, Enum):
    """ Broad category of what an action does. """
    CRUD = "crud"
    NAVIGATION = "navigation"
    SYSTEM = "system"
    ANALYSIS = "analysis"
    IMPORT_EXPORT = "import_export"

class CRUDOperation(str, Enum):
    """ Specific CRUD operation type."""    
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    NONE = "none"

class TokenType(str, Enum):
    """Type classification for parsed tokens"""
    WORD = "word"        # Token that matches a Word in the registry
    VALUE = "value"      # Token representing a value (company name, etc.)
    FLAG = "flag"        # Command-line style flag (--key=value)
    UNKNOWN = "unknown"  # Token that doesn't match any known pattern

class ContextLevel(IntEnum):
    SYS = 0
    ORG = 1
    APP = 2


### ENUM for requirements

class RequirementType(Enum):
    """Defines whether a word/attribute is required in a command"""
    REQUIRED = "required"           # Must be present
    OPTIONAL = "optional"           # Can be omitted
    CONDITIONAL = "conditional"     # Required under certain conditions


### Company Enums

class Entity(str, Enum):
    """Company entity types"""

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


