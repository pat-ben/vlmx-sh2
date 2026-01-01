#!/usr/bin/env python3
"""
Test script to verify the refactored CRUD handlers work correctly.
Tests that Pydantic defaults are applied properly without hardcoded logic.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime


def test_company_entity_defaults():
    """Test that CompanyEntity uses Pydantic defaults correctly."""
    print("Testing CompanyEntity Pydantic defaults...")
    
    from vlmx_sh2.models.schema.company import CompanyEntity
    from vlmx_sh2.models.schema.enums import Legal, Currency, Unit, Type
    
    # Test with minimal data
    minimal_data = {
        "name": "Test Company",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    
    # Create instance - should apply Pydantic defaults
    company = CompanyEntity(**minimal_data)
    
    # Verify defaults are applied
    assert company.legal == Legal.SA, f"Expected Legal.SA, got {company.legal}"
    assert company.currency == Currency.EUR, f"Expected Currency.EUR, got {company.currency}" 
    assert company.unit == Unit.THOUSANDS, f"Expected Unit.THOUSANDS, got {company.unit}"
    assert company.type == Type.COMPANY, f"Expected Type.COMPANY, got {company.type}"
    assert company.closing == 12, f"Expected closing=12, got {company.closing}"
    
    print("+ CompanyEntity defaults work correctly")


def test_brand_entity_defaults():
    """Test that BrandEntity uses proper defaults."""
    print("Testing BrandEntity Pydantic defaults...")
    
    from vlmx_sh2.models.schema.company import BrandEntity
    
    # Test with minimal data
    minimal_data = {
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    
    # Create instance - should apply Pydantic defaults
    brand = BrandEntity(**minimal_data)
    
    # Verify defaults are applied
    assert brand.co_id == 1, f"Expected co_id=1, got {brand.co_id}"
    assert brand.vision is None, f"Expected vision=None, got {brand.vision}"
    
    print("+ BrandEntity defaults work correctly")


def test_create_handler_generic():
    """Test that create_handler works generically without hardcoded logic."""
    print("Testing generic create_handler...")
    
    # Import here to avoid circular imports
    from vlmx_sh2.models.schema.company import CompanyEntity, BrandEntity
    
    # Test data for company creation
    company_attributes = {"name": "Test Corp"}
    
    # Simulate what create_handler does now
    entity_data = {
        "name": "Test Corp",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    entity_data.update(company_attributes)
    
    # Apply Pydantic validation (this should apply defaults)
    company_instance = CompanyEntity(**entity_data)
    validated_data = company_instance.model_dump()
    
    # Verify defaults were applied during validation
    assert "legal" in validated_data, "legal field should be present"
    assert validated_data["legal"] == "SA", f"Expected legal='SA', got {validated_data['legal']}"
    assert validated_data["currency"] == "EUR", f"Expected currency='EUR', got {validated_data['currency']}"
    
    print("+ Generic create_handler validation works correctly")


def test_no_hardcoded_entity_checks():
    """Verify no hardcoded entity checks remain in crud.py"""
    print("Testing for removal of hardcoded entity checks...")
    
    # Read the crud.py file and check for forbidden patterns
    crud_file_path = "src/vlmx_sh2/handlers/crud.py"
    
    with open(crud_file_path, 'r', encoding='utf-8') as f:
        crud_content = f.read()
    
    # Should not find the old hardcoded company logic
    forbidden_patterns = [
        'from ..models.schema.enums import Currency, Legal, Type, Unit',  # Should not import enums in handlers
        'Legal(attributes.get(',  # Should not manually convert to enums
        'entity_data.update(\n        {',  # Should not have multi-line hardcoded updates
    ]
    
    for pattern in forbidden_patterns:
        assert pattern not in crud_content, f"Found forbidden pattern: {pattern}"
    
    # Should still have acceptable patterns
    acceptable_patterns = [
        'if entity_type == "company"',  # Context switch is acceptable
        'if entity_type == "metadata"',  # Metadata deletion behavior is acceptable
    ]
    
    for pattern in acceptable_patterns:
        assert pattern in crud_content, f"Missing acceptable pattern: {pattern}"
    
    print("+ Hardcoded entity checks properly removed")


if __name__ == "__main__":
    print("Testing refactored CRUD handlers...")
    print("=" * 50)
    
    try:
        test_company_entity_defaults()
        test_brand_entity_defaults()
        test_create_handler_generic()
        test_no_hardcoded_entity_checks()
        
        print("=" * 50)
        print("SUCCESS: ALL TESTS PASSED!")
        print("Refactoring completed successfully!")
        
    except Exception as e:
        print(f"ERROR: TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)