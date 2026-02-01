import requests
import random

SEARXNG_URL = "http://127.0.0.1:4000/search"

def search(query):
    """Fetches broad search results (up to 15) for context sharding."""
    try:
        params = {"q": query, "format": "json", "engines": "bing,duckduckgo"}
        res = requests.get(SEARXNG_URL, params=params).json()
        return res.get('results', [])
    except Exception:
        return []

def get_sharded_context(search_pool, seed, limit=4):
    """
    Deterministically shuffles and selects a subset of search results 
    based on the agent's seed.
    """
    if not search_pool:
        return "", ""
        
    # Create a local copy to shuffle
    shuffled = search_pool.copy()
    
    # Deterministic shuffle
    random.seed(seed)
    random.shuffle(shuffled)
    
    # Select subset
    selection = shuffled[:limit]
    
    # Format for LLM
    context_str = "\n".join([f"[{r.get('title')}]({r.get('url')}): {r.get('content')}" for r in selection])
    
    # Format for Log/Display
    source_summary = ", ".join([r.get('domain', r.get('url'))[:20] for r in selection])
    
    return context_str, source_summary
