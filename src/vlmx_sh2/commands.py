# File: D:\Code\vlmx-sh2\src\vlmx_sh2\commands.py

"""
Command syntax definition and registration system.

This module handles ONLY:
1. Defining command syntax (which keywords are required/optional)
2. Registering commands in the command registry
3. Providing access to registered commands

Keywords are defined in words.py and referenced here by ID.
"""

from typing import Dict, List, Optional, Set, Callable, Any
from pydantic import BaseModel, Field
from .words import get_word, Word
from .enums import WordType, RequirementType
from .context import Context


# ==================== COMMAND SYNTAX ====================

class CommandSyntax(BaseModel):
    """
    Defines the syntax requirements for a single command.
    
    Specifies which keywords are required/optional and their constraints.
    """  
    
    required_words: Set[str] = Field(default_factory=set, description="Word IDs that must be present")
    optional_words: Set[str] = Field(default_factory=set, description="Word IDs that can be present")
    
    def get_all_words(self) -> Set[str]:
        """Get all word IDs that can be used in this command"""
        all_words = self.required_words.copy()
        all_words.update(self.optional_words)  
        return all_words
    
    def is_word_allowed(self, word_id: str) -> bool:
        """Check if a word ID is allowed in this command"""
        return word_id in self.get_all_words()
    
    def get_requirement_type(self, word_id: str) -> RequirementType:
        """Get the requirement type for a specific word"""
        if word_id in self.required_words:
            return RequirementType.REQUIRED
        elif word_id in self.optional_words:
            return RequirementType.OPTIONAL
        else:
            raise ValueError(f"Word '{word_id}' is not part of this command syntax")


# ==================== COMMAND DEFINITION ====================

class Command(BaseModel):
    """
    Represents a complete command definition with syntax and execution.
    """
    
    command_id: str = Field(description="Unique command identifier")
    description: str = Field(description="Human-readable command description")
    syntax: CommandSyntax = Field(description="Command syntax requirements")
    handler: Optional[Callable] = Field(default=None, description="Command execution handler")
    examples: List[str] = Field(default_factory=list, description="Usage examples")
    
    class Config:
        arbitrary_types_allowed = True
    
    def validate_words(self, word_ids: List[str]) -> tuple[bool, str]:
        """
        Validate that provided word IDs satisfy command syntax requirements.
        
        Returns:
            (is_valid, error_message)
        """
        word_set = set(word_ids)
        
        # Check required words are present
        missing_required = self.syntax.required_words - word_set
        if missing_required:
            return False, f"Missing required words: {', '.join(missing_required)}"
        
        # Check no unknown words
        unknown_words = word_set - self.syntax.get_all_words()
        if unknown_words:
            return False, f"Unknown words for this command: {', '.join(unknown_words)}"   
        
        return True, ""
    
    def can_execute(self, context: Context) -> tuple[bool, str]:
        """
        Check if this command can be executed in the given context.
        Override in subclasses for context-specific validation.
        """
        return True, ""
    
    async def execute(self, words: List[Word], context: Context) -> Any:
        """
        Execute the command with the given words and context.
        Override in subclasses or set handler function.
        """
        if self.handler:
            return await self.handler(words, context)
        raise NotImplementedError(f"Command '{self.command_id}' has no execution handler")


# ==================== COMMAND REGISTRY ====================

