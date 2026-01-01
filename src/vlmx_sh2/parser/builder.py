"""
Command builder for VLMX DSL parser.

Builds structured ParsedCommand objects from recognized token streams.
This is a simple aggregator - all complex classification logic is handled
by the recognizer.
"""

from typing import Optional, Dict, List
from ..models.parser import RecognizedToken, ParsedCommand
from ..models.words import ActionWord, EntityWord


class CommandBuilder:
    """
    Builds structured ParsedCommand from recognized tokens.
    
    Takes the output from WordRecognizer (List[RecognizedToken]) and
    constructs a clean ParsedCommand object ready for handler execution.
    
    This class is intentionally simple - all complex logic for classifying
    tokens is handled by the recognizer. CommandBuilder just aggregates
    the already-classified tokens into a structured object.
    """
    
    @staticmethod
    def build(tokens: List[RecognizedToken], raw_input: str) -> ParsedCommand:
        """
        Build a ParsedCommand from recognized tokens.
        
        Args:
            tokens: List of recognized tokens from WordRecognizer
            raw_input: Original user input text
            
        Returns:
            Structured ParsedCommand object
            
        Raises:
            ValueError: If required components (action, entity) are missing
            
        Examples:
            >>> tokens = [
            ...     RecognizedToken(text="create", token_type=WORD, word=ActionWord(...)),
            ...     RecognizedToken(text="company", token_type=WORD, word=EntityWord(...)),
            ...     RecognizedToken(text="ACME", token_type=VALUE, value_context=ENTITY)
            ... ]
            >>> command = CommandBuilder.build(tokens, 'create company "ACME"')
            >>> command.action.id
            'create'
            >>> command.entity.id
            'company'
            >>> command.entity_name
            'ACME'
        """
        return ParsedCommand(
            action=CommandBuilder._extract_action(tokens),
            entity=CommandBuilder._extract_entity(tokens),
            entity_name=CommandBuilder._extract_entity_name(tokens),
            attributes=CommandBuilder._extract_fields(tokens),
            raw_input=raw_input,
            tokens=tokens
        )
    
    @staticmethod
    def _extract_action(tokens: List[RecognizedToken]) -> ActionWord:
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
                # Type safety: is_action_word ensures this is an ActionWord
                from ..models.words import ActionWord
                if token.word and isinstance(token.word, ActionWord):
                    return token.word
        
        raise ValueError("No action word found in command")
    
    @staticmethod
    def _extract_entity(tokens: List[RecognizedToken]) -> EntityWord:
        """
        Extract the entity word from tokens.
        
        Args:
            tokens: List of recognized tokens
            
        Returns:
            The first EntityWord found
            
        Raises:
            ValueError: If no entity word found
        """
        for token in tokens:
            if token.is_entity_word:
                # Type safety: is_entity_word ensures this is an EntityWord
                from ..models.words import EntityWord
                if token.word and isinstance(token.word, EntityWord):
                    return token.word
        
        raise ValueError("No entity word found in command")
    
    @staticmethod
    def _extract_entity_name(tokens: List[RecognizedToken]) -> Optional[str]:
        """
        Extract entity name from tokens.
        
        Finds entity values (company names, fund names, etc.) by looking
        for VALUE tokens with ENTITY context that follow entity words.
        
        Args:
            tokens: List of recognized tokens
            
        Returns:
            Entity name if found, None otherwise
            
        Examples:
            >>> # From: create company "ACME"
            >>> _extract_entity_name(tokens)
            'ACME'
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
    
    @staticmethod
    def _extract_fields(tokens: List[RecognizedToken]) -> Dict[str, str]:
        """
        Extract field-value pairs from tokens.
        
        Finds field assignments by looking for FIELD words followed
        by FIELD values. The recognizer has already classified which
        values are field values vs entity values.
        
        Args:
            tokens: List of recognized tokens
            
        Returns:
            Dictionary of field names to values
            
        Examples:
            >>> # From: add fund vision="Our vision" currency=EUR
            >>> _extract_fields(tokens)
            {'vision': 'Our vision', 'currency': 'EUR'}
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