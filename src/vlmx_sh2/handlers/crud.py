"""
SQL-inspired CRUD handlers with clean, simple routing.

Refactored handlers using parsed command structure to eliminate all hardcoded
entity-specific logic and complex nested conditionals. Uses SQL-inspired
semantics with create/drop for structure and add/delete/reset for content.
"""

from datetime import datetime
from typing import Type, Optional, Dict, Any, List
from pydantic import BaseModel

from ..models.context import Context, ContextLevel
from ..models.responses import CommandResult, ErrorResult, HandlerResult
from ..models.parser.parsed_command import ParsedCommand
from ..models.words import SchemaWord, EntityWord
from vlmx_sh2.enums import Cardinality
from ..handlers.utils import get_company_name_from_context, format_entity_data_for_display
from ..storage.database import StorageInterface, entity_exists, find_company_by_name, load_all_entities
from ..storage.filters import apply_filters


# ==================== STRUCTURE OPERATIONS ====================

async def create_handler(parsed_command: ParsedCommand, context: Context) -> HandlerResult:
    """
    Create database or entity structure.
    
    Structure operations (create/drop) work on:
    - Schema (database): create company "Valmetrics"
    - Entity (table): create table brand [FUTURE - blocked by validation]
    - Fields (columns): create field vision [FUTURE - blocked by validation]
    """
    
    # Validate
    if not parsed_command.target:
        return ErrorResult(errors=["No target specified"])
    
    # Route based on target type
    if isinstance(parsed_command.target, SchemaWord):
        # Create database
        return await _create_database(
            schema_word=parsed_command.target,
            name=parsed_command.target_name,
            fields=parsed_command.attributes,
            context=context
        )
    elif isinstance(parsed_command.target, EntityWord):
        # Create table (future - validation layer will block for now)
        return await _create_table(
            entity_word=parsed_command.target,
            context=context
        )
    else:
        return ErrorResult(errors=["Invalid target for create operation"])


async def drop_handler(parsed_command: ParsedCommand, context: Context) -> HandlerResult:
    """
    Drop database or table structure.
    
    Structure operations work on:
    - Schema (database): drop company "Valmetrics"
    - Entity (table): drop table brand [FUTURE - blocked by validation]
    - Fields (columns): drop field vision [FUTURE - blocked by validation]
    """
    
    if isinstance(parsed_command.target, SchemaWord):
        # Drop database
        return await _drop_database(
            name=parsed_command.target_name,
            context=context
        )
    elif isinstance(parsed_command.target, EntityWord):
        # Drop table (future - validation layer will block for now)
        return await _drop_table(
            entity_word=parsed_command.target,
            context=context
        )
    else:
        return ErrorResult(errors=["Invalid target for drop operation"])


# ==================== CONTENT OPERATIONS ====================

async def add_handler(parsed_command: ParsedCommand, context: Context) -> HandlerResult:
    """Add or set field values."""
    
    if not parsed_command.attributes:
        return ErrorResult(errors=["No fields specified"])
    
    # Get company name
    company_name = get_company_name_from_context(context)
    if not company_name:
        return ErrorResult(errors=["Must be in organization context"])
    
    # Add/update field values
    return await _add_field_values(
        entity_model=parsed_command.target_model,
        fields=parsed_command.attributes,
        filters=parsed_command.filters,  # NEW: can filter which rows to update
        company_name=company_name,
        context=context
    )


async def delete_handler(parsed_command: ParsedCommand, context: Context) -> HandlerResult:
    """Delete data (not structure - use drop for that)."""
    
    company_name = get_company_name_from_context(context)
    if not company_name:
        return ErrorResult(errors=["Must be in organization context"])
    
    # Determine what to delete based on what was specified
    if parsed_command.field_words:
        # Delete specific fields: delete brand vision mission
        # Can combine with filters: delete news date [category=product]
        return await _delete_field_values(
            entity_model=parsed_command.target_model,
            field_names=parsed_command.field_words,
            filters=parsed_command.filters,
            company_name=company_name,
            context=context
        )
    
    elif parsed_command.filters:
        # Delete matching rows: delete news [category=product]
        cardinality = getattr(parsed_command.target_model, 'cardinality', Cardinality.SINGLE)
        if cardinality == Cardinality.SINGLE:
            return ErrorResult(errors=["Cannot delete rows from single-record entity"])
        
        return await _delete_rows(
            entity_model=parsed_command.target_model,
            filters=parsed_command.filters,
            company_name=company_name,
            context=context
        )
    
    else:
        # Delete all entity content: delete brand
        return await _reset_entity(
            entity_model=parsed_command.target_model,
            company_name=company_name,
            context=context,
            to_defaults=False  # Delete all vs reset to defaults
        )


