"""
Main parser for VLMX commands.

Orchestrates the parsing process by coordinating tokenization, word recognition,
value extraction, and command validation. Provides the primary interface for
parsing natural language commands into structured data.
"""

from typing import Any, List, Optional, Dict
from ..models.parser import ParseResult, ParsedCommand, RecognizedToken
from ..models.words import ActionWord, SchemaWord, EntityWord
from .tokenizer import Tokenizer
from .recognizer import WordRecognizer
from .filter import FilterParser
from ..words.macros import expand_macros


class VLMXParser:
    """Main parser for VLMX commands."""
    
    def __init__(self):
        """Initialize the parser."""
        self.tokenizer = Tokenizer()
        self.word_recognizer = WordRecognizer()
        self.filter_parser = FilterParser()
    
    def parse(self, input_text: str) -> ParseResult:
        """
        Parse input text into a structured result.
        
        Simplified 3-step process:
        1. Tokenize (break input into tokens)
        2. Recognize (classify tokens and extract values)
        3. Build command (aggregate into ParsedCommand)
        
        Args:
            input_text: User input to parse
            
        Returns:
            ParseResult with command object and validation status
        """
        result = ParseResult(input_text=input_text)
        
        try:
            # Step 1: Tokenize (produces TWO lists)
            expanded_input = expand_macros(input_text)
            tokenizer_result = self.tokenizer.tokenize(expanded_input)
            
            # Step 2: Recognize BOTH lists separately
            recognized_command_tokens = self.word_recognizer.process_tokens(
                tokenizer_result.command_tokens
            )
            
            recognized_filter_tokens = []
            if tokenizer_result.has_filter:
                recognized_filter_tokens = self.word_recognizer.process_tokens(
                    tokenizer_result.filter_tokens
                )
            
            # Store both in result
            result.command_tokens = recognized_command_tokens
            result.filter_tokens = recognized_filter_tokens
            result.tokens = recognized_command_tokens  # Backward compatibility
            
            # Step 3: Build command using BOTH lists
            try:
                command = self._build_command(
                    recognized_command_tokens,
                    recognized_filter_tokens,
                    input_text
                )
                result.command = command
                result.is_valid = True
                
            except ValueError as e:
                # Command building failed (missing action/entity)
                result.errors.append(str(e))
                result.is_valid = False
            
            
        except Exception as e:
            result.errors.append(f"Parse error: {str(e)}")
            result.is_valid = False
        
        return result
    
    def _build_command(
        self,
        command_tokens: List[RecognizedToken],
        filter_tokens: List[RecognizedToken],
        raw_input: str
    ) -> ParsedCommand:
        """
        Build a ParsedCommand from recognized tokens.
        
        Args:
            command_tokens: List of recognized command tokens from WordRecognizer
            filter_tokens: List of recognized filter tokens from WordRecognizer
            raw_input: Original user input text
            
        Returns:
            Structured ParsedCommand object
            
        Raises:
            ValueError: If required components (action, entity) are missing
        """
        # Extract action first to check if entity is required
        action = self._extract_action(command_tokens)
        
        # Extract target and target_name - navigation commands like cd don't have entity targets
        target = None
        target_name = None
        
        if action.id == "cd":
            # For navigation commands, extract target_name from UNKNOWN tokens
            target_name = self._extract_navigation_target(command_tokens)
        else:
            # For all other commands, try to extract target (entity/schema)
            try:
                target = self._extract_target(command_tokens)
                target_name = self._extract_target_name(command_tokens)
            except ValueError:
                # No target found - this might be valid for some commands
                pass
        
        # Parse filters from recognized filter tokens
        filters = None
        if filter_tokens:
            filters = self.filter_parser.parse_filters(filter_tokens)
        
        return ParsedCommand(
            action=action,
            target=target,
            target_name=target_name,
            attributes=self._extract_fields(command_tokens),
            field_words=self._extract_field_words(command_tokens),
            raw_input=raw_input,
            tokens=command_tokens,  # Main tokens are command tokens
            filter_tokens=filter_tokens,
            filters=filters
        )
    
    def _extract_action(self, tokens: List[RecognizedToken]) -> ActionWord:
        """
        Extract the action word from tokens.
        
        Args:
            tokens: List of recognized tokens
            
        Returns:
            The first ActionWord found
            
        Raises:
            ValueError: If no action word found
        """
        for token in tokens:
            if token.is_action_word:
                if token.word and isinstance(token.word, ActionWord):
                    return token.word
        
        raise ValueError("No action word found in command")
    
    def _extract_target(self, tokens: List[RecognizedToken]):
        """
        Extract the target word from tokens.
        
        This can be either a SchemaWord (for database operations) or EntityWord (for table operations).
        SchemaWords have higher priority in the word registry, so they'll be recognized first.
        
        Args:
            tokens: List of recognized tokens
            
        Returns:
            The first SchemaWord or EntityWord found
            
        Raises:
            ValueError: If no target word found
        """
        for token in tokens:
            if token.is_entity_word:
                if token.word and (isinstance(token.word, SchemaWord) or isinstance(token.word, EntityWord)):
                    return token.word
        
        raise ValueError("No target word found in command")
    
    def _extract_target_name(self, tokens: List[RecognizedToken]) -> Optional[str]:
        """
        Extract target name from tokens.
        
        Finds target values (company names, fund names, etc.) by looking
        for VALUE tokens with ENTITY context that follow target words.
        
        Args:
            tokens: List of recognized tokens
            
        Returns:
            Target name if found, None otherwise
        """
        for i in range(len(tokens) - 1):
            current = tokens[i]
            next_token = tokens[i + 1]
            
            # Simple: ENTITY word followed by ENTITY value
            # Recognizer already classified these!
            if current.is_entity_word and next_token.is_entity_value:
                return next_token.text
        
        # Also check for standalone entity values (when entity word is implied)
        for token in tokens:
            if token.is_entity_value:
                return token.text
        
        return None
    
    def _extract_navigation_target(self, tokens: List[RecognizedToken]) -> Optional[str]:
        """
        Extract navigation target from UNKNOWN tokens for commands like cd.
        
        For commands that don't require entity words (like cd), the target
        (company name, .., ~, root) will be in UNKNOWN tokens.
        
        Args:
            tokens: List of recognized tokens
            
        Returns:
            Navigation target if found, None otherwise
        """
        # Look for UNKNOWN tokens (navigation targets)
        unknown_tokens = []
        for token in tokens:
            if hasattr(token, 'token_type') and hasattr(token.token_type, 'name'):
                if token.token_type.name == "UNKNOWN":
                    unknown_tokens.append(token.text)
        
        if unknown_tokens:
            # Join multiple unknown tokens with spaces (for unquoted multi-word targets)
            return " ".join(unknown_tokens)
        
        return None
    
    def _extract_fields(self, tokens: List[RecognizedToken]) -> Dict[str, str]:
        """
        Extract field-value pairs from tokens.
        
        Finds field assignments by looking for FIELD words followed
        by FIELD values. The recognizer has already classified which
        values are field values vs entity values.
        
        Args:
            tokens: List of recognized tokens
            
        Returns:
            Dictionary of field names to values
        """
        fields = {}
        
        for i in range(len(tokens) - 1):
            current = tokens[i]
            next_token = tokens[i + 1]
            
            # Simple: FIELD word followed by FIELD value
            # Recognizer already classified these!
            if current.is_field_word and next_token.is_field_value:
                fields[current.text] = next_token.text
        
        return fields
    
    def _extract_field_words(self, tokens: List[RecognizedToken]) -> List[str]:
        """
        Extract field names without values (for field selection/deletion).
        
        Finds standalone FieldWord tokens that are not followed by field values.
        These are used for commands like 'delete brand vision mission'.
        
        Args:
            tokens: List of recognized tokens
            
        Returns:
            List of field names
        """
        field_words = []
        
        for i, token in enumerate(tokens):
            if token.is_field_word:
                # Check if this field word is NOT followed by a field value
                # If it's the last token or the next token is not a field value, include it
                if i == len(tokens) - 1 or not tokens[i + 1].is_field_value:
                    field_words.append(token.text)
        
        return field_words
    
    def _validate_handler_requirements(self, result: ParseResult, context) -> bool:
        """
        Validate that the parse result has the minimum requirements for handler execution.
        
        Requirements:
        1. Must have an action word with handler
        2. Must satisfy context requirements based on the specific command
        """
        if not result.action_handler:
            result.errors.append("No action handler found")
            return False
        
        # Get the action word for validation
        action_words = result.action_words
        if not action_words:
            result.errors.append("No action word found")
            return False
            
        from ..models.words import ActionWord
        action_word = action_words[0]
        if not isinstance(action_word, ActionWord):
            result.errors.append("Invalid action word type")
            return False
        
        # Validate context requirements using new command-level validation
        from ..utils.context_helpers import validate_command_context_requirements
        
        # Get entity_value for navigation commands
        entity_value = None
        if result.command and hasattr(result.command, 'target') and result.command.target:
            if hasattr(result.command.target, 'entity') and result.command.target.entity:
                entity_value = result.command.target.entity.id
        
        # Check if command has schema (schema_word present)
        has_schema = bool(result.schema_words)
        
        # Check if command has app (app parameter - we'd need to implement this)
        has_app = False  # For now, we don't have app parameter detection
        
        # Validate command context requirements
        is_valid, error_msg = validate_command_context_requirements(
            action_word, context, entity_value, has_schema, has_app
        )
        
        if not is_valid:
            result.errors.append(error_msg)
            return False
        
        return True
    

    async def execute_parsed_command(self, parse_result: ParseResult, context) -> Any:
        """
        Execute a parsed command by calling the action handler directly.
        
        Args:
            parse_result: The result from parsing user input
            context: Execution context
            
        Returns:
            Result from handler execution
        """
        if not parse_result.is_valid:
            raise ValueError(f"Cannot execute invalid parse result: {parse_result.errors}")
        
        if not parse_result.action_handler:
            raise ValueError("No action handler available for execution")
        
        # Validate handler requirements
        if not self._validate_handler_requirements(parse_result, context):
            raise ValueError(f"Handler requirements not met: {parse_result.errors}")
        
        # Call the handler with the new simplified signature
        try:
            return await parse_result.action_handler(
                parsed_command=parse_result.command,
                context=context
            )
        except Exception as e:
            raise RuntimeError(f"Handler execution failed: {str(e)}")