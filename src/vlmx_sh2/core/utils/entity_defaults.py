"""
Entity default data creation utilities.

Provides utilities for creating default entity data from Pydantic models.
Used by both handlers and storage layers to avoid duplication.
"""

from datetime import datetime
from typing import Dict, Any, Type
from pydantic import BaseModel


def create_default_entity_data(entity_model: Type[BaseModel], entity_type: str) -> Dict[str, Any]:
    """
    Create default entity data from Pydantic model.
    
    Args:
        entity_model: Pydantic model class
        entity_type: Entity type string (for default name)
        
    Returns:
        Dictionary with default entity data
        
    Raises:
        Exception: If model instantiation fails
    """
    default_entity_data = {
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    
    # For entities with a "name" field, set a default name
    if hasattr(entity_model, 'model_fields') and 'name' in entity_model.model_fields:
        default_entity_data["name"] = f"default_{entity_type}"
    
    # Create instance with minimal required data
    entity_instance = entity_model(**default_entity_data)
    
    # Get all model fields and create a complete data dict with explicit None for optional fields
    complete_data = {}
    for field_name, field_info in entity_model.model_fields.items():
        if hasattr(entity_instance, field_name):
            value = getattr(entity_instance, field_name)
            complete_data[field_name] = value
        else:
            # For fields not in the instance, explicitly set to None if they're optional
            if not field_info.is_required():
                complete_data[field_name] = None
    
    return complete_data


def create_default_entity_data_simple(entity_class) -> Dict[str, Any]:
    """
    Create default entity data from entity class (simpler version for storage layer).
    
    This is a compatibility function that matches the database.py signature
    but uses a simpler approach with fallback error handling.
    
    Args:
        entity_class: Pydantic entity class (untyped for backwards compatibility)
        
    Returns:
        Dictionary with default entity data
    """
    default_data = {
        "id": None,
        "co_id": 1,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    try:
        entity_instance = entity_class(**default_data)
        return entity_instance.model_dump()
    except Exception:
        return default_data