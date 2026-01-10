"""
Action word definitions.

Contains all manually defined ActionWord objects with their handlers, aliases,
and metadata. These words require custom handlers and are maintained manually
while EntityWord and FieldWord objects are auto-generated.
"""

from typing import List

from ..models.words import ActionWord
from ..models.words import ActionCategory, CRUDOperation, ContextLevel, ExecutionType

# Import handlers
from ..handlers.crud import (
    create_handler,
    add_handler,
    update_handler,
    show_handler,
    list_handler,
    delete_handler
)
from ..handlers.navigation import navigate_handler
from ..handlers.wizard import fill_handler


# ==================== ACTION WORDS ====================

ACTION_WORDS: List[ActionWord] = [
    ActionWord(
        id="create",
        context=ContextLevel.SYS,
        description="Create a new entity (company, milestone, etc.)",
        aliases=["c","post"],
        handler=create_handler,
        action_category=ActionCategory.CRUD,
        crud_operation=CRUDOperation.CREATE,
        database=True,
    ),
    
    ActionWord(
        id="delete",
        context=ContextLevel.SYS,
        description="Delete an existing entity",
        aliases=["d","remove","rm"],
        handler=delete_handler,
        action_category=ActionCategory.CRUD,
        crud_operation=CRUDOperation.DELETE,
        database=True,        
        destructive=True,
        warning="This action will permanently delete the entity"
    ),
    
    ActionWord(
        id="cd",
        context=ContextLevel.SYS,  # Available from SYS level and up (all levels)
        description="Navigate between contexts (SYS, ORG, APP levels)",
        aliases=[],
        handler=navigate_handler,
        action_category=ActionCategory.NAVIGATION,
        crud_operation=CRUDOperation.NONE,
        requires_entity=False
    ),
    
    ActionWord(
        id="add",
        context=ContextLevel.ORG,
        description="Add or set field values to entities",
        aliases=["a","set"],
        handler=add_handler,
        action_category=ActionCategory.CRUD,
        crud_operation=CRUDOperation.CREATE,
    ),
    
    ActionWord(
        id="update",
        context=ContextLevel.ORG,
        description="Update existing field values for entities",
        aliases=["u","put", "patch"],
        handler=update_handler,
        action_category=ActionCategory.CRUD,
        crud_operation=CRUDOperation.UPDATE,
    ),
    
    ActionWord(
        id="show",
        context=ContextLevel.ORG,
        description="Display entity data or specific fields",
        aliases=["s","read","get"],
        handler=show_handler,
        action_category=ActionCategory.CRUD,
        crud_operation=CRUDOperation.READ,
    ),
    
    ActionWord(
        id="list",
        context=ContextLevel.ORG,
        description="List all records of entities with multiple cardinality, with optional filtering",
        aliases=["l","ls","find"],
        handler=list_handler,
        action_category=ActionCategory.CRUD,
        crud_operation=CRUDOperation.READ,
    ),
    
    ActionWord(
        id="fill",
        context=ContextLevel.ORG,
        description="displays an intermediate form for filling out",
        aliases=["viz","wiz","f"],
        handler=fill_handler,
        execution_type=ExecutionType.WIZARD,
        action_category=ActionCategory.CRUD,
        crud_operation=CRUDOperation.UPDATE,
        requires_entity=True
    ),
]