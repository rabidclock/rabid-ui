import streamlit as st
import random
import subprocess
from app_utils import battle_royale, arena, ranked_choice

def execute_losers(losers_data, judge_model_tag):
    """
    Simulates execution by logging the event. 
    Actual model deletion is disabled to prevent accidental fleet wiping.
    """
    execution_log = []
    for agent in losers_data:
        model_tag = agent['model']
        name = agent['name']
        
        # Safety: Don't delete the Judge!
        if model_tag == judge_model_tag:
            execution_log.append(f"🛡️ {name} ({model_tag}) was spared (Judge Immunity).")
            continue

        # VIRTUAL EXECUTION ONLY
        execution_log.append(f"💀 **ELIMINATED:** {name} ({model_tag}) has been removed from the active roster.")
            
    return execution_log

def summarize_victory(winning_text, prompt, client, model):
    """
    Summarizes the winning result and restates the prompt.
    """
    system_prompt = f"""
    You are an expert synthesizer. 
    Task:
    1. Restate the original User Query clearly.
    2. Summarize the WINNING ANSWER below. Retain key technical details, code blocks, and insights.
    3. Remove any "As an AI" fluff.
    
    USER QUERY: {prompt}
    WINNING ANSWER: {winning_text}
    """
    
    try:
        response = client.chat(
            model=model,
            messages=[{'role': 'user', 'content': system_prompt}],
            options={"temperature": 0.2}
        )
        return response['message']['content']
    except Exception as e:
        return f"Summarization Failed: {e}\n\nOriginal Text:\n{winning_text}"

