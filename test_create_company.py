#!/usr/bin/env python3
"""
Test creating a company to see if directories and JSON files are actually created.
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vlmx_sh2.dsl.parser import VLMXParser
from vlmx_sh2.core.models.context import Context

async def test_create_company():
    """Test creating a company and check if files are created."""
    print("=== Testing Company Creation ===")
    
    parser = VLMXParser()
    context = Context(level=0)  # SYS level
    
    # Test the "create company DD" command
    test_command = "create company DD entity=SA currency=EUR"
    print(f"Testing: '{test_command}'")
    
    try:
        # Parse the command
        result = parser.parse(test_command)
        
        print(f"Parse result:")
        print(f"  Valid: {result.is_valid}")
        print(f"  Action words: {[w.id for w in result.action_words]}")
        print(f"  Entity words: {[w.id for w in result.entity_words]}")
        print(f"  Entity values: {result.entity_values}")
        print(f"  Attributes: {result.attribute_values}")
        print(f"  Has handler: {result.action_handler is not None}")
        print(f"  Entity model: {result.entity_model.__name__ if result.entity_model else None}")
        
        if result.is_valid and result.action_handler:
            print(f"\nExecuting command...")
            
            # Execute the command
            exec_result = await parser.execute_parsed_command(result, context)
            
            print(f"Execution result: {exec_result}")
            print(f"Result type: {type(exec_result)}")
            
            # Check if files were created
            print(f"\nChecking for created files...")
            
            # Look for company directories/files
            current_dir = os.getcwd()
            print(f"Current directory: {current_dir}")
            
            # Check for common locations where company data might be stored
            possible_paths = [
                "data/companies/DD",
                "companies/DD", 
                "DD",
                "data/DD",
                "storage/DD",
                ".vlmx/companies/DD"
            ]
            
            found_files = False
            for path in possible_paths:
                if os.path.exists(path):
                    print(f"  Found: {path}")
                    if os.path.isdir(path):
                        contents = os.listdir(path)
                        print(f"    Contents: {contents}")
                    found_files = True
                    
            # Also check for any JSON files created
            for root, dirs, files in os.walk("."):
                for file in files:
                    if "DD" in file and file.endswith(".json"):
                        print(f"  Found JSON file: {os.path.join(root, file)}")
                        found_files = True
            
            if not found_files:
                print(f"  No company files/directories found")
                
                # Let's check what the storage module does
                from vlmx_sh2.storage.database import create_company
                print(f"\n  Testing storage module directly...")
                
                test_data = {
                    "name": "TEST_COMPANY",
                    "entity": "SA",
                    "type": "COMPANY",
                    "currency": "EUR",
                    "unit": "THOUSANDS"
                }
                
                storage_result = create_company(test_data, context)
                print(f"  Storage result: {storage_result}")
        
        else:
            print(f"Cannot execute: valid={result.is_valid}, handler={result.action_handler is not None}")
            if result.errors:
                print(f"Errors: {result.errors}")
                
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Run the test."""
    print("Company Creation Test")
    print("=" * 30)
    
    try:
        asyncio.run(test_create_company())
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())