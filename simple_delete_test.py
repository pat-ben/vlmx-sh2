#!/usr/bin/env python3
"""
Simple delete command test.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vlmx_sh2.dsl.parser import VLMXParser
from vlmx_sh2.core.models.context import Context

async def test_simple_delete():
    parser = VLMXParser()
    org_context = Context(level=1, org_id=1, org_name="TestCompany")
    
    # Test delete command parsing and execution
    test_command = "delete brand vision"
    print(f"Testing: '{test_command}'")
    
    result = parser.parse(test_command)
    print(f"Parse valid: {result.is_valid}")
    print(f"Attribute words: {[w.id for w in result.attribute_words]}")
    
    if result.is_valid and result.action_handler:
        try:
            exec_result = await parser.execute_parsed_command(result, org_context)
            print(f"Execution result: {exec_result}")
            print(f"Result type: {type(exec_result)}")
            
            if hasattr(exec_result, 'success'):
                print(f"Success: {exec_result.success}")
                if hasattr(exec_result, 'errors'):
                    print(f"Errors: {exec_result.errors}")
                if hasattr(exec_result, 'message'):
                    print(f"Message: {exec_result.message}")
                    
        except Exception as e:
            print(f"Execution error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple_delete())