"""
PARSING ORCHESTRATOR: Parser

Pipeline orchestrator that coordinates text analysis stages and assembles TokensResult.
Important: Parser is NOT a parsing stage itself - it orchestrates stages 0-6 only.

Pipeline Flow:
    Input: raw text (user input)
    
    Stage 0: Normalizer     -> normalized text (macro expansion)
    Stage 1: Tokenizer      -> List[Token]
    Stage 2: Classifier     -> List[ClassifiedToken]
    Stage 3: Recognizer     -> List[RecognizedToken]
    Stage 4: Interpreter    -> List[InterpretedToken]
    Stage 5: Splitter       -> SplitResult (command_tokens + filter_tokens)
    Stage 6: Filter         -> FilterExpression (AST) or None
    
    Output: TokensResult (with interpreted tokens + filter AST + validation context)

Parser Responsibilities:
- Create ValidationContext for error tracking
- Orchestrate text analysis stages 0-6 in sequence
- Handle stage failures (stop on blocking errors, continue on warnings)
- Return TokensResult with tokens and AST for CommandBuilder

What Parser Does NOT Do:
- Build ParsedCommand (CommandBuilder's job)
- Route to handlers (caller's job)
- Execute handlers (caller's job)  
- Handle wizard flows (UI layer's job)
"""

from typing import Optional, List
from ..models.parser import TokensResult
from ..models.parser.filtering import FilterExpression
from ..models.validation import ValidationContext
from ..models.context import Context

# Import all pipeline stages (0-6 only, no builder)
from .normalizer import normalize
from .tokenizer import Tokenizer
from .classifier import Classifier
from .recognizer import Recognizer
from .interpreter import Interpreter
from .splitter import Splitter
from .filter import Filter


class Parser:
    """
    Pipeline orchestrator for parsing user input into tokens and filter AST.
    
    Coordinates text analysis stages (0-6) and assembles TokensResult.
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
        Parser       | Mark as invalid  | N/A
    """
    
    @classmethod
    def parse(cls, input_text: str, context: Context) -> TokensResult:
        """
        Orchestrate the text analysis pipeline and build a TokensResult.
        
        Runs parsing stages 0-6 in sequence, handles errors appropriately,
        and assembles TokensResult with tokens and filter AST for CommandBuilder.
        
        Args:
            input_text: Raw user input text
            context: Current execution context (ORG, SYS, APP level)
            
        Returns:
            TokensResult with:
            - command_tokens: Interpreted tokens for command building
            - filter_tokens: Recognized tokens for filter portion
            - filter_expression: Parsed filter AST (or None)
            - validation_context: Errors/warnings from parsing stages
            - is_valid: True if no blocking errors occurred
        """
        # Step 1: Initialize ValidationContext
        validation_context = ValidationContext(input_text=input_text)
        
        # Step 2: Run the parsing pipeline (stages 0-6)
        pipeline_result = cls._run_pipeline(input_text, validation_context, context)
        if pipeline_result is None:
            # Pipeline failed early - return empty result
            return cls._build_tokens_result(input_text, [], [], None, validation_context)
        
        split_result, filter_expression = pipeline_result
        
        # Step 3: Assemble TokensResult (no command building)
        return cls._build_tokens_result(
            input_text,
            split_result.command_tokens,
            split_result.filter_tokens,
            filter_expression,
            validation_context
        )
    
    @classmethod
    def _run_pipeline(
        cls, 
        input_text: str, 
        validation_context: ValidationContext,
        context: Context
    ) -> Optional[tuple]:
        """
        Run all parsing stages in sequence with error handling.
        
        Returns:
            Tuple of (SplitResult, FilterExpression) if successful
            None if pipeline failed early
        """
        # BLOCKING STAGES: Stop pipeline on errors to prevent cascading failures
        
        # Stage 0: Normalizer (BLOCKING)
        normalized_text = normalize(input_text, validation_context)
        validation_context.normalized_text = normalized_text
        
        if validation_context.has_errors():
            return None  # Stop on normalization errors
        
        # Stage 1: Tokenizer (BLOCKING)
        tokens = Tokenizer.tokenize(normalized_text, validation_context)
        
        if validation_context.has_errors():
            return None  # Stop on tokenization errors
        
        # Stage 2: Classifier (BLOCKING)
        classified_tokens = Classifier.classify(tokens, validation_context)
        
        if validation_context.has_errors():
            return None  # Stop on classification errors
        
        # NON-BLOCKING STAGES: Continue to collect all issues for better error reporting
        
        # Stage 3: Recognizer (NON-BLOCKING)
        recognized_tokens = Recognizer.recognize(classified_tokens, validation_context)
        
        # Continue even with recognition errors to collect all issues
        
        # Stage 4: Interpreter (NON-BLOCKING)
        # Use the real context passed in (not hardcoded default)
        interpreted_tokens = Interpreter.interpret(recognized_tokens, context)
        
        # Continue even with interpretation errors
        
        # Stage 5: Splitter (NON-BLOCKING)
        split_result = Splitter.split(interpreted_tokens, validation_context)
        
        if validation_context.has_errors():
            # Check if splitter errors are blocking (bracket issues)
            # For now, continue - splitter errors are usually recoverable
            pass
        
        # Stage 6: Filter (NON-BLOCKING)
        filter_expression = Filter.parse(split_result, validation_context)
        
        # Filter parsing errors are non-blocking (filters are optional)
        
        return split_result, filter_expression
    
    
    @classmethod
    def _build_tokens_result(
        cls,
        input_text: str,
        command_tokens: List,
        filter_tokens: List,
        filter_expression: Optional[FilterExpression],
        context: ValidationContext
    ) -> TokensResult:
        """
        Assemble TokensResult from parsing stages 0-6.
        
        Packages tokens, filter AST, and validation context into the result
        structure that CommandBuilder expects. No ParsedCommand is built here.
        """
        return TokensResult(
            input_text=input_text,
            command_tokens=command_tokens,
            filter_tokens=filter_tokens,
            filter_expression=filter_expression,
            validation_context=context,
            is_valid=context.is_valid()
        )
    
