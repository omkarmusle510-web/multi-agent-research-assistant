# System Architecture: Multi-Agent Research Assistant

This document outlines the architectural design, agent interaction protocols, data contracts, and implementation specifications for the **Multi-Agent Research Assistant**.
This document outlines the architectural specifications, agent interaction protocols, data contracts, and citation validation mechanics for the **Multi-Agent Research Assistant**.

---

## 1. System Overview

The Multi-Agent Research Assistant is an autonomous, multi-agent intelligence platform designed to decompose complex inquiry topics, execute multi-source external web investigations, rigorously cross-examine claims and contradictions, and synthesize publication-ready research dossiers with inline citations.
The Multi-Agent Research Assistant is an autonomous multi-agent intelligence platform designed to transform an open-ended research question into an executive-ready, citation-backed research dossier. 

Rather than relying on a single monolithic LLM prompt, the system segregates responsibilities across three isolated agents governed by a centralized Orchestrator:
- **Research Agent**: Evidence Collector (Topic decomposition & live web search).
- **Analysis Agent**: Evidence Examiner (Claim corroboration, conflict detection & citation validation).
- **Report Agent**: Evidence Synthesizer (Executive brief, narrative sections & dossier compilation).

### Core Architectural Principles
1. **Zero Fabrication**: No synthetic search results or mock fallbacks. If an API key or query fails, the pipeline aborts cleanly with explicit errors.
2. **Strict Provider Specialization**: Locked to **Groq** (`qwen/qwen3.8-27b`) for sub-second inference and **Tavily** for focused web search.
3. **Rigid Inter-Agent Contracts**: Typed Pydantic v2 schemas govern every boundary.
4. **Deterministic Orchestration**: Agents never communicate directly; the Orchestrator owns all transitions and telemetry.
5. **Fixed Resource Budget**: Exactly 3 Groq calls per pipeline run and bounded Tavily queries (max 3 queries × 3 results).

---

## 2. End-to-End Orchestrated Pipeline Flow

```mermaid
flowchart TD
    User([User / UI / CLI]) -->|Topic Request| Orchestrator[Research Orchestrator]
    
    subgraph Pipeline [Multi-Agent Execution Pipeline]
        Orchestrator -->|1. Topic| ResearchAgent[1. Research Agent]
        ResearchAgent -->|Decompose Topic & Formulate Queries| SearchTool[Web Search Tool]
        SearchTool -->|DuckDuckGo / Tavily / Scraping| Web[(Live Web / Sources)]
        Web -->|Raw Source Documents| SearchTool
        SearchTool -->|Curated Sources S1..Sn| ResearchAgent
        
        ResearchAgent -->|ResearchPacket| AnalysisAgent[2. Analysis Agent]
        
        AnalysisAgent -->|Cross-examine Sources & Detect Conflicts| AnalysisAgent
        AnalysisAgent -->|AnalysisPacket| ReportAgent[3. Report Agent]
        
        ReportAgent -->|Synthesize Dossier & Bracket Citations| ReportAgent
sequenceDiagram
    autonumber
    actor User as User / UI
    participant Orch as Research Orchestrator
    participant RA as 1. Research Agent
    participant Tavily as Tavily Web Search
    participant AA as 2. Analysis Agent
    participant RepA as 3. Report Agent

    User->>Orch: run(topic)
    Note over Orch: Emit: Pipeline Started<br/>Stage 1: Dispatch to Research Agent

    Orch->>RA: run(topic)
    Note over RA: Emit: Started<br/>Emit: Planning
    RA->>RA: Groq Call #1 (Decomposition into 3 queries)
    Note over RA: Emit: Planning Complete

    loop For each bounded query (Max 3)
        RA->>Tavily: search(query, max_results=3)
        Tavily-->>RA: Raw web results
    end
    Note over RA: URL Deduplication & Indexing S1..Sn<br/>Emit: Searching & Indexing<br/>Emit: Completed
    RA-->>Orch: ResearchPacket (Sources, Queries, Summary)

    ReportAgent -->|FinalReport| Orchestrator
    Orchestrator -->|Event Stream / Dossier| User
    Note over Orch: Emit: Handoff 1 (ResearchPacket -> Analysis)
    Orch->>AA: run(research_packet)
    Note over AA: Emit: Started<br/>Emit: Preparing Context<br/>Emit: Analyzing
    AA->>AA: Groq Call #2 (Claims, Consensus & Conflicts)
    Note over AA: Validate & strip invalid source IDs<br/>Emit: Validating Citations<br/>Emit: Completed
    AA-->>Orch: AnalysisPacket (Findings, Conflicts, Takeaways)

    Note over Orch: Emit: Handoff 2 (AnalysisPacket + ResearchPacket -> Report)
    Orch->>RepA: run(analysis_packet, research_packet)
    Note over RepA: Emit: Started<br/>Emit: Building Context<br/>Emit: Synthesizing
    RepA->>RepA: Groq Call #3 (Executive Summary, Sections & Recs)
    Note over RepA: Validate section citations & [Sn] refs<br/>Emit: Validating Citations<br/>Emit: Completed
    RepA-->>Orch: FinalReport (Markdown, Sections, Bibliography)

    Note over Orch: Save Markdown to reports/<br/>Emit: Report Produced<br/>Emit: Pipeline Complete
    Orch-->>User: FinalReport / PipelineResult
```