async def reset_handler(parsed_command: ParsedCommand, context: Context) -> HandlerResult:
    """Reset entity or fields to default values."""
    
    company_name = get_company_name_from_context(context)
    if not company_name:
        return ErrorResult(errors=["Must be in organization context"])
    
    if parsed_command.field_words:
        # Reset specific fields to defaults
        return await _reset_field_values(
            entity_model=parsed_command.target_model,
            field_names=parsed_command.field_words,
            filters=parsed_command.filters,
            company_name=company_name,
            context=context
        )
    else:
        # Reset entire entity to defaults
        return await _reset_entity(
            entity_model=parsed_command.target_model,
            company_name=company_name,
            context=context,
            to_defaults=True
        )


async def show_handler(parsed_command: ParsedCommand, context: Context) -> HandlerResult:
    """
    Display data with optional field selection and filtering.
    
    Can show both structure and content:
    - show company "Valmetrics" → database info (structure)
    - show brand → entity data (content)
    - show brand vision → specific field (content)
    - show news [category=product] → filtered rows (content)
    """
    
    # Database structure info
    if isinstance(parsed_command.target, SchemaWord):
        return await _show_database(
            name=parsed_command.target_name,
            context=context
        )
    
    # Entity content
    company_name = get_company_name_from_context(context)
    if not company_name:
        return ErrorResult(errors=["Must be in organization context"])
    
    # Show entity data with optional field selection and filtering
    return await _show_entity(
        entity_model=parsed_command.target_model,
        field_names=parsed_command.field_words,  # Empty = show all fields
        filters=parsed_command.filters,  # None = show all rows
        company_name=company_name,
        context=context
    )


# ==================== DATABASE OPERATION HELPERS ====================

async def _create_database(
    schema_word: SchemaWord, 
    name: Optional[str], 
    fields: Dict[str, Any], 
    context: Context
) -> HandlerResult:
    """Create organization database."""
    
    entity_type = schema_word.id
    
    try:
        # Prepare entity data with user-provided fields
        entity_data = {
            "name": name or f"{entity_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        entity_data.update(fields)

        # Validate using the schema class (Pydantic validation applies defaults automatically)
        try:
            entity_instance = schema_word.schema_class(**entity_data)
            validated_data = entity_instance.model_dump()
        except Exception as e:
            return ErrorResult(
                errors=[f"Validation failed: {str(e)}"],
                suggestions=["Check field names and value formats"]
            )

        # Use generic storage - works for ANY entity
        storage_result = StorageInterface.create_entity(
            entity_type=entity_type, 
            data=validated_data, 
            context=context
        )

        if not storage_result.success:
            return ErrorResult(
                errors=[storage_result.error or f"Failed to create {entity_type}"],
                suggestions=["Check database connection and permissions"]
            )

        # Handle context switch for company creation (navigation behavior)
        if entity_type == "company":
            result = CommandResult(
                success=True,
                message=storage_result.message or f"Created {entity_type} {validated_data['name']}",
                data={
                    "entity_type": entity_type,
                    "entity_name": validated_data['name'],
                    "fields": validated_data,
                    "storage_result": storage_result.data,
                    "context_switch": {
                        "level": "ORG",
                        "org_id": 1,
                        "org_name": validated_data["name"],
                        "org_db_path": None
                    }
                }
            )
            return result

        # Return generic success result
        return CommandResult(
            success=True,
            message=storage_result.message or f"Created {entity_type} {validated_data['name']}",
            data={
                "entity_type": entity_type,
                "entity_name": validated_data['name'],
                "fields": validated_data,
                "storage_result": storage_result.data
            }
        )

    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to create entity: {str(e)}"],
            suggestions=["Check input values and system status"]
        )


