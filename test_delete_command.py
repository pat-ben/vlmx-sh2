#!/usr/bin/env python3
"""
Test the delete command functionality.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vlmx_sh2.dsl.parser import VLMXParser
from vlmx_sh2.core.models.context import Context

async def test_delete_command():
    """Test the delete command end-to-end."""
    print("=== Testing Delete Command ===")
    
    parser = VLMXParser()
    sys_context = Context(level=0)  # SYS level
    org_context = Context(level=1, org_id=1, org_name="TestCompany")  # ORG level
    
    commands = [
        # First, create a company
        {
            "command": "create company TestCompany",
            "context": sys_context,
            "description": "Create test company"
        },
        
        # Add some brand attributes
        {
            "command": "add brand vision='Our test vision' mission='Our test mission'",
            "context": org_context,
            "description": "Add brand attributes"
        },
        
        # Show brand data before delete
        {
            "command": "show brand",
            "context": org_context,
            "description": "Show brand before delete"
        },
        
        # Delete a specific attribute
        {
            "command": "delete brand vision",
            "context": org_context,
            "description": "Delete brand vision attribute"
        },
        
        # Show brand data after delete
        {
            "command": "show brand",
            "context": org_context,
            "description": "Show brand after delete"
        },
    ]
    
    for i, test in enumerate(commands, 1):
        print(f"\n{i}. {test['description']}")
        print(f"   Command: '{test['command']}'")
        
        try:
            # Parse the command
            result = parser.parse(test['command'])
            
            if result.is_valid and result.action_handler:
                # Execute the command
                exec_result = await parser.execute_parsed_command(result, test['context'])
                
                # Check result
                if hasattr(exec_result, 'success'):
                    success = exec_result.success
                    message = getattr(exec_result, 'message', 'No message')
                elif isinstance(exec_result, dict):
                    success = exec_result.get('success', False)
                    message = exec_result.get('message', 'No message')
                else:
                    success = True
                    message = str(exec_result)
                
                status = "[SUCCESS]" if success else "[FAILED]"
                print(f"   Result: {status} {message}")
                
            else:
                print(f"   Result: [FAILED] Parse failed")
                if result.errors:
                    print(f"   Errors: {result.errors}")
                    
        except Exception as e:
            print(f"   Result: [ERROR] {str(e)}")
            import traceback
            traceback.print_exc()

def main():
    """Run the delete command test."""
    print("Delete Command Test")
    print("=" * 30)
    
    try:
        asyncio.run(test_delete_command())
        print(f"\n" + "=" * 30)
        print("Delete command test completed!")
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())