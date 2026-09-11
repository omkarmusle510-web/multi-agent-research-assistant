# Architecture Decision Records (ADRs)

This document records the architectural and engineering decisions made for the **Multi-Agent Research Assistant** across Layers 1 through 4.

---

## ADR-001: Strict Schema Enforcement via Pydantic v2 for Inter-Agent Contracts

### Context
In multi-agent systems, agents frequently exchange unstructured text or loosely typed JSON dictionaries. Without strict boundary contracts, downstream agents fail unpredictably when an upstream agent alters its keys, invents unexpected structures, or produces malformed payloads.

### Decision
Adopt **Pydantic v2** (`src/models.py`) as the single source of truth for all inter-agent data contracts:
- `SourceDocument`: Empirical evidence collected from the web with application-assigned IDs (`S1`, `S2`, ...).
- `SearchQuery`: Structured queries formulated during topic decomposition.
- `ResearchPacket`: Handed off from Research Agent to Analysis Agent.
- `Claim`, `Conflict`, `Finding`: Corroborated evidence structures.
- `AnalysisPacket`: Handed off from Analysis Agent to Report Agent.
- `ReportSection`, `FinalReport`: Synthesized dossier with pre-rendered Markdown and verified bibliography.
- `AgentEvent`: Structured telemetry emitted across all agent lifecycle steps.

### Consequences
- **Positive**: Compile-time and runtime validation; explicit field boundaries; direct mapping to LLM JSON schemas; serialization to clean dict/JSON; automated schema validation in test suites.
- **Trade-off**: LLM completions must be constrained to JSON mode (`json_mode=True`) and parsed strictly into these domain models with explicit error handlers.

---

## ADR-002: Zero-Fabrication Policy & Locked Providers (Groq + Tavily)

### Context
Typical prototypes frequently resort to mock fallbacks, synthetic search results, or bloated multi-provider abstraction layers (OpenAI, Anthropic, Gemini, Ollama, DuckDuckGo) that increase maintenance overhead and mask integration failures. In a research tool, silently returning mock or hallucinated data undermines user trust.

### Decision
1. **Lock Core Providers**: Exclusively use **Groq** (`qwen/qwen3.8-27b`) for high-speed inference and **Tavily** for live web search.
2. **Eliminate All Mock Fallbacks**: Completely remove offline simulation fallbacks, fake research generators, and fallback search backends.
3. **Fail-Fast Error Handling**: If credentials are missing or an API call fails, immediately raise an explicit `ValueError` or `RuntimeError`. Never fabricate research packets or silently proceed with synthetic data.

### Consequences
- **Positive**: Guarantees 100% genuine research outputs; prevents silent data corruption; eliminates provider abstraction bloat; delivers sub-second inference speeds via Groq LPU hardware.
- **Trade-off**: Active internet connectivity and valid `GROQ_API_KEY` and `TAVILY_API_KEY` credentials are mandatory for execution.

---

## ADR-003: Sequential Orchestration with Visible Handoffs & Preserved Event Stream

### Context
Agents in a multi-agent system should have clear separation of concerns. If agents call each other directly, tight coupling ensues, making tracing, debugging, and visualization difficult. Additionally, frontends need complete visibility into every intermediate transition.

### Decision
Implement a centralized coordinator pattern in `ResearchOrchestrator` (`src/orchestrator.py`):
1. **No Direct Agent-to-Agent Invocation**: Agents are completely isolated. The orchestrator receives `ResearchPacket` from `ResearchAgent`, validates it, passes it to `AnalysisAgent`, receives `AnalysisPacket`, and passes both to `ReportAgent`.
2. **Explicit Handoff Events**: Emits visible handoff events (`Handoff 1`, `Handoff 2`) capturing source counts, query counts, and finding metrics.
3. **Preserved 22-Stage Lifecycle**: Accumulates all `AgentEvent` objects in order and exposes them via `orchestrator.events` and the `PipelineResult` dataclass.
4. **Zero-LLM Orchestrator**: The orchestrator acts purely as a deterministic state machine and makes 0 LLM calls.

### Consequences
- **Positive**: Deterministic execution flow; clean dependency injection; seamless observability for both CLI and Streamlit; auditable trail of all agent actions.
- **Trade-off**: Orchestration is synchronous and sequential; parallel branch execution across multiple research agents is deferred to future milestones.

---

## ADR-004: Strict Citation Integrity & Application-Assigned Source IDs

### Context
LLMs frequently hallucinate citations, referencing non-existent URLs or citing source IDs (`[S99]`) that were never retrieved. In academic or executive research, every factual claim must trace back to a verifiable primary source.

### Decision
Enforce a comprehensive citation integrity pipeline:
1. **Deterministic Application-Assigned IDs**: The application logic in `WebSearchTool`, NOT the search engine and NOT the LLM, assigns sequential IDs (`S1`, `S2`, ...) upon URL deduplication.
2. **Analysis Agent Citation Stripping**: When parsing findings and conflicts, the Analysis Agent compares all cited IDs against the incoming `ResearchPacket`. Any invalid IDs are stripped; claims with 0 valid sources are pruned.
3. **Report Agent Validation**: The Report Agent validates section citation lists and scans the generated Markdown text for bracket citations (`[S1]`), verifying every reference against the original `ResearchPacket` bibliography.

### Consequences
- **Positive**: 100% citation grounding; eliminates citation hallucination; ensures every `[Sn]` footnote in the final report resolves to an active, real-world URL.
- **Trade-off**: Requires pre- and post-generation regex scanning and set-filtering logic in each agent.

---

## ADR-005: Strict API Budgeting & Token Bounding for Free-Tier Quotas

### Context
Free-tier LLM and search APIs impose restrictive rate limits (e.g., Groq on-demand free tier enforces 1,000 Output Tokens Per Minute (OTPM) and 30 Requests Per Minute). Unbounded generation prompts easily trigger `429 RateLimitError`.

### Decision
Enforce strict resource budgeting across the architecture:
1. **Fixed Call Budget**: Exactly **3 Groq LLM calls** per research pipeline (Research: 1, Analysis: 1, Report: 1; Orchestrator: 0).
2. **Bounded Search Retrieval**: Enforce `MAX_SEARCH_QUERIES=3` and `MAX_RESULTS_PER_QUERY=3` (maximum 9 deduplicated sources per topic).
3. **Token Capping**: Explicitly bind `max_tokens` on Groq calls (800 for Research Agent, 900 for Analysis Agent, 900 for Report Agent) to guarantee output stays within the 1,000 OTPM ceiling during sequential execution.
4. **Model Selection**: Standardize on `qwen/qwen3.8-27b` on Groq, providing high reasoning capability and full JSON mode support under standard quotas.

### Consequences
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
