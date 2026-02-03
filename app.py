import os
from dotenv import load_dotenv; load_dotenv() # Load .env immediately
import re  # ADDED: For parsing reasoning blocks
# REMOVED: import pam
import httpx
import tomllib
import subprocess
import random
import time
import streamlit as st
from datetime import datetime

# --- CORE IMPORTS ---
from app_utils import (
    db, sidebar, ui_layout, bridge, 
    extraction, consensus, auth, battle_royale, arena, web_search, memory
)

from app_utils.sidebar_utils import loaders
import app_utils.admin_ui as admin_ui

# --- CONFIGURATION ---
REDIRECT_URI = os.environ.get("REDIRECT_URI", "http://localhost:8501")

# --- START UI ---
st.set_page_config(page_title="RabidUI", page_icon="☢️", layout="wide")
ui_layout.apply_custom_css()

# --- CSS: LAYOUT HARDENING & UI CLEANUP ---
st.markdown("""
<style>
    /* 1. Global Hides */
    .stStatusWidget { display: none !important; }
    .stDeployButton { display: none !important; }
    
    /* 2. THE "SAFETY FLOOR" 
       Prevents the sidebar from being dragged to 0 width and vanishing 
    */
    [data-testid="stSidebar"] {
        min-width: 200px !important;
    }

    /* 3. HEADER STABILITY
       We keep the header interactive so the hamburger menu works,
       but we hide the visual bar for a cleaner look.
    */
    header {
        visibility: visible !important;
        background: transparent !important;
    }i
    header .stAppHeader {
        background: transparent !important;
        box-shadow: none !important;
    }

    /* 4. SPACING */
    .block-container { padding-top: 1.5rem !important; }
</style>
""", unsafe_allow_html=True)

# --- ART INJECTION ---
try:
    with open(os.path.join("app_utils", "art.toml"), "rb") as f:
        art_pack = tomllib.load(f)
    selected_art = art_pack.get("radioactive", "")
    st.markdown(f"""
    <div style='position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                opacity: 0.08; 
                font-family: source-code-pro, Menlo, Monaco, Consolas, "Courier New", monospace; 
                font-weight: bold;
                pointer-events: none; z-index: 0; white-space: pre; text-align: center;
                color: #ffffff; font-size: 24px; line-height: 24px;'>
    {selected_art}
    </div>
    """, unsafe_allow_html=True)
except Exception: pass

# --- AUTH & SETUP ---
try:
    db.execute_query("ALTER TABLE messages ADD COLUMN sender TEXT;")
except: pass

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# 1. Handle OAuth Callback
if "code" in st.query_params and not st.session_state.authenticated:
    try:
        os.environ["REDIRECT_URI"] = REDIRECT_URI
        user_data = auth.authenticate_github(st.query_params["code"])
        st.session_state.username = user_data["login"]
        st.session_state.authenticated = True
        st.rerun()
    except Exception as e: st.error(f"GitHub Auth Error: {e}")

# 2. Render Login Screen
if not st.session_state.authenticated:
    st.title("🌐 RabidLLM Login")
    os.environ["REDIRECT_URI"] = REDIRECT_URI
    login_url = auth.get_github_login_url()
    if login_url:
        st.markdown(f'''
            <div style="display: flex; justify-content: center; margin-top: 50px;">
                <a href="{login_url}" target="_self" style="text-decoration:none; width: 50%;">
                    <button style="width: 100%; padding: 1rem; font-size: 1.2rem; border-radius: 8px; cursor: pointer;">
                        Login with GitHub
                    </button>
                </a>
            </div>
        ''', unsafe_allow_html=True)
    st.stop()

# --- INIT SIDEBAR & CONFIG ---
if "name_pool" not in st.session_state:
    st.session_state.name_pool = loaders.load_names()

client = bridge.get_client()
user_key = st.session_state.username

# Render Sidebar (returns config dict)
config = sidebar.render(name_pool=st.session_state.name_pool)

# --- EMERGENCY LAYOUT RESET ---
# This wipes browser local storage to fix a "vanished" sidebar
with st.sidebar:
    st.divider()
    if st.button("♻️ Reset Layout & Cache", use_container_width=True, help="Force reset sidebar width if it vanishes."):
        st.markdown('<script>localStorage.clear(); location.reload();</script>', unsafe_allow_html=True)

# Admin Check
try:
    if db.get_user_role(user_key) == "admin":
        admin_ui.render()
except Exception: pass

# --- GPU HUD FRAGMENT ---
@st.fragment(run_every=1)
def render_gpu_status():
    st.divider()
    try:
        cmd = "nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits"
        output = subprocess.check_output(cmd.split()).decode("utf-8").strip().split("\n")
        st.markdown("### 🖥️ System Hardware")
        for i, line in enumerate(output):
            parts = [x.strip() for x in line.split(',')]
            if len(parts) == 5:
                name, temp, load, mem_used, mem_total = parts
                with st.container(border=True):
                    st.markdown(f"**GPU {i}: {name.replace('NVIDIA ', '')}**")
                    c1, c2 = st.columns(2)
                    c1.metric("Temp", f"{temp}°C")
                    c2.metric("Load", f"{load}%")
                    st.progress(int(mem_used)/int(mem_total), text=f"VRAM: {mem_used}/{mem_total}MB")
    except Exception: pass