def run_decision_system(mode, response_data, prompt, client, judge_model=None, status_container=None):
    """
    Orchestrates the selected consensus mode using the RTX 3090 bridge.
    Returns: (final_text, source_label, deliberation_log, survivor_names)
    """
    def log(msg):
        log_entries.append(msg)
        if status_container:
            status_container.markdown(msg)

    def update_status(label):
        if status_container:
            status_container.update(label=label, state="running")

    log_entries = []
    log(f"### 🏟️ Arena Initialized: {mode} Mode")
    
    # Default: Everyone survives unless the mode kills them
    surviving_names = [r['name'] for r in response_data]
    
    # --- [MODE 1] FIGHT TO THE DEATH ---
    if mode == "Fight to the Death":
        hit_lists = {}
        update_status("📡 Targeting Phase...")
        log("📡 Agents are identifying targets and calculating trajectory...")
        
        candidate_names = [r['name'] for r in response_data]
        
        # 1. Targeting Phase
        for agent in response_data:
            update_status(f"📡 Targeting: {agent['name']}...")
            targets = battle_royale.collect_hit_list(agent, response_data, prompt, client=client)
            if targets: 
                hit_lists[agent['name']] = targets
                log(f"🎯 **{agent['name']}** locked onto targets: {', '.join(targets)}")
        
        # 2. Elimination Phase
        update_status("⚔️ Fighting...")
        results = battle_royale.run_elimination(hit_lists, candidate_names)
        arena.render_battle(candidate_names, results.get('logs', []), results.get('survivor'))
        
        log("\n--- BATTLE LOG ---")
        for l in results.get('logs', []):
            log(f"🗡️ {l}")
            
        survivor = results.get('survivor')
        finalists = results.get('finalists', [])
        
        winning_text = ""
        winner_name = ""

        # 3. Determine Winner
        if survivor and survivor != "No One (TPK)":
            log(f"\n🏆 **VICTORY:** {survivor} is the last intelligence standing.")
            winning_text = next((r['content'] for r in response_data if r['name'] == survivor), "Data Lost.")
            winner_name = survivor
            
            losers = [r for r in response_data if r['name'] != survivor]
            surviving_names = [survivor] 
            
        else:
            # TOTAL PARTY KILL
            log(f"\n💀 **TOTAL PARTY KILL.** All agents have been eliminated.")
            losers = response_data
            surviving_names = [] 
            
            if judge_model:
                update_status(f"⚖️ Judge {judge_model} Deliberating...")
                log(f"⚖️ **JUDGE {judge_model}** enters the arena to review the fallen...")
                
                finalist_content = "\n\n".join([
                    f"AGENT {r['name']}:\n{r['content']}" 
                    for r in response_data if r['name'] in finalists
                ])
                
                judge_prompt = f"""
                The debate arena has ended in a mutual kill. 
                You are the NECROMANCER JUDGE. 
                Review the final arguments from the fallen agents below and construct the BEST POSSIBLE ANSWER.
                
                USER PROMPT: {prompt}
                
                FINALIST ARGUMENTS:
                {finalist_content}
                """
                
                try:
                    res = client.chat(model=judge_model, messages=[{'role': 'user', 'content': judge_prompt}])
                    winning_text = res['message']['content']
                    winner_name = f"Judge {judge_model} (Post-Mortem)"
                    log(f"✅ Judge has reconstructed a solution from the finalists.")
                except Exception as e:
                    winning_text = "Judgment failed."
                    log(f"❌ Judge failed to answer: {e}")
            else:
                ex_logs = execute_losers(losers, judge_model)
                for l in ex_logs: log(l)
                return "The arena is silent. No judge configured.", "Total Party Kill", "\n".join(log_entries), surviving_names

        # 4. EXECUTION PHASE
        update_status("💀 Executing Losers...")
        log(f"\n⚖️ **EXECUTING LOSERS...**")
        ex_logs = execute_losers(losers, judge_model)
        for l in ex_logs: log(l)

        # 5. Summarization
        update_status("📝 Summarizing...")
        log(f"\n📝 **SUMMARIZING VICTORY ({winner_name})...**")
        summary_model = judge_model if "Judge" in winner_name else next((r['model'] for r in response_data if r['name'] == winner_name), judge_model)
        final_summary = summarize_victory(winning_text, prompt, client, summary_model)
        return final_summary, f"Winner: {winner_name}", "\n".join(log_entries), surviving_names

    # --- [MODE 2] JUDGE & JURY (Hybrid with Mistrial Logic) ---
    if mode == "Judge & Jury" and judge_model:
        max_retries = 1
        current_attempt = 0
        
        while current_attempt <= max_retries:
            is_retrial = current_attempt > 0
            seed = random.randint(1, 1000000) if is_retrial else None
            
            if is_retrial:
                update_status(f"⚠️ Mistrial! Retrying (Seed {seed})...")
                log(f"\n⚠️ **MISTRIAL DECLARED.** Empaneling new Jury (Seed: {seed})...")
            else:
                update_status("🗳️ Jury Voting...")
                log("👥 **THE JURY DELIBERATES:** Agents are casting ranked votes...")
            
            # 1. The Jury
            vote_results = ranked_choice.conduct_vote(response_data, prompt, client, seed=seed)
            jury_winner = vote_results.get('winner')
            
            arena.render_ranked_choice_rounds(vote_results.get('tallies', []))
            if is_retrial:
                 log(f"🔄 **Retrial Vote Complete.** New Winner: {jury_winner}")
            else:
                 for l in vote_results.get('logs', []): log(l)
                 log(f"\n🗳️ **Jury Recommendation:** {jury_winner}")

            # 2. The Judge
            update_status(f"⚖️ Judge {judge_model} Reviewing...")
            log(f"\n⚖️ **JUDGE {judge_model}** is reviewing the verdict...")
            
            context_block = "\n\n".join([f"AGENT {r['name']}:\n{r['content']}" for r in response_data])
            
            verdict_prompt = f"""
            ACT AS A SUPREME COURT JUDGE.
            USER PROMPT: {prompt}
            THE JURY VOTED FOR: {jury_winner}
            
            ALL ARGUMENTS:
            {context_block}
            
            TASK: Do you UPHOLD the jury's decision or OVERTURN it?
            If the jury's winner is reasonable, UPHOLD it.
            Only OVERTURN if another answer is objectively superior.
            
            OUTPUT: Reply ONLY with the word "UPHOLD" or "OVERTURN".
            """
            
            try:
                judge_opts = {"temperature": 0.1}
                if is_retrial: 
                    judge_opts = {"temperature": 0.7, "seed": seed}

                verdict_res = client.chat(
                    model=judge_model, 
                    messages=[{'role': 'user', 'content': verdict_prompt}],
                    options=judge_opts
                )
                verdict = verdict_res['message']['content'].strip().upper()
                
                if "UPHOLD" in verdict:
                    log(f"✅ Judge **UPHOLDS** the Jury's decision ({jury_winner}).")
                    
                    final_prompt = f"Summarize and refine the winning answer from {jury_winner}.\n\nCONTENT:\n{next((r['content'] for r in response_data if r['name'] == jury_winner), '')}"
                    res_stream = client.chat(model=judge_model, messages=[{'role': 'user', 'content': final_prompt}], stream=True)
                    final_text = st.write_stream(chunk['message']['content'] for chunk in res_stream)
                    return final_text, f"Verdict: {jury_winner} (Upheld)", "\n".join(log_entries), surviving_names
                
                else:
                    if current_attempt < max_retries:
                        log(f"❌ Judge **OVERTURNS** the Jury! Conflict detected.")
                        current_attempt += 1
                        continue 
                    else:
                        log(f"❌ Judge **OVERTURNS** the Jury again! Hung Jury.")
                        log(f"⚖️ **SUPREME COURT RULING:** Judge {judge_model} issues binding verdict.")
                        
                        judge_final_prompt = f"The Jury is hung. You have final authority. Review all answers to '{prompt}' and generate the best possible response."
                        res_stream = client.chat(model=judge_model, messages=[{'role': 'user', 'content': judge_final_prompt}], stream=True)
                        final_text = st.write_stream(chunk['message']['content'] for chunk in res_stream)
                        return final_text, f"Verdict: Judge Override", "\n".join(log_entries), surviving_names

            except Exception as e:
                st.error(f"Judge Error: {e}")
                return "Error", "Error", str(e), surviving_names

    # --- [MODE 3] ARBITER (Solo Judge) ---
    if mode == "Arbiter" and judge_model:
        update_status(f"⚖️ Judge {judge_model} Deciding...")
        log(f"⚖️ **{judge_model}** is reviewing the arguments (No Jury)...")
        
        context_block = "\n\n".join([f"AGENT {r['name']}:\n{r['content']}" for r in response_data])
        judge_prompt = f"USER QUERY: {prompt}\n\nAGENT RESPONSES:\n{context_block}\n\nINSTRUCTION: Act as a final judge. Synthesize the best answer or pick a winner."
        
        try:
            res_stream = client.chat(model=judge_model, messages=[{'role': 'user', 'content': judge_prompt}], stream=True)
            final_text = st.write_stream(chunk['message']['content'] for chunk in res_stream)
            return final_text, f"Judge Verdict ({judge_model})", "\n".join(log_entries), surviving_names
        except Exception as e:
            return "Judgment failed.", "Error", str(e), surviving_names

    # --- [MODE 4] RANKED CHOICE (Pure Democracy) ---
    if mode == "Ranked Choice":
        update_status("🗳️ Voting...")
        log("🗳️ **Ranked Choice Voting** initialized...")
        
        results = ranked_choice.conduct_vote(response_data, prompt, client)
        winner_name = results.get('winner')
        
        arena.render_ranked_choice_rounds(results.get('tallies', []))
        
        log(f"\n✅ **VOTE COMPLETE:** {winner_name} won.")
        final_text = next((r['content'] for r in response_data if r['name'] == winner_name), "Selection error.")
        return final_text, f"Ranked Choice Winner: {winner_name}", "\n".join(results.get('logs', [])), surviving_names

    # --- [FALLBACK] STANDARD AGGREGATION ---
    log("📜 No combat requested. Aggregating all intelligence outputs.")
    fallback_text = "\n\n".join([f"**{r['name']}**:\n{r['content']}" for r in response_data])
    return fallback_text, "Standard Aggregation", "\n".join(log_entries), surviving_names