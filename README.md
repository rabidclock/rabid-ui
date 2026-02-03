# RabidUI 

A modular, multi-agent LLM frontend featuring advanced consensus systems and deep web-scraping capabilities.

## Key Features

- **Multi-Agent Consensus**: Orchestrate multiple local models (via Ollama) to collaborate or compete for the best answer.
- **The Retirement Lounge 🍵**: A graceful selection process where agents recognize excellence in their peers and recommend slightly less optimal responses for honorary retirement.
- **Judge & Jury ⚖️**: A hybrid mode where the Jury (the models in your squad) votes on the best answer, and a Judge (your selected master model) either upholds or overturns the verdict. Includes mistrial logic and retrials.
- **Smart Web Scraper 🕸️**: Powered by Playwright and Tesseract OCR. Bypasses common bot detection and extracts high-quality intelligence from the live web.
- **Contextual Search**: Uses LLMs to optimize your conversational queries into targeted search terms.
- **Admin Control Tower**: Live hardware monitoring (GPU/VRAM) and scraper database inspector.

##  Setup

1. **Clone & Install**:
   ```bash
   git clone <repository-url>
   cd rabid-ui
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure**:
   Copy `.env.example` to `.env` and fill in your GitHub OAuth credentials and SearXNG URL.

3. **Run**:
   ```bash
   streamlit run app.py
   ```

##  System Requirements

- **Backend**: Requires [Ollama](https://ollama.ai/) and [SearXNG](https://github.com/searxng/searxng).
- **GPU**: Optimized for NVIDIA RTX 3090 (24GB VRAM) for parallel model execution.
- **Scraper**: Integrated with `rabid-backend` for heavy-duty scraping.

---
Built for the "Chaos Barista" lifestyle.
