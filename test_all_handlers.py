#!/usr/bin/env python3
"""
Test all ACTION handlers to make sure they work.
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vlmx_sh2.dsl.parser import VLMXParser
from vlmx_sh2.models.context import Context

async def test_all_handlers():
    """Test all ACTION word handlers."""
    print("=== Testing All ACTION Handlers ===")
    
    parser = VLMXParser()
    sys_context = Context(level=0)  # SYS level
    org_context = Context(level=1, org_id=1, org_name="TestCompany")  # ORG level
    
    test_cases = [
        # CREATE handler (should work at SYS level)
        {
            "command": "create company TestCompany entity=SA currency=EUR",
            "context": sys_context,
            "description": "Create handler - company creation"
        },
        
        # NAVIGATION handler (should work at any level)
        {
            "command": "cd ~",
            "context": sys_context,
            "description": "Navigate handler - go to root"
        },
        {
            "command": "cd TestCompany",
            "context": sys_context,
            "description": "Navigate handler - go to company"
        },
        
        # ADD handler (should work at ORG level)
        {
            "command": "add brand vision='Our company vision'",
            "context": org_context,
            "description": "Add handler - set brand vision"
        },
        
        # UPDATE handler (should work at ORG level)  
        {
            "command": "update brand mission='Updated mission statement'",
            "context": org_context,
            "description": "Update handler - modify brand mission"
        },
        
        # SHOW handler (should work at ORG level)
        {
            "command": "show brand",
            "context": org_context,
            "description": "Show handler - display brand data"
        },
        
        # Test shortcuts
        {
            "command": "cc AnotherCompany",
            "context": sys_context,
            "description": "Shortcut - cc → create company"
        },
        {
            "command": "sb",
            "context": org_context,
            "description": "Shortcut - sb → show brand"
        },
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['description']}")
        print(f"   Command: '{test_case['command']}'")
        print(f"   Context: Level {test_case['context'].level}")
        
        try:
            # Parse the command
            result = parser.parse(test_case['command'])
            
            if result.is_valid and result.action_handler:
                # Execute the command
                exec_result = await parser.execute_parsed_command(result, test_case['context'])
                
                # Check result type and success
                if hasattr(exec_result, 'success'):
                    success = exec_result.success
                    if hasattr(exec_result, 'message') and exec_result.message:
                        message = exec_result.message
                    else:
                        message = f"Operation: {getattr(exec_result, 'operation', 'unknown')}"
                elif isinstance(exec_result, dict):
                    success = exec_result.get('success', False)
                    message = exec_result.get('message', 'No message')
                else:
                    success = exec_result is not None
                    message = str(exec_result)
                
                status = "[SUCCESS]" if success else "[FAILED]"
                print(f"   Result: {status} {message}")
                
            else:
                print(f"   Result: [FAILED] Parse failed - valid:{result.is_valid}, handler:{result.action_handler is not None}")
                if result.errors:
                    print(f"   Errors: {result.errors}")
                
        except Exception as e:
            print(f"   Result: [ERROR] {str(e)}")

def main():
    """Run all handler tests."""
    print("VLMX-SH2 Handler Test")
    print("=" * 30)
    
    try:
        asyncio.run(test_all_handlers())
        print(f"\n" + "=" * 30)
        print("Handler testing completed!")
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())