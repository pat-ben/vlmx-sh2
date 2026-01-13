"""
Main parser for VLMX commands.

Orchestrates the parsing process by coordinating tokenization, word recognition,
value extraction, and command validation. Provides the primary interface for
parsing natural language commands into structured data.
"""

from typing import Any, List, Optional, Dict, Union
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
            result.tokens = recognized_command_tokens  # TODO: Remove backward compatibility
            
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
        action = self._extract_action(command_tokens)
        target: Optional[Union[SchemaWord, EntityWord]] = None
        schema_name = None
        
        if action.id == "cd":
            # For navigation commands, extract schema_name from UNKNOWN tokens
            schema_name = self._extract_navigation_target(command_tokens)
        else:
            # For all other commands, try to extract target (entity/schema)
            try:
                target = self._extract_target(command_tokens)
                schema_name = self._extract_schema_name(command_tokens)
            except ValueError:
                # No target found - this might be valid for some commands
                pass
        
        filters = None
        if filter_tokens:
            filters = self.filter_parser.parse_filters(filter_tokens)
        
        return ParsedCommand(
            action=action,
            target=target,
            target_name=schema_name,
            field_values=self._extract_fields(command_tokens),
            field_words=self._extract_field_words(command_tokens),
            raw_input=raw_input,
            command_tokens=command_tokens,  # Main tokens are command tokens
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
            if token.is_action_word and token.word and isinstance(token.word, ActionWord):
                return token.word
        
        raise ValueError("No action word found in command")
    
    def _extract_target(self, tokens: List[RecognizedToken]) -> Union[SchemaWord, EntityWord]:
        """
        Extract the target word from tokens.
        
        This can be either a SchemaWord (for database operations) or EntityWord (for table operations).
        
        Args:
            tokens: List of recognized tokens
            
        Returns:
            The first SchemaWord or EntityWord found
            
        Raises:
            ValueError: If no target word found
        """
        for token in tokens:
            if token.is_entity_word and token.word and isinstance(token.word, EntityWord):
                return token.word
            elif token.is_schema_word and token.word and isinstance(token.word, SchemaWord):
                return token.word
        
        raise ValueError("No target word found in command")
    
    def _extract_schema_name(self, tokens: List[RecognizedToken]) -> Optional[str]:
        """
        Extract schema name from tokens.
        
        Finds target values (company names, fund names, etc.) by looking
        for VALUE tokens with ENTITY context that follow target words.
        
        Returns:
            Schema name if found, None otherwise
        """
        for i in range(len(tokens) - 1):
            if (tokens[i].is_entity_word or tokens[i].is_schema_word) and tokens[i + 1].is_schema_name:
                return tokens[i + 1].text
        
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
        unknown_tokens = [token.text for token in tokens if token.is_unknown]
        return " ".join(unknown_tokens) if unknown_tokens else None
    
    def _extract_fields(self, tokens: List[RecognizedToken]) -> Dict[str, str]:
        """
        Extract field-value pairs from tokens.
        
        Finds field assignments by looking for FIELD words followed
        by FIELD values. Returns dictionary of field names to values.
        """
        fields = {}
        
        for i in range(len(tokens) - 1):
            if tokens[i].is_field_word and tokens[i + 1].is_field_value:
                fields[tokens[i].text] = tokens[i + 1].text
        
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
        return [
            token.text for i, token in enumerate(tokens)
            if token.is_field_word and (i == len(tokens) - 1 or not tokens[i + 1].is_field_value)
        ]
    
    def _validate_handler_requirements(self, result: ParseResult, context) -> bool:
        """
        Validate that the parse result has the minimum requirements for handler execution.
        
        Requirements:
        1. Must have an action handler
        2. Must have a valid action word
        """
        if not result.action_handler:
            result.errors.append("No action handler found")
            return False
        
        action_words = result.action_words
        if not action_words or not isinstance(action_words[0], ActionWord):
            result.errors.append("No valid action word found")
            return False
        
        # TODO: Implement context validation based on command requirements
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