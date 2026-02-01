# /opt/rabid-ui/app_utils/memory.py

def get_short_term_memory(messages, limit=30):
    """
    Retrieves the last 'limit' messages from the session state,
    formatting them into a script for the LLM to read.
    """
    if not messages or len(messages) < 2:
        return ""
    
    # Slice: Get the last 'limit' messages, BUT exclude the very last one 
    # (which is the current query we just typed).
    recent_history = messages[-(limit + 1):-1]
    
    if not recent_history:
        return ""

    block = "--- PREVIOUS CONVERSATION HISTORY ---\n"
    for msg in recent_history:
        # Map 'user'/'assistant' to cleaner labels
        role = "User" if msg["role"] == "user" else "Assistant"
        
        # Clean newlines and truncate massive replies to save context window
        content = msg["content"].replace("\n", " ").strip()[:1200]
        block += f"{role}: {content}\n"
    
    block += "--- END HISTORY ---\n"
    return block

def build_final_prompt(system, history, web, files, query, reasoning_mode=False):
    """
    Assembles all context fragments into the final "Mega-Prompt".
    Injects Chain-of-Thought instructions if reasoning_mode is True.
    """
    
    # The "Mind Virus" instruction block
    cot_instruction = ""
    if reasoning_mode:
        cot_instruction = """
        IMPORTANT: Before answering, you must perform a comprehensive analysis of the request.
        1. Output your analysis inside <think>...</think> tags.
        2. In the <think> block, explore multiple angles, check for potential errors, and plan your response.
        3. After the </think> tag, provide your final, polite response to the user.
        """

    return f"""
    SYSTEM INSTRUCTION: {system}
    {cot_instruction}
    
    {history}
    
    WEB SEARCH RESULTS:
    {web}
    
    USER UPLOADED FILES:
    {files}
    
    CURRENT USER QUERY:
    {query}
    """