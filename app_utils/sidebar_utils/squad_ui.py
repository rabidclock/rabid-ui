import streamlit as st
from app_utils import workspaces

def render(available_models, current_chain, is_locked, selected_ws_name, name_pool):
    """Renders the Agent Squad using native Streamlit columns for perfect alignment."""
    st.sidebar.divider()
    st.sidebar.subheader("Agent Squad")
    user_key = st.session_state.get("github_id", st.session_state.username)

    # --- 1. SQUAD LIMITS & ADDING ---
    total_count = len(current_chain)
    limit_reached = total_count >= 9
    
    if available_models and not is_locked:
        # Replicated geometry: Selectbox + Plus Button
        c1, c2 = st.sidebar.columns([0.8, 0.2], vertical_alignment="bottom")
        with c1:
            new_model = st.selectbox("Add Model", available_models, key="squad_add_sel", disabled=limit_reached)
        with c2:
            if st.button("➕", key="squad_add_btn", disabled=limit_reached, use_container_width=True):
                new_agent = workspaces.generate_identity(new_model, name_pool, [m['name'] for m in current_chain])
                current_chain.append(new_agent)
                workspaces.update(user_key, selected_ws_name, models=current_chain)
                st.rerun()

    # --- 2. THE UNIFIED AGENT LIST ---
    if current_chain:
        st.sidebar.caption(f"Active Agents ({total_count}/9):")
        for i, agent in enumerate(current_chain):
            # Using the exact same 8:2 ratio and centering vertically
            col_info, col_action = st.sidebar.columns([0.8, 0.2], vertical_alignment="center")
            
            with col_info:
                # Clean, native formatting for name and model tag
                st.markdown(f"**{i+1}. {agent['name']}**")
                st.caption(f"({agent['model']})")
                
            with col_action:
                # Native button with minus sign for removal
                unique_key = f"remove_btn_{i}_{agent['name']}"
                if not is_locked and st.button("➖", key=unique_key, use_container_width=True):
                    updated_chain = list(current_chain)
                    updated_chain.pop(i)
                    workspaces.update(user_key, selected_ws_name, models=updated_chain)
                    st.rerun()