import ollama
import streamlit as st

TRANSLATOR_MODEL = "qwen2.5:7b"

def ensure_model_exists():
    """Checks/Pulls model."""
    try:
        models_info = ollama.list()
        if hasattr(models_info, 'models'): 
            installed = [m.model for m in models_info.models]
        else: 
            installed = [m.get('model') or m.get('name') for m in models_info.get('models', [])]

        is_installed = any(TRANSLATOR_MODEL in m for m in installed)

        if not is_installed:
            st.warning(f"⚠️ Downloading {TRANSLATOR_MODEL}...")
            ollama.pull(TRANSLATOR_MODEL)
        return True
    except Exception as e:
        st.error(f"Model Check Failed: {e}")
        return True

def detect_language(text):
    """
    Step 1: Classification.
    """
    clean_sample = text.replace("*", "").replace("#", "")[:300]
    prompt = f"""
    TASK: Identify the language.
    INPUT: "{clean_sample}"
    OUTPUT: Just the language name (e.g. English, Spanish).
    """
    try:
        response = ollama.chat(
            model=TRANSLATOR_MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            options={"temperature": 0.0}
        )
        return response['message']['content'].strip()
    except:
        return "Unknown"

def translate_text(text, target_language):
    """
    Step 2: Aggressive Translation.
    """
    # We use XML tags to clearly separate instructions from data.
    # We also give a strong System Instruction.
    prompt = f"""
    INSTRUCTIONS:
    You are a professional interpreter. Translate the content inside the <content> tags into {target_language}.
    
    RULES:
    1. Output ONLY the translated text. 
    2. Do NOT repeat the input text.
    3. Do NOT converse or reply to the text.
    4. Maintain ALL markdown formatting (lists, bolding, code blocks).
    
    <content>
    {text}
    </content>
    
    OUTPUT TRANSLATION IN {target_language.upper()}:
    """
    try:
        response = ollama.chat(
            model=TRANSLATOR_MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            options={"temperature": 0.1} # Slight creativity helps translation flow better than 0.0
        )
        return response['message']['content'].strip()
    except Exception as e:
        return f"[Translation Failed] {e}"

def check_and_fix(text, target_language_name):
    """
    Two-Step Pipeline with Debugger.
    """
    if not text or len(text) < 10: return text
    ensure_model_exists()

    # 1. DETECT
    detected_lang = detect_language(text)
    
    # 2. COMPARE
    needs_translation = target_language_name.lower() not in detected_lang.lower()

    # 3. DEBUGGER UI
    with st.expander(f"🕵️ Translator Debugger ({target_language_name})", expanded=True):
        st.write(f"**Target:** {target_language_name}")
        st.write(f"**Detected:** `{detected_lang}`")
        
        if needs_translation:
            st.warning(f"Mismatch! Translating {detected_lang} -> {target_language_name}...")
            
            # 4. EXECUTE TRANSLATION
            translated_text = translate_text(text, target_language_name)
            
            # 5. SANITY CHECK
            # If the "translated" text is identical to input, the model failed.
            if translated_text.strip() == text.strip():
                st.error("Model Error: Returned identical text (Echoing).")
                return text
            
            st.info("Translation applied successfully.")
            return translated_text
        else:
            st.success("Language Match. No action taken.")
            return text