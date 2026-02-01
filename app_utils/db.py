import sqlite3
import os

# Use the established deployment path for consistency
DB_FILE = "/opt/rabid-ui/rabidui.db"

def init_db():
    """Initializes messages, workspaces, and the new RBAC users table."""
    # Ensure directory exists for deployment
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    
    with sqlite3.connect(DB_FILE) as conn:
        # 1. Messages Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                sender TEXT,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 2. Workspaces Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workspaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_key TEXT,
                workspace_name TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 3. NEW: RBAC Users Table
        # This is the 'Gatekeeper' for the Awaiting/Blocked system
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                role TEXT DEFAULT 'awaiting'
            )
        """)
        conn.commit()

# --- RBAC / USER MANAGEMENT ---

def get_user_role(username):
    """Retrieves user role or auto-registers them as 'awaiting'."""
    init_db()
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.execute("SELECT role FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        
        if not result:
            # First-time GitHub/PAM login: enter the waiting room
            register_new_user(username)
            return 'awaiting'
        return result[0]

def register_new_user(username, role='awaiting'):
    """Inserts a new user record."""
    init_db()
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (username, role) VALUES (?, ?)", 
            (username, role)
        )
        conn.commit()

def update_user_role(username, new_role):
    """Admin tool to Approve, Block, or Promote users."""
    init_db()
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, username))
        conn.commit()

def get_users_by_role(role):
    """Fetches list of usernames for specific role status."""
    init_db()
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.execute("SELECT username FROM users WHERE role = ?", (role,))
        return [row[0] for row in cursor.fetchall()]

# --- WORKSPACE MANAGEMENT ---

def get_user_workspaces(user_key):
    """Fetches workspaces belonging to a specific user."""
    init_db()
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.execute(
            "SELECT workspace_name FROM workspaces WHERE user_key = ?", (user_key,)
        )
        return [row[0] for row in cursor.fetchall()]

def create_workspace(user_key, workspace_name):
    """Initializes a new personal workspace."""
    init_db()
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO workspaces (user_key, workspace_name) VALUES (?, ?)",
            (user_key, workspace_name)
        )
        conn.commit()

# --- MESSAGE LOGIC ---

def load_history(session_id):
    """Loads chat history for a session."""
    init_db()
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC", 
            (session_id,)
        )
        return [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]

def save_message(session_id, sender, role, content):
    """Saves a single message."""
    init_db()
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO messages (session_id, sender, role, content) VALUES (?, ?, ?, ?)",
            (session_id, sender, role, content)
        )
        conn.commit()

def clear_history(session_id):
    """Deletes all messages for a session."""
    init_db()
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.commit()