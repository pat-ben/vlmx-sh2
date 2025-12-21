# File: D:\Code\vlmx-sh2\src\vlmx_sh2\commands\command.py

"""
Command syntax definition and registration system.

This module handles ONLY:
1. Defining command syntax (which keywords are required/optional)
2. Registering commands in the command registry
3. Providing access to registered commands

Keywords are defined in keywords.py and referenced here by ID.
"""

from typing import Dict, List, Optional, Callable, Any
from pydantic import BaseModel, Field, field_validator


# ==================== COMMAND REGISTRY ====================

COMMAND_REGISTRY: Dict[str, 'CommandSyntax'] = {}


# ==================== COMMAND SYNTAX ====================

class CommandSyntax(BaseModel):
    """
    Defines the complete syntax for a command.
    
    Specifies WHICH keywords are used (required/optional), but NOT their order.
    Order is determined automatically by composition rules.
    
    Keywords are referenced by ID from the keyword registry (keywords.py).
    
    Example:
        create company ACME-SA --entity=SA --currency=EUR
        
        required_keywords = ["create", "company", "company_name"]
        optional_keywords = ["entity", "currency"]
    """
    
    # Basic identification
    name: str = Field(
        description="Unique command name (e.g., 'create_company')"
    )
    
    description: str = Field(
        description="Human-readable description of what the command does"
    )
    
    # Keyword composition
    required_keywords: List[str] = Field(
        default_factory=list,
        description="List of required keyword IDs (from keywords registry)"
    )
    
    optional_keywords: List[str] = Field(
        default_factory=list,
        description="List of optional keyword IDs (from keywords registry)"
    )
    
    # Usage examples
    examples: List[str] = Field(
        default_factory=list,
        description="Example usage strings to help users"
    )
    
    # Metadata for organization
    category: str = Field(
        default="general",
        description="Command category (e.g., 'company', 'data', 'query', 'system')"
    )
    
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for search/filtering (e.g., ['database', 'setup', 'financial'])"
    )
    
    # Validation
    @field_validator('required_keywords', 'optional_keywords')
    @classmethod
    def validate_keywords_not_empty_strings(cls, keywords):
        """Ensure keyword IDs are not empty strings"""
        for kw_id in keywords:
            if not kw_id or not kw_id.strip():
                raise ValueError("Keyword ID cannot be empty")
        return keywords
    
    @field_validator('name')
    @classmethod
    def validate_name_format(cls, name):
        """Ensure command name follows naming conventions"""
        if not name:
            raise ValueError("Command name cannot be empty")
        if not name.replace('_', '').isalnum():
            raise ValueError(f"Command name '{name}' must be alphanumeric (underscores allowed)")
        return name
    
    def get_all_keywords(self) -> List[str]:
        """Get all keyword IDs (required + optional)"""
        return self.required_keywords + self.optional_keywords
    
    def is_keyword_required(self, keyword_id: str) -> bool:
        """Check if a keyword is required"""
        return keyword_id in self.required_keywords
    
    def is_keyword_optional(self, keyword_id: str) -> bool:
        """Check if a keyword is optional"""
        return keyword_id in self.optional_keywords


# ==================== DECORATOR FOR COMMAND REGISTRATION ====================

def command(**kwargs) -> Callable[[Any], Any]:
    """
    Decorator to define and register command syntax.
    
    The command class only needs to specify WHICH keywords it uses (by ID).
    Order is determined automatically by composition rules.
    
    Usage:
        @command(
            name="create_company",
            description="Create a new company database",
            category="company",
            tags=["database", "setup"]
        )
        class CreateCompanyCommand:
            required_keywords = ["create", "company", "company_name"]
            optional_keywords = ["entity", "currency"]
            
            examples = [
                "create company ACME-SA",
                "create company ACME-SA --entity=SA --currency=EUR"
            ]
    
    Args:
        name: Command name (optional, defaults to class name)
        description: Command description (optional, defaults to class docstring)
        category: Command category (optional, defaults to "general")
        tags: Command tags (optional, defaults to empty list)
    
    Returns:
        Decorator function that registers the command
    """
    def decorator(cls):
        # Build CommandSyntax from class attributes
        syntax = CommandSyntax(
            name=kwargs.get('name', cls.__name__),
            description=kwargs.get('description', cls.__doc__ or ""),
            required_keywords=getattr(cls, 'required_keywords', []),
            optional_keywords=getattr(cls, 'optional_keywords', []),
            examples=getattr(cls, 'examples', []),
            category=kwargs.get('category', 'general'),
            tags=kwargs.get('tags', [])
        )
        
        # Register the command syntax
        COMMAND_REGISTRY[syntax.name] = syntax
        
        # Attach syntax to class for reference
        cls._syntax = syntax
        
        return cls
    
    return decorator


