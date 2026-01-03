"""
Command execution handlers.

Provides truly dynamic handlers that work with any entity-field
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
from .wizard import fill_handler

__all__ = [
    'create_handler',
    'add_handler', 
    'update_handler',
    'show_handler',
    'delete_handler',
    'navigate_handler',
    'fill_handler'
]