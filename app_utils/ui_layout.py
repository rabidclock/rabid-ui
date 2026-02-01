import streamlit as st
from app_utils import auth

def apply_custom_css():
    """Restores the original stable CSS for the UI."""
    st.markdown("""
        <style>
        .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
        .auth-container { border: 1px solid #444; padding: 20px; border-radius: 10px; }
        </style>
    """, unsafe_allow_html=True)

def render_login():
    """Original dual-path login screen logic."""
    if "username" in st.session_state:
        return

    st.title("RabidUI: Access Protocol")
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("System Login")
        with st.container(border=True):
            user = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            if st.button("Authorize (PAM)"):
                # Authenticates against the /etc/shadow mount
                if auth.login(user, pw):
                    st.session_state.username = user
                    st.session_state.auth_method = "pam"
                    st.rerun()
                else:
                    st.error("Invalid credentials.")

    with col2:
        st.subheader("Developer Login")
        with st.container(border=True):
            st.write("Use your GitHub account.")
            # Standard link button (stable)
            st.link_button("🚀 Login with GitHub", auth.get_github_login_url())

    st.stop()