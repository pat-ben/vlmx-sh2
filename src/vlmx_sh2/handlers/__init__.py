"""
Command execution handlers for VLMX DSL.

Provides truly dynamic handlers that work with any entity-attribute
combination without hardcoded entity-specific logic.
"""

from .crud import (
    create_handler,
    add_handler,
    update_handler,
    show_handler,
    delete_handler
)
from .navigation import navigate_handler

__all__ = [
    'create_handler',
    'add_handler', 
    'update_handler',
    'show_handler',
    'delete_handler',
    'navigate_handler'
]