async def _drop_database(name: Optional[str], context: Context) -> HandlerResult:
    """Drop organization database."""
    
    if context.level != ContextLevel.SYS:
        return ErrorResult(
            errors=["Can only drop databases from system level"],
            suggestions=["Use 'cd' to navigate to system level first"]
        )
    
    if not name:
        return ErrorResult(
            errors=["Database name required for deletion"],
            suggestions=["Specify database name: drop company 'CompanyName'"]
        )
    
    # For company deletion, use intelligent name matching
    actual_company_name = find_company_by_name(name, context)
    if not actual_company_name:
        return ErrorResult(
            errors=[f"Company '{name}' not found"],
            suggestions=["Check company name spelling or list existing companies"]
        )
    
    # Delete the entire entity
    delete_result = StorageInterface.delete_entity("company", actual_company_name, context)
    
    if delete_result.success:
        return CommandResult(
            success=True,
            message=f"Dropped database {actual_company_name}",
            data={
                "entity_type": "company",
                "deleted_entity": actual_company_name,
                "delete_message": delete_result.message or "Successfully deleted"
            }
        )
    else:
        return ErrorResult(
            errors=[delete_result.error or f"Failed to drop database"],
            suggestions=["Check if database exists and database permissions"]
        )


async def _show_database(name: Optional[str], context: Context) -> HandlerResult:
    """Show database information."""
    
    if not name:
        return ErrorResult(
            errors=["Database name required"],
            suggestions=["Specify database name: show company 'CompanyName'"]
        )
    
    # For company info, use intelligent name matching
    actual_company_name = find_company_by_name(name, context)
    if not actual_company_name:
        return ErrorResult(
            errors=[f"Company '{name}' not found"],
            suggestions=["Check company name spelling or list existing companies"]
        )
    
    # Load company data
    load_result = StorageInterface.load_entity("company", actual_company_name, context)
    if not load_result.success or not load_result.data:
        return ErrorResult(
            errors=[f"Failed to load company data"],
            suggestions=["Check if company exists and database connection"]
        )
    
    return CommandResult(
        success=True,
        message=f"Database information for {actual_company_name}",
        data={
            "entity_type": "company",
            "entity_name": actual_company_name,
            "database_info": load_result.data,
            "formatted_data": format_entity_data_for_display(load_result.data)
        }
    )


async def _create_table(entity_word: EntityWord, context: Context) -> HandlerResult:
    """Create table (future implementation)."""
    return ErrorResult(
        errors=["Table creation not yet supported"],
        suggestions=["Use existing entity types or wait for future implementation"]
    )


async def _drop_table(entity_word: EntityWord, context: Context) -> HandlerResult:
    """Drop table (future implementation)."""
    return ErrorResult(
        errors=["Table deletion not yet supported"],
        suggestions=["Use existing entity types or wait for future implementation"]
    )


# ==================== ENTITY CONTENT OPERATION HELPERS ====================

async def _add_field_values(
    entity_model: Type[BaseModel],
    fields: Dict[str, str],
    filters: Optional[Any],
    company_name: str,
    context: Context
) -> HandlerResult:
    """Add/update field values, optionally filtered."""
    
    try:
        entity_type = entity_model.__name__.replace("Entity", "").lower()
        
        # Create entity if it doesn't exist using Pydantic model defaults
        if not entity_exists(entity_type, company_name, context):
            # Create default entity data using the entity model's Pydantic defaults
            default_entity_data = {
                "name": f"default_{entity_type}",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            
            # Validate and apply model defaults
            try:
                entity_instance = entity_model(**default_entity_data)
                default_data = entity_instance.model_dump()
            except Exception as e:
                return ErrorResult(
                    errors=[f"Failed to create default entity: {str(e)}"],
                    suggestions=["Check entity model configuration"]
                )
                
            StorageInterface.save_entity(entity_type, default_data, company_name, context)

        # Load current entity data
        load_result = StorageInterface.load_entity(entity_type, company_name, context)
        current_data = load_result.data if load_result.success else {}
        
        # Ensure current_data is not None
        if current_data is None:
            current_data = {}

        # Create updated data with new fields
        updated_data = current_data.copy()
        updated_data.update(fields)
        updated_data["updated_at"] = datetime.now().isoformat()

        # Save the updated entity
        save_result = StorageInterface.save_entity(entity_type, updated_data, company_name, context)
        if not save_result.success:
            return ErrorResult(
                errors=[save_result.error or f"Failed to save {entity_type} data"],
                suggestions=["Check database permissions and disk space"]
            )

        return CommandResult(
            success=True,
            message=f"Added fields to {entity_type}",
            data={
                "entity_type": entity_type,
                "added_fields": fields
            }
        )

    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to add fields: {str(e)}"],
            suggestions=["Check input format and system status"]
        )


