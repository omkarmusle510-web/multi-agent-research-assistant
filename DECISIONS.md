# Architecture Decision Records (ADRs)

This document records the architectural and design decisions made for the Multi-Agent Research Assistant.
This document records the architectural and engineering decisions made for the **Multi-Agent Research Assistant** across Layers 1 through 4.

---

## ADR-001: Strict Schema Enforcement via Pydantic v2 for Inter-Agent Contracts

### Context
In multi-agent systems, agents frequently exchange unstructured text or loosely typed JSON dictionaries. Without strict boundary contracts, errors cascade downstream when an upstream agent changes its formatting or omits critical keys.
In multi-agent systems, agents frequently exchange unstructured text or loosely typed JSON dictionaries. Without strict boundary contracts, downstream agents fail unpredictably when an upstream agent alters its keys, invents unexpected structures, or produces malformed payloads.

### Decision
Adopt **Pydantic v2** (`src/models.py`) as the single source of truth for all data exchanges between agents:
- `ResearchPacket`: Emitted by Research Agent, ingested by Analysis Agent.
- `AnalysisPacket`: Emitted by Analysis Agent, ingested by Report Agent.
- `FinalReport`: Emitted by Report Agent, returned by Orchestrator.
Adopt **Pydantic v2** (`src/models.py`) as the single source of truth for all inter-agent data contracts:
- `SourceDocument`: Empirical evidence collected from the web with application-assigned IDs (`S1`, `S2`, ...).
- `SearchQuery`: Structured queries formulated during topic decomposition.
- `ResearchPacket`: Handed off from Research Agent to Analysis Agent.
- `Claim`, `Conflict`, `Finding`: Corroborated evidence structures.
- `AnalysisPacket`: Handed off from Analysis Agent to Report Agent.
- `ReportSection`, `FinalReport`: Synthesized dossier with pre-rendered Markdown and verified bibliography.
- `AgentEvent`: Structured telemetry emitted across all agent lifecycle steps.

### Consequences
- **Positive**: Compile-time and runtime validation; explicit fields (`claims`, `supporting_sources`, `conflicts`); automatic serialization to JSON and dict.
- **Trade-off**: Requires serialization/deserialization logic when agents interface with LLM outputs, handled cleanly with structured JSON prompts and parsing fallbacks.
- **Positive**: Compile-time and runtime validation; explicit field boundaries; direct mapping to LLM JSON schemas; serialization to clean dict/JSON; automated schema validation in test suites.
- **Trade-off**: LLM completions must be constrained to JSON mode (`json_mode=True`) and parsed strictly into these domain models with explicit error handlers.

---

## ADR-002: Dual-Mode Architecture (Live API + Intelligent Offline Mock Fallback)
## ADR-002: Zero-Fabrication Policy & Locked Providers (Groq + Tavily)

### Context
Developers, evaluators, and users reviewing or testing this repository may not possess an immediate paid OpenAI or Tavily API key, or may run tests in environments without internet access.
Typical prototypes frequently resort to mock fallbacks, synthetic search results, or bloated multi-provider abstraction layers (OpenAI, Anthropic, Gemini, Ollama, DuckDuckGo) that increase maintenance overhead and mask integration failures. In a research tool, silently returning mock or hallucinated data undermines user trust.

### Decision
Implement a **Dual-Mode System**:
1. **Live Mode**: Uses external LLM providers (OpenAI, Groq, Ollama) and live DuckDuckGo/Tavily search when configured.
2. **Mock / Simulation Mode**: Built-in intelligent rule-based engine that produces realistic, grounded topic breakdowns, empirical claims, conflict matrices, and citations matching the topic prompt.
1. **Lock Core Providers**: Exclusively use **Groq** (`qwen/qwen3.8-27b`) for high-speed inference and **Tavily** for live web search.
2. **Eliminate All Mock Fallbacks**: Completely remove offline simulation fallbacks, fake research generators, and fallback search backends.
3. **Fail-Fast Error Handling**: If credentials are missing or an API call fails, immediately raise an explicit `ValueError` or `RuntimeError`. Never fabricate research packets or silently proceed with synthetic data.

