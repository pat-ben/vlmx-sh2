"""
Application-wide constants.

Contains shared constants used across multiple modules to avoid duplication
and ensure consistency.
"""

# System-managed fields that should be excluded from user-editable forms
# These fields are automatically managed by the shell and should not be
# directly modified by users through form interfaces
SYSTEM_FIELDS = {
    'id',           # Record identifier
    'co_id',        # Company identifier
    'brand_id',     # Brand identifier
    'created_at',   # Creation timestamp
    'updated_at',   # Last update timestamp
    'source_db',    # Source database reference
    'last_synced_at'  # Last synchronization timestamp
}