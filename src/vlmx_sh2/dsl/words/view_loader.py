"""
TOML view loader.

Loads ViewWord definitions from TOML files in the shell/views/ directory.
This replaces the hardcoded view definitions with dynamic configuration.
"""

import logging
from pathlib import Path
from typing import List

import tomllib

from ...core.enums.core import ContextLevel
from ...core.models.words import ViewWord


logger = logging.getLogger(__name__)


def load_views_from_directory(views_dir: Path) -> List[ViewWord]:
    """
    Load ViewWord objects from TOML files in a directory.
    
    Args:
        views_dir: Path to directory containing .toml files
        
    Returns:
        List of ViewWord objects loaded from valid TOML files
        
    Notes:
        - Skips files that fail to parse (logs warning)
        - Returns empty list if directory doesn't exist
        - Flattens entity lists from [entities] section
    """
    views = []
    
    # Return empty list if directory doesn't exist
    if not views_dir.exists():
        logger.debug(f"Views directory does not exist: {views_dir}")
        return views
        
    # Find all .toml files in the directory
    toml_files = list(views_dir.glob("*.toml"))
    
    if not toml_files:
        logger.debug(f"No TOML files found in views directory: {views_dir}")
        return views
        
    for toml_file in toml_files:
        try:
            # Parse TOML file
            with open(toml_file, "rb") as f:
                data = tomllib.load(f)
                
            # Extract view metadata
            view_data = data.get("view", {})
            if not view_data:
                logger.warning(f"TOML file missing [view] section: {toml_file}")
                continue
                
            view_id = view_data.get("id")
            if not view_id:
                logger.warning(f"TOML file missing 'id' in [view] section: {toml_file}")
                continue
                
            # Extract entities and flatten them
            entities_data = data.get("entities", {})
            entities = []
            for module_entities in entities_data.values():
                if isinstance(module_entities, list):
                    entities.extend(module_entities)
                
            # Create ViewWord object
            view_word = ViewWord(
                id=view_id,
                name=view_data.get("name", ""),
                description=view_data.get("description", ""),
                aliases=view_data.get("aliases", []),
                context=ContextLevel.APP,  # All views are APP-level
                entities=entities,
                schema_id=view_data.get("schema", "company")
            )
            
            views.append(view_word)
            logger.debug(f"Loaded view '{view_id}' from {toml_file}")
            
        except tomllib.TOMLDecodeError as e:
            logger.warning(f"Failed to parse TOML file {toml_file}: {e}")
            continue
        except Exception as e:
            logger.warning(f"Error loading view from {toml_file}: {e}")
            continue
    
    return views