# ==================== REGISTRY ACCESS FUNCTIONS ====================

def get_command(name: str) -> Optional[CommandSyntax]:
    """
    Get command syntax by name.
    
    Args:
        name: Command name
        
    Returns:
        CommandSyntax if found, None otherwise
        
    Example:
        >>> syntax = get_command("create_company")
        >>> print(syntax.description)
        "Create a new company database"
        >>> print(syntax.required_keywords)
        ["create", "company", "company_name"]
    """
    return COMMAND_REGISTRY.get(name)


def list_all_commands() -> Dict[str, CommandSyntax]:
    """
    Get all registered command syntaxes.
    
    Returns:
        Dictionary of {command_name: CommandSyntax}
        
    Example:
        >>> commands = list_all_commands()
        >>> for name, syntax in commands.items():
        ...     print(f"{name}: {syntax.description}")
    """
    return COMMAND_REGISTRY.copy()


def list_commands_by_category(category: str) -> Dict[str, CommandSyntax]:
    """
    Get commands filtered by category.
    
    Args:
        category: Category name (e.g., "company", "data", "query")
        
    Returns:
        Dictionary of {command_name: CommandSyntax} for matching category
        
    Example:
        >>> company_commands = list_commands_by_category("company")
        >>> print(f"Found {len(company_commands)} company commands")
    """
    return {
        name: syntax
        for name, syntax in COMMAND_REGISTRY.items()
        if syntax.category == category
    }


def list_commands_by_tag(tag: str) -> Dict[str, CommandSyntax]:
    """
    Get commands filtered by tag.
    
    Args:
        tag: Tag to search for (e.g., "database", "financial")
        
    Returns:
        Dictionary of {command_name: CommandSyntax} for commands with this tag
        
    Example:
        >>> db_commands = list_commands_by_tag("database")
    """
    return {
        name: syntax
        for name, syntax in COMMAND_REGISTRY.items()
        if tag in syntax.tags
    }


def search_commands(query: str) -> Dict[str, CommandSyntax]:
    """
    Search commands by name or description.
    
    Args:
        query: Search query string
        
    Returns:
        Dictionary of matching commands
        
    Example:
        >>> results = search_commands("company")
        >>> # Returns all commands with "company" in name or description
    """
    query_lower = query.lower()
    return {
        name: syntax
        for name, syntax in COMMAND_REGISTRY.items()
        if query_lower in name.lower() or query_lower in syntax.description.lower()
    }


def get_command_count() -> int:
    """
    Get total number of registered commands.
    
    Returns:
        Number of commands in registry
    """
    return len(COMMAND_REGISTRY)


def get_commands_using_keyword(keyword_id: str) -> Dict[str, CommandSyntax]:
    """
    Get all commands that use a specific keyword.
    
    Args:
        keyword_id: Keyword ID to search for
        
    Returns:
        Dictionary of commands that use this keyword
        
    Example:
        >>> commands = get_commands_using_keyword("company")
        >>> # Returns all commands that use the "company" keyword
    """
    return {
        name: syntax
        for name, syntax in COMMAND_REGISTRY.items()
        if keyword_id in syntax.get_all_keywords()
    }


def clear_registry():
    """
    Clear all registered commands.
    Useful for testing.
    """
    COMMAND_REGISTRY.clear()