# File: D:\Code\vlmx-sh2\src\vlmx_sh2\commands.py

"""
Command syntax definition and registration system.

This module handles ONLY:
1. Defining command syntax (which keywords are required/optional)
2. Registering commands in the command registry
3. Providing access to registered commands

Keywords are defined in words.py and referenced here by ID.
"""

from typing import Any, Callable, Dict, List, Optional, Set

from pydantic import BaseModel, Field, field_validator

from .context import Context
from .enums import ContextLevel, RequirementType, WordType
from .syntax import get_composition_error, is_valid_command, sort_words
from .words import Word, get_word

# ==================== COMMAND SYNTAX ====================


class CommandWords(BaseModel):
    """
    Defines the word requirements for a single command.

    Specifies WHAT words are required/optional, not HOW they are ordered.
    Ordering and composition logic is handled automatically by syntax.py.
    """

    required_words: Set[str] = Field(
        default_factory=set, description="Word IDs that must be present"
    )
    optional_words: Set[str] = Field(
        default_factory=set, description="Word IDs that can be present"
    )

    @field_validator("required_words", "optional_words")
    @classmethod
    def validate_word_ids_exist(cls, v: Set[str]) -> Set[str]:
        """Validate that all word IDs exist in the word registry"""
        invalid_words = []
        for word_id in v:
            if get_word(word_id) is None:
                invalid_words.append(word_id)

        if invalid_words:
            raise ValueError(
                f"Unknown word IDs: {', '.join(invalid_words)}. "
                f"Word IDs must be defined in words.py"
            )

        return v

    @field_validator("optional_words")
    @classmethod
    def validate_no_overlap(cls, v: Set[str], info) -> Set[str]:
        """Validate that required and optional words don't overlap"""
        if info.data and "required_words" in info.data:
            required_words = info.data["required_words"]
            overlap = v & required_words
            if overlap:
                raise ValueError(
                    f"Words cannot be both required and optional: {', '.join(overlap)}"
                )

        return v

    def get_all_words(self) -> Set[str]:
        """Get all word IDs that can be used in this command"""
        all_words = self.required_words.copy()
        all_words.update(self.optional_words)
        return all_words


# ==================== COMMAND DEFINITION ====================


