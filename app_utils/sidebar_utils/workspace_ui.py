import streamlit as st
from app_utils import workspaces 

def render(user_key):
    """Renders Workspace UI with a dynamic key-shift to force UI re-anchoring."""
    
    # 1. INITIALIZE PERSISTENT STATE
    if "selected_workspace" not in st.session_state: 
        st.session_state.selected_workspace = "Default"
    if "ws_version" not in st.session_state:
        st.session_state.ws_version = 0

    # 2. LOAD DATA
    all_workspaces = workspaces.load(user_key)
    workspace_names = list(all_workspaces.keys())
    if "Default" in workspace_names:
        workspace_names.remove("Default")
        workspace_names.insert(0, "Default")

    # 3. SELECTOR WIDGET (Dynamic Key ensures the UI jumps)
    try:
        current_index = workspace_names.index(st.session_state.selected_workspace)
    except ValueError:
        current_index = 0

    # The key changes whenever we increment ws_version, forcing a fresh render
    selected_ws_name = st.sidebar.selectbox(
        "Workspace", 
        workspace_names, 
        index=current_index,
        key=f"ws_selector_v{st.session_state.ws_version}" 
    )
    
    # Sync manual changes
    if selected_ws_name != st.session_state.selected_workspace:
        st.session_state.selected_workspace = selected_ws_name
        st.rerun()

    # 4. MANAGEMENT UI
    with st.sidebar.expander("➕ Manage Workspaces", expanded=False):
        st.caption(f"Profile: {st.session_state.username}")
        new_ws_input = st.text_input("New Name", placeholder="test", key="new_ws_field")
        
        if st.button("Create & Switch", use_container_width=True):
            if new_ws_input and new_ws_input not in workspace_names:
                # Create with required arguments from your crash log
                workspaces.create(
                    user_key=user_key, 
                    name=new_ws_input, 
                    models=[], 
                    prompt="You are a helpful assistant.",
                    search=True, 
                    code=True
                )
                
                # THE PIVOT: Change state AND increment version to kill widget memory
                st.session_state.selected_workspace = new_ws_input
                st.session_state.ws_version += 1 
                st.rerun()

        if selected_ws_name != "Default":
            st.divider()
            if st.button(f"🗑️ Delete '{selected_ws_name}'", type="primary", use_container_width=True):
                workspaces.delete(user_key=user_key, name=selected_ws_name)
                # Revert and Shift Key
                st.session_state.selected_workspace = "Default"
                st.session_state.ws_version += 1
                st.rerun()

    return all_workspaces.get(selected_ws_name, all_workspaces["Default"]), selected_ws_name