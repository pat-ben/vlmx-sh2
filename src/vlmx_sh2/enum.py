from enum import Enum

### ENUM for keywords


class KeywordType(Enum):
    VERB = "verb"
    NOUN = "noun"
    ADJECTIVE = "adjective"
    PREPOSITION = "preposition"


class KeywordUsage(Enum):
    ACTION = "action"  # verbs only (eg. create, update, delete)
    MODIFIER = "modifier"  # adjectives or nouns that modify an entity (only one adjective per entity). Additional filers can be added with where"
    ENTITY = "entity"  # noun only :An entity is an Pydantic model which corresponds to a SQL table (eg. MetadataModel => metadata table)
    ATTRIBUTE = "attribute"  # noun or adjective: attributes are Pydantic model's fields which correspond to SQL table columns (eg. key field => key column)
    FILTER = (
        "filter"  # preposition: Filters are used to filter entities (eg. where id=5)
    )


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


