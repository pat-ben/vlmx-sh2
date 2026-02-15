"""
Core package for VLMX-SH2.

This package is the canonical home for *shared* definitions and utilities used
across the project, including:

- `enums/`   : shared enumerations
- `models/`  : shared Pydantic models / DTOs
- `schemas/` : shared SQLModel schemas and entities
- `utils/`   : shared helper functions used across layers
- `constants.py`: shared constants

Guideline:
    Application/runtime code should import from `vlmx_sh2.core.*` rather than
    legacy top-level packages.
"""

__all__ = [
    "enums",
    "models",
    "schemas",
    "utils",
]
