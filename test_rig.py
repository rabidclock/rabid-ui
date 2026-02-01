import sys
import os

# Point to the current directory for native module resolution
sys.path.append(os.getcwd()) 
from app_utils import auth, bridge

def test_pam_access():
    """Verifies the host user can authenticate against common-auth."""
    print("🔍 Testing Native PAM Stack...")
    
    # Prompting for password so you don't have to hardcode it in a file
    import getpass
    test_user = "ben" 
    test_pw = getpass.getpass(f"Enter password for {test_user}: ")
    
    result = auth.login(test_user, test_pw)
    if result:
        print("✅ RESULT: PAM Path Clear")
    else:
        print("❌ RESULT: PAM Access Denied")
        print("   TIP: Check if your user is in the 'shadow' group: sudo usermod -aG shadow ben")

def test_3090_bridge():
    """Verifies Ollama is reachable on localhost."""
    print("🔍 Testing RTX 3090 Bridge (Local)...")
    try:
        client = bridge.get_client()
        models = client.list()
        print(f"✅ RESULT: Bridge Active. Found {len(models['models'])} models.")
    except Exception as e:
        print(f"❌ RESULT: Bridge Broken: {e}")

if __name__ == "__main__":
    test_pam_access()
    print("-" * 30)
    test_3090_bridge()