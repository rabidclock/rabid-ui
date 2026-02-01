import os
import sys
import importlib.util

# 1. DYNAMIC PATH RESOLUTION
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Note the nested path revealed by your 'ls -R' command
LOADERS_PATH = os.path.join(BASE_DIR, "app_utils", "sidebar_utils", "loaders.py")
WORKSPACES_PATH = os.path.join(BASE_DIR, "app_utils", "workspaces.py")

print(f"☢️ RabidUI: Starting Path-Corrected Diagnostic...")
print(f"🔍 Loading Loaders from: {LOADERS_PATH}")

def check_step(name, success, details=""):
    symbol = "✅" if success else "❌"
    print(f"{symbol} {name}: {details}")

def manual_load(module_name, file_path):
    """Bypasses package locks to load a clean version from disk."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Missing: {file_path}")
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# 2. VERIFY MODULES
try:
    loaders = manual_load("loaders", LOADERS_PATH)
    workspaces = manual_load("workspaces", WORKSPACES_PATH)
    check_step("Import Integrity", True, "Files found in sidebar_utils and loaded.")
except Exception as e:
    check_step("Import Integrity", False, f"Error: {str(e)}")
    sys.exit(1)

# 3. VERIFY INJECTED IDENTITY
try:
    # Bridged to your RTX 3090 name pool
    mock_pool = loaders.load_names()
    test_id = workspaces.generate_identity(
        model_name="llama3", 
        name_pool=mock_pool, 
        existing_names=[]
    )
    check_step("Identity Injection", True, f"Deity Assigned: '{test_id['name']}'")
except Exception as e:
    check_step("Identity Injection", False, f"Logic Error: {str(e)}")

print("\n🏁 Diagnostic Complete.")