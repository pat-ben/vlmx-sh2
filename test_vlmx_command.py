#!/usr/bin/env python3
"""
Test that the vlmx command works properly.
"""

import subprocess
import sys
import time

def test_vlmx_command():
    """Test that uv run vlmx starts without errors."""
    print("Testing: uv run vlmx")
    print("This will start the app and then kill it after 3 seconds...")
    
    try:
        # Start the vlmx command
        process = subprocess.Popen(
            ["uv", "run", "vlmx"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd="D:/Code/vlmx-sh2"
        )
        
        # Let it run for 3 seconds
        try:
            stdout, stderr = process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            # This is expected - kill the process
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
        
        # Check if the process started successfully
        if process.returncode is None or process.returncode == 0 or process.returncode == -15:  # -15 is SIGTERM
            print("[SUCCESS] vlmx command started successfully!")
            print("[SUCCESS] The Textual UI application is working!")
            return True
        else:
            print(f"[FAIL] vlmx command failed with return code: {process.returncode}")
            if stderr:
                print(f"Error output: {stderr}")
            return False
        
    except FileNotFoundError:
        print("[FAIL] uv command not found")
        return False
    except Exception as e:
        print(f"[FAIL] Unexpected error: {str(e)}")
        return False

def main():
    """Run the vlmx command test."""
    print("VLMX Command Test")
    print("=" * 30)
    
    success = test_vlmx_command()
    
    print("\n" + "=" * 30)
    if success:
        print("[SUCCESS] The vlmx command is working correctly!")
        print("You can now run: uv run vlmx")
    else:
        print("[FAILED] The vlmx command has issues!")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())