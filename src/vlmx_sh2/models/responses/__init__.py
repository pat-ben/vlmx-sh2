"""
Handler response models.

This package contains all response types that handlers can return:
- Results: Final responses that complete execution
- Requests: Interactive workflows requiring user input
"""

from .results import CommandResult, ErrorResult, StorageResult
from .requests import FormRequest, PickerRequest, QueryRequest

# Union type for all possible handler responses
from typing import Union

HandlerResult = Union[
    CommandResult, 
    ErrorResult, 
    FormRequest, 
    PickerRequest, 
    QueryRequest
]

__all__ = [
    # Results
    'CommandResult',
    'ErrorResult',
    'StorageResult',
    # Requests
    'FormRequest',
    'PickerRequest',
    'QueryRequest',
    # Union type
    'HandlerResult',
]