import os
import pam
import httpx
import streamlit as st
from subprocess import check_output

# --- CONFIGURATION (Loaded via systemd/EnvironmentFile) ---
CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")
# Prioritize the .env value, fallback to localhost
REDIRECT_URI = os.environ.get("REDIRECT_URI", "http://localhost:8501")

# 1. LOCAL SYSTEM AUTH (PAM)
def login(username, password):
    """Authenticates against local Linux users."""
    p = pam.pam()
    return p.authenticate(username, password)

def get_system_users():
    """Reads system users from the host."""
    try:
        users = check_output(["cut", "-d:", "-f1", "/etc/passwd"]).decode().split("\n")
        return [u for u in users if u]
    except Exception:
        return []

# 2. GITHUB OAUTH LOGIC
def get_github_login_url():
    """Generates the redirect URL for GitHub OAuth."""
    if not CLIENT_ID:
        return None
    return f"https://github.com/login/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=read:user"

def authenticate_github(code):
    """Exchanges GitHub code for user profile data with robust error checking."""
    headers = {
        "Accept": "application/json",
        "User-Agent": "RabidUI-Production-Server" 
    }

    with httpx.Client(timeout=10.0) as client:
        # STEP A: Exchange code for Access Token
        token_res = client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "redirect_uri": REDIRECT_URI
            },
            headers=headers
        )
        
        # Guard against non-JSON responses from misconfigured DDNS/Gateways
        if "application/json" not in token_res.headers.get("Content-Type", "").lower():
            raise ConnectionError(f"GitHub returned non-JSON. Status: {token_res.status_code}")

        token_data = token_res.json()
        token = token_data.get("access_token")
        
        if not token:
            error_desc = token_data.get("error_description", "Invalid Code or Secret")
            raise ConnectionError(f"GitHub Auth Error: {error_desc}")

        # STEP B: Fetch Profile Data using the token
        user_res = client.get(
            "https://api.github.com/user", 
            headers={"Authorization": f"token {token}", "User-Agent": "RabidUI"}
        )
        return user_res.json()