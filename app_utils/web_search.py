# /opt/rabid-ui/app_utils/web_search.py
import httpx
import concurrent.futures
import sqlite3
import subprocess
import os
import sys

# --- CONFIGURATION ---
SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8080")
TIMEOUT = 5.0
MAX_DEEP_READS = 3
MAX_CHARS_PER_PAGE = 8000

# --- INTEGRATION WITH RABID-SCRAPE ---
SCRAPER_ROOT = "/opt/rabid-scrape"
DB_PATH = os.path.join(SCRAPER_ROOT, "scrapes.db")
PYTHON_EXEC = os.path.join(SCRAPER_ROOT, "venv/bin/python")
MAIN_SCRIPT = os.path.join(SCRAPER_ROOT, "main.py")

def get_from_db(url):
    """Retrieve the latest scrape content for a URL from the shared database."""
    if not os.path.exists(DB_PATH):
        return None
        
    try:
        # Connect strictly read-only to avoid locking
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT content FROM scrapes 
            WHERE url = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''', (url,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return row[0]
        return None
    except Exception as e:
        return None

def scrape_url(url):
    """
    Leverages the 'rabid-scrape' engine (Playwright/OCR).
    """
    if not url or url.startswith('#') or url.startswith('/'): 
        return None

    # 1. Check Cache First
    cached_content = get_from_db(url)
    if cached_content:
        return cached_content[:MAX_CHARS_PER_PAGE]

    # 2. Trigger External Scraper
    try:
        subprocess.run(
            [PYTHON_EXEC, MAIN_SCRIPT, url],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )
        
        # 3. Fetch Result
        content = get_from_db(url)
        if content:
            return content[:MAX_CHARS_PER_PAGE]
        else:
            return "[System: Scraper ran but produced no content]"
            
    except subprocess.CalledProcessError as e:
        return f"[System: Scraper Process Failed - {e.stderr.decode().strip()}]"
    except Exception as e:
        return f"[System: Scraper Invocation Error - {e}]"

def generate_optimized_query(raw_prompt, history, client, model="gemma3:27b"):
    """
    Uses an LLM to convert a conversational prompt into a targeted search query.
    """
    try:
        context = ""
        if history:
            # Take last 3 turns for context to resolve references
            relevant = history[-3:]
            for msg in relevant:
                role = msg.get('role', 'user').upper()
                content = msg.get('content', '')[:500] # Truncate to save tokens
                context += f"{role}: {content}\n"
        
        system_prompt = f"""
        You are a Search Engine Operator.
        Task: Convert the User's input into a single, highly effective search query.
        
        CONTEXT:
        {context}
        
        USER INPUT: {raw_prompt}
        
        INSTRUCTIONS:
        - Remove conversational fluff ("Can you tell me...", "I'm looking for...").
        - Use specific keywords.
        - If the user refers to "it" or "that", use the Context to resolve the entity.
        - OUTPUT ONLY THE QUERY STRING. NO QUOTES. NO EXPLANATION.
        """
        
        response = client.chat(
            model=model, 
            messages=[{'role': 'user', 'content': system_prompt}],
            options={"temperature": 0.1}
        )
        return response['message']['content'].strip().strip('"')
    except Exception as e:
        return raw_prompt

def search(query, num_results=8, client=None, history=None, model="gemma3:27b"):
    """
    Main Entry Point:
    1. Optimizes query using LLM (if client provided).
    2. Gets JSON snippets from SearXNG.
    3. Spawns threads to Deep-Scrape the top N results using rabid-scrape.
    4. Combines everything into a context block.
    """
    try:
        final_query = query
        optimization_note = ""
        
        if client:
            final_query = generate_optimized_query(query, history, client, model)
            if final_query != query:
                optimization_note = f" (Optimized from: '{query}')"

        headers = {"User-Agent": "RabidUI-Agent/1.0"}
        params = {
            "q": final_query,
            "format": "json",
            "engines": "google,bing,duckduckgo,wikipedia",
            "safesearch": 0,
            "language": "en-US"
        }
        
        response = httpx.get(f"{SEARXNG_URL}/search", headers=headers, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("results", [])

        if not results:
            return f"[System Log]: Search for '{final_query}' returned 0 results."

        # --- PHASE 2: DEEP READ (PARALLEL) ---
        deep_read_targets = []
        seen_urls = set()
        for res in results:
            u = res.get("url")
            if u and u not in seen_urls:
                deep_read_targets.append(u)
                seen_urls.add(u)
            if len(deep_read_targets) >= MAX_DEEP_READS:
                break

        scraped_data = {} 
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_DEEP_READS) as executor:
            future_to_url = {executor.submit(scrape_url, url): url for url in deep_read_targets}
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    data = future.result()
                    scraped_data[url] = data
                except Exception:
                    scraped_data[url] = None

        # --- PHASE 3: REPORT GENERATION ---
        context_str = f"--- BEGIN WEB INTELLIGENCE FOR: '{final_query}'{optimization_note} ---\n"
        
        for i, res in enumerate(results[:num_results]):
            title = res.get("title", "No Title")
            url = res.get("url", "#")
            snippet = res.get("content", "No snippet available.")
            
            context_str += f"\n=== SOURCE {i+1}: {title} ===\n"
            context_str += f"URL: {url}\n"
            
            if url in scraped_data and scraped_data[url]:
                context_str += f"STATUS: [FULL SCRAPE (PLAYWRIGHT/OCR)]\n"
                context_str += f"--- START CONTENT ---\n{scraped_data[url]}\n--- END CONTENT ---\n"
            else:
                context_str += f"STATUS: [SNIPPET ONLY]\n"
                context_str += f"CONTENT: {snippet}\n"
            
            context_str += "-" * 40

        context_str += "\n--- END WEB INTELLIGENCE ---\n"
        return context_str

    except Exception as e:
        return f"[System Error]: Web search subsystem failed. Reason: {e}"