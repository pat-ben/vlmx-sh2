import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vlmx_sh2.dsl.parser import VLMXParser
from vlmx_sh2.models.context import Context

async def test():
    parser = VLMXParser()
    result = parser.parse('show brand')
    ctx = Context(level=1, org_id=1, org_name='TestCompany')
    
    print(f"Parse result: {result.is_valid}")
    
    try:
        exec_result = await parser.execute_parsed_command(result, ctx)
        print(f"Execution result type: {type(exec_result)}")
        print(f"Execution result success: {getattr(exec_result, 'success', 'N/A')}")
        print(f"Execution result message: {repr(getattr(exec_result, 'message', 'N/A'))}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())