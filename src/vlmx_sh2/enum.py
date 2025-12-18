from enum import Enum


### ENUM for keywords

class KeywordType(Enum):
    VERB = "verb"
    NOUN = "noun"
    ADJECTIVE = "adjective"
    PREPOSITION = "preposition"

class KeywordUsage(Enum):
    ACTION = "action"          #
    MODIFIER = "modifier"
    ENTITY = "entity" 
    PROPERTY = "property"


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


