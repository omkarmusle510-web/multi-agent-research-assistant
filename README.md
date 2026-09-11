# Multi-Agent Research Assistant

An autonomous, multi-agent intelligence platform that conducts rigorous, grounded web research. Rather than relying on a single-shot chatbot prompt, this system orchestrates three specialized AI agents to decompose questions, gather live empirical evidence, cross-examine claims and controversies, and synthesize publication-ready research dossiers with verified citations.

---

## 🌟 Key Capabilities

- **True Multi-Agent Architecture**: Dedicated **Evidence Collector** (Research Agent), **Evidence Examiner** (Analysis Agent), and **Evidence Synthesizer** (Report Agent). Agents never call each other directly; the Orchestrator governs all handoffs.
- **Zero Fabricated Research**: All factual assertions are anchored to live web pages indexed via Tavily. The pipeline enforces a strict **Zero-Hallucination Citation Policy**: agents validate citations against actual collected source IDs and strip ungrounded references.
- **Strict API Budget**: Engineered for hackathons and production cost-efficiency:
  - **Exactly 3 Groq LLM calls** per complete research run (1 per agent; 0 for the orchestrator).
  - **Bounded Web Search**: Maximum 3 targeted queries × 3 results per query (max 9 deduplicated sources).
  - **Token Bounded**: Configured with `max_tokens` limits (800–900) to respect free-tier Output Tokens Per Minute (OTPM) constraints.
- **Visible Handoffs & 22-Stage Event Stream**: Every state transition, decomposition step, search query, claim extraction, and handoff emits typed `AgentEvent` objects for real-time UI/CLI progress tracking.
- **Full Dossier Markdown Output**: Generates complete reports with an Executive Summary, thematic analysis sections, inline bracket citations (`[S1]`, `[S2]`), conflict analysis, conclusions, strategic recommendations, and a complete bibliography.

---

## 🏗️ Architecture & Pipeline Flow

```
                      USER / CLI / STREAMLIT UI
                                │
                                ▼
                   ┌─────────────────────────┐
                   │  RESEARCH ORCHESTRATOR  │
                   └────────────┬────────────┘
                                │
                         Research Topic
                                │
                                ▼
                   ┌─────────────────────────┐
                   │   1. RESEARCH AGENT     │
                   │   (Evidence Collector)  │
                   │                         │
                   │ • Decompose subtopics   │
                   │ • Formulate 3 queries   │──► [Tavily Web Search]
                   │ • Deduplicate URLs      │         │
                   │ • Assign IDs (S1..Sn)   │◄────────┘
                   └────────────┬────────────┘
                                │
                         ResearchPacket
                                │
                  [HANDOFF 1: Visible Transition]
                                │
                                ▼
                   ┌─────────────────────────┐
                   │   2. ANALYSIS AGENT     │
                   │   (Evidence Examiner)   │
                   │                         │
                   │ • Cross-examine sources │
                   │ • Extract claims & data │
                   │ • Identify consensus    │
                   │ • Detect conflicts      │
                   │ • Validate source IDs   │
                   └────────────┬────────────┘
                                │
                         AnalysisPacket
                                │
                  [HANDOFF 2: Visible Transition]
                                │
                                ▼
                   ┌─────────────────────────┐
                   │    3. REPORT AGENT      │
                   │  (Evidence Synthesizer) │
                   │                         │
                   │ • Executive Summary     │
                   │ • Thematic sections     │
                   │ • Inline [Sn] citations │
                   │ • Recommendations       │
                   │ • Pre-render Markdown   │
                   └────────────┬────────────┘
                                │
                           FinalReport
                                │
                                ▼
                   ┌─────────────────────────┐
                   │  ORCHESTRATOR COMPLETE  │
                   │  • Markdown Dossier     │
                   │  • 22-Event Audit Trail │
                   │  • PipelineResult State │
                   └─────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Prerequisites & Installation

- Python 3.10+
- Groq API Key ([console.groq.com](https://console.groq.com))
- Tavily API Key ([tavily.com](https://tavily.com))

Clone the repository and install dependencies:

```powershell
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `.env.example` to `.env` and insert your credentials:

