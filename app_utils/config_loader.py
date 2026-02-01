import yaml
import os

POLICY_PATH = "/opt/rabid-ui/config/model_policy.yaml"

def load_model_policy():
    """Loads the filtering rules from the YAML config."""
    if not os.path.exists(POLICY_PATH):
        return {"forbidden_patterns": [], "roles": {"user": []}}
    
    with open(POLICY_PATH, 'r') as f:
        return yaml.safe_load(f)

def filter_models(raw_list, role="user"):
    """Applies the YAML rules to a raw list of Ollama models."""
    policy = load_model_policy()
    forbidden = policy.get("forbidden_patterns", [])
    role_whitelist = policy.get("roles", {}).get(role, [])

    # 1. Remove forbidden patterns globally
    clean_list = [
        m for m in raw_list 
        if not any(pattern in m.lower() for pattern in forbidden)
    ]

    # 2. Apply role-based whitelist (Admins bypass if whitelist is '*')
    if "*" in role_whitelist:
        return clean_list
    
    return [m for m in clean_list if m in role_whitelist]
