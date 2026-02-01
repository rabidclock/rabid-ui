# /opt/rabid-ui/app_utils/sidebar.py
import streamlit as st
from . import workspaces, db, bridge
from .sidebar_utils import squad_ui, decision_ui, workspace_ui 

SUPPORTED_LANGUAGES = [
    "English", "Spanish", "French", "German", 
    "Chinese (Simplified)", "Japanese", "Korean", 
    "Russian", "Portuguese", "Italian", "Hindi", "Arabic"
]

def render(name_pool):
    """Renders the configuration sidebar."""
    username = st.session_state.username
    user_key = st.session_state.get("github_id", username)
    st.sidebar.header(f"{username}'s Config")
    
    # 1. Workspace
    ws_config, selected_ws_name = workspace_ui.render(user_key=user_key)
    
    # 2. Ollama Status
    try:
        client = bridge.get_client()
        response = client.list()
        available_models = [m.model for m in response.models] if hasattr(response, 'models') else [m["model"] for m in response.get("models", [])]
    except Exception as e:
        st.sidebar.error(f"⚠️ Ollama Offline: {str(e)}")
        available_models = []

    # 3. Squad
    current_chain = ws_config.get("models", [])
    squad_ui.render(available_models, current_chain, ws_config.get("locked", False), selected_ws_name, name_pool=name_pool)
    
    selected_mode, final_judge_val = decision_ui.render(
        ws_config, available_models, ws_config.get("locked", False), selected_ws_name
    )

    # 4. Neural Cortex (Stacked Vertically)
    st.sidebar.divider()
    st.sidebar.caption("🧠 Neural Cortex")
    
    # STACKED: No columns used here to prevent text wrapping
    enable_reasoning = st.sidebar.toggle(
        "Reasoning Mode", 
        value=True, 
        help="Forces the model to output an internal monologue/plan before answering."
    )
    
    enable_search = st.sidebar.toggle(
        "Web Search", 
        value=True, 
        help="Grants the model access to real-time web data via SearXNG."
    )

    # 5. Settings
    st.sidebar.divider()
    current_lang = ws_config.get("language", "English")
    selected_lang = st.sidebar.selectbox("Output Language", SUPPORTED_LANGUAGES, 
                                        index=SUPPORTED_LANGUAGES.index(current_lang) if current_lang in SUPPORTED_LANGUAGES else 0)
    
    if selected_lang != current_lang:
        workspaces.update(user_key, selected_ws_name, language=selected_lang)

    with st.sidebar.expander("System Prompt"):
        prompt_val = ws_config.get("prompt", "You are a helpful assistant.")
        system_prompt = st.text_area("Persona", prompt_val, height=100)
        if system_prompt != prompt_val:
            workspaces.update(user_key, selected_ws_name, prompt=system_prompt)

    # 6. History
    st.sidebar.divider()
    if st.sidebar.button("Clear History", use_container_width=True):
        db.clear_history(f"{selected_ws_name}_{user_key}")
        st.session_state.messages = []
        st.rerun()

    return {
        "workspace_name": selected_ws_name,
        "models": current_chain,
        "consensus_mode": selected_mode,
        "judge_model": final_judge_val,
        "system_prompt": system_prompt,
        "language": selected_lang,
        "reasoning_mode": enable_reasoning,
        "web_search": enable_search
    }