"""
Parser package.

Provides modular text analysis functionality with clean separation of concerns:
- Normalization: Text preprocessing and macro expansion
- Tokenization: Breaking input into tokens
- Classification: Structural token analysis
- Recognition: Matching tokens to known words
- Interpretation: Intelligence layer for user intent
- Splitting: Command/Filter separation
- Filtering: Filter expression parsing

The parsing pipeline consists of 6 text analysis stages (command building moved to core).
"""

from .normalizer import normalize           # Stage 0
from .tokenizer import tokenize             # Stage 1
from .classifier import classify            # Stage 2
from .recognizer import recognize, get_words_by_type  # Stage 3
from .interpreter import interpret          # Stage 4
from .splitter import split                 # Stage 5
# Both filter.py and parser.py define a function named `parse`, so the stage 6
# entry point is aliased here to avoid shadowing the orchestrator:
#   parse_filter(split_result, context) -> FilterExpression | None
#       Operates on a SplitResult produced by the Splitter stage and builds
#       a FilterExpression AST from the filter token stream.
#   parse(input_text, context) -> TokensResult
#       Full pipeline orchestrator: accepts raw text and drives all stages 0-6,
#       returning a TokensResult containing tokens, the filter AST, and
#       validation state for CommandBuilder.
from .filter import parse as parse_filter   # Stage 6
from .parser import parse                   # Pipeline Orchestrator


__all__ = [
    'normalize',          # Stage 0
    'tokenize',           # Stage 1
    'classify',           # Stage 2
    'recognize',          # Stage 3
    'get_words_by_type',  # Stage 3
    'interpret',          # Stage 4
    'split',              # Stage 5
    'parse_filter',       # Stage 6
    'parse',              # Pipeline Orchestrator
]
