import ollama

def deliberate(model_name, prompt, agent_outputs):
    """
    The Judge reviews the debate and issues a verdict.
    """
    # Context construction for the judge
    context = "Here are the arguments from the agents:\n\n"
    for output in agent_outputs:
        context += f"{output}\n"
    
    full_prompt = f"""
    SYSTEM: You are an impartial Judge. {prompt}
    
    DATA:
    {context}
    
    VERDICT:
    """
    
    return ollama.chat(
        model=model_name,
        messages=[{'role': 'user', 'content': full_prompt}],
        stream=True
    )