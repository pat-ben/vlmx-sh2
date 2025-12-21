# File: src/vlmx_sh2/commands.py

from typing import List, Optional, Set, Dict
from pydantic import BaseModel, Field, field_validator

class Command(BaseModel):
    """
    Simplified command model.
    
    A command is just a collection of keywords with metadata.
    All keyword details are stored in the keyword registry.
    """
    
    id: str = Field(description="Unique command identifier (e.g., 'create_company', 'show_financials')")
    required_keywords: List[str] = Field(description="List of keyword IDs that MUST be present (e.g., ['create', 'company'])")
    optional_keywords: List[str] = Field(default_factory=list, description="List of keyword IDs that CAN be present (e.g., ['holding', 'name', 'currency'])")
    level: int = Field(description="Context level where this command is available: 0, 1, or 2")
    description: str = Field(description="Human-readable description of what this command does")
    example: List[str] = Field(default_factory=list, description="Example usages of this command")
    
    @field_validator('level')
    @classmethod
    def validate_level(cls, v: int) -> int:
        """Ensure level is 0, 1, or 2"""
        if v not in [0, 1, 2]:
            raise ValueError(f"Level must be 0, 1, or 2, got {v}")
        return v
    
    @field_validator('required_keywords')
    @classmethod
    def validate_not_empty(cls, v: List[str]) -> List[str]:
        """Ensure at least one required keyword (command cannot be empty)"""
        if not v:
            raise ValueError("Command must have at least one required keyword")
        return v
    
    @property
    def all_keywords(self) -> Set[str]:
        """Returns all keyword IDs (required + optional)"""
        return set(self.required_keywords) | set(self.optional_keywords)
    
    @property
    def is_simple(self) -> bool:
        """Check if command has only required keywords (no optional ones)"""
        return len(self.optional_keywords) == 0


# ==================== COMMAND REGISTRY ====================

class CommandRegistry:
    """
    Global registry of all commands, organized by context level.
    """
    
    def __init__(self):
        self._commands: Dict[int, List[Command]] = {
            0: [],  # Level 0 commands (global)
            1: [],  # Level 1 commands (company context)
            2: [],  # Level 2 commands (data context)
        }
        self._by_id: Dict[str, Command] = {}
    
    def register(self, command: Command) -> None:
        """Register a command"""
        if command.id in self._by_id:
            raise ValueError(f"Command '{command.id}' already registered")
        
        self._commands[command.level].append(command)
        self._by_id[command.id] = command
    
    def get_available_commands(self, current_level: int) -> List[Command]:
        """
        Get all commands available at the current context level.
        
        Commands inherit downward:
        - Level 0 commands work at all levels
        - Level 1 commands work at levels 1 and 2
        - Level 2 commands work only at level 2
        """
        available = []
        
        # Add level 0 commands (available everywhere)
        available.extend(self._commands[0])
        
        # Add level 1 commands if at level 1 or 2
        if current_level >= 1:
            available.extend(self._commands[1])
        
        # Add level 2 commands if at level 2
        if current_level >= 2:
            available.extend(self._commands[2])
        
        return available
    
    def get_by_id(self, command_id: str) -> Optional[Command]:
        """Get a command by ID"""
        return self._by_id.get(command_id)


# Global registry instance
COMMAND_REGISTRY = CommandRegistry()