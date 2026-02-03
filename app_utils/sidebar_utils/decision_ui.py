import streamlit as st
from app_utils import workspaces

def render(ws_config, available_models, is_locked, selected_ws_name):
    """Renders the Decision System section with Multi-Tenant Awareness."""
    st.sidebar.divider()
    st.sidebar.subheader("Decision System")
    
    # Grab the unique user_key from the GitHub session
    user_key = st.session_state.get("github_id", st.session_state.username)
    
    # 1. Consensus Mode Logic
    current_mode = ws_config.get("consensus_mode", "None")
    mode_options = ["None", "Arbiter", "Ranked Choice", "Judge & Jury", "The Retirement Lounge (Honorary)"]
    
    # Robust index mapping including legacy support
    idx = 0
    if current_mode in mode_options: 
        idx = mode_options.index(current_mode)
    elif current_mode == "Judge Only": idx = 1
    elif current_mode == "Ranked Choice Only": idx = 2 
    elif current_mode == "Both": idx = 3 
    elif current_mode == "Fight to the Death": idx = 4
        
    selected_mode = st.sidebar.selectbox("Consensus Mode", mode_options, index=idx, disabled=is_locked)
    
    # FIXED: Pass user_key as the first argument
    if not is_locked and selected_mode != current_mode:
        workspaces.update(user_key, selected_ws_name, consensus_mode=selected_mode)

    # 2. Judge Selection Logic
    current_judge = ws_config.get("judge_model", None)
    judge_options = ["Disabled"] + available_models
    
    judge_idx = 0
    if current_judge in available_models:
        judge_idx = judge_options.index(current_judge)
        
    # UI Logic for enabling/disabling the judge dropdown
    judge_disabled = is_locked or (selected_mode in ["None", "Ranked Choice"])
    
    label = "Judge Model"
    if selected_mode == "The Retirement Lounge (Honorary)": 
        label = "Curator (for Ties/Archive)"

    selected_judge = st.sidebar.selectbox(label, judge_options, index=judge_idx, disabled=judge_disabled)
    
    final_judge_val = None if selected_judge == "Disabled" else selected_judge
    
    # FIXED: Pass user_key as the first argument
    if not is_locked and final_judge_val != current_judge:
        workspaces.update(user_key, selected_ws_name, judge_model=final_judge_val)
        
    return selected_mode, final_judge_val