#!/usr/bin/env python3
"""
Realistic delete command test with proper setup.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vlmx_sh2.dsl.parser import VLMXParser
from vlmx_sh2.core.context import Context

async def test_realistic_delete():
    """Test realistic delete scenario."""
    print("=== Realistic Delete Test ===")
    
    parser = VLMXParser()
    
    # Step 1: Create company at SYS level
    sys_context = Context(level=0)
    print("\n1. Creating company 'ACME'...")
    
    result = parser.parse("create company ACME")
    if result.is_valid:
        exec_result = await parser.execute_parsed_command(result, sys_context)
        print(f"   Create result: {exec_result.success if hasattr(exec_result, 'success') else 'Unknown'}")
    
    # Step 2: Navigate to ORG level
    org_context = Context(level=1, org_id=1, org_name="ACME")
    print("\n2. Adding brand attributes...")
    
    # Add some brand data
    result = parser.parse("add brand vision='To innovate' mission='Our mission'")
    if result.is_valid:
        exec_result = await parser.execute_parsed_command(result, org_context)
        print(f"   Add result: {exec_result.success if hasattr(exec_result, 'success') else 'Unknown'}")
    
    # Step 3: Show brand data before delete
    print("\n3. Showing brand data before delete...")
    result = parser.parse("show brand")
    if result.is_valid:
        exec_result = await parser.execute_parsed_command(result, org_context)
        if hasattr(exec_result, 'success') and exec_result.success:
            data = exec_result.attributes.get('data', 'No data')
            print(f"   Brand data: {data}")
    
    # Step 4: Delete specific attribute
    print("\n4. Deleting brand vision...")
    result = parser.parse("delete brand vision")
    print(f"   Parsed attribute words: {[w.id for w in result.attribute_words]}")
    
    if result.is_valid:
        exec_result = await parser.execute_parsed_command(result, org_context)
        print(f"   Delete result: {exec_result.success if hasattr(exec_result, 'success') else 'Unknown'}")
        if hasattr(exec_result, 'attributes'):
            removed = exec_result.attributes.get('removed_attributes', 'None')
            print(f"   Removed attributes: {removed}")
    
    # Step 5: Show brand data after delete
    print("\n5. Showing brand data after delete...")
    result = parser.parse("show brand")
    if result.is_valid:
        exec_result = await parser.execute_parsed_command(result, org_context)
        if hasattr(exec_result, 'success') and exec_result.success:
            data = exec_result.attributes.get('data', 'No data')
            print(f"   Brand data after delete: {data}")

if __name__ == "__main__":
    asyncio.run(test_realistic_delete())