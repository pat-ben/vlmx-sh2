"""
ParsedCommand model for structured command representation.

Contains all information extracted from parsing, ready for handler execution.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

from .recognized_token import RecognizedToken
from ..words import ActionWord, EntityWord, AttributeWord


class ParsedCommand(BaseModel):
    """
    Structured representation of a parsed command.
    
    Contains all information needed to execute a command, extracted from
    the token stream and organized into a clean, type-safe structure.
    
    Fields:
        action: The action word (create, update, show, delete, etc.)
        entity: The entity word (company, fund, metadata, etc.)
        entity_name: The name of the entity instance ("ACME", "TechCorp", etc.)
        attributes: Field-value pairs ({"currency": "EUR", "vision": "Our vision"})
        raw_input: Original user input text
        tokens: All recognized tokens from the parser
    
    Examples:
        >>> ParsedCommand(
        ...     action=ActionWord(id="create", ...),
        ...     entity=EntityWord(id="company", ...),
        ...     entity_name="ACME",
        ...     attributes={"currency": "EUR"},
        ...     raw_input='create company "ACME" currency=EUR',
        ...     tokens=[...]
        ... )
    """
    
    # Core command components
    action: ActionWord = Field(
        description="The action to perform (create, update, show, delete)"
    )
    entity: Optional[EntityWord] = Field(
        default=None,
        description="The entity type to operate on (company, fund, metadata). None for navigation commands."
    )
    
    # Command data
    entity_name: Optional[str] = Field(
        default=None,
        description="Name of the entity instance (e.g., 'ACME', 'TechCorp')"
    )
    attributes: Dict[str, str] = Field(
        default_factory=dict,
        description="Field-value pairs for entity attributes"
    )
    
    # Metadata
    raw_input: str = Field(
        description="Original user input text"
    )
    tokens: List[RecognizedToken] = Field(
        default_factory=list,
        description="All recognized tokens from parsing"
    )
    
    class Config:
        arbitrary_types_allowed = True
    
    @property
    def entity_model(self):
        """Get the entity model class from the entity word."""
        return self.entity.entity_model if self.entity else None
    
    @property
    def action_handler(self):
        """Get the handler function from the action word."""
        return self.action.handler
    
    @property
    def has_entity_name(self) -> bool:
        """True if an entity name was provided."""
        return self.entity_name is not None and len(self.entity_name) > 0
    
    @property
    def has_attributes(self) -> bool:
        """True if any attributes were provided."""
        return len(self.attributes) > 0
    
    def get_entity_data(self) -> Dict[str, Any]:
        """
        Get entity data for creation/update operations.
        
        Returns:
            Dictionary with entity name and attributes ready for model validation
        """
        data = {}
        
        # Add entity name if provided
        if self.has_entity_name:
            data["name"] = self.entity_name
        
        # Add all attributes
        data.update(self.attributes)
        
        # Add timestamps for creation
        if self.action.crud_operation.value == "create":
            now = datetime.now().isoformat()
            data.setdefault("created_at", now)
            data.setdefault("updated_at", now)
        
        return data