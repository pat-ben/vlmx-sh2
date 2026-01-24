"""
PARSING ORCHESTRATOR: Builder

Pipeline orchestrator that coordinates all parsing stages and assembles the final ParseResult.
Important: Builder is NOT a parsing stage itself - it orchestrates stages 0-6.

Pipeline Flow:
    Input: raw text (user input)
    
    Stage 0: Normalizer     -> normalized text (macro expansion)
    Stage 1: Tokenizer      -> List[Token]
    Stage 2: Classifier     -> List[ClassifiedToken]
    Stage 3: Recognizer     -> List[RecognizedToken]
    Stage 4: Interpreter    -> List[InterpretedToken]
    Stage 5: Splitter       -> SplitResult (command_tokens + filter_tokens)
    Stage 6: Filter   -> FilterExpression (AST) or None
    
    Output: ParseResult (with ParsedCommand + ValidationContext)

Builder Responsibilities:
- Create ValidationContext for error tracking
- Orchestrate stages 0-6 in sequence
- Handle stage failures (stop on blocking errors, continue on warnings)
- Build ParsedCommand from tokens + filter AST
- Return ParseResult with everything packaged for caller

What Builder Does NOT Do:
- Route to handlers (caller's job)
- Execute handlers (caller's job)  
- Handle wizard flows (UI layer's job)
"""

from typing import Optional, Dict, List, Union
from ..models.parser import ParseResult, ParsedCommand
from ..models.parser.filter import FilterExpression
from ..models.validation import ValidationContext
from ..models.words import ActionWord, SchemaWord, EntityWord
from vlmx_sh2.enums import TokenType, IssueStage

# Import all pipeline stages
from .normalizer import normalize
from .tokenizer import Tokenizer
from .classifier import Classifier
from .recognizer import Recognizer
from .interpreter import Interpreter
from .splitter import Splitter
from .filter import Filter


class Builder:
    """
    Pipeline orchestrator for parsing user input into structured commands.
    
    Coordinates all parsing stages (0-6) and assembles the final ParseResult.
    Builder is stateless - all state is maintained in ValidationContext.
    
    Error Handling Strategy:
        Stage        | On Blocking Error | On Warning
        -------------|------------------|------------
        Normalizer   | Stop, return     | Continue  
        Tokenizer    | Stop, return     | Continue
        Classifier   | Stop, return     | Continue
        Recognizer   | Continue (collect)| Continue
        Interpreter  | Continue (collect)| Continue  
        Splitter     | Stop if brackets | Continue
        Filter       | Continue (optional)| Continue
        Command Build| Mark as invalid  | N/A
    """
    
    @classmethod
    def build(cls, input_text: str) -> ParseResult:
        """
        Orchestrate the parsing pipeline and build a ParseResult.
        
        Runs all parsing stages in sequence, handles errors appropriately,
        and assembles the final ParseResult with structured command.
        
        Args:
            input_text: Raw user input text
            
        Returns:
            ParseResult with:
            - command: ParsedCommand (if valid)
            - is_valid: True if no blocking errors  
            - errors/warnings from ValidationContext
            - tokens: For backward compatibility
        """
        # Step 1: Initialize ValidationContext
        context = ValidationContext(input_text=input_text)
        
        # Step 2: Run the parsing pipeline
        pipeline_result = cls._run_pipeline(input_text, context)
        if pipeline_result is None:
            # Pipeline failed early - return empty result
            return cls._build_result(input_text, None, None, [], [], context)
        
        split_result, filter_expression = pipeline_result
        
        # Step 3: Build ParsedCommand from tokens
        parsed_command = cls._build_command(
            split_result.command_tokens, 
            filter_expression, 
            input_text,
            context
        )
        
        # Step 4: Assemble final ParseResult
        return cls._build_result(
            input_text,
            parsed_command,
            filter_expression,
            split_result.command_tokens,
            split_result.filter_tokens,
            context
        )
    
    @classmethod
    def _run_pipeline(
        cls, 
        input_text: str, 
        context: ValidationContext
    ) -> Optional[tuple]:
        """
        Run all parsing stages in sequence with error handling.
        
        Returns:
            Tuple of (SplitResult, FilterExpression) if successful
            None if pipeline failed early
        """
        # Stage 0: Normalizer
        normalized_text = normalize(input_text, context)
        context.normalized_text = normalized_text
        
        if context.has_errors():
            return None  # Stop on normalization errors
        
        # Stage 1: Tokenizer
        tokens = Tokenizer.tokenize(normalized_text, context)
        
        if context.has_errors():
            return None  # Stop on tokenization errors
        
        # Stage 2: Classifier
        classified_tokens = Classifier.classify(tokens, context)
        
        if context.has_errors():
            return None  # Stop on classification errors
        
        # Stage 3: Recognizer
        recognizer = Recognizer()
        recognized_tokens = recognizer.recognize(classified_tokens, context)
        
        # Continue even with recognition errors to collect all issues
        
        # Stage 4: Interpreter
        # Create default context and word registry for interpreter
        from ..words.registry import WORD_REGISTRY
        from ..models.context import Context
        from ..enums.core import ContextLevel
        
        default_context = Context(level=ContextLevel.SYS)
        interpreter = Interpreter(WORD_REGISTRY, default_context)
        interpreted_tokens = interpreter.interpret(recognized_tokens)
        
        # Continue even with interpretation errors
        
        # Stage 5: Splitter
        split_result = Splitter.split(interpreted_tokens, context)
        
        if context.has_errors():
            # Check if splitter errors are blocking (bracket issues)
            # For now, continue - splitter errors are usually recoverable
            pass
        
        # Stage 6: FilterParser
        filter_expression = Filter.parse(split_result, context)
        
        # Filter parsing errors are non-blocking (filters are optional)
        
        return split_result, filter_expression
    
    @classmethod
    def _build_command(
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
                stage=IssueStage.RECOGNIZER,  # Use existing stage name for command building errors
                message=f"Command building failed: {str(e)}"
            )
            return None
    
    @classmethod
    def _build_result(
        cls,
        input_text: str,
        parsed_command: Optional[ParsedCommand],
        filter_expression: Optional[FilterExpression],
        command_tokens: List,
        filter_tokens: List,
        context: ValidationContext
    ) -> ParseResult:
        """
        Assemble final ParseResult from all components.
        
        Packages everything into the final result structure that callers expect.
        """
        return ParseResult(
            input_text=input_text,
            command=parsed_command,
            is_valid=context.is_valid() and parsed_command is not None,
            errors=[issue.message for issue in context.errors],
            suggestions=[issue.suggestion for issue in context.errors if issue.suggestion],
            command_tokens=command_tokens,
            filter_tokens=filter_tokens,
            tokens=command_tokens,  # Backward compatibility
        )
    
    # =============================================================================
    # Command Extraction Methods (adapted from DEPRECATED parser)
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
                    # Note: We need to check the actual word type from the word registry
                    from vlmx_sh2.models.words import WordType
                    if hasattr(token.word, 'word_type') and token.word.word_type == WordType.FIELD:
                        field_words.append(token.text)
        
        return field_words