---

## 2. Agent Responsibilities & Protocols
## 3. The 22-Stage Event Stream & Visible Handoffs

### A. Orchestrator (`src/orchestrator.py`)
- **Role**: Coordinates pipeline progression, manages intermediate states, logs progress, and emits event callbacks for UI streaming.
- **Inputs**: User research prompt (`str`), execution parameters (`save_output`, `output_path`).
- **Outputs**: `FinalReport` object and saved Markdown dossier on disk (`./reports/`).
- **Guarantees**: Enforces sequential integrity: ensures `ResearchPacket` is validated before triggering `Analysis Agent`, and validates `AnalysisPacket` before invoking `Report Agent`.
The Orchestrator and agents record every execution phase into an ordered list of typed `AgentEvent` objects. A standard complete run produces the following 22-stage event stream:

### B. 1. Research Agent (`src/agents/research_agent.py`)
- **Role**: Dissects abstract queries into actionable investigative angles and retrieves corroborating sources.
- **Key Tasks**:
  1. Breaks the query into 3–4 thematic dimensions (Technical foundations, Market adoption, Regulatory challenges, Future outlook).
  2. Formulates precise search queries for each dimension.
  3. Queries external web backends via `WebSearchTool`.
  4. Deduplicates URLs, scores source relevance, and assigns deterministic source identifiers (`[S1]`, `[S2]`, ...).
- **Data Contract Produced**: `ResearchPacket`.
| # | Emitter | Step Name | Status | Purpose / Description |
|---|---|---|---|---|
| **1** | Orchestrator | Pipeline Started | `started` | Pipeline initialized with user research topic |
| **2** | Orchestrator | Stage 1 | `running` | Dispatching topic to Research Agent |
| **3** | Research Agent | Started | `started` | Evidence collector activated |
| **4** | Research Agent | Planning | `running` | Groq Call #1: Decomposing topic into subtopics & queries |
| **5** | Research Agent | Planning Complete | `running` | 3 targeted queries formulated |
| **6** | Research Agent | Searching | `running` | Executing live searches via Tavily (max 3x3) |
| **7** | Research Agent | Indexing | `running` | Deduplicating URLs and assigning sequential IDs (`S1`..`Sn`) |
| **8** | Research Agent | Completed | `completed` | ResearchPacket compiled with real sources |
| **9** | Orchestrator | Handoff 1 | `running` | **Visible Handoff**: ResearchPacket passed to Analysis Agent |
| **10** | Analysis Agent | Started | `started` | Evidence examiner activated |
| **11** | Analysis Agent | Preparing Context | `running` | Formatting source snippets for LLM input |
| **12** | Analysis Agent | Analyzing | `running` | Groq Call #2: Cross-source examination & claim extraction |
| **13** | Analysis Agent | Validating Citations | `running` | Verifying cited source IDs exist in ResearchPacket |
| **14** | Analysis Agent | Completed | `completed` | AnalysisPacket compiled with validated findings & conflicts |
| **15** | Orchestrator | Handoff 2 | `running` | **Visible Handoff**: Analysis + Research packets passed to Report Agent |
| **16** | Report Agent | Started | `started` | Evidence synthesizer activated |
| **17** | Report Agent | Building Context | `running` | Organizing findings, conflicts & source references |
| **18** | Report Agent | Synthesizing | `running` | Groq Call #3: Drafting summary, narrative sections & recs |
| **19** | Report Agent | Validating Citations | `running` | Validating section citations and `[Sn]` brackets in prose |
| **20** | Report Agent | Completed | `completed` | FinalReport compiled and Markdown rendered |
| **21** | Orchestrator | Report Produced | `running` | Validating dossier metrics & persisting to disk |
| **22** | Orchestrator | Pipeline Complete | `completed` | Full workflow finished successfully |