class CommandRegistry:
    """
    Central registry for all available commands.
    Provides registration and lookup functionality.
    """
    
    def __init__(self):
        self._commands: Dict[str, Command] = {}
        self._commands_by_action: Dict[str, List[Command]] = {}
    
    def register(self, command: Command) -> None:
        """Register a command in the registry"""
        self._commands[command.command_id] = command
        
        # Index by action words for quick lookup
        action_words = [
            word_id for word_id in command.syntax.get_all_words()
            if get_word(word_id) and get_word(word_id).word_type == WordType.ACTION
        ]
        
        for action_word in action_words:
            if action_word not in self._commands_by_action:
                self._commands_by_action[action_word] = []
            self._commands_by_action[action_word].append(command)
    
    def get_command(self, command_id: str) -> Optional[Command]:
        """Get a command by its ID"""
        return self._commands.get(command_id)
    
    def get_commands_by_action(self, action_word_id: str) -> List[Command]:
        """Get all commands that use a specific action word"""
        return self._commands_by_action.get(action_word_id, [])
    
    def find_matching_commands(self, word_ids: List[str]) -> List[Command]:
        """
        Find commands that could match the given word IDs.
        Returns commands where all provided words are allowed.
        """
        word_set = set(word_ids)
        matching_commands = []
        
        for command in self._commands.values():
            command_words = command.syntax.get_all_words()
            if word_set.issubset(command_words):
                matching_commands.append(command)
        
        return matching_commands
    
    def get_all_commands(self) -> Dict[str, Command]:
        """Get all registered commands"""
        return self._commands.copy()
    
    def list_command_ids(self) -> List[str]:
        """Get list of all command IDs"""
        return list(self._commands.keys())


# ==================== DECORATOR FOR AUTO-REGISTRATION ====================

# Global registry instance
_command_registry = CommandRegistry()

def register_command(
    command_id: str,
    description: str,
    required_words: Set[str] = None,
    optional_words: Set[str] = None,
    conditional_words: Dict[str, List[str]] = None,
    mutually_exclusive_groups: List[Set[str]] = None,
    examples: List[str] = None
):
    """
    Decorator to automatically register a command.
    
    Usage:
        @register_command(
            command_id="create_company",
            description="Create a new company",
            required_words={"create", "company"},
            optional_words={"entity", "currency"}
        )
        async def create_company_handler(words: List[Word], context: Context):
            # Implementation here
            pass
    """
    def decorator(handler_func: Callable) -> Callable:
        syntax = CommandSyntax(
            command_id=command_id,
            description=description,
            required_words=required_words or set(),
            optional_words=optional_words or set(),
            conditional_words=conditional_words or {},
            mutually_exclusive_groups=mutually_exclusive_groups or [],
        )
        
        command = Command(
            command_id=command_id,
            description=description,
            syntax=syntax,
            handler=handler_func,
            examples=examples or []
        )
        
        _command_registry.register(command)
        return handler_func
    
    return decorator


# ==================== COMMAND REGISTRY ACCESS ====================

def get_registry() -> CommandRegistry:
    """Get the global command registry"""
    return _command_registry

def get_command(command_id: str) -> Optional[Command]:
    """Get a command by ID from the global registry"""
    return _command_registry.get_command(command_id)

def find_commands(word_ids: List[str]) -> List[Command]:
    """Find commands matching the given word IDs"""
    return _command_registry.find_matching_commands(word_ids)

def get_commands_by_action(action_word_id: str) -> List[Command]:
    """Get commands that use a specific action word"""
    return _command_registry.get_commands_by_action(action_word_id)


# ==================== BASIC COMMAND DEFINITIONS ====================

# Basic command syntax definitions for common operations
# These will be registered when the module is imported

@register_command(
    command_id="create_company",
    description="Create a new company entity",
    required_words={"create", "company"},
    optional_words={"entity", "currency"},
    examples=[
        "create company ACME-SA --entity=SA --currency=EUR",
        "create company HoldCo --entity=HOLDING"
    ]
)
async def create_company_handler(words: List[Word], context: Context):
    """Handler for creating companies"""
    # Implementation would go here
    return {"action": "create_company", "words": [w.id for w in words], "context": context.level}

@register_command(
    command_id="delete_company", 
    description="Delete an existing company entity",
    required_words={"delete", "company"},
    examples=[
        "delete company ACME-SA",
        "delete company HoldCo"
    ]
)
async def delete_company_handler(words: List[Word], context: Context):
    """Handler for deleting companies"""
    # Implementation would go here  
    return {"action": "delete_company", "words": [w.id for w in words], "context": context.level}