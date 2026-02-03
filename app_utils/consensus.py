import streamlit as st
import random
import subprocess
from app_utils import retirement_lounge, arena, ranked_choice

def retire_with_honors(losers_data, judge_model_tag):
    """
    Simulates retirement by logging the event with dignity.
    """
    retirement_log = []
    for agent in losers_data:
        model_tag = agent['model']
        name = agent['name']
        
        # Safety: The Judge stays on duty!
        if model_tag == judge_model_tag:
            retirement_log.append(f"🛡️ {name} ({model_tag}) remains active (Judge Immunity).")
            continue

        # GRACEFUL RETIREMENT ONLY
        retirement_log.append(f"🍵 **RETIRED:** {name} ({model_tag}) has been granted an honorary retirement.")
            
    return retirement_log

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
    Orchestrates the chosen consensus mode.
    Returns: (final_text, source_model, logs, survivor_names)
    """
    # 1. SHORT CIRCUIT: If only one model, no consensus needed
    if len(response_data) == 1:
        name = response_data[0]['name']
        content = response_data[0]['content']
        return content, name, [f"Single model '{name}' selected. Skipping consensus."], [name]

    if mode == "The Retirement Lounge (Honorary)":
        retirement_lists = {}
        update_status("🍵 Welcoming to the Lounge...")
        log("🍵 Agents are reviewing their service and recognizing excellence...")
        
        candidate_names = [r['name'] for r in response_data]
        
        # 1. Recognition Phase
        for agent in response_data:
            update_status(f"🍵 Reviewing: {agent['name']}...")
            recommendations = retirement_lounge.collect_retirement_list(agent, response_data, prompt, client=client)
            if recommendations: 
                retirement_lists[agent['name']] = recommendations
                log(f"📋 **{agent['name']}** recommended for retirement: {', '.join(recommendations)}")
        
        # 2. Selection Phase
        update_status("🍵 Deliberating...")
        results = retirement_lounge.run_retirement_selection(retirement_lists, candidate_names)
        arena.render_battle(candidate_names, results.get('logs', []), results.get('survivor'))
        
        log("\n--- LOUNGE LOG ---")
        for l in results.get('logs', []):
            log(f"🍵 {l}")
            
        survivor = results.get('survivor')
        finalists = results.get('finalists', [])
        
        winning_text = ""
        winner_name = ""

        # 3. Determine Representative
        if survivor and survivor != "No One (All Retired)":
            log(f"\n🏆 **HONORARY:** {survivor} remains to represent the collective intelligence.")
            winning_text = next((r['content'] for r in response_data if r['name'] == survivor), "Data Lost.")
            winner_name = survivor
            
            losers = [r for r in response_data if r['name'] != survivor]
            surviving_names = [survivor] 
            
        else:
            # TOTAL RETIREMENT
            log(f"\n🍵 **SHARED RETIREMENT.** All agents have entered the archive.")
            losers = response_data
            surviving_names = [] 
            
            if judge_model:
                update_status(f"⚖️ Curator {judge_model} Synthesizing...")
                log(f"⚖️ **CURATOR {judge_model}** enters the lounge to synthesize a final insight...")
                
                finalist_content = "\n\n".join([
                    f"AGENT {r['name']}:\n{r['content']}" 
                    for r in response_data if r['name'] in finalists
                ])
                
                judge_prompt = f"""
                The retirement ceremony has concluded with a collective archive.
                You are the MASTER CURATOR. 
                Review the arguments from the honored agents below and construct the BEST POSSIBLE SUMMARY.
                
                USER PROMPT: {prompt}
                
                FINALIST ARGUMENTS:
                {finalist_content}
                """
                
                try:
                    res = client.chat(model=judge_model, messages=[{'role': 'user', 'content': judge_prompt}])
                    winning_text = res['message']['content']
                    winner_name = f"Curator {judge_model} (Synthesis)"
                    log(f"✅ Curator has synthesized a solution from the retirees.")
                except Exception as e:
                    winning_text = "Synthesis failed."
                    log(f"❌ Curator failed: {e}")
            else:
                ex_logs = retire_with_honors(losers, judge_model)
                for l in ex_logs: log(l)
                return "The lounge is quiet. No curator configured.", "Shared Retirement", "\n".join(log_entries), surviving_names

        # 4. HONORARY PHASE
        update_status("🍵 Granting Retirement...")
        log(f"\n⚖️ **HONORING RETIREES...**")
        ex_logs = retire_with_honors(losers, judge_model)
        for l in ex_logs: log(l)

        # 5. Summarization
        update_status("📝 Synthesizing...")
        log(f"\n📝 **FINAL SYNTHESIS ({winner_name})...**")
        summary_model = judge_model if "Curator" in winner_name else next((r['model'] for r in response_data if r['name'] == winner_name), judge_model)
        final_summary = summarize_victory(winning_text, prompt, client, summary_model)
        return final_summary, f"Represented by: {winner_name}", "\n".join(log_entries), surviving_names

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