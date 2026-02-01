"""
CommandBuilder - Stage 7 of parsing and wizard command construction.

Unified command builder that constructs ParsedCommand from two sources:
1. from_tokens() - Build from interpreted tokens (stage 7 of text parsing)  
2. from_wizard() - Build from wizard form submission data

This separates command construction logic from the parser/ module, which should
only handle text analysis (stages 0-6). CommandBuilder lives in core/ because
it's orchestration logic, not parsing logic.
"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from ..models.parser import ParsedCommand
from ..models.parser.filtering import FilterExpression
from ..models.validation import ValidationContext
from ..dsl.registry import get_word
from ..models.words import ActionWord, SchemaWord, EntityWord

if TYPE_CHECKING:
    from ..models.parser.interpretation import InterpretedToken


class CommandBuilder:
    """
    Unified command builder for all ParsedCommand construction.
    
    Handles stage 7 of the parsing pipeline for text commands and also
    provides wizard form submission command building. This is the single
    place where ParsedCommand objects are constructed.
    """
    
    # =============================================================================
    # Text Command Building (Stage 7 of parsing pipeline)
    # =============================================================================
    
    @classmethod
    def from_tokens(
        cls,
        command_tokens: List["InterpretedToken"],
        filter_expression: Optional[FilterExpression],
        raw_input: str,
        context: ValidationContext
    ) -> Optional[ParsedCommand]:
        """
        Build ParsedCommand from interpreted tokens (stage 7 of parsing).
        
        This method handles the final stage of text command parsing, extracting
        action, target, field values from tokens and constructing a ParsedCommand.
        
        Args:
            command_tokens: Interpreted tokens from splitter (command portion)
            filter_expression: Parsed filter AST (or None)
            raw_input: Original user input text
            context: ValidationContext for error reporting
            
        Returns:
            ParsedCommand if successful, None if building failed
        """
        try:
            # Extract action (required)
            action_token = next((t for t in command_tokens if t.is_action_word), None)
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
            target_token = next((t for t in command_tokens if t.is_schema_word or t.is_entity_word), None)
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
            target_name_token = next((t for t in command_tokens if t.is_value or t.is_unknown), None)
            target_name = target_name_token.text if target_name_token else None
            
            # Extract field=value pairs
            field_values = cls._extract_field_value_pairs(command_tokens)
            
            # Extract standalone field dsl (not part of assignments)
            field_words = cls._extract_standalone_field_words(command_tokens)
            
            return ParsedCommand(
                action=action_token.word,
                target=target,
                target_name=target_name,
                field_values=field_values,
                field_words=field_words,
                filters=filter_expression,
                raw_input=raw_input,
                command_tokens=command_tokens
            )
            
        except Exception as e:
            from vlmx_sh2.enums import IssueStage
            context.add_error(
                stage=IssueStage.RECOGNIZER,
                message=f"Command building failed: {str(e)}"
            )
            return None
    
    # =============================================================================
    # Wizard Command Building
    # =============================================================================
    
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
        Build ParsedCommand from wizard form submission data.
        
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
    
    # =============================================================================
    # Helper Methods (moved from ParsedCommand)
    # =============================================================================
    
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