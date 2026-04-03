"""Test script to verify imports work correctly."""
import sys
import os

# Add src directory to Python path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if src_dir not in sys.path:
  sys.path.insert(0, src_dir)

print("Testing imports...")
print(f"Python path includes src: {src_dir in sys.path}")
print(f"Src directory: {src_dir}")

try:
  print("\n1. Testing data.config import...")
  from data.config import SETTINGS

  print("   ✓ SETTINGS imported successfully")
  print(f"   MongoDB database: {SETTINGS['MONGO_DB']}")

  print("\n2. Testing api.models import...")
  from api.models import HealthResponse

  print("   ✓ API models imported successfully")

  print("\n3. Testing api.queries import...")
  from api.queries import get_symbols

  print("   ✓ API queries imported successfully")

  print("\n4. Testing api.app import...")
  from api.app import app

  print("   ✓ FastAPI app imported successfully")
  print(f"   App title: {app.title}")

  print("\nAll imports successful! The API should work correctly.")
  print("\nYou can now run:")
  print("  python run_api.py")

except ImportError as e:
  print(f"\nImport error: {e}")
  print("\nTroubleshooting:")
  print("1. Make sure you're running this from the project root directory")
  print("2. Check that all required files exist in src/")
  print("3. Verify your Python environment has all dependencies installed")
  sys.exit(1)
except Exception as e:
  print(f"\nUnexpected error: {e}")
  sys.exit(1)