### C. 2. Analysis Agent (`src/agents/analysis_agent.py`)
- **Role**: Cross-references raw sources to extract substantiated claims, grade confidence, and identify opposing viewpoints.
- **Key Tasks**:
  1. Corroborates claims across multiple sources.
  2. Detects explicit conflicts or disputed projections (e.g., rapid commercialization timelines vs regulatory stagnation).
  3. Evaluates evidence quality and assigns confidence levels (`High`, `Medium`, `Low`).
  4. Formulates core strategic takeaways.
- **Data Contract Produced**: `AnalysisPacket`.
---

### D. 3. Report Agent (`src/agents/report_agent.py`)
- **Role**: Synthesizes verified findings and source bibliographies into an executive research dossier.
- **Key Tasks**:
  1. Drafts a high-impact Executive Summary.
  2. Generates thematic analysis sections incorporating bracket citations (e.g., `[S1]`, `[S2]`).
  3. Compiles a Conflict & Controversy matrix with neutral evaluations.
  4. Formulates actionable strategic recommendations and conclusions.
  5. Assembles a complete bibliography mapping each source ID to title, URL, snippet, and relevance rating.
- **Data Contract Produced**: `FinalReport`.
## 4. Agent Specialization & Boundaries

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            RESEARCH AGENT                                   │
│                        Role: Evidence Collector                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ • Ingests: Research topic string                                            │
│ • LLM Calls: Exactly 1 (Groq JSON mode, max_tokens=800)                     │
│ • External I/O: Tavily Search API (max 3 queries × 3 results)               │
│ • Responsibilities:                                                         │
│   - Topic decomposition into 3 inquiry angles                               │
│   - URL deduplication across searches                                       │
│   - Sequential source indexing (S1, S2, ...)                                │
│ • Boundary Guarantee: Does NOT analyze or synthesize findings               │
│ • Produces: ResearchPacket                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ANALYSIS AGENT                                   │
│                         Role: Evidence Examiner                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ • Ingests: ResearchPacket                                                   │
│ • LLM Calls: Exactly 1 (Groq JSON mode, max_tokens=900)                     │
│ • External I/O: None (operates strictly on collected evidence)              │
│ • Responsibilities:                                                         │
│   - Corroborates claims across multiple sources                             │
│   - Evaluates confidence (High, Medium, Low)                                │
│   - Detects explicit contradictions and disputes between sources            │
│   - Strips any hallucinated source IDs not present in ResearchPacket        │
│ • Boundary Guarantee: Does NOT perform web search; does NOT write reports   │
│ • Produces: AnalysisPacket                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             REPORT AGENT                                    │
│                       Role: Evidence Synthesizer                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ • Ingests: AnalysisPacket + ResearchPacket                                  │
│ • LLM Calls: Exactly 1 (Groq JSON mode, max_tokens=900)                     │
│ • External I/O: None                                                        │
│ • Responsibilities:                                                         │
│   - Drafts executive summary, thematic sections, conclusions & recommendations│
│   - Attaches bracket citations ([S1], [S2]) directly in text body           │
│   - Audits all citations against ResearchPacket bibliography                │
│   - Pre-renders full GitHub Flavored Markdown document                      │
│ • Boundary Guarantee: Does NOT fetch new information or alter analysis      │
│ • Produces: FinalReport                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Contracts & Schema Specification
## 5. Data Contracts & Pydantic v2 Specifications

All inter-agent communication is governed by typed Pydantic v2 schemas (`src/models.py`):
All inter-agent communication is governed by typed schemas defined in `src/models.py`:

```mermaid
classDiagram
    class SourceDocument {
        +str id
        +str title
        +str url
        +str snippet
        +str published_date
        +Optional~str~ content
        +Optional~str~ published_date
        +float relevance_score
    }

    class SearchQuery {
        +str query
        +str aspect
        +str rationale
    }

    class ResearchPacket {
        +str topic
        +List~str~ subtopics
        +List~SearchQuery~ search_queries
        +List~SourceDocument~ sources
        +str summary
        +str created_at
    }

    class Claim {
        +str claim_id
        +str statement
        +List~str~ supporting_sources
        +str confidence
        +str evidence
    }

    class Conflict {
        +str conflict_id
        +str topic
        +str side_a
        +List~str~ side_a_sources
        +str side_b
        +List~str~ side_b_sources
        +str resolution_or_assessment
    }

    class Finding {
        +str theme
        +List~Claim~ claims
        +str consensus_summary
    }

    class AnalysisPacket {
        +str topic
        +List~Finding~ findings
        +List~Conflict~ conflicts
        +List~str~ key_takeaways
        +str created_at
    }

    class ReportSection {
        +str heading
        +str content
        +List~str~ citations
    }

    class FinalReport {
        +str topic
        +str executive_summary
        +List~ReportSection~ sections
        +List~str~ key_findings
        +List~Conflict~ conflict_analysis
        +List~str~ conclusions
        +List~str~ recommendations
        +List~SourceDocument~ sources
        +str to_markdown()
        +str generated_at
        +Optional~str~ markdown_content
        +to_markdown() str
    }

    ResearchPacket o-- SourceDocument
    ResearchPacket o-- SearchQuery
    AnalysisPacket o-- Conflict
    AnalysisPacket o-- Claim
    FinalReport o-- SourceDocument
    FinalReport o-- Conflict
    class AgentEvent {
        +str agent
        +str step
        +str status
        +str message
        +Optional~dict~ data
        +str timestamp
    }

    ResearchPacket "1" *-- "many" SourceDocument
    ResearchPacket "1" *-- "many" SearchQuery
    AnalysisPacket "1" *-- "many" Finding
    AnalysisPacket "1" *-- "many" Conflict
    Finding "1" *-- "many" Claim
    FinalReport "1" *-- "many" ReportSection
    FinalReport "1" *-- "many" SourceDocument
    FinalReport "1" *-- "many" Conflict
```

---

## 4. Dual-Mode Architecture (Live API + High-Fidelity Mock)
## 6. Citation Integrity Architecture

To ensure zero friction during local development, offline evaluations, and demos:
1. **Live Mode**:
   - Integrates with OpenAI-compatible APIs (OpenAI, Groq, Together, Ollama) via `src/llm.py`.
   - Executes live searches via DuckDuckGo (HTML parser or `duckduckgo-search`) or Tavily.
2. **Mock Mode (Built-In Fallback)**:
   - Activated automatically if no API keys are provided or when `--mock` is flagged.
   - Generates topic-aware decomposition, claim corroboration, conflict modeling, and citations with zero latency and zero external dependencies.
To prevent citation hallucination, the system implements a three-tier validation mechanism:

```
[Live Web Results via Tavily]
             │
             ▼
   [WebSearchTool.search()]
   • Deduplicates URLs
   • Programmatically assigns ID: S1, S2, ... Sn
             │
             ▼
      [ResearchPacket]
      Valid ID Set = {"S1", "S2", ... "Sn"}
             │
             ├────────────────────────────────────────┐
             ▼                                        ▼
    [Analysis Agent]                           [Report Agent]
    • Receives Valid ID Set                    • Receives Valid ID Set
    • LLM outputs claims with sources          • LLM outputs sections with [Sn]
    • Validation:                              • Validation:
      - Strips IDs ∉ Valid ID Set                - Strips section citations ∉ Valid Set
      - Prunes claims with 0 valid sources       - Scans prose for regex r'\[S\d+\]'
                                                 - Cross-references against Valid Set
             │                                        │
             └───────────────────┬────────────────────┘
                                 │
                                 ▼
                           [FinalReport]
           • Pre-rendered Markdown with footnotes
           • Full References bibliography
           • 100% verified source traceability
```

---

## 5. Event-Driven UI Streaming
## 7. Resource Constraints & API Budget

The orchestrator and all agents accept an optional `on_event: Callable[[AgentEvent], None]` callback:
- Emits structured events (`agent`, `step`, `status`, `message`, `data`).
- Both the Streamlit dashboard (`src/ui/app.py`) and the CLI (`src/main.py`) subscribe to these events for real-time visual progress indication and intermediate artifact inspection.
| Component | Target Budget | Enforcement Mechanism |
|---|---|---|
| **Research Agent LLM** | Exactly 1 Groq call | `json_mode=True`, `max_tokens=800` |
| **Web Search Retrieval** | Max 3 queries × 3 results | `MAX_SEARCH_QUERIES=3`, `MAX_RESULTS_PER_QUERY=3` |
| **Analysis Agent LLM** | Exactly 1 Groq call | `json_mode=True`, `max_tokens=900` |
| **Report Agent LLM** | Exactly 1 Groq call | `json_mode=True`, `max_tokens=900` |
| **Orchestrator LLM** | Exactly 0 Groq calls | Deterministic Python coordination logic |
| **Total Pipeline Calls** | **3 Groq calls + 3 Tavily searches** | Enforced by architecture, verified in Layer 4 test |

Token limits (800–900) guarantee compliance with Groq on-demand free-tier constraints (1,000 Output Tokens Per Minute) during sequential execution.
