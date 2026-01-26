"""
Command model for structured command representation (builder stage).

Contains all information extracted from parsing, ready for handler execution.
"""

from typing import Optional, Dict, Any, List, Union, TYPE_CHECKING, Sequence
from datetime import datetime
from pydantic import BaseModel, Field

from .recognition import RecognizedToken
from .filtering import FilterExpression
from ..words import ActionWord, SchemaWord, EntityWord

if TYPE_CHECKING:
    from .interpretation import InterpretedToken
    from ..validation import ValidationContext


class ParsedCommand(BaseModel):
    """
    Structured representation of a parsed command.
    
    Contains all information needed to execute a command, extracted from
    the token stream and organized into a clean, type-safe structure.
    
    Fields:
        action: The action word (create, update, show, delete, etc.)
        target: The target word (SchemaWord for database ops, EntityWord for table ops)
        target_name: Schema name - name of the target instance ("ACME", "TechCorp", etc.)
        field_values: Field-value pairs ({"currency": "EUR", "vision": "Our vision"})
        field_words: Field names without values (["vision", "mission"])
        raw_input: Original user input text
        command_tokens: All recognized tokens from the parser
    
    Examples:
        >>> # Database operation
        >>> ParsedCommand(
        ...     action=ActionWord(id="create", ...),
        ...     target=SchemaWord(id="company", ...),
        ...     target_name="ACME",
        ...     field_values={"currency": "EUR"},
        ...     raw_input='create company "ACME" currency=EUR',
        ...     command_tokens=[...]
        ... )
        >>> # Table operation  
        >>> ParsedCommand(
        ...     action=ActionWord(id="show", ...),
        ...     target=EntityWord(id="organization", ...),
        ...     target_name=None,
        ...     field_values={},
        ...     raw_input='show organization',
        ...     command_tokens=[...]
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
        description="Schema name - name of the target instance (e.g., 'ACME', 'TechCorp')"
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
    command_tokens: List[Union[RecognizedToken, Any]] = Field(
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
    def entity_model(self):
        """Get the entity_model from target if it's an EntityWord."""
        if isinstance(self.target, EntityWord):
            return self.target.entity_model
        return None
    
    
    @property
    def has_target_name(self) -> bool:
        """True if a target name was provided."""
        return self.target_name is not None and len(self.target_name) > 0
    
    @property
    def has_field_values(self) -> bool:
        """True if any field values were provided."""
        return len(self.field_values) > 0
    
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
    
    @classmethod
    def from_tokens(
        cls,
        tokens: List["InterpretedToken"],
        filter_expression: Optional["FilterExpression"],
        raw_input: str,
        context: "ValidationContext"
    ) -> Optional["ParsedCommand"]:
        """
        Build a ParsedCommand from interpreted tokens.
        
        Uses token properties (is_action_word, is_entity_word, etc.) for clean extraction.
        
        Args:
            tokens: List of interpreted tokens from the parser
            filter_expression: Parsed filter AST (or None)
            raw_input: Original user input text
            context: ValidationContext for error reporting
            
        Returns:
            ParsedCommand if successful, None if building failed
        """
        try:
            # Extract action (required)
            action_token = next((t for t in tokens if t.is_action_word), None)
            if not action_token:
                from vlmx_sh2.enums import IssueStage
                context.add_error(
                    stage=IssueStage.RECOGNIZER,
                    message="No action word found in command",
                    error_code="missing_action"
                )
                return None
            
            # Ensure action_token.word is actually an ActionWord
            if not isinstance(action_token.word, ActionWord):
                from vlmx_sh2.enums import IssueStage
                context.add_error(
                    stage=IssueStage.RECOGNIZER,
                    message=f"Expected ActionWord but got {type(action_token.word)}",
                    error_code="invalid_action_type"
                )
                return None
            
            # Extract optional components using token properties
            target_token = next((t for t in tokens if t.is_schema_word or t.is_entity_word), None)
            target = None
            if target_token:
                # Ensure target is either SchemaWord or EntityWord
                if isinstance(target_token.word, (SchemaWord, EntityWord)):
                    target = target_token.word
                else:
                    from vlmx_sh2.enums import IssueStage
                    context.add_error(
                        stage=IssueStage.RECOGNIZER,
                        message=f"Expected SchemaWord or EntityWord but got {type(target_token.word)}",
                        error_code="invalid_target_type"
                    )
            
            # Extract target name from VALUE or UNKNOWN tokens
            target_name_token = next((t for t in tokens if t.is_value or t.is_unknown), None)
            target_name = target_name_token.text if target_name_token else None
            
            # Extract field=value pairs
            field_values = cls._extract_field_value_pairs(tokens)
            
            # Extract standalone field words (not part of assignments)
            field_words = cls._extract_standalone_field_words(tokens)
            
            # Store the tokens as-is (InterpretedToken should be compatible)
            
            return cls(
                action=action_token.word,
                target=target,
                target_name=target_name,
                field_values=field_values,
                field_words=field_words,
                filters=filter_expression,
                raw_input=raw_input,
                command_tokens=tokens
            )
            
        except Exception as e:
            from vlmx_sh2.enums import IssueStage
            context.add_error(
                stage=IssueStage.RECOGNIZER,
                message=f"Command building failed: {str(e)}"
            )
            return None
    
    @classmethod
    def _extract_field_value_pairs(cls, tokens: List["InterpretedToken"]) -> Dict[str, str]:
        """
        Extract field=value pairs from tokens using pattern matching.
        
        Args:
            tokens: List of interpreted tokens
            
        Returns:
            Dictionary of field names to values
        """
        field_values = {}
        
        # Look for field=value patterns
        i = 0
        while i < len(tokens) - 2:
            field_token = tokens[i]
            operator_token = tokens[i + 1] 
            value_token = tokens[i + 2]
            
            # Check if this is a field assignment pattern
            if (field_token.is_field_word and 
                operator_token.is_structural_token and 
                operator_token.operator and
                value_token.is_value):
                
                field_values[field_token.text] = value_token.text
                i += 3  # Skip the triplet we just processed
            else:
                i += 1
        
        return field_values
    
    @classmethod
    def _extract_standalone_field_words(cls, tokens: List["InterpretedToken"]) -> List[str]:
        """
        Extract field names that are not part of field=value assignments.
        
        Used for commands like 'delete brand vision mission'.
        
        Args:
            tokens: List of interpreted tokens
            
        Returns:
            List of field names
        """
        field_words = []
        
        for i, token in enumerate(tokens):
            if not token.is_field_word:
                continue
                
            # Check if this field is followed by an operator (indicating assignment)
            is_assignment = (i + 1 < len(tokens) and 
                           tokens[i + 1].is_structural_token and 
                           tokens[i + 1].operator)
            
            if not is_assignment:
                field_words.append(token.text)
        
        return field_words
    
