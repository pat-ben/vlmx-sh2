"""
Main parser for VLMX DSL commands.

Orchestrates the parsing process by coordinating tokenization, word recognition,
value extraction, and command validation. Provides the primary interface for
parsing natural language commands into structured data.
"""

from typing import Any, List
from ..models.parser import TokenType, ParseResult
from ..models.words import WordType
from .tokenizer import Tokenizer
from .recognizer import WordRecognizer
from .builder import CommandBuilder
from .utils import expand_macros


class VLMXParser:
    """Main parser for VLMX DSL commands."""
    
    def __init__(self):
        """Initialize the parser."""
        self.tokenizer = Tokenizer()
        self.word_recognizer = WordRecognizer()
        self.command_builder = CommandBuilder()
    
    def parse(self, input_text: str) -> ParseResult:
        """
        Parse input text into a structured result.
        
        Args:
            input_text: User input to parse
            
        Returns:
            ParseResult with command object and validation status
        """
        result = ParseResult(input_text=input_text)
        
        try:
            # Step 1: Expand shortcuts
            expanded_input = expand_macros(input_text)
            
            # Step 2: Tokenize → Returns List[Token]
            tokens = self.tokenizer.tokenize(expanded_input)
            
            # Step 3: Recognize → Returns List[RecognizedToken]
            recognized_tokens = self.word_recognizer.process_tokens(tokens)
            
            # Store tokens in result
            result.tokens = recognized_tokens
            
            # Step 4: Build command → Returns ParsedCommand
            try:
                command = self.command_builder.build(recognized_tokens, input_text)
                
                # Store command and mark as valid
                result.command = command
                result.is_valid = True
                
            except ValueError as e:
                # Command building failed (missing action/entity)
                result.errors.append(str(e))
                result.is_valid = False
            
            # Step 5: Generate suggestions
            result.suggestions = self._generate_suggestions(result)
            
        except Exception as e:
            result.errors.append(f"Parse error: {str(e)}")
            result.is_valid = False
        
        return result
    
    def _validate_handler_requirements(self, result: ParseResult) -> bool:
        """
        Validate that the parse result has the minimum requirements for handler execution.
        
        Requirements:
        1. Must have an action word with handler
        2. For most actions, must have an entity word (unless action doesn't require entity)
        """
        if not result.action_handler:
            result.errors.append("No action handler found")
            return False
        
        # Check if action requires entity
        action_words = result.action_words
        if action_words:
            from ..models.words import ActionWord
            action_word = action_words[0]
            if isinstance(action_word, ActionWord) and action_word.requires_entity:
                if not result.entity_words:
                    result.errors.append("Action requires an entity word")
                    return False
        
        return True
    
    def _generate_suggestions(self, result: ParseResult) -> List[str]:
        """Generate helpful suggestions based on parse result and command analysis."""
        suggestions = []
        
        # Suggest corrections for unrecognized words
        for token in result.tokens:
            if token.token_type == TokenType.UNKNOWN and token.suggestions:
                suggestions.append(f"Did you mean '{token.suggestions[0]}' instead of '{token.text}'?")
        
        # Suggest word type completion based on DSL patterns
        word_types_present = set(result.word_types_present)
        
        # If we have ACTION but no ENTITY, suggest adding an entity
        if WordType.ACTION in word_types_present and WordType.ENTITY not in word_types_present:
            action_words = result.action_words
            if action_words:
                from ..models.words import ActionWord
                action_word = action_words[0]
                if isinstance(action_word, ActionWord) and action_word.requires_entity:
                    suggestions.append("Consider adding an entity word (e.g., 'company', 'brand', 'metadata')")
        
        # If we have ENTITY but no ACTION, suggest adding an action
        if WordType.ENTITY in word_types_present and WordType.ACTION not in word_types_present:
            suggestions.append("Consider adding an action word (e.g., 'create', 'add', 'update', 'show', 'delete')")
        
        # Suggest common attribute patterns
        if result.action_words and result.entity_words and not result.attributes:
            action = result.action_words[0].id
            entity = result.entity_words[0].id
            if action == 'create' and entity == 'company':
                suggestions.append("Consider adding attributes like entity=SA currency=EUR")
            elif action in ['add', 'update'] and entity in ['brand', 'metadata', 'offering']:
                suggestions.append("Consider adding attributes like name=value or key=value")
        
        return suggestions

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
        if not self._validate_handler_requirements(parse_result):
            raise ValueError(f"Handler requirements not met: {parse_result.errors}")
        
        # Call the handler with the parsed data
        entity_value = None
        if parse_result.entity_values:  # Property access - works
            # Get the first entity value (for commands with entities)
            entity_value = next(iter(parse_result.entity_values.values()))
        elif parse_result.entity_name:
            # For commands without entities (like navigation), use entity_name
            entity_value = parse_result.entity_name
        
        # For delete operations, we need to pass the list of field words to delete
        field_words_to_process = [w.id for w in parse_result.attribute_words]  # Property access - works
        
        try:
            return await parse_result.action_handler(  # Property access - works
                entity_model=parse_result.entity_model,  # Property access - works
                entity_value=entity_value,
                attributes=parse_result.attributes,  # Use new property name
                context=context,
                attribute_words=field_words_to_process
            )
        except Exception as e:
            raise RuntimeError(f"Handler execution failed: {str(e)}")