async def _delete_field_values(
    entity_model: Type[BaseModel],
    field_names: List[str],
    filters: Optional[Any],
    company_name: str,
    context: Context
) -> HandlerResult:
    """Delete specific field values, optionally filtered."""
    
    entity_type = entity_model.__name__.replace("Entity", "").lower()
    
    # Check if entity exists
    if not entity_exists(entity_type, company_name, context):
        return ErrorResult(
            errors=[f"Entity '{entity_type}' does not exist for company '{company_name}'"],
            suggestions=[f"Create the {entity_type} first or check the entity name"]
        )
    
    # Load current entity data
    load_result = StorageInterface.load_entity(entity_type, company_name, context)
    current_data = load_result.data if load_result.success else None
    if current_data is None:
        return ErrorResult(
            errors=[f"No data found for {entity_type}"],
            suggestions=["Check entity exists and database connection"]
        )
    
    # Remove the specified fields
    updated_data = current_data.copy()
    removed_fields = []
    
    for field_name in field_names:
        if field_name in updated_data:
            # Set to null (rather than deleting the key entirely)
            updated_data[field_name] = None
            removed_fields.append(field_name)
    
    if not removed_fields:
        return ErrorResult(
            errors=[f"None of the specified fields exist in {entity_type}: {', '.join(field_names)}"],
            suggestions=["Check field names or show the entity to see available fields"]
        )
    
    # Update timestamp
    if "updated_at" in updated_data:
        updated_data["updated_at"] = datetime.now().isoformat()
    
    # Save the updated entity
    save_result = StorageInterface.save_entity(entity_type, updated_data, company_name, context)
    if not save_result.success:
        return ErrorResult(
            errors=[save_result.error or f"Failed to save {entity_type} data"],
            suggestions=["Check database permissions and disk space"]
        )
    
    return CommandResult(
        success=True,
        message=f"Deleted fields from {entity_type}",
        data={
            "entity_type": entity_type,
            "removed_fields": removed_fields
        }
    )


async def _delete_rows(
    entity_model: Type[BaseModel],
    filters: Any,
    company_name: str,
    context: Context
) -> HandlerResult:
    """Delete rows matching filters."""
    
    entity_type = entity_model.__name__.replace("Entity", "").lower()
    
    # This would need to be implemented with proper filter support for multi-record entities
    return ErrorResult(
        errors=["Row deletion with filters not yet implemented"],
        suggestions=["Use field deletion or reset entity for now"]
    )


