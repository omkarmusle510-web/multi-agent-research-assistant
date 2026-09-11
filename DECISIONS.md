# Architecture Decision Records (ADRs)

This document records the architectural and design decisions made for the Multi-Agent Research Assistant.

---

## ADR-001: Strict Schema Enforcement via Pydantic v2 for Inter-Agent Contracts

### Context
In multi-agent systems, agents frequently exchange unstructured text or loosely typed JSON dictionaries. Without strict boundary contracts, errors cascade downstream when an upstream agent changes its formatting or omits critical keys.

### Decision
Adopt **Pydantic v2** (`src/models.py`) as the single source of truth for all data exchanges between agents:
- `ResearchPacket`: Emitted by Research Agent, ingested by Analysis Agent.
- `AnalysisPacket`: Emitted by Analysis Agent, ingested by Report Agent.
- `FinalReport`: Emitted by Report Agent, returned by Orchestrator.

### Consequences
- **Positive**: Compile-time and runtime validation; explicit fields (`claims`, `supporting_sources`, `conflicts`); automatic serialization to JSON and dict.
- **Trade-off**: Requires serialization/deserialization logic when agents interface with LLM outputs, handled cleanly with structured JSON prompts and parsing fallbacks.

---

## ADR-002: Dual-Mode Architecture (Live API + Intelligent Offline Mock Fallback)

### Context
Developers, evaluators, and users reviewing or testing this repository may not possess an immediate paid OpenAI or Tavily API key, or may run tests in environments without internet access.

### Decision
Implement a **Dual-Mode System**:
1. **Live Mode**: Uses external LLM providers (OpenAI, Groq, Ollama) and live DuckDuckGo/Tavily search when configured.
2. **Mock / Simulation Mode**: Built-in intelligent rule-based engine that produces realistic, grounded topic breakdowns, empirical claims, conflict matrices, and citations matching the topic prompt.

### Consequences
- **Positive**: The codebase works 100% out-of-the-box on first clone without any prerequisite configuration or API keys, while remaining fully upgradeable to live models by setting `.env`.
- **Trade-off**: Requires maintaining both live completion and mock generation branches in `src/llm.py` and `src/tools/web_search.py`.

---

## ADR-003: Sequential Orchestration with Event-Driven Progress Callbacks

### Context
Research workflows have distinct dependent stages (gathering must precede cross-examination, which must precede dossier drafting). Users on CLI or Web UIs need live visibility into agent actions rather than staring at a frozen screen during multi-step runs.

### Decision
Use a **Synchronous Sequential Pipeline** managed by `ResearchOrchestrator`, augmented with an event callback pattern (`Callable[[AgentEvent], None]`):
- Pipeline: `Research Agent` ➔ `Analysis Agent` ➔ `Report Agent`.
- Callbacks emit `AgentEvent` objects containing current step, agent name, status, message, and preview payloads.

### Consequences
- **Positive**: Deterministic execution flow; simplified debugging; rich real-time visual progress bars and status updates in both CLI and Streamlit without heavy asynchronous queue infrastructure.
- **Trade-off**: The current implementation runs sequentially rather than parallelizing multi-query searches, which is planned for future optimization.

---

## ADR-004: Direct Search Tooling with Resilient HTTP/DDG Fallbacks

### Context
Commercial search APIs (e.g. SerpAPI, Tavily) require credit card registration or subscription quotas. Relying solely on a paid search API would break out-of-the-box usability.

### Decision
Structure `WebSearchTool` with a prioritized 3-tier retrieval strategy:
1. Tavily API (if `TAVILY_API_KEY` configured).
2. DuckDuckGo (via `duckduckgo_search` library or direct HTTP scraper with `requests` and `BeautifulSoup4`).
3. Topic-grounded simulation fallback if offline or rate-limited.

### Consequences
- **Positive**: Free, unlimited web search capability by default, with automatic graceful degradation.
- **Trade-off**: HTML search scraping is subject to rate-limiting if abused; the simulation fallback guarantees resilience.

---

## ADR-005: Streamlit Web UI with Intermediate Artifact Inspection Tabs

### Context
Users evaluating a multi-agent system need to verify that each agent performed its designated role rather than viewing a single monolithic response.

### Decision
Build the web UI using **Streamlit** (`src/ui/app.py`) featuring dedicated inspection tabs:
1. **Final Dossier**: Markdown report with citations.
2. **Analysis & Conflict Matrix**: Claims with confidence badges and side-by-side controversy comparisons.
3. **Gathered Sources & Queries**: Decomposed queries and URLs with relevance ratings.
4. **Raw Structured JSON**: Full Pydantic packet schemas for technical auditing.

### Consequences
- **Positive**: Total transparency into inter-agent handoffs; non-technical users can interact effortlessly via preset topics and download buttons.
- **Trade-off**: Streamlit redraws script on interaction; managed efficiently via `st.session_state`.

