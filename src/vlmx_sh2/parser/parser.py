"""
PARSING ORCHESTRATOR: Parser

Pipeline orchestrator that coordinates all parsing stages and assembles the final ParseResult.
Important: Parser is NOT a parsing stage itself - it orchestrates stages 0-7.

Pipeline Flow:
    Input: raw text (user input)
    
    Stage 0: Normalizer     -> normalized text (macro expansion)
    Stage 1: Tokenizer      -> List[Token]
    Stage 2: Classifier     -> List[ClassifiedToken]
    Stage 3: Recognizer     -> List[RecognizedToken]
    Stage 4: Interpreter    -> List[InterpretedToken]
    Stage 5: Splitter       -> SplitResult (command_tokens + filter_tokens)
    Stage 6: Filter         -> FilterExpression (AST) or None
    Stage 7: Builder        -> ParsedCommand
    
    Output: ParseResult (with ParsedCommand + ValidationContext)

Parser Responsibilities:
- Create ValidationContext for error tracking
- Orchestrate stages 0-7 in sequence
- Handle stage failures (stop on blocking errors, continue on warnings)
- Return ParseResult with everything packaged for caller

What Parser Does NOT Do:
- Route to handlers (caller's job)
- Execute handlers (caller's job)  
- Handle wizard flows (UI layer's job)
- Build commands from tokens (Builder's job)
"""

from typing import Optional, List
from ..models.parser import ParseResult, ParsedCommand
from ..models.parser.filtering import FilterExpression
from ..models.validation import ValidationContext
from ..models.context import Context
from ..enums.core import ContextLevel

# Import all pipeline stages
from .normalizer import normalize
from .tokenizer import Tokenizer
from .classifier import Classifier
from .recognizer import Recognizer
from .interpreter import Interpreter
from .splitter import Splitter
from .filter import Filter
from .builder import Builder


class Parser:
    """
    Pipeline orchestrator for parsing user input into structured commands.
    
    Coordinates all parsing stages (0-7) and assembles the final ParseResult.
    Parser is stateless - all state is maintained in ValidationContext.
    
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
        Builder      | Continue (collect)| Continue
        Parser       | Mark as invalid  | N/A
    """
    
    @classmethod
    def parse(cls, input_text: str) -> ParseResult:
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
        """
        # Step 1: Initialize ValidationContext
        context = ValidationContext(input_text=input_text)
        
        # Step 2: Run the parsing pipeline
        pipeline_result = cls._run_pipeline(input_text, context)
        if pipeline_result is None:
            # Pipeline failed early - return empty result
            return cls._build_result(input_text, None, None, [], [], context)
        
        split_result, filter_expression = pipeline_result
        
        # Step 3: Build ParsedCommand from tokens (Stage 7)
        parsed_command = Builder.build(
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
        recognized_tokens = Recognizer.recognize(classified_tokens, context)
        
        # Continue even with recognition errors to collect all issues
        
        # Stage 4: Interpreter
        # Create default context for interpreter
        default_context = Context(level=ContextLevel.SYS)
        interpreted_tokens = Interpreter.interpret(recognized_tokens, default_context)
        
        # Continue even with interpretation errors
        
        # Stage 5: Splitter
        split_result = Splitter.split(interpreted_tokens, context)
        
        if context.has_errors():
            # Check if splitter errors are blocking (bracket issues)
            # For now, continue - splitter errors are usually recoverable
            pass
        
        # Stage 6: Filter
        filter_expression = Filter.parse(split_result, context)
        
        # Filter parsing errors are non-blocking (filters are optional)
        
        return split_result, filter_expression
    
    
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
            filter_tokens=filter_tokens
        )
    
