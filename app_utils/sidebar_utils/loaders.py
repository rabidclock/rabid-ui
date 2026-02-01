import os
import json
import streamlit as st
from ollama import Client

# --- OLLAMA DOCKER BRIDGE ---
# Use the internal Docker bridge to access the host's Ollama service and 3090 VRAM
OLLAMA_HOST = "http://host.docker.internal:11434"
client = Client(host=OLLAMA_HOST)

# --- FILE PATHS (Container Optimized) ---
# Point directly to the mythological name pool discovered in your sidebar_utils directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NAMES_FILE = os.path.join(BASE_DIR, "names.json")
FALLBACK_NAMES = ["Agent_001", "Agent_002", "Agent_003"]

def load_names():
    """Loads mythological names from the 200-entry pool in names.json."""
    if not os.path.exists(NAMES_FILE): 
        return FALLBACK_NAMES
        
    try:
        with open(NAMES_FILE, "r") as f:
            data = json.load(f)
            
            # 1. Flatten logic for Categorized Dictionaries (Norse, Greek, etc.)
            if isinstance(data, dict):
                flat_list = []
                for category_list in data.values():
                    if isinstance(category_list, list):
                        flat_list.extend(category_list)
                return flat_list if flat_list else FALLBACK_NAMES
            
            # 2. Return direct flat lists
            if isinstance(data, list) and len(data) > 0: 
                return data
                
            return FALLBACK_NAMES
    except (json.JSONDecodeError, IOError, Exception): 
        return FALLBACK_NAMES

def get_installed_models():
    """Fetches local open-weight models from the host bridge using the 3090."""
    try:
        # Communicate with the host machine via the Docker bridge
        response = client.list()
        
        # Handle both object-attribute and dictionary-key response formats
        model_list = response.models if hasattr(response, 'models') else response.get('models', [])
        
        available = []
        for m in model_list:
            if hasattr(m, 'model'): 
                available.append(m.model)
            elif isinstance(m, dict):
                # Fallback check for different Ollama API version signatures
                name = m.get('model') or m.get('name')
                if name:
                    available.append(name)
        
        return sorted(available)
    except Exception as e:
        # Display the bridge status in the UI if the host is unreachable
        st.sidebar.error(f"Ollama Connection Error ({OLLAMA_HOST}): {e}")
        return []