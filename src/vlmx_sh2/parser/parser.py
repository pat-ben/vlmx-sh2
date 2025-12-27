"""
Main parser for VLMX DSL commands.

Orchestrates the parsing process by coordinating tokenization, word recognition,
value extraction, and command validation. Provides the primary interface for
parsing natural language commands into structured data.
"""

from typing import Any, List
from ..models.parser import ParseResult, ParsedToken, TokenType
from ..models.words import WordType, ActionWord, EntityWord
from .tokenizer import Tokenizer
from .recognizer import WordRecognizer
from .extractor import ValueExtractor
from .utils import expand_shortcuts


class VLMXParser:
    """Main parser for VLMX DSL commands."""
    
    def __init__(self):
        """Initialize the parser."""
        self.tokenizer = Tokenizer()
        self.word_recognizer = WordRecognizer()
        self.value_extractor = ValueExtractor()
    
    def parse(self, input_text: str) -> ParseResult:
        """
        Parse input text into a structured result.
        
        Args:
            input_text: User input to parse
            
        Returns:
            ParseResult with all extracted information
        """
        result = ParseResult(input_text=input_text)
        
        try:
            # Step 1: Expand shortcuts
            expanded_input = expand_shortcuts(input_text)
            
            # Step 2: Tokenize
            tokens = self.tokenizer.tokenize(expanded_input)
            
            # Step 3: Recognize words
            tokens = self.word_recognizer.process_tokens(tokens)
            
            # Step 4: Extract values and attributes
            result.attribute_values = self.value_extractor.extract_attribute_values(tokens)
            result.entity_values = self.value_extractor.extract_entity_values(tokens)
            
            # Step 5: Collect recognized words
            recognized_words = []
            for token in tokens:
                if token.word:
                    recognized_words.append(token.word)
            
            result.tokens = tokens
            result.recognized_words = recognized_words
            
            # Step 6: Extract action handler and entity model
            if recognized_words:
                action_words = [w for w in recognized_words if isinstance(w, ActionWord)]
                entity_words = [w for w in recognized_words if isinstance(w, EntityWord)]
                
                if action_words:
                    # Get the handler from the action word
                    action_word = action_words[0]  # Take the first action word
                    result.action_handler = action_word.handler
                    
                if entity_words:
                    # Get the entity model from the entity word
                    entity_word = entity_words[0]  # Take the first entity word
                    result.entity_model = entity_word.entity_model
                
                # Validate that we have the minimum requirements
                if action_words:
                    result.is_valid = True
            
            # Step 7: Generate suggestions
            result.suggestions = self._generate_suggestions(result)
            
        except Exception as e:
            result.errors.append(f"Parse error: {str(e)}")
        
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
        if action_words and action_words[0].requires_entity:
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
            if action_words and action_words[0].requires_entity:
                suggestions.append("Consider adding an entity word (e.g., 'company', 'brand', 'metadata')")
        
        # If we have ENTITY but no ACTION, suggest adding an action
        if WordType.ENTITY in word_types_present and WordType.ACTION not in word_types_present:
            suggestions.append("Consider adding an action word (e.g., 'create', 'add', 'update', 'show', 'delete')")
        
        # Suggest common attribute patterns
        if result.action_words and result.entity_words and not result.attribute_values:
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
        # Handler signature: handler(entity_model, entity_value, attributes, context, attribute_words)
        entity_value = None
        if parse_result.entity_values:
            # Get the first entity value
            entity_value = next(iter(parse_result.entity_values.values()))
        
        # For delete operations, we need to pass the list of attribute words to delete
        attribute_words_to_process = [w.id for w in parse_result.attribute_words]
        
        try:
            return await parse_result.action_handler(
                entity_model=parse_result.entity_model,
                entity_value=entity_value,
                attributes=parse_result.attribute_values,
                context=context,
                attribute_words=attribute_words_to_process
            )
        except Exception as e:
            raise RuntimeError(f"Handler execution failed: {str(e)}")