import json
import os
import random
import hashlib

# --- MULTI-TENANT PATHING ---
# Resolves to /opt/rabid-ui/user_data/workspaces on your Ubuntu host
WORKSPACE_DIR = os.path.join(os.path.dirname(__file__), "..", "user_data", "workspaces")
os.makedirs(WORKSPACE_DIR, exist_ok=True)

DEFAULT_CONFIG = {
    "Default": {
        "prompt": "You are a helpful assistant.",
        "models": [], 
        "judge_model": None,
        "consensus_mode": "None",
        "tools": {"search": True, "code": True},
        "locked": True
    }
}

# --- IDENTITY LOGIC (Dependency Injection) ---
def generate_identity(model_name, name_pool, existing_names=None):
    """
    Assigns a name from the provided pool, physically breaking the import loop.
    This function no longer imports 'loaders.py' directly.
    """
    if existing_names is None:
        existing_names = []
        
    try:
        # Filter out names already active on your 3090
        available_names = [n for n in name_pool if n not in existing_names]
        
        if available_names:
            name = random.choice(available_names)
        else:
            name = f"Agent_{random.randint(100, 999)}"
            
    except Exception:
        # Fallback if the name pool is malformed or empty
        name = f"Agent_{random.randint(100, 999)}"
        
    return {
        "model": model_name,
        "name": name,
        "seed": random.randint(1, 1000000)
    }

# --- MULTI-TENANT CORE ---

def get_path(user_key):
    """Returns the unique file path for a user's GitHub ID."""
    return os.path.join(WORKSPACE_DIR, f"{user_key}.json")

def load(user_key):
    """Loads private workspaces for a specific user."""
    path = get_path(user_key)
    if not os.path.exists(path):
        save(user_key, DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    
    try:
        with open(path, "r") as f:
            data = json.load(f)
            # Integrity check to prevent 'models' key errors in the UI
            for k, v in data.items():
                if "models" not in v: 
                    v["models"] = []
            return data
    except Exception:
        return DEFAULT_CONFIG

def save(user_key, data):
    """Saves a user's workspace file to the persistent volume."""
    path = get_path(user_key)
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def create(user_key, name, models, prompt, search, code, judge_model=None, consensus_mode="None"):
    """Creates a workspace within a user's private JSON file."""
    data = load(user_key)
    if name and name not in data:
        data[name] = {
            "prompt": prompt, "models": models, "judge_model": judge_model,
            "consensus_mode": consensus_mode, "tools": {"search": search, "code": code},
            "locked": False
        }
        save(user_key, data)
        return True
    return False

def update(user_key, name, **kwargs):
    """Updates a specific workspace for a specific user."""
    data = load(user_key)
    if name in data:
        # Do not allow editing prompt on locked 'Default' profile
        if data[name].get("locked", False) and 'prompt' in kwargs: 
            return False 
        
        for key, value in kwargs.items():
            if key in ["models", "prompt", "judge_model", "consensus_mode"]:
                data[name][key] = value
            if key in ["search", "code"]:
                if "tools" not in data[name]: 
                    data[name]["tools"] = {}
                data[name]["tools"][key] = value
        
        save(user_key, data)
        return True
    return False

def delete(user_key, name):
    """Deletes a workspace from the user's private file."""
    data = load(user_key)
    if name in data and not data[name].get("locked", False):
        del data[name]
        save(user_key, data)
        return True
    return False