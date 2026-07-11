import subprocess
import signal
import os

# Find and kill uvicorn processes
result = subprocess.run(['pkill', '-f', 'uvicorn'], capture_output=True, text=True)
print(f"pkill result: {result.returncode}")
if result.stdout:
    print(f"stdout: {result.stdout}")
if result.stderr:
    print(f"stderr: {result.stderr}")