### Consequences
- **Positive**: The codebase works 100% out-of-the-box on first clone without any prerequisite configuration or API keys, while remaining fully upgradeable to live models by setting `.env`.
- **Trade-off**: Requires maintaining both live completion and mock generation branches in `src/llm.py` and `src/tools/web_search.py`.
- **Positive**: Guarantees 100% genuine research outputs; prevents silent data corruption; eliminates provider abstraction bloat; delivers sub-second inference speeds via Groq LPU hardware.
- **Trade-off**: Active internet connectivity and valid `GROQ_API_KEY` and `TAVILY_API_KEY` credentials are mandatory for execution.

---

## ADR-003: Sequential Orchestration with Event-Driven Progress Callbacks
## ADR-003: Sequential Orchestration with Visible Handoffs & Preserved Event Stream

### Context
Research workflows have distinct dependent stages (gathering must precede cross-examination, which must precede dossier drafting). Users on CLI or Web UIs need live visibility into agent actions rather than staring at a frozen screen during multi-step runs.
Agents in a multi-agent system should have clear separation of concerns. If agents call each other directly, tight coupling ensues, making tracing, debugging, and visualization difficult. Additionally, frontends need complete visibility into every intermediate transition.

### Decision
Use a **Synchronous Sequential Pipeline** managed by `ResearchOrchestrator`, augmented with an event callback pattern (`Callable[[AgentEvent], None]`):
- Pipeline: `Research Agent` ➔ `Analysis Agent` ➔ `Report Agent`.
- Callbacks emit `AgentEvent` objects containing current step, agent name, status, message, and preview payloads.
Implement a centralized coordinator pattern in `ResearchOrchestrator` (`src/orchestrator.py`):
1. **No Direct Agent-to-Agent Invocation**: Agents are completely isolated. The orchestrator receives `ResearchPacket` from `ResearchAgent`, validates it, passes it to `AnalysisAgent`, receives `AnalysisPacket`, and passes both to `ReportAgent`.
2. **Explicit Handoff Events**: Emits visible handoff events (`Handoff 1`, `Handoff 2`) capturing source counts, query counts, and finding metrics.
3. **Preserved 22-Stage Lifecycle**: Accumulates all `AgentEvent` objects in order and exposes them via `orchestrator.events` and the `PipelineResult` dataclass.
4. **Zero-LLM Orchestrator**: The orchestrator acts purely as a deterministic state machine and makes 0 LLM calls.

### Consequences
- **Positive**: Deterministic execution flow; simplified debugging; rich real-time visual progress bars and status updates in both CLI and Streamlit without heavy asynchronous queue infrastructure.
- **Trade-off**: The current implementation runs sequentially rather than parallelizing multi-query searches, which is planned for future optimization.
- **Positive**: Deterministic execution flow; clean dependency injection; seamless observability for both CLI and Streamlit; auditable trail of all agent actions.
- **Trade-off**: Orchestration is synchronous and sequential; parallel branch execution across multiple research agents is deferred to future milestones.

---

## ADR-004: Direct Search Tooling with Resilient HTTP/DDG Fallbacks
## ADR-004: Strict Citation Integrity & Application-Assigned Source IDs

### Context
Commercial search APIs (e.g. SerpAPI, Tavily) require credit card registration or subscription quotas. Relying solely on a paid search API would break out-of-the-box usability.
LLMs frequently hallucinate citations, referencing non-existent URLs or citing source IDs (`[S99]`) that were never retrieved. In academic or executive research, every factual claim must trace back to a verifiable primary source.

### Decision
Structure `WebSearchTool` with a prioritized 3-tier retrieval strategy:
1. Tavily API (if `TAVILY_API_KEY` configured).
2. DuckDuckGo (via `duckduckgo_search` library or direct HTTP scraper with `requests` and `BeautifulSoup4`).
3. Topic-grounded simulation fallback if offline or rate-limited.
Enforce a comprehensive citation integrity pipeline:
1. **Deterministic Application-Assigned IDs**: The application logic in `WebSearchTool`, NOT the search engine and NOT the LLM, assigns sequential IDs (`S1`, `S2`, ...) upon URL deduplication.
2. **Analysis Agent Citation Stripping**: When parsing findings and conflicts, the Analysis Agent compares all cited IDs against the incoming `ResearchPacket`. Any invalid IDs are stripped; claims with 0 valid sources are pruned.
3. **Report Agent Validation**: The Report Agent validates section citation lists and scans the generated Markdown text for bracket citations (`[S1]`), verifying every reference against the original `ResearchPacket` bibliography.

