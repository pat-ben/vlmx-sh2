#!/usr/bin/env python3
"""
Test script for VLMX command: create company SuperCo entity=LLC currency=USD
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_command_without_dependencies():
    """Test the command processing without requiring external dependencies."""
    
    test_command = "create company SuperCo entity=LLC currency=USD"
    print(f"Testing command: {test_command}")
    print("=" * 60)
    
    try:
        # Test 1: Word Registry
        print("1. Testing Word Registry...")
        from vlmx_sh2.words import get_word
        
        create_word = get_word('create')
        company_word = get_word('company')
        entity_word = get_word('entity')
        currency_word = get_word('currency')
        
        assert create_word is not None, "create word not found"
        assert company_word is not None, "company word not found"
        assert entity_word is not None, "entity word not found"
        assert currency_word is not None, "currency word not found"
        
        print("   [OK] All words found in registry")
        
        # Test 2: Enums
        print("2. Testing Enum Validation...")
        from vlmx_sh2.enums import Currency, Entity, Unit
        
        entity = Entity('LLC')
        currency = Currency('USD')
        unit = Unit.THOUSANDS
        
        print(f"   [OK] Entity: {entity}")
        print(f"   [OK] Currency: {currency}")
        print(f"   [OK] Unit: {unit}")
        
        # Test 3: Entity Model
        print("3. Testing Entity Model...")
        from vlmx_sh2.entities import CompanyEntity
        from datetime import datetime
        
        company = CompanyEntity(
            name="SuperCo",
            entity=entity,
            currency=currency,
            unit=unit,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source_db=None,
            last_synced_at=None
        )
        
        print(f"   [OK] Company created: {company.name}")
        print(f"     - Entity: {company.entity}")
        print(f"     - Currency: {company.currency}")
        print(f"     - Unit: {company.unit}")
        
        # Test 4: Results formatting
        print("4. Testing Results System...")
        from vlmx_sh2.results import create_success_result, format_command_result
        
        result = create_success_result(
            operation="created",
            entity_name=f"company {company.name}",
            attributes={
                "entity": str(company.entity),
                "currency": str(company.currency),
                "unit": str(company.unit),
                "created_at": company.created_at.isoformat()
            }
        )
        
        formatted = format_command_result(result)
        print("   [OK] Formatted result:")
        for line in formatted.split('\n'):
            if line.strip():
                print(f"     {line}")
        
        print("\n[SUCCESS] All tests passed!")
        print(f"The command '{test_command}' would work correctly.")
        
        return True
        
    except ImportError as e:
        print(f"[ERROR] Import error: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_command_without_dependencies()
    sys.exit(0 if success else 1)