class Command(BaseModel):
    """
    Represents a complete command definition with syntax and execution.
    """

    command_id: str = Field(description="Unique command identifier")
    description: str = Field(description="Human-readable command description")
    words: CommandWords = Field(description="Command syntax requirements")
    context: ContextLevel = Field(
        default=ContextLevel.SYS,
        description="Minimum context level required: SYS(0), ORG(1), or APP(2)",
    )
    handler: Optional[Callable] = Field(
        default=None, description="Command execution handler"
    )
    examples: List[str] = Field(default_factory=list, description="Usage examples")

    class Config:
        arbitrary_types_allowed = True

    def can_execute(self, context: Context) -> tuple[bool, str]:
        """
        Check if this command can be executed in the given context.
        """
        if context.level < self.context:
            # Get readable level names
            level_names = {
                ContextLevel.SYS: "sys",
                ContextLevel.ORG: "org",
                ContextLevel.APP: "app",
            }

            required = level_names[self.context]
            current = level_names[ContextLevel(context.level)]

            return False, (
                f"Command requires '{required}' context, "
                f"currently at '{current}' context"
            )

        return True, ""

    def validate_words(self, word_ids: List[str]) -> tuple[bool, str]:
        """
        Validate that provided word IDs satisfy command syntax requirements.

        Uses automatic composition rules from syntax.py for ordering validation.

        Returns:
            (is_valid, error_message)
        """
        word_set = set(word_ids)

        # Check required words are present
        missing_required = self.words.required_words - word_set
        if missing_required:
            return False, f"Missing required words: {', '.join(missing_required)}"

        # Check no unknown words for this command
        unknown_words = word_set - self.words.get_all_words()
        if unknown_words:
            return False, f"Unknown words for this command: {', '.join(unknown_words)}"

        # Get word objects for composition validation
        word_objects = []
        for word_id in word_ids:
            word_obj = get_word(word_id)
            if word_obj:
                word_objects.append(word_obj)
            else:
                return False, f"Unknown word ID: {word_id}"

        # Use automatic composition validation from syntax.py
        composition_error = get_composition_error(word_objects)
        if composition_error:
            return False, composition_error

        return True, ""

    async def execute(self, words: List[Word], context: Context) -> Any:
        """
        Execute the command with the given words and context.

        Automatically sorts words by composition rules before execution.
        Ensures context is properly injected throughout the execution chain.
        """
        if not self.handler:
            raise NotImplementedError(
                f"Command '{self.command_id}' has no execution handler"
            )

        # Sort words according to automatic composition rules
        sorted_words = sort_words(words)

        # Validate context requirements before execution
        can_exec, error_msg = self.can_execute(context)
        if not can_exec:
            raise ValueError(f"Cannot execute command in current context: {error_msg}")

        # Execute with sorted words and injected context
        return await self.handler(sorted_words, context)


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
        action_words = []
        for word_id in command.words.get_all_words():
            word_obj = get_word(word_id)
            if word_obj and word_obj.word_type == WordType.ACTION:
                action_words.append(word_id)

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

        Uses automatic composition validation from syntax.py.
        """
        word_set = set(word_ids)
        matching_commands = []

        # Get word objects for composition validation
        word_objects = []
        for word_id in word_ids:
            word_obj = get_word(word_id)
            if word_obj:
                word_objects.append(word_obj)

        # Skip if we don't have valid word objects
        if len(word_objects) != len(word_ids):
            return matching_commands

        # Check if the word combination follows composition rules
        if not is_valid_command(word_objects):
            return matching_commands

        for command in self._commands.values():
            command_words = command.words.get_all_words()
            if word_set.issubset(command_words):
                matching_commands.append(command)

        return matching_commands

    def sort_command_words(self, word_ids: List[str]) -> List[str]:
        """
        Sort word IDs according to automatic composition rules.
        Returns properly ordered word IDs using syntax.py rules.
        """
        word_objects = []
        for word_id in word_ids:
            word_obj = get_word(word_id)
            if word_obj:
                word_objects.append(word_obj)

        sorted_words = sort_words(word_objects)
        return [word.id for word in sorted_words]

    def get_all_commands(self) -> Dict[str, Command]:
        """Get all registered commands"""
        return self._commands.copy()

    def list_command_ids(self) -> List[str]:
        """Get list of all command IDs"""
        return list(self._commands.keys())

    async def execute_command(
        self, command_id: str, word_ids: List[str], context: Context
    ) -> Any:
        """
        Execute a command by ID with automatic word resolution and context injection.

        Args:
            command_id: The command to execute
            word_ids: List of word IDs to pass to the command
            context: Execution context to inject

        Returns:
            Command execution result

        Raises:
            ValueError: If command not found or validation fails
        """
        command = self.get_command(command_id)
        if not command:
            raise ValueError(f"Command '{command_id}' not found")

        # Resolve word objects from IDs
        words = []
        for word_id in word_ids:
            word_obj = get_word(word_id)
            if not word_obj:
                raise ValueError(f"Unknown word ID: {word_id}")
            words.append(word_obj)

        # Validate words against command syntax
        is_valid, error_msg = command.validate_words(word_ids)
        if not is_valid:
            raise ValueError(f"Command validation failed: {error_msg}")

        # Execute with context injection
        return await command.execute(words, context)


# ==================== DECORATOR FOR AUTO-REGISTRATION ====================

# Global registry instance
_command_registry = CommandRegistry()


def register_command(
    command_id: str,
    description: str,
    required_words: Optional[Set[str]] = None,
    optional_words: Optional[Set[str]] = None,
    examples: Optional[List[str]] = None,
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
        syntax = CommandWords(
            required_words=required_words or set(),
            optional_words=optional_words or set(),
        )

        command = Command(
            command_id=command_id,
            description=description,
            words=syntax,
            handler=handler_func,
            examples=examples or [],
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


def sort_command_words(word_ids: List[str]) -> List[str]:
    """Sort word IDs according to automatic composition rules"""
    return _command_registry.sort_command_words(word_ids)


def validate_command_composition(word_ids: List[str]) -> tuple[bool, str]:
    """
    Validate word composition using automatic syntax rules.

    Args:
        word_ids: List of word IDs to validate

    Returns:
        (is_valid, error_message)
    """
    word_objects = []
    for word_id in word_ids:
        word_obj = get_word(word_id)
        if not word_obj:
            return False, f"Unknown word ID: {word_id}"
        word_objects.append(word_obj)

    composition_error = get_composition_error(word_objects)
    if composition_error:
        return False, composition_error

    return True, ""


async def execute_command(
    command_id: str, word_ids: List[str], context: Context
) -> Any:
    """Execute a command with automatic validation and context injection"""
    return await _command_registry.execute_command(command_id, word_ids, context)


# ==================== BASIC COMMAND DEFINITIONS ====================

# Basic command syntax definitions for common operations
# These will be registered when the module is imported


# Example using the traditional approach with validation
@register_command(
    command_id="create_company",
    description="Create a new company entity",
    required_words={"create", "company"},
    optional_words={"entity", "currency"},
    examples=[
        "create company ACME-SA --entity=SA --currency=EUR",
        "create company HoldCo --entity=HOLDING",
    ],
)
async def create_company_handler(words: List[Word], context: Context):
    """Handler for creating companies"""
    # Implementation would go here
    return {
        "action": "create_company",
        "words": [w.id for w in words],
        "context": context.level,
    }


@register_command(
    command_id="delete_company",
    description="Delete an existing company entity",
    required_words={"delete", "company"},
    examples=["delete company ACME-SA", "delete company HoldCo"],
)
async def delete_company_handler(words: List[Word], context: Context):
    """Handler for deleting companies"""
    # Implementation would go here
    return {
        "action": "delete_company",
        "words": [w.id for w in words],
        "context": context.level,
    }


# Example using the new CommandWords.from_word_types approach
def register_advanced_commands():
    """
    Example of how to register commands using the improved CommandWords validation.
    This shows the recommended approach for creating command syntax definitions.
    """

    # Create command syntax using the type-organized approach
    create_syntax = CommandWords.from_word_types(
        required_actions={"create"},
        required_entities={"company"},
        optional_attributes={"entity", "currency"},
    )

    # Register the command with the pre-built syntax
    command = Command(
        command_id="create_company_advanced",
        description="Create a new company entity (advanced validation)",
        words=create_syntax,
        examples=[
            "create company ACME-SA --entity=SA --currency=EUR",
            "create company HoldCo --entity=HOLDING",
        ],
    )

    # The syntax validation happens automatically when CommandWords is created
    # Any invalid word IDs will raise a ValueError during instantiation
    get_registry().register(command)


# Uncomment to register the advanced example:
# register_advanced_commands()
