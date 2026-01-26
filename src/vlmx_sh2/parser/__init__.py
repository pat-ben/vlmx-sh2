"""
Parser package.

Provides modular parsing functionality with clean separation of concerns:
- Normalization: Text preprocessing and macro expansion
- Tokenization: Breaking input into tokens
- Classification: Structural token analysis
- Recognition: Matching tokens to known words
- Interpretation: Intelligence layer for user intent
- Splitting: Command/Filter separation
- Filtering: Filter expression parsing
- Building: Command assembly from tokens

The parsing pipeline consists of 7 stages, each with specific responsibilities.
"""

from .normalizer import normalize      # Stage 0
from .tokenizer import Tokenizer       # Stage 1
from .classifier import Classifier     # Stage 2
from .recognizer import Recognizer     # Stage 3
from .interpreter import Interpreter   # Stage 4
from .splitter import Splitter         # Stage 5
from .filter import Filter             # Stage 6
from .builder import Builder           # Stage 7
from .parser import Parser             # Pipeline Orchestrator

# Legacy alias for compatibility
VLMXParser = Parser

__all__ = [
    'normalize',       # Stage 0
    'Tokenizer',       # Stage 1
    'Classifier',      # Stage 2
    'Recognizer',      # Stage 3
    'Interpreter',     # Stage 4
    'Splitter',        # Stage 5
    'Filter',          # Stage 6
    'Builder',         # Stage 7
    'Parser',          # Pipeline Orchestrator
    'VLMXParser',      # Legacy alias
]

