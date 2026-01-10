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
    update_handler,
    show_handler,
    list_handler,
    delete_handler
)
from ...handlers.navigation import navigate_handler
from ...handlers.wizard import fill_handler


# ==================== ACTION WORDS ====================

ACTION_WORDS: List[ActionWord] = [
    ActionWord(
        id="create",        
        description="Create a new entity (company, milestone, etc.)",
        aliases=["c","post"],
        handler=create_handler,
        crud_operation=CRUDOperation.CREATE,
        database=True,
    ),
    
    ActionWord(
        id="delete",        
        description="Delete an existing entity",
        aliases=["d","remove","rm"],
        handler=delete_handler,
        crud_operation=CRUDOperation.DELETE,
        database=True,        
        destructive=True,
        warning="This action will permanently delete the entity"
    ),
    
    ActionWord(
        id="cd",        
        description="Navigate between contexts (SYS, ORG, APP levels)",
        aliases=[],
        handler=navigate_handler,
        action_category=ActionCategory.NAVIGATION,
        requires_entity=False
    ),
    
    ActionWord(
        id="add",
        description="Add or set field values to entities",
        aliases=["a","set"],
        handler=add_handler,
        crud_operation=CRUDOperation.CREATE,
    ),
    
    ActionWord(
        id="update",
        description="Update existing field values for entities",
        aliases=["u","put", "patch"],
        handler=update_handler,
        crud_operation=CRUDOperation.UPDATE,
    ),
    
    ActionWord(
        id="show",
        description="Display entity data or specific fields",
        aliases=["s","read","get"],
        handler=show_handler,
        crud_operation=CRUDOperation.READ,
    ),
    
    ActionWord(
        id="list",
        description="List all records of entities with multiple cardinality, with optional filtering",
        aliases=["l","ls","find"],
        handler=list_handler,
        crud_operation=CRUDOperation.READ,
    ),
    
    ActionWord(
        id="fill",
        description="displays an intermediate form for filling out",
        aliases=["viz","wiz","f"],
        handler=fill_handler,
        execution_type=ExecutionType.WIZARD,
        crud_operation=CRUDOperation.UPDATE,
        requires_entity=True
    ),
]