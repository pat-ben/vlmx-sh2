"""
PARSING STAGE 7/7: Command Building

Assembles ParsedCommand from interpreted tokens.
Extracts action, target, field values from tokens and assembles a ParsedCommand.

This stage operates on interpreted tokens to extract command components:
- Action words (create, add, delete, etc.)
- Target schemas/entities (company, brand, etc.)  
- Target names (quoted strings or unknown tokens)
- Field-value pairs (currency=EUR, vision="Our vision")
- Standalone field words (for field selection/deletion)
"""

from typing import Optional, List, Dict, Any
from ..models.parser import ParsedCommand
from ..models.parser.filtering import FilterExpression
from ..models.validation import ValidationContext
from ..words.registry import get_word
from ..models.words import ActionWord, SchemaWord, EntityWord


class Builder:
    """
    Thin wrapper for ParsedCommand.from_tokens().
    
    Maintains consistency with other parsing stages while delegating
    the actual command building logic to ParsedCommand itself.
    """
    
    # =============================================================================
    # Public API - Main Entry Point
    # =============================================================================
    
    @classmethod
    def build(
        cls,
        command_tokens: List,
        filter_expression: Optional[FilterExpression],
        raw_input: str,
        context: ValidationContext
    ) -> Optional[ParsedCommand]:
        """
        Build ParsedCommand from command tokens and filter AST.
        
        Delegates to ParsedCommand.from_tokens() for the actual building logic.
        
        Args:
            command_tokens: Interpreted tokens from splitter (command portion)
            filter_expression: Parsed filter AST (or None)
            raw_input: Original user input
            context: ValidationContext for error reporting
            
        Returns:
            ParsedCommand if successful, None if building failed
        """
        return ParsedCommand.from_tokens(
            tokens=command_tokens,
            filter_expression=filter_expression,
            raw_input=raw_input,
            context=context
        )
    
    @classmethod
    def from_wizard(
        cls,
        action_id: str,
        entity_id: str,
        entity_name: Optional[str],
        field_values: Dict[str, Any],
        record_id: Optional[str] = None
    ) -> Optional[ParsedCommand]:
        """
        Build ParsedCommand from wizard submission data.
        
        This method enables wizard submissions to use the same unified command
        pipeline as standard text commands by constructing a ParsedCommand
        from structured form data instead of parsing tokens.
        
        Args:
            action_id: The action to perform (e.g., "add", "update")
            entity_id: The entity type (e.g., "organization", "brand") 
            entity_name: Optional entity name/target name
            field_values: Form data submitted by user
            record_id: For updates, the ID of record being updated
            
        Returns:
            ParsedCommand if successful, None if building failed
        """
        try:
            # Look up the ActionWord
            action_word = get_word(action_id)
            if not action_word or not isinstance(action_word, ActionWord):
                return None
            
            # Look up the target (SchemaWord or EntityWord)
            target_word = get_word(entity_id)
            if not target_word or not isinstance(target_word, (SchemaWord, EntityWord)):
                return None
            
            # Convert field_values to strings (handlers expect string values)
            string_field_values = {
                key: str(value) if value is not None else ""
                for key, value in field_values.items()
            }
            
            # Add record_id as a special filter-like field if present (for updates)
            if record_id is not None:
                # For updates, we can either:
                # 1. Add record_id to field_values as a special field
                # 2. Create a filter expression
                # For now, let's add it to field_values and let handlers decide
                string_field_values['_record_id'] = str(record_id)
            
            # Construct raw_input for debugging/logging purposes
            field_pairs = [f"{k}={v}" for k, v in string_field_values.items() if not k.startswith('_')]
            raw_input_parts = [action_id, entity_id]
            if entity_name:
                raw_input_parts.append(f'"{entity_name}"')
            raw_input_parts.extend(field_pairs)
            raw_input = " ".join(raw_input_parts)
            
            return ParsedCommand(
                action=action_word,
                target=target_word,
                target_name=entity_name,
                field_values=string_field_values,
                field_words=[],
                filters=None,
                raw_input=f"[WIZARD] {raw_input}",
                command_tokens=[]
            )
            
        except Exception:
            # If anything goes wrong during building, return None
            # The CommandExecutor will handle this gracefully
            return None