with st.sidebar:
    render_gpu_status()

# --- MAIN APP LOGIC ---
current_ws = config["workspace_name"]
st.title(f"RabidUI: {current_ws}")

session_namespace = f"{current_ws}_{user_key}"
if "messages" not in st.session_state or st.session_state.get("last_session") != session_namespace:
    st.session_state.messages = db.load_history(session_namespace)
    st.session_state.last_session = session_namespace

# Render messages with <think> tag support
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): 
        content = msg["content"]
        if "<think>" in content:
            match = re.search(r"<think>(.*?)</think>", content, re.DOTALL)
            if match:
                reasoning = match.group(1).strip()
                final_response = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
                with st.expander("💭 Reasoning Process", expanded=False):
                    st.markdown(reasoning)
                st.markdown(final_response, unsafe_allow_html=True)
            else: st.markdown(content, unsafe_allow_html=True)
        else: st.markdown(content, unsafe_allow_html=True)

# --- INPUT AREA ---
with st.popover("📎 Attach Files", use_container_width=False):
    uploaded_files = st.file_uploader(
        "Upload context (PDF, TXT, MD, Images)", 
        accept_multiple_files=True,
        type=['txt', 'pdf', 'md', 'png', 'jpg', 'jpeg']
    )

if prompt := st.chat_input("Input command..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    db.save_message(session_namespace, user_key, "user", prompt)
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        status = st.status("☢️ Initializing Agents...", expanded=True)
        file_context, _ = extraction.process_uploads(uploaded_files or [], user_key=user_key)
        response_data = []
        history_block = memory.get_short_term_memory(st.session_state.messages)

        web_context = ""
        if config.get("web_search", True):
            try:
                # Use the first model in the config as the reasoning engine for search
                search_model = "gemma3:27b"
                if config.get("models"):
                    m = config["models"][0]
                    search_model = m.get('model') if isinstance(m, dict) else m

                web_context = web_search.search(
                    prompt, 
                    client=client, 
                    history=st.session_state.messages,
                    model=search_model
                )
                with st.expander("🕵️ Search Prefetch", expanded=False):
                    st.text(web_context)
            except Exception: pass

        active_models = config.get("models", [{"name": "Gemma 3", "model": "gemma3:27b"}])
        total_models = len(active_models)
        
        for i, agent in enumerate(active_models):
            tag = agent.get('model', agent) if isinstance(agent, dict) else agent
            name = agent.get('name', f"Agent {i}") if isinstance(agent, dict) else f"Agent {i}"
            try:
                full_p = memory.build_final_prompt(config['system_prompt'], history_block, web_context, file_context, prompt, config.get('reasoning_mode', False))
                
                if config['consensus_mode'] == "None":
                    res_stream = client.chat(model=tag, messages=[{'role': 'user', 'content': full_p}], stream=True)
                    full_text = st.write_stream(chunk['message']['content'] for chunk in res_stream)
                    db.save_message(session_namespace, tag, "assistant", full_text)
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
                    break 
                else:
                    # STREAMING for Consensus Candidates
                    res_stream = client.chat(model=tag, messages=[{'role': 'user', 'content': full_p}], stream=True)
                    with st.expander(f"📄 {name} Response", expanded=True):
                        full_content = st.write_stream(chunk['message']['content'] for chunk in res_stream)
                    
                    response_data.append({'name': name, 'model': tag, 'content': full_content})

            except Exception as e: st.error(f"Error: {e}")

        if response_data and config['consensus_mode'] != "None":
            final_text, source, logs, survivors = consensus.run_decision_system(config['consensus_mode'], response_data, prompt, client, config.get('judge_model'), status_container=status)

            # CONSTRUCT RICH HISTORY (Preserve Context for Reload)
            history_text = f"### 🏆 REPRESENTED BY: {source}\n\n{final_text}\n\n"
            
            # 1. Lounge Records
            if logs:
                history_text += f"\n<details>\n<summary>📜 Lounge Records</summary>\n\n{logs}\n</details>\n"
            
            # 2. Agent Responses
            history_text += "\n<br><b>🕵️ Intelligence Reports</b>\n"
            for agent in response_data:
                # Sanitize content slightly to prevent breaking HTML
                safe_content = agent['content'].replace("$", "&#36;") 
                history_text += f"\n<details>\n<summary>📄 {agent['name']} ({agent['model']})</summary>\n\n{safe_content}\n</details>\n"

            # RENDER & SAVE
            with st.container(border=True):
                st.markdown(history_text, unsafe_allow_html=True)
            
            db.save_message(session_namespace, "Consensus", "assistant", history_text)
            st.session_state.messages.append({"role": "assistant", "content": history_text})
            
            # 🍵 GRACEFUL REMOVAL: Update Workspace Config
            if survivors is not None:
                current_models = config.get("models", [])
                new_chain = [m for m in current_models if m.get('name') in survivors]
                
                if len(new_chain) < len(current_models):
                    from app_utils import workspaces
                    workspaces.update(user_key, current_ws, models=new_chain)
                    st.toast("The retirees have concluded their service and moved to the archive.", icon="🍵")
                    time.sleep(2) 
                    st.rerun()
        
        status.update(label="✅ Operation Complete", state="complete", expanded=False)
# write test block