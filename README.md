# Multi-Agent Research Assistant

An autonomous multi-agent intelligence platform that decomposes research questions, gathers and validates multi-source web evidence, detects claims and contradictions, and compiles executive-ready research dossiers with citations.

---

## 🌟 Architecture Overview

Built according to the 3-agent pipeline:

```
                      USER / CLI / UI
                            │
                            ▼
                     ┌─────────────┐
                     │ ORCHESTRATOR│
                     └──────┬──────┘
                            │
                     research topic
                            │
                            ▼
               ┌────────────────────────┐
               │  1. RESEARCH AGENT     │
               │                        │
               │ • break topic down     │
               │ • generate queries     │
               │ • web search           │
               │ • collect sources      │
               └───────────┬────────────┘
                           │
                     ResearchPacket
                           │
                           ▼
               ┌────────────────────────┐
               │  2. ANALYSIS AGENT     │
               │                        │
               │ • compare sources      │
               │ • identify findings     │
               │ • detect conflicts     │
               │ • assess evidence      │
               └───────────┬────────────┘
                           │
                     AnalysisPacket
                           │
                           ▼
               ┌────────────────────────┐
               │  3. REPORT AGENT       │
               │                        │
               │ • synthesize findings  │
               │ • executive summary    │
               │ • key findings         │
               │ • evidence/citations   │
               │ • conclusion           │
               └───────────┬────────────┘
                           │
                           ▼
                     FINAL REPORT
```

---

## 🚀 Quick Start

### 1. Installation
```powershell
pip install -r requirements.txt
```

### 2. Run Instant CLI Demo (Offline / Mock Mode)
No API keys required to test! The assistant includes a built-in reasoning engine for immediate evaluation:
```powershell
python src/main.py --topic "Solid-State Batteries vs Lithium-Ion" --mock
```

### 3. Run Interactive Web Dashboard (Streamlit)
```powershell
streamlit run src/ui/app.py
```

### 4. Run with Live LLMs (OpenAI, Groq, or Ollama)
Copy `.env.example` to `.env` and provide your API key:
```powershell
copy .env.example .env
```
Edit `.env`:
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o-mini
SEARCH_PROVIDER=duckduckgo
```
Then run:
```powershell
python src/main.py "Quantum Computing in Drug Discovery"
```

---

## 📁 Repository Structure

```
multi-agent-research-assistant/
├── ARCHITECTURE.md          # Complete architectural specification & diagrams
├── DECISIONS.md             # Architecture Decision Records (ADRs)
├── DEMO_SCRIPT.md           # Step-by-step evaluation & demo instructions
├── PROJECT_CONTEXT.md       # High-level pipeline context
├── README.md                # Main repository documentation
├── TASKS.md                 # Development milestones & task checklist
├── requirements.txt         # Pinned Python package dependencies
├── .env.example             # Template for API keys & settings
├── src/
│   ├── main.py              # Command-Line Interface (CLI)
│   ├── config.py            # Environment & application settings
│   ├── models.py            # Pydantic v2 data contracts & schemas
│   ├── orchestrator.py      # Master workflow coordinator
│   ├── llm.py               # Unified LLM provider & offline fallback
│   ├── agents/
│   │   ├── research_agent.py# Topic decomposition & source collection
│   │   ├── analysis_agent.py# Claim extraction & conflict matrix
│   │   └── report_agent.py  # Executive dossier synthesis & citations
│   ├── tools/
│   │   └── web_search.py    # DuckDuckGo, Tavily & scraping utilities
│   └── ui/
│       └── app.py           # Streamlit dashboard with real-time stepper
└── reports/                 # Auto-generated markdown research dossiers
```

---

## 📄 License
MIT License

