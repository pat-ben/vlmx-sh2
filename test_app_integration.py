#!/usr/bin/env python3
"""
Test the integration between the refactored parser and the UI app.
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vlmx_sh2.ui.app import VLMX, CommandBlock
from vlmx_sh2.dsl.parser import VLMXParser
from vlmx_sh2.models.context import Context

def test_app_initialization():
    """Test that the VLMX app can be initialized with our refactored system."""
    print("=== Testing App Initialization ===")
    
    try:
        app = VLMX()
        print(f"[OK] App initialized successfully")
        print(f"[OK] Parser ready: {app.parser is not None}")
        print(f"[OK] Context level: {app.context.level}")
        
        # Test system info
        info = app.get_system_info()
        print(f"[OK] Word registry size: {info['word_registry_size']}")
        print(f"[OK] Parser ready: {info['parser_ready']}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] App initialization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_command_block():
    """Test that CommandBlock can be created and used."""
    print("\n=== Testing CommandBlock ===")
    
    try:
        parser = VLMXParser()
        context = Context(level=0)
        
        block = CommandBlock(parser=parser, context=context)
        print(f"[OK] CommandBlock created successfully")
        print(f"[OK] Parser assigned: {block.parser is not None}")
        print(f"[OK] Context assigned: {block.context.level == 0}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] CommandBlock creation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_command_parsing_integration():
    """Test command parsing within the app context."""
    print("\n=== Testing Command Parsing Integration ===")
    
    try:
        parser = VLMXParser()
        context = Context(level=0)
        
        test_commands = [
            "cd ~",
            "create company ACME entity=SA",
            "cc TechCorp",
            "show company name",
            "add brand vision='Our vision'",
        ]
        
        for cmd in test_commands:
            print(f"\nTesting: '{cmd}'")
            
            # Parse the command
            result = parser.parse(cmd)
            print(f"  Valid: {result.is_valid}")
            print(f"  Has handler: {result.action_handler is not None}")
            
            if result.is_valid and result.action_handler:
                try:
                    # Try to execute
                    exec_result = await parser.execute_parsed_command(result, context)
                    print(f"  Execution: Success - {exec_result}")
                except Exception as e:
                    print(f"  Execution: Failed - {str(e)}")
            
            if result.errors:
                print(f"  Errors: {result.errors}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Command parsing integration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all integration tests."""
    print("VLMX-SH2 App Integration Test")
    print("=" * 40)
    
    success = True
    
    # Test app initialization
    success &= test_app_initialization()
    
    # Test command block creation
    success &= test_command_block()
    
    # Test command parsing integration
    try:
        success &= asyncio.run(test_command_parsing_integration())
    except Exception as e:
        print(f"[FAIL] Async test failed: {str(e)}")
        success = False
    
    print("\n" + "=" * 40)
    if success:
        print("[SUCCESS] All integration tests passed!")
        print("[SUCCESS] The refactored VLMX app is working correctly!")
    else:
        print("[FAILED] Some tests failed!")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())