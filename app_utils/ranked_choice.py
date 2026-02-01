import re
import json
import streamlit as st
import random

def conduct_vote(all_responses, user_query, client, seed=None):
    """Orchestrates the Ranked Choice Vote and captures all round data."""
    ballots = []
    candidate_names = [r['name'] for r in all_responses]
    tally = {name: 0 for name in candidate_names} 
    
    # Use provided seed or fallback (None = Ollama default/random)
    options = {"seed": seed} if seed is not None else {}

    # 1. Collect Ballots from EVERY agent in the squad
    for agent in all_responses:
        ballot = collect_ballot(agent, all_responses, user_query, client, options)
        if ballot:
            ballots.append(ballot)
            # Round 1 Tally for the initial donut chart
            first_choice = ballot[0]
            for official_name in candidate_names:
                if first_choice.lower().strip() == official_name.lower().strip():
                    tally[official_name] += 1
                    break
        else:
            # Visual notification for disenfranchised voters
            st.sidebar.warning(f"⚠️ Voter disenfranchised: {agent['name']}")

    # 2. Run IRV and capture all round data for Plotly
    results = calculate_winner(ballots, candidate_names)
    
    return {
        'winner': results['winner'],
        'tally': tally,
        'tallies': results.get('tallies', []),
        'logs': results['logs']
    }

def collect_ballot(agent_config, all_responses, user_query, client, options=None):
    """Bulletproof ballot collection: allows self-voting & sanitizes JSON."""
    my_name = agent_config['name']
    candidate_names = [r['name'] for r in all_responses]
    candidate_list_str = ", ".join(candidate_names)
    
    candidate_text = ""
    for r in all_responses:
        candidate_text += f"---\nNAME: {r['name']}\nRESPONSE: {r['content'][:800]}\n"
        
    prompt = f"""
    Evaluate the following Candidate Responses for this query: "{user_query}"
    CANDIDATES: {candidate_list_str}
    
    EVIDENCE:
    {candidate_text}
    
    TASK: Rank the top 3 best responses. 
    NOTE: You are {my_name}. You MAY vote for yourself if you believe your 
    response is the most accurate.
    
    OUTPUT: Return ONLY a JSON list of names. No explanation.
    Example: ["{candidate_names[0]}", "{candidate_names[1]}"]
    """
    
    try:
        # Increase temperature slightly if we are re-rolling seeds to encourage diversity
        final_opts = options.copy() if options else {}
        if 'seed' in final_opts:
            final_opts['temperature'] = 0.7 # Higher temp for retrials/specific seeds

        response = client.chat(
            model=agent_config['model'], 
            messages=[{'role': 'user', 'content': prompt}],
            options=final_opts
        )
        content = response['message']['content']
        
        # Aggressive JSON Extraction for smaller models
        match = re.search(r'[[\s"].*?["\s]*?(?:,[\s"].*?["\s]*)*]', content, re.DOTALL)
        if not match:
            match = re.search(r"[[\s'.*?['\s]*?(?:,[\s'.*?['\s]*)*]", content, re.DOTALL)
            
        if match:
            json_str = match.group(0).replace("'", '"')
            raw_votes = json.loads(json_str)

            # Map votes back to official casing for exact matching
            official_map = {n.lower().strip(): n for n in candidate_names}
            clean_votes = []
            for v in raw_votes:
                v_clean = str(v).lower().strip()
                if v_clean in official_map:
                    clean_votes.append(official_map[v_clean])
            
            return clean_votes[:3]
    except Exception as e:
        print(f"Extraction Error for {my_name}: {e}")
    return []

def calculate_winner(ballots, candidate_names):
    """Calculates IRV winner and explicitly saves snapshots for Plotly."""
    active_candidates = set(candidate_names)
    logs = []
    round_tallies = [] 
    
    while True:
        counts = {c: 0 for c in active_candidates}
        for ballot in ballots:
            for candidate in ballot:
                if candidate in active_candidates:
                    counts[candidate] += 1
                    break
        
        # Save round data for the donut charts
        round_tallies.append(counts.copy())
        
        total_votes = sum(counts.values())
        if total_votes == 0: 
            return {'winner': "No Clear Winner", 'logs': logs, 'tallies': round_tallies}

        sorted_res = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        winner, votes = sorted_res[0]
        
        # Victory check (>50% or only one candidate left)
        if votes > total_votes / 2 or len(active_candidates) <= 1:
            return {'winner': winner, 'logs': logs, 'tallies': round_tallies}
            
        # Tie-breaker logic
        if sorted_res[0][1] == sorted_res[-1][1]:
            logs.append("⚖️ Dead tie detected. Applying tie-breaker rule.")
            return {'winner': winner, 'logs': logs, 'tallies': round_tallies}

        loser = sorted_res[-1][0]
        active_candidates.remove(loser)
        logs.append(f"Eliminated: {loser} with {counts[loser]} votes")
