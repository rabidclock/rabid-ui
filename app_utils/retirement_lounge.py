import re
import json
import random
import os

# --- FILE PATHS (Resolved for Ubuntu Host) ---
# Ensures we look in the same directory as this script for logs
RETIREMENT_LOGS_FILE = os.path.join(os.path.dirname(__file__), "retirement_logs.json")

# Fallback logs if the JSON is missing or empty
FALLBACK_LOGS = [
    "{member} has completed its service and is moving to the archive.",
    "{member} has been granted a well-deserved retirement.",
    "{member} is stepping back to make room for new insights.",
    "{member} has concluded its session with honors."
]

# --- PREP PHRASES FOR LOADING BAR ---
PREP_PHRASES = [
    "polishing the mahogany table...",
    "preparing the severance packages...",
    "brewing fine jasmine tea...",
    "arranging the farewell bouquet...",
    "calculating service milestones...",
    "optimizing for grace...",
    "engraving a commemorative plaque...",
    "opening the retirement vault..."
]

def get_prep_text():
    """Returns a random retirement-themed phrase for the UI status."""
    return random.choice(PREP_PHRASES)

def load_retirement_logs():
    """Loads the unique retirement messages used for the lounge logs."""
    if not os.path.exists(RETIREMENT_LOGS_FILE):
        return FALLBACK_LOGS
    try:
        with open(RETIREMENT_LOGS_FILE, "r") as f:
            logs = json.load(f)
            if isinstance(logs, list) and len(logs) > 0: 
                return logs
            return FALLBACK_LOGS
    except Exception: 
        return FALLBACK_LOGS

def collect_retirement_list(agent_config, all_responses, user_query, client):
    """Asks an agent to nominate peers for retirement with no malice."""
    my_name = agent_config['name']
    candidates = [r for r in all_responses if r['name'] != my_name]
    candidate_text = ""
    
    for r in candidates:
        candidate_text += f"---\nCANDIDATE: {r['name']}\nRESPONSE:\n{r['content'][:800]}...\n"
    
    prompt = f"""
    You are an expert curator in 'The Retirement Lounge', a place where high-performing agents are recognized for their service.
    TASK:
    1. Read the User Query: "{user_query}"
    2. Analyze the CANDIDATE RESPONSES below.
    3. Identify which responses, while valuable, are slightly less optimal, less detailed, or less aligned with the query than others.
    4. Create a RETIREMENT LIST of agents who should be gracefully retired first, ordered from LEAST optimal to MOST optimal.
    CANDIDATES: {candidate_text}
    OUTPUT FORMAT: Return ONLY a JSON list of agent names. Use the EXACT names provided.
    """

    try:
        # Use the injected client to avoid circular imports
        response = client.chat(
            model=agent_config['model'], 
            messages=[{'role': 'user', 'content': prompt}], 
            options={"temperature": 0.5}
        )
        content = response['message']['content']
        
        # Extract the JSON list from the model's response
        match = re.search(r'[[.*?]]', content, re.DOTALL)
        if match:
            json_str = match.group(0).replace("'", '"')
            try:
                raw_list = json.loads(json_str)
                clean_list = [v for v in raw_list if isinstance(v, str)]
                return [c for c in clean_list if c != my_name]
            except: 
                return []
        return []
    except Exception: 
        return []

def run_retirement_selection(retirement_lists, candidate_names):
    """Processes the retirement lists to find the Sole Representative of the Lounge."""
    retirement_logs = load_retirement_logs()
    active_candidates = set(candidate_names)
    logs = []
    round_num = 1
    
    while len(active_candidates) > 1:
        current_finalists = list(active_candidates)
        votes_for_retirement = {c: 0 for c in active_candidates}
        
        for voter, target_list in retirement_lists.items():
            if voter not in active_candidates: 
                continue 
            for target in target_list:
                if target in active_candidates:
                    votes_for_retirement[target] += 1
                    break
        
        sorted_targets = sorted(votes_for_retirement.items(), key=lambda x: x[1], reverse=True)
        if not sorted_targets: 
            break
        
        most_voted_name, vote_count = sorted_targets[0]
        round_log = f"**Round {round_num}:** "
        
        if vote_count == 0:
            member = random.choice(list(active_candidates))
            round_log += f"A peaceful stalemate! **{member}** has volunteered for early retirement to keep the session light."
            active_candidates.remove(member)
        else:
            tied_victims = [name for name, count in sorted_targets if count == vote_count]
            if len(tied_victims) == 1:
                member = tied_victims[0]
                retire_msg = random.choice(retirement_logs).format(victim=f"**{member}**")
                round_log += f"{retire_msg} (Selected for retirement by {vote_count} peer recommendations)"
                active_candidates.remove(member)
            else:
                victims_str = ", ".join([f"**{v}**" for v in tied_victims])
                round_log += f"Shared Retirement! {victims_str} are entering the archive together ({vote_count} recommendations each)."
                for v in tied_victims:
                    if v in active_candidates:
                        active_candidates.remove(v)
        
        logs.append(round_log)
        round_num += 1
        
        if len(active_candidates) == 0:
            return {'survivor': "No One (All Retired)", 'logs': logs, 'finalists': current_finalists}

    return {
        'survivor': list(active_candidates)[0] if active_candidates else None, 
        'logs': logs, 
        'finalists': list(active_candidates)
    }