```powershell
copy .env.example .env
```

Edit `.env`:

```env
# Groq LLM Configuration (Default: qwen/qwen3.8-27b)
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=qwen/qwen3.8-27b

# Tavily Web Search Configuration
TAVILY_API_KEY=tvly-your_tavily_api_key_here

# Execution Constraints
MAX_SEARCH_QUERIES=3
MAX_RESULTS_PER_QUERY=3
OUTPUT_DIR=reports
LOG_LEVEL=INFO
```

### 3. Run via CLI

Execute an autonomous research run directly from your terminal:

```powershell
python src/main.py "Quantum computing applications in drug discovery"
```

To output raw structured JSON for automated pipelines:

```powershell
python src/main.py "Solid-state batteries vs lithium-ion" --json
```

Reports are automatically saved as formatted Markdown files in the `reports/` directory.

### 4. Run Interactive Web Dashboard (Streamlit)

Launch the real-time UI with live stepper events and artifact inspection tabs:

```powershell
streamlit run src/ui/app.py
```

---

## 🧪 Validation & Test Suite

The system includes test suites for all 4 architectural layers:

```powershell
# Layer 1: Pydantic v2 Data Contracts & Handoff Schemas
python -m tests.test_layer1_contracts

# Layer 2: Real Groq LLM & Tavily Search Integration
python -m tests.test_layer2_intelligence

# Layer 3: Three Specialized Agents & Citation Integrity
python -m tests.test_layer3_agents

# Layer 4: Orchestration, Visible Handoffs & 22-Stage Lifecycle
python -m tests.test_layer4_orchestration
```

---

## 📁 Repository Structure

```
multi-agent-research-assistant/
├── ARCHITECTURE.md          # Complete system architecture and data contract specs
├── DECISIONS.md             # Architecture Decision Records (ADRs)
├── DEMO_SCRIPT.md           # Step-by-step hackathon presentation & demo guide
├── PROJECT_CONTEXT.md       # High-level product summary & requirements
├── README.md                # Main repository guide
├── TASKS.md                 # Development milestones & layer checklist
├── requirements.txt         # Pinned Python package dependencies
├── .env.example             # Environment configuration template
│
├── src/
│   ├── config.py            # Settings singleton & credential validation
│   ├── models.py            # Pydantic v2 data contracts (Source, Packets, FinalReport)
│   ├── llm.py               # Groq LLM client (JSON mode, error handling, token limits)
│   ├── orchestrator.py      # ResearchOrchestrator, PipelineResult & event streaming
│   ├── main.py              # CLI entry point with colored event formatting
│   ├── agents/
│   │   ├── research_agent.py# Evidence Collector (topic decomposition + Tavily search)
│   │   ├── analysis_agent.py# Evidence Examiner (cross-source claims + conflict matrix)
│   │   └── report_agent.py  # Evidence Synthesizer (dossier drafting + citation audit)
│   ├── tools/
│   │   └── web_search.py    # Tavily client wrapper (URL dedup, S1..Sn indexing)
│   └── ui/
│       └── app.py           # Streamlit web dashboard with real-time lifecycle stepper
│
├── tests/
│   ├── test_layer1_contracts.py      # Tests domain schemas and model handoffs
│   ├── test_layer2_intelligence.py   # Tests Groq & Tavily live API integration
│   ├── test_layer3_agents.py         # Tests agent behaviors & citation validation
│   └── test_layer4_orchestration.py  # Tests end-to-end orchestrator & 22-event flow
│
└── reports/                 # Auto-generated Markdown research dossiers
```

---

## 🔒 Security & Data Integrity

- **No Mock Fallbacks**: Unlike basic demos, this system will never silently substitute hallucinated fake research if an API key is missing or invalid; it raises explicit, traceable exceptions.
- **Source ID Pinning**: Source IDs (`S1`, `S2`, ...) are assigned deterministically by the application logic upon URL deduplication, preventing the LLM from inventing arbitrary references.
- **Citation Stripping**: The Analysis and Report agents actively inspect generated references and prune any citations that do not map to real documents in the `ResearchPacket`.

---

## 📄 License

MIT License.