### Consequences
- **Positive**: Free, unlimited web search capability by default, with automatic graceful degradation.
- **Trade-off**: HTML search scraping is subject to rate-limiting if abused; the simulation fallback guarantees resilience.
- **Positive**: 100% citation grounding; eliminates citation hallucination; ensures every `[Sn]` footnote in the final report resolves to an active, real-world URL.
- **Trade-off**: Requires pre- and post-generation regex scanning and set-filtering logic in each agent.

---

## ADR-005: Streamlit Web UI with Intermediate Artifact Inspection Tabs
## ADR-005: Strict API Budgeting & Token Bounding for Free-Tier Quotas

### Context
Users evaluating a multi-agent system need to verify that each agent performed its designated role rather than viewing a single monolithic response.
Free-tier LLM and search APIs impose restrictive rate limits (e.g., Groq on-demand free tier enforces 1,000 Output Tokens Per Minute (OTPM) and 30 Requests Per Minute). Unbounded generation prompts easily trigger `429 RateLimitError`.

### Decision
Build the web UI using **Streamlit** (`src/ui/app.py`) featuring dedicated inspection tabs:
1. **Final Dossier**: Markdown report with citations.
2. **Analysis & Conflict Matrix**: Claims with confidence badges and side-by-side controversy comparisons.
3. **Gathered Sources & Queries**: Decomposed queries and URLs with relevance ratings.
4. **Raw Structured JSON**: Full Pydantic packet schemas for technical auditing.
Enforce strict resource budgeting across the architecture:
1. **Fixed Call Budget**: Exactly **3 Groq LLM calls** per research pipeline (Research: 1, Analysis: 1, Report: 1; Orchestrator: 0).
2. **Bounded Search Retrieval**: Enforce `MAX_SEARCH_QUERIES=3` and `MAX_RESULTS_PER_QUERY=3` (maximum 9 deduplicated sources per topic).
3. **Token Capping**: Explicitly bind `max_tokens` on Groq calls (800 for Research Agent, 900 for Analysis Agent, 900 for Report Agent) to guarantee output stays within the 1,000 OTPM ceiling during sequential execution.
4. **Model Selection**: Standardize on `qwen/qwen3.8-27b` on Groq, providing high reasoning capability and full JSON mode support under standard quotas.

### Consequences
- **Positive**: Total transparency into inter-agent handoffs; non-technical users can interact effortlessly via preset topics and download buttons.
- **Trade-off**: Streamlit redraws script on interaction; managed efficiently via `st.session_state`.
- **Positive**: Eliminates run-away API costs; prevents rate-limit aborts during consecutive agent execution; predictable execution latency.
- **Trade-off**: Prompts must be concise and tightly structured so JSON outputs fit comfortably within 800–900 tokens.

---

## ADR-006: Dedicated Web Dashboard & Real-Time Stepper UI via Streamlit

### Context
Evaluators and end users need to inspect intermediate agent reasoning rather than just the final text document. They need to verify that evidence was gathered from real sources, claims were corroborated, and conflicts were analyzed.

### Decision
Build a Streamlit web dashboard (`src/ui/app.py`) featuring:
1. **Real-time Lifecycle Stepper**: Subscribes to `AgentEvent` callbacks to render a live progress stepper showing active agent states.
2. **Multi-Tab Inspection**:
   - Tab 1: **Final Research Dossier** (rendered Markdown with inline citations).
   - Tab 2: **Analysis & Claims Matrix** (thematic findings, confidence badges, conflict disputes).
   - Tab 3: **Evidence & Sources** (gathered URLs, snippets, and relevance scores).
   - Tab 4: **Telemetry & Audit Trail** (full chronological event stream with JSON payload inspection).

### Consequences
- **Positive**: Complete transparency into multi-agent operations; compelling live demo experience; easy export of final research dossiers.
- **Trade-off**: Requires managing Streamlit session state across re-renders during pipeline execution.
