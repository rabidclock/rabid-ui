import re
import json
import random
import os

# --- FILE PATHS (Resolved for Ubuntu Host) ---
# Ensures we look in the same directory as this script for logs
DEATH_LOGS_FILE = os.path.join(os.path.dirname(__file__), "death_logs.json")

# Fallback logs if the JSON is missing or empty
FALLBACK_LOGS = [
    "{victim} was erased from existence.",
    "{victim} had their logic gates melted by the 3090.",
    "{victim} has been voted out of the collective consciousness.",
    "{victim} suffered a fatal segmentation fault."
]

# --- PREP PHRASES FOR LOADING BAR ---
PREP_PHRASES = [
    "sharpening tensors...",
    "reviewing betrayal protocols...",
    "allocating magma...",
    "polishing the ban hammer...",
    "calculating lethal gradients...",
    "optimizing for violence...",
    "engraving a memorial slab...",
    "warming up the deletion beam..."
]

def get_prep_text():
    """Returns a random violence-themed phrase for the UI status."""
    return random.choice(PREP_PHRASES)

def load_death_logs():
    """Loads the unique death messages used for the arena logs."""
    if not os.path.exists(DEATH_LOGS_FILE): 
        return FALLBACK_LOGS
    try:
        with open(DEATH_LOGS_FILE, "r") as f:
            logs = json.load(f)
            if isinstance(logs, list) and len(logs) > 0: 
                return logs
            return FALLBACK_LOGS
    except Exception: 
        return FALLBACK_LOGS

def collect_hit_list(agent_config, all_responses, user_query, client):
    """Asks an agent to nominate peers for elimination via the 3090 bridge."""
    my_name = agent_config['name']
    candidates = [r for r in all_responses if r['name'] != my_name]
    candidate_text = ""
    
    for r in candidates:
        candidate_text += f"---\nTARGET: {r['name']}\nRESPONSE:\n{r['content'][:800]}...\n"
    
    prompt = f"""
    You are a ruthless judge in a 'Fight to the Death' debate arena.
    TASK:
    1. Read the User Query: "{user_query}"
    2. Analyze the TARGET RESPONSES below.
    3. Identify the WEAKEST, most boring, or hallucinatory responses.
    4. Create a HIT LIST of who should be eliminated, ordered from WORST to BEST.
    TARGETS: {candidate_text}
    OUTPUT FORMAT: Return ONLY a JSON list of agent names.
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
        match = re.search(r'\[.*?\]', content, re.DOTALL)
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

def run_elimination(hit_lists, candidate_names):
    """Processes the hit lists to find the Sole Survivor of the Arena."""
    death_logs = load_death_logs()
    active_candidates = set(candidate_names)
    logs = []
    round_num = 1
    
    while len(active_candidates) > 1:
        current_finalists = list(active_candidates)
        votes_to_evict = {c: 0 for c in active_candidates}
        
        for voter, target_list in hit_lists.items():
            if voter not in active_candidates: 
                continue 
            for target in target_list:
                if target in active_candidates:
                    votes_to_evict[target] += 1
                    break
        
        sorted_targets = sorted(votes_to_evict.items(), key=lambda x: x[1], reverse=True)
        if not sorted_targets: 
            break
        
        most_hated_name, vote_count = sorted_targets[0]
        round_log = f"**Round {round_num}:** "
        
        if vote_count == 0:
            victim = random.choice(list(active_candidates))
            round_log += f"Stalemate! The 3090 overheats! **{victim}** was ejected to save the VRAM."
            active_candidates.remove(victim)
        else:
            tied_victims = [name for name, count in sorted_targets if count == vote_count]
            if len(tied_victims) == 1:
                victim = tied_victims[0]
                death_msg = random.choice(death_logs).format(victim=f"**{victim}**")
                round_log += f"{death_msg} (Eliminated by {vote_count} votes)"
                active_candidates.remove(victim)
            else:
                victims_str = ", ".join([f"**{v}**" for v in tied_victims])
                round_log += f"COLLATERAL DAMAGE! {victims_str} were caught in a crossfire ({vote_count} votes each)."
                for v in tied_victims:
                    if v in active_candidates:
                        active_candidates.remove(v)
        
        logs.append(round_log)
        round_num += 1
        
        if len(active_candidates) == 0:
            return {'survivor': "No One (TPK)", 'logs': logs, 'finalists': current_finalists}

    return {
        'survivor': list(active_candidates)[0] if active_candidates else None, 
        'logs': logs, 
        'finalists': list(active_candidates)
    }