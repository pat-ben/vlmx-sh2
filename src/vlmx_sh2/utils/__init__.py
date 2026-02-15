"""
Shared utilities for VLMX-SH2.

Provides common functions used across different components
while maintaining proper separation between backend and UI.
"""

from .field_specs import build_field_specs, build_column_specs

__all__ = ['build_field_specs', 'build_column_specs']