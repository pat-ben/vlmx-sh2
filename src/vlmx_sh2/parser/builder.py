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

from typing import Optional, Dict, List, Union
from ..models.parser import ParsedCommand
from ..models.parser.filter import FilterExpression
from ..models.validation import ValidationContext
from ..models.words import ActionWord, SchemaWord, EntityWord, WordType
from vlmx_sh2.enums import TokenType, IssueStage


class Builder:
    """
    Assembles ParsedCommand from interpreted tokens and filter expression.
    
    Takes interpreted tokens from the pipeline and extracts structured components
    to build a ParsedCommand that handlers can execute.
    
    Responsibilities:
    - Extract action word (required)
    - Extract target schema/entity (optional)
    - Extract target name from values/unknowns (optional)
    - Extract field=value pairs (optional)
    - Extract standalone field words (optional)
    - Combine with filter expression
    - Handle extraction errors via ValidationContext
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
        
        Extracts action, target, field values, etc. from tokens and combines
        with filter expression to create structured command.
        
        Args:
            command_tokens: Interpreted tokens from splitter (command portion)
            filter_expression: Parsed filter AST (or None)
            raw_input: Original user input
            context: ValidationContext for error reporting
            
        Returns:
            ParsedCommand if successful, None if building failed
        """
        try:
            # Extract required components
            action = cls._extract_action(command_tokens, context)
            if action is None:
                return None  # No action = invalid command
            
            # Extract optional components
            target = cls._extract_target(command_tokens, context)
            target_name = cls._extract_target_name(command_tokens, context)
            field_values = cls._extract_field_values(command_tokens, context)
            field_words = cls._extract_field_words(command_tokens, context)
            
            return ParsedCommand(
                action=action,
                target=target,
                target_name=target_name,
                field_values=field_values,
                field_words=field_words,
                filters=filter_expression,
                raw_input=raw_input,
                command_tokens=command_tokens
            )
            
        except Exception as e:
            context.add_error(
                stage=IssueStage.RECOGNIZER,
                message=f"Command building failed: {str(e)}"
            )
            return None
    
    # =============================================================================
    # Private Helpers - Component Extraction
    # =============================================================================
    
    @classmethod
    def _extract_action(
        cls, 
        tokens: List, 
        context: ValidationContext
    ) -> Optional[ActionWord]:
        """
        Extract the action word from tokens.
        
        Args:
            tokens: List of interpreted tokens
            context: ValidationContext for error reporting
            
        Returns:
            ActionWord if found, None if missing
        """
        for token in tokens:
            if (hasattr(token, 'token_type') and 
                token.token_type == TokenType.WORD and
                hasattr(token, 'word') and
                isinstance(token.word, ActionWord)):
                return token.word
        
        context.add_error(
            stage=IssueStage.RECOGNIZER,
            message="No action word found in command",
            error_code="missing_action"
        )
        return None
    
    @classmethod
    def _extract_target(
        cls,
        tokens: List,
        context: ValidationContext
    ) -> Optional[Union[SchemaWord, EntityWord]]:
        """
        Extract the target word from tokens.
        
        This can be either a SchemaWord (for database operations) or 
        EntityWord (for table operations).
        
        Args:
            tokens: List of interpreted tokens
            context: ValidationContext for error reporting
            
        Returns:
            SchemaWord or EntityWord if found, None if missing
        """
        for token in tokens:
            if (hasattr(token, 'token_type') and 
                token.token_type == TokenType.WORD and
                hasattr(token, 'word')):
                
                if isinstance(token.word, (SchemaWord, EntityWord)):
                    return token.word
        
        # Target is optional for some commands (like cd, help)
        return None
    
    @classmethod
    def _extract_target_name(
        cls,
        tokens: List,
        context: ValidationContext
    ) -> Optional[str]:
        """
        Extract target name from tokens.
        
        Looks for VALUE tokens or quoted strings that represent the target name
        (e.g., company name, entity instance name).
        
        Args:
            tokens: List of interpreted tokens
            context: ValidationContext for error reporting
            
        Returns:
            Target name if found, None otherwise
        """
        # Look for VALUE tokens that might be target names
        for token in tokens:
            if (hasattr(token, 'token_type') and 
                token.token_type == TokenType.VALUE):
                return token.text
        
        # Also check for UNKNOWN tokens (might be target names)
        for token in tokens:
            if (hasattr(token, 'token_type') and 
                token.token_type == TokenType.UNKNOWN):
                return token.text
        
        return None
    
    @classmethod
    def _extract_field_values(
        cls,
        tokens: List,
        context: ValidationContext
    ) -> Dict[str, str]:
        """
        Extract field-value pairs from tokens.
        
        Looks for patterns like: field_name = value
        where the tokens have been processed to include operators.
        
        Args:
            tokens: List of interpreted tokens
            context: ValidationContext for error reporting
            
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
            
            # Check if this looks like a field assignment
            if (hasattr(field_token, 'token_type') and
                field_token.token_type == TokenType.WORD and
                hasattr(operator_token, 'operator') and
                operator_token.operator and
                hasattr(value_token, 'token_type') and
                value_token.token_type == TokenType.VALUE):
                
                field_values[field_token.text] = value_token.text
                i += 3  # Skip the triplet we just processed
            else:
                i += 1
        
        return field_values
    
    @classmethod 
    def _extract_field_words(
        cls,
        tokens: List,
        context: ValidationContext
    ) -> List[str]:
        """
        Extract field names without values (for field selection/deletion).
        
        Finds standalone field words that are not part of field=value assignments.
        These are used for commands like 'delete brand vision mission'.
        
        Args:
            tokens: List of interpreted tokens
            context: ValidationContext for error reporting
            
        Returns:
            List of field names
        """
        field_words = []
        
        for i, token in enumerate(tokens):
            if (hasattr(token, 'token_type') and 
                token.token_type == TokenType.WORD and
                hasattr(token, 'word') and
                token.word and
                hasattr(token.word, 'word_type')):
                
                # Check if this is a field word not followed by an operator
                is_field_assignment = False
                if i + 1 < len(tokens):
                    next_token = tokens[i + 1]
                    if (hasattr(next_token, 'operator') and next_token.operator):
                        is_field_assignment = True
                
                if not is_field_assignment:
                    # Check if word type indicates this is a field
                    if hasattr(token.word, 'word_type') and token.word.word_type == WordType.FIELD:
                        field_words.append(token.text)
        
        return field_words