async def _reset_entity(
    entity_model: Type[BaseModel],
    company_name: str,
    context: Context,
    to_defaults: bool
) -> HandlerResult:
    """Reset entity to defaults or clear all data."""
    
    entity_type = entity_model.__name__.replace("Entity", "").lower()
    
    if to_defaults:
        # Reset to model defaults
        try:
            default_entity_data = {
                "name": f"default_{entity_type}",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            
            entity_instance = entity_model(**default_entity_data)
            default_data = entity_instance.model_dump()
        except Exception as e:
            return ErrorResult(
                errors=[f"Failed to generate defaults: {str(e)}"],
                suggestions=["Check entity model configuration"]
            )
        
        # Save the default entity
        save_result = StorageInterface.save_entity(entity_type, default_data, company_name, context)
        if not save_result.success:
            return ErrorResult(
                errors=[save_result.error or f"Failed to reset {entity_type}"],
                suggestions=["Check database permissions and disk space"]
            )
        
        return CommandResult(
            success=True,
            message=f"Reset {entity_type} to defaults",
            data={
                "entity_type": entity_type,
                "operation": "reset_to_defaults"
            }
        )
    else:
        # Delete all entity content
        delete_result = StorageInterface.delete_entity(entity_type, company_name, context)
        
        if delete_result.success:
            return CommandResult(
                success=True,
                message=f"Deleted all {entity_type} data",
                data={
                    "entity_type": entity_type,
                    "operation": "delete_all"
                }
            )
        else:
            return ErrorResult(
                errors=[delete_result.error or f"Failed to delete {entity_type}"],
                suggestions=["Check database permissions"]
            )


async def _reset_field_values(
    entity_model: Type[BaseModel],
    field_names: List[str],
    filters: Optional[Any],
    company_name: str,
    context: Context
) -> HandlerResult:
    """Reset specific fields to defaults."""
    
    entity_type = entity_model.__name__.replace("Entity", "").lower()
    
    # Get default values for the fields from the model
    try:
        default_instance = entity_model()
        default_data = default_instance.model_dump()
    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to get default values: {str(e)}"],
            suggestions=["Check entity model configuration"]
        )
    
    # Load current entity data
    load_result = StorageInterface.load_entity(entity_type, company_name, context)
    current_data = load_result.data if load_result.success else {}
    if current_data is None:
        current_data = {}
    
    # Reset specified fields to defaults
    updated_data = current_data.copy()
    reset_fields = []
    
    for field_name in field_names:
        if field_name in default_data:
            updated_data[field_name] = default_data[field_name]
            reset_fields.append(field_name)
    
    if not reset_fields:
        return ErrorResult(
            errors=[f"None of the specified fields have default values: {', '.join(field_names)}"],
            suggestions=["Check field names or use delete to clear fields"]
        )
    
    # Update timestamp
    updated_data["updated_at"] = datetime.now().isoformat()
    
    # Save the updated entity
    save_result = StorageInterface.save_entity(entity_type, updated_data, company_name, context)
    if not save_result.success:
        return ErrorResult(
            errors=[save_result.error or f"Failed to save {entity_type} data"],
            suggestions=["Check database permissions and disk space"]
        )
    
    return CommandResult(
        success=True,
        message=f"Reset fields in {entity_type} to defaults",
        data={
            "entity_type": entity_type,
            "reset_fields": reset_fields
        }
    )


async def _show_entity(
    entity_model: Type[BaseModel],
    field_names: Optional[List[str]],
    filters: Optional[Any],
    company_name: str,
    context: Context
) -> HandlerResult:
    """Show entity data with optional field/row filtering."""
    
    try:
        entity_type = entity_model.__name__.replace("Entity", "").lower()

        # Check if entity exists
        if not entity_exists(entity_type, company_name, context):
            return ErrorResult(
                errors=[f"Entity '{entity_type}' does not exist for company '{company_name}'"],
                suggestions=[f"Create the {entity_type} first or check the entity name"]
            )

        # Load entity data
        load_result = StorageInterface.load_entity(entity_type, company_name, context)
        entity_data = load_result.data if load_result.success else None
        if entity_data is None:
            return ErrorResult(
                errors=[f"No data found for {entity_type}"],
                suggestions=["Check entity exists and database connection"]
            )

        # For multi-cardinality entities, we might want to show multiple records
        cardinality = getattr(entity_model, 'cardinality', Cardinality.SINGLE)
        if cardinality == Cardinality.MULTIPLE:
            # Load all records and apply filtering
            all_records = load_all_entities(entity_type, company_name, context)
            
            # Apply filters if present
            if filters:
                try:
                    filtered_records = apply_filters(all_records, filters)
                except Exception as filter_error:
                    return ErrorResult(
                        errors=[f"Filter application failed: {str(filter_error)}"],
                        suggestions=["Check filter syntax and field names"]
                    )
            else:
                filtered_records = all_records
            
            # Format multiple records
            count = len(filtered_records)
            total_count = len(all_records)
            
            message = f"Found {count} of {total_count} {entity_type} records" if filters else f"Found {count} {entity_type} records"
            
            return CommandResult(
                success=True,
                message=message,
                data={
                    "entity_type": entity_type,
                    "records": filtered_records,
                    "count": count,
                    "total_count": total_count,
                    "filtered": bool(filters)
                }
            )
        else:
            # Single record - format data for display
            specific_fields = field_names if field_names else None
            formatted_data = format_entity_data_for_display(
                entity_data, specific_fields
            )

            return CommandResult(
                success=True,
                message=f"Displaying {entity_type} data",
                data={
                    "entity_type": entity_type,
                    "formatted_data": formatted_data,
                    "raw_data": entity_data
                }
            )

    except Exception as e:
        return ErrorResult(
            errors=[f"Failed to show entity data: {str(e)}"],
            suggestions=["Check entity exists and database connection"]
        )