import httpx
from bs4 import BeautifulSoup

def fetch_and_distill(url, timeout=5):
    """
    Grabs HTML, strips the junk (scripts, styles, nav), and returns clean text.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        # 1. The Grab
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()

        # 2. The Parse
        soup = BeautifulSoup(resp.text, "html.parser")

        # 3. The Purge (Remove noise)
        for element in soup(["script", "style", "nav", "footer", "header", "form", "svg"]):
            element.decompose()  # Nuke it from orbit

        # 4. The Distill
        # get_text with separator='\n' preserves paragraph structure, which LLMs need.
        text = soup.get_text(separator="\n", strip=True)
        
        # 5. The Budget Control (Optional but recommended)
        # Limit to ~2000 words (approx 8-10k characters) to save tokens
        return text[:10000] 

    except Exception as e:
        return f"[System Error: Failed to scrape {url} - {e}]"
