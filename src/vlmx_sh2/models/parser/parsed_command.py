"""
ParsedCommand model for structured command representation.

Contains all information extracted from parsing, ready for handler execution.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

from .recognized_token import RecognizedToken
from .filter import FilterExpression
from ..words import ActionWord, SchemaWord, EntityWord, FieldWord
from typing import Union


class ParsedCommand(BaseModel):
    """
    Structured representation of a parsed command.
    
    Contains all information needed to execute a command, extracted from
    the token stream and organized into a clean, type-safe structure.
    
    Fields:
        action: The action word (create, update, show, delete, etc.)
        target: The target word (SchemaWord for database ops, EntityWord for table ops)
        target_name: The name of the target instance ("ACME", "TechCorp", etc.)
        attributes: Field-value pairs ({"currency": "EUR", "vision": "Our vision"})
        field_words: Field names without values (["vision", "mission"])
        raw_input: Original user input text
        tokens: All recognized tokens from the parser
    
    Examples:
        >>> # Database operation
        >>> ParsedCommand(
        ...     action=ActionWord(id="create", ...),
        ...     target=SchemaWord(id="company", ...),
        ...     target_name="ACME",
        ...     attributes={"currency": "EUR"},
        ...     raw_input='create company "ACME" currency=EUR',
        ...     tokens=[...]
        ... )
        >>> # Table operation  
        >>> ParsedCommand(
        ...     action=ActionWord(id="show", ...),
        ...     target=EntityWord(id="organization", ...),
        ...     target_name=None,
        ...     attributes={},
        ...     raw_input='show organization',
        ...     tokens=[...]
        ... )
    """
    
    # Core command components
    action: ActionWord = Field(
        description="The action to perform (create, update, show, delete)"
    )
    target: Optional[Union[SchemaWord, EntityWord]] = Field(
        default=None,
        description="The target to operate on. SchemaWord for database operations, EntityWord for table operations. None for navigation commands."
    )
    
    # Command data
    target_name: Optional[str] = Field(
        default=None,
        description="Name of the target instance (e.g., 'ACME', 'TechCorp')"
    )
    field_values: Dict[str, str] = Field(
        default_factory=dict,
        description="Field-value pairs for entity attributes"
    )
    field_words: List[str] = Field(
        default_factory=list,
        description="Field names without values (for selection/deletion)"
    )
    
    # Metadata
    raw_input: str = Field(
        description="Original user input text"
    )
    command_tokens: List[RecognizedToken] = Field(
        default_factory=list,
        description="All recognized tokens from parsing (command tokens)"
    )
    
    # Filter tokens
    filter_tokens: List[RecognizedToken] = Field(
        default_factory=list,
        description="Recognized tokens from filter expression"
    )
    
    # Filtering
    filters: Optional[FilterExpression] = Field(
        default=None,
        description="Parsed filter expression for list/show commands"
    )
    
    class Config:
        arbitrary_types_allowed = True
    
    @property
    def is_database_operation(self) -> bool:
        """True if operating on database level (SchemaWord)."""
        return isinstance(self.target, SchemaWord)
    
    @property
    def is_entity_operation(self) -> bool:
        """True if operating on entity/table level (EntityWord)."""
        return isinstance(self.target, EntityWord)
    
    @property
    def target_model(self):
        """Get the schema_class or entity_model from target."""
        if isinstance(self.target, SchemaWord):
            return self.target.schema_class
        elif isinstance(self.target, EntityWord):
            return self.target.entity_model
        return None
    
    @property
    def action_handler(self):
        """Get the handler function from the action word."""
        return self.action.handler
    
    # ==================== BACKWARD COMPATIBILITY ====================
    # These properties will be removed in Phase 5
    
    @property
    def entity(self):
        """Deprecated: use target instead."""
        return self.target
    
    @property
    def entity_name(self):
        """Deprecated: use target_name instead."""
        return self.target_name
    
    @property
    def entity_model(self):
        """Deprecated: use target_model instead."""
        if isinstance(self.target, EntityWord):
            return self.target.entity_model
        return None
    
    @property
    def has_target_name(self) -> bool:
        """True if a target name was provided."""
        return self.target_name is not None and len(self.target_name) > 0
    
    @property
    def has_entity_name(self) -> bool:
        """Deprecated: use has_target_name instead."""
        return self.has_target_name
    
    @property
    def has_field_values(self) -> bool:
        """True if any field values were provided."""
        return len(self.field_values) > 0
    
    @property
    def has_attributes(self) -> bool:
        """Deprecated: use has_field_values instead."""
        return self.has_field_values
    
    @property
    def has_filters(self) -> bool:
        """True if any filters were provided."""
        return self.filters is not None
    
    def get_target_data(self) -> Dict[str, Any]:
        """
        Get target data for creation/update operations.
        
        Returns:
            Dictionary with target name and attributes ready for model validation
        """
        data = {}
        
        # Add target name if provided
        if self.has_target_name:
            data["name"] = self.target_name
        
        # Add all field values
        data.update(self.field_values)
        
        # Add timestamps for creation
        if self.action.crud_operation.value == "create":
            now = datetime.now().isoformat()
            data.setdefault("created_at", now)
            data.setdefault("updated_at", now)
        
        return data
    
    def get_entity_data(self) -> Dict[str, Any]:
        """Deprecated: use get_target_data instead."""
        return self.get_target_data()