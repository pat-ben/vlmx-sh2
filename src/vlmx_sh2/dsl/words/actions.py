"""
Action word definitions.

Contains all manually defined ActionWord objects with their handlers, aliases,
and metadata. These words require custom handlers and are maintained manually
while EntityWord and FieldWord objects are auto-generated.
"""

from typing import List

from ...models.words import ActionWord, ActionCategory, CRUDOperation, ExecutionType

# Import handlers
from ...handlers.crud import (
    create_handler,
    add_handler,
    show_handler,
    delete_handler,
    drop_handler,
    reset_handler
)
from ...handlers.navigation import navigate_handler
from ...handlers.wizard import fill_handler


# ==================== ACTION WORDS ====================

ACTION_WORDS_LIST: List[ActionWord] = [
    ActionWord(
        id="create",        
        description="Create a new entity (company, milestone, etc.)",
        aliases=["c","post"],
        handler=create_handler,
        crud_operation=CRUDOperation.CREATE,
    ),
    
    ActionWord(
        id="delete",        
        description="Delete data (rows, fields, or all entity content)",
        aliases=["d"],
        handler=delete_handler,
        crud_operation=CRUDOperation.DELETE,        
        destructive=True,
        warning="This action will permanently delete the data"
    ),
    
    ActionWord(
        id="drop",
        description="Drop database or table structure",
        aliases=["remove", "rm"],
        handler=drop_handler,
        crud_operation=CRUDOperation.DELETE,
        destructive=True,
        warning="This action will permanently remove the structure"
    ),
    
    ActionWord(
        id="cd",        
        description="Navigate between contexts (SYS, ORG, APP levels)",
        aliases=[],
        handler=navigate_handler,
        action_category=ActionCategory.NAVIGATION,
    ),
    
    ActionWord(
        id="add",
        description="Add or set field values to entities",
        aliases=["a","set"],
        handler=add_handler,
        crud_operation=CRUDOperation.CREATE,
    ),
    
    ActionWord(
        id="reset",
        description="Reset entity or fields to default values",
        aliases=["clear", "restore"],
        handler=reset_handler,
        crud_operation=CRUDOperation.UPDATE,
    ),
    
    ActionWord(
        id="show",
        description="Display data with optional field selection and filtering",
        aliases=["s","read","get","l","ls","list","find"],
        handler=show_handler,
        crud_operation=CRUDOperation.READ,
    ),
    
    ActionWord(
        id="fill",
        description="displays an intermediate form for filling out",
        aliases=["viz","wiz","f"],
        handler=fill_handler,
        execution_type=ExecutionType.WIZARD,
        crud_operation=CRUDOperation.UPDATE,
    ),
]