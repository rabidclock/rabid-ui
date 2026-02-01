import streamlit as st
import subprocess
import time
import os
import sqlite3
import pandas as pd

# REMOVED top-level import to prevent circular crash

SCRAPER_DB_PATH = "/opt/rabid-scrape/scrapes.db"

def get_scrapes(limit=50):
    """Fetches recent scrapes from the central database."""
    if not os.path.exists(SCRAPER_DB_PATH):
        return []
    try:
        # Open in Read-Only mode to be safe
        conn = sqlite3.connect(f"file:{SCRAPER_DB_PATH}?mode=ro", uri=True)
        query = "SELECT id, url, method, content, timestamp FROM scrapes ORDER BY timestamp DESC LIMIT ?"
        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database Error: {e}")
        return pd.DataFrame()

def get_ollama_models():
    """Parses 'ollama list' output to get installed models."""
    try:
        cmd = "ollama list"
        output = subprocess.check_output(cmd.split()).decode("utf-8").strip().split("\n")
        models = []
        # Skip header row
        for line in output[1:]:
            parts = line.split()
            if parts:
                models.append({"name": parts[0], "size": parts[2] + parts[3]})
        return models
    except Exception as e:
        return []

# --- MODAL: SYSTEM SHELL ---
@st.dialog("💻 Root Terminal", width="large")
def shell_modal():
    st.caption("⚠️ Connected to: " + os.uname().nodename)
    
    # Initialize Session State for Shell
    if "shell_history" not in st.session_state:
        st.session_state.shell_history = []
    if "cwd" not in st.session_state:
        st.session_state.cwd = os.getcwd()

    # Command Input
    # We use a callback to handle execution so we can clear the input box easily
    def execute_command():
        cmd_input = st.session_state.modal_shell_input
        if not cmd_input: return
        
        # Handle 'cd' manually
        if cmd_input.strip().startswith("cd "):
            parts = cmd_input.strip().split(maxsplit=1)
            if len(parts) > 1:
                target_dir = parts[1]
                if not target_dir.startswith("/"):
                    target_path = os.path.join(st.session_state.cwd, target_dir)
                else:
                    target_path = target_dir
                target_path = os.path.normpath(target_path)
                if os.path.isdir(target_path):
                    st.session_state.cwd = target_path
                    output = f"Changed directory to: {target_path}"
                else:
                    output = f"bash: cd: {target_dir}: No such file or directory"
            else:
                output = "cd: missing argument"
        else:
            # Run standard shell command
            try:
                result = subprocess.run(
                    cmd_input,
                    cwd=st.session_state.cwd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                output = result.stdout + result.stderr
            except subprocess.TimeoutExpired:
                output = "Error: Command timed out (10s limit)."
            except Exception as e:
                output = f"System Error: {e}"

        # Insert to history
        timestamp = time.strftime("%H:%M:%S")
        st.session_state.shell_history.insert(0, {
            "time": timestamp,
            "cmd": cmd_input, 
            "out": output,
            "cwd": st.session_state.cwd
        })
        
        # Clear the input box for the next command
        st.session_state.modal_shell_input = ""

    st.text_input(
        "Execute:", 
        key="modal_shell_input", 
        placeholder="ls -la /opt/rabid-ui", 
        on_change=execute_command
    )

    st.divider() 
    
    # History Container
    with st.container(height=500, border=True):
        st.markdown(f"**Working Directory:** `{st.session_state.cwd}`")
        for entry in st.session_state.shell_history:
            st.markdown(f"**`$ {entry['cmd']}`** <span style='float:right; color:grey'>{entry['time']}</span>", unsafe_allow_html=True)
            if entry['out']:
                st.code(entry['out'], language="bash")
            st.divider()
            
    # CLOSE BUTTON (To properly unset the state)
    if st.button("Close Terminal", use_container_width=True):
        st.session_state.show_terminal = False
        st.rerun()

def render():
    """Renders the User Management dashboard for Administrators."""
    
    from app_utils import db 
    
    # Ensure our toggle state exists
    if "show_terminal" not in st.session_state:
        st.session_state.show_terminal = False
    
    st.sidebar.divider()
    with st.sidebar.expander("🛡️ Admin Console", expanded=False):
        
        tab_users, tab_models, tab_shell, tab_scraper = st.tabs(["👥 Users", "🧠 Fleet", "💻 Shell", "👁️ Scraper"])

        # --- TAB 1: USER MANAGEMENT ---
        with tab_users:
            st.caption("Pending Approval")
            try: awaiting = db.get_users_by_role("awaiting")
            except AttributeError: awaiting = []
            
            if not awaiting: st.info("No pending users.")
            
            for user in awaiting:
                col1, col2, col3 = st.columns([0.4, 0.3, 0.3])
                col1.text(user)
                if col2.button("✅", key=f"app_{user}"):
                    db.update_user_role(user, "user")
                    st.rerun()
                if col3.button("🚫", key=f"blk_{user}"):
                    db.update_user_role(user, "blocked")
                    st.rerun()

            st.divider()
            st.caption("Active Users")
            try: active = db.get_users_by_role("user")
            except: active = []
            for user in active:
                if user in ["ben", "guest", "rabidclock", "admin"]: continue
                c1, c2 = st.columns([0.7, 0.3])
                c1.text(user)
                if c2.button("🚫", key=f"ban_{user}"):
                    db.update_user_role(user, "blocked")
                    st.rerun()

            st.caption("Blacklisted")
            try: blocked = db.get_users_by_role("blocked")
            except: blocked = []
            for user in blocked:
                c1, c2 = st.columns([0.7, 0.3])
                c1.text(user)
                if c2.button("♻️", key=f"unban_{user}"):
                    db.update_user_role(user, "awaiting")
                    st.rerun()

        # --- TAB 2: FLEET ---
        with tab_models:
            st.caption("Manage Local Models")
            
            with st.popover("⬇️ Pull New Model", use_container_width=True):
                new_model = st.text_input("Model Tag (e.g. llama3:8b)")
                if st.button("Start Pull", use_container_width=True):
                    if new_model:
                        status_box = st.empty()
                        try:
                            process = subprocess.Popen(
                                ["ollama", "pull", new_model],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
                            )
                            for line in iter(process.stdout.readline, ''):
                                status_box.code(line.strip())
                            process.wait()
                            if process.returncode == 0:
                                st.success(f"Pulled {new_model}!")
                                time.sleep(1)
                                st.rerun()
                            else: st.error("Failed.")
                        except Exception as e: st.error(f"Error: {e}")

            st.divider()
            models = get_ollama_models()
            for m in models:
                with st.container(border=True):
                    c1, c2 = st.columns([0.7, 0.3])
                    c1.markdown(f"**{m['name']}**")
                    c1.caption(f"Size: {m['size']}")
                    if c2.button("🗑️", key=f"del_{m['name']}"):
                        try:
                            subprocess.run(["ollama", "rm", m['name']], check=True)
                            st.toast(f"Deleted {m['name']}")
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")

        # --- TAB 3: SHELL (Trigger) ---
        with tab_shell:
            st.info("Launch the interactive terminal.")
            # Button just toggles the state
            if st.button("🖥️ Launch Terminal", use_container_width=True):
                st.session_state.show_terminal = True
                st.rerun()

        # --- TAB 4: SCRAPER INSPECTOR ---
        with tab_scraper:
            st.caption("Inspect collected intelligence")
            
            if st.button("🔄 Refresh DB", use_container_width=True):
                st.rerun()
                
            df = get_scrapes()
            
            if not df.empty:
                for idx, row in df.iterrows():
                    method = row['method']
                    color = "blue"
                    if method == "METHOD_NETWORK": color = "green"
                    if method == "METHOD_VISION": color = "red"
                    
                    with st.expander(f":{color}[{method}] {row['url']}", expanded=False):
                        st.caption(f"Captured: {row['timestamp']}")
                        st.code(row['content'], language="text")
            else:
                st.info("No scrapes found in database.")

    # --- RENDER MODAL IF STATE IS TRUE ---
    # This check happens on every run, keeping the window open
    if st.session_state.show_terminal:
        shell_modal()
