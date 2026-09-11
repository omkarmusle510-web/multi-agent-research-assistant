# Demo Script: Multi-Agent Research Assistant

Follow this step-by-step walkthrough to test, demonstrate, and evaluate the Multi-Agent Research Assistant across both CLI and Web interfaces.

---

## 1. Quick Verification & Syntax Check

Run syntax compilation to verify that all agent modules and schemas are valid:

```powershell
python -m py_compile src/config.py src/models.py src/llm.py src/tools/web_search.py src/agents/research_agent.py src/agents/analysis_agent.py src/agents/report_agent.py src/orchestrator.py src/main.py src/ui/app.py
```

Expected output: Exits cleanly with code 0 (no output means all files compile without syntax errors).

---

## 2. Demo 1: Instant CLI Demo (Offline / Mock Mode)

Execute an autonomous research cycle on a sample topic with instantaneous mock reasoning (zero API keys needed):

```powershell
python src/main.py --topic "Solid-State Batteries vs Lithium-Ion" --mock
```

### What You Will Observe:
1. **[Orchestrator]** initializes the pipeline for the topic.
2. **[Research Agent]** decomposes the topic into 4 angles and formulates targeted search queries.
3. **[Research Agent]** collects and deduplicates source documents (`[S1]`, `[S2]`, `[S3]`).
4. **[Analysis Agent]** compares sources, extracts verified claims (`[C1]`, `[C2]`), and detects a controversy regarding commercialization timelines.
5. **[Report Agent]** compiles an executive summary, narrative sections citing `[S1]`, `[S2]`, and actionable recommendations.
6. **[Orchestrator]** saves the finished report to `reports/report_solid_state_batteries_vs_lithium_io.md`.

---

## 3. Demo 2: CLI with Custom Topic, JSON Output & Custom File Path

Run research on an emerging scientific subject and save to a custom destination:

```powershell
python src/main.py --topic "Quantum Computing in Drug Discovery" --mock --output ./reports/quantum_drug_discovery.md
```

To view the raw structured Pydantic schema in the console:

```powershell
python src/main.py --topic "Autonomous Drone Delivery Regulations" --mock --json
```

---

## 4. Demo 3: Interactive Streamlit Web Dashboard

Launch the browser-based dashboard:

```powershell
streamlit run src/ui/app.py
```

### Interactive Steps to Showcase:
1. Open the URL shown in terminal (typically `http://localhost:8501`).
2. **Preset Topics**: Click any of the one-click preset buttons (e.g. *🔋 Solid-State Batteries* or *🧬 CRISPR in Medicine*).
3. **Trigger Pipeline**: Click **🚀 Start Multi-Agent Research**.
4. **Watch Live Agents**: Notice the step-by-step progress tracker as the Orchestrator delegates tasks:
   - 🔍 Research Agent ➔ 📊 Analysis Agent ➔ 📝 Report Agent.
5. **Inspect Tabs**:
   - **📑 Final Dossier**: Read the complete formatted research dossier with inline citations.
   - **🔍 Analysis & Conflict Matrix**: Examine the side-by-side controversy cards (Perspective A vs Perspective B) and confidence levels.
   - **🌐 Gathered Sources & Queries**: View the queries generated and the links/snippets of all collected sources.
   - **⚙️ Raw Structured JSON**: Audit the raw JSON packets transferred between agents.
6. **Download Dossier**: Click **📥 Download Markdown Report (.md)** or **🌐 Download Plain HTML (.html)** to save the report.

---

## 5. Demo 4: Running with Live LLMs (OpenAI / Groq)

To test with real external LLM models:
1. Copy `.env.example` to `.env`:
   ```powershell
   copy .env.example .env
   ```
2. Open `.env` and set:
   ```env
   LLM_PROVIDER=openai
   OPENAI_API_KEY=sk-...your_key_here...
   OPENAI_MODEL=gpt-4o-mini
   SEARCH_PROVIDER=duckduckgo
   ```
3. Run the CLI without the `--mock` flag:
   ```powershell
   python src/main.py "Recent Breakthroughs in Fusion Energy"
   ```
   The agents will query live DuckDuckGo and invoke OpenAI for real-time synthesis.

---

## 6. Evaluation Criteria Checklist

During the demo, verify that each requirement from `PROJECT_CONTEXT.md` is met:

- [x] **Research Agent**: Breaks topic down, generates queries, searches web, collects sources.
- [x] **Analysis Agent**: Compares sources, identifies findings, detects conflicts, assesses evidence.
- [x] **Report Agent**: Synthesizes findings, executive summary, key findings, evidence/citations, conclusion.
- [x] **Orchestrator**: Coordinates all three agents and handles state transitions cleanly.
