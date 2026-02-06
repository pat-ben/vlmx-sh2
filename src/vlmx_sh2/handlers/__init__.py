"""
Command execution handlers.

Provides truly dynamic handlers that work with any entity-field
combination without hardcoded entity-specific logic.
"""

from .crud import (
    create_handler,
    add_handler,
    show_handler,
    delete_handler,
    drop_handler,
    reset_handler
)
from .navigation import navigate_handler
from .wizard import fill_handler
from .apps import apply_handler, run_handler

__all__ = [
    'create_handler',
    'add_handler', 
    'show_handler',
    'delete_handler',
    'drop_handler',
    'reset_handler',
    'navigate_handler',
    'fill_handler',
    'apply_handler',
    'run_handler'
]