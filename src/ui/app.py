"""Streamlit Web Dashboard for the Multi-Agent Research Assistant."""

import json
import sys
from datetime import datetime
from pathlib import Path
import streamlit as st

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import settings
from src.models import AgentEvent, FinalReport
from src.orchestrator import ResearchOrchestrator

# Page setup
st.set_page_config(
    page_title="Multi-Agent Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
        color: #1E293B;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .agent-card {
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #E2E8F0;
        background-color: #F8FAFC;
        margin-bottom: 0.8rem;
    }
    .badge-pill {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        font-size: 0.75rem;
        font-weight: 600;
        border-radius: 9999px;
        background-color: #E0E7FF;
        color: #3730A3;
        margin-right: 0.4rem;
    }
</style>
""", unsafe_allow_html=True)


def main():
    # Sidebar controls
    st.sidebar.title("⚙️ System Configuration")

    st.sidebar.markdown("### Execution Mode")
    mode = st.sidebar.radio(
        "Select Operating Mode",
        options=["Offline / Mock Mode (Free & Instant)", "Live API Mode"],
        index=0,
        help="Mock mode executes instantly without API keys. Live mode calls external LLM & search services."
    )

    if mode == "Live API Mode":
        settings.LLM_PROVIDER = st.sidebar.selectbox("LLM Provider", ["openai", "groq", "ollama"], index=0)
        api_key = st.sidebar.text_input("OpenAI / Provider API Key", type="password", value=settings.OPENAI_API_KEY or "")
        if api_key:
            settings.OPENAI_API_KEY = api_key
        settings.OPENAI_MODEL = st.sidebar.text_input("Model Name", value=settings.OPENAI_MODEL)
        settings.SEARCH_PROVIDER = st.sidebar.selectbox("Search Backend", ["duckduckgo", "tavily"], index=0)
    else:
        settings.LLM_PROVIDER = "mock"
        settings.SEARCH_PROVIDER = "mock"
        st.sidebar.info("Running in Mock Mode. High-fidelity topic synthesis enabled without external credentials.")

    st.sidebar.markdown("---")
    settings.MAX_SEARCH_QUERIES = st.sidebar.slider("Max Search Queries", min_value=2, max_value=6, value=4)
    settings.MAX_RESULTS_PER_QUERY = st.sidebar.slider("Results Per Query", min_value=2, max_value=5, value=3)

    # Main Header
    st.markdown('<div class="main-title">🔬 Multi-Agent Research Assistant</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Autonomous multi-agent research pipeline: '
        '<b>Research Agent</b> (Decomposition & Search) ➔ '
        '<b>Analysis Agent</b> (Claims & Conflicts) ➔ '
        '<b>Report Agent</b> (Synthesis & Citations)</div>',
        unsafe_allow_html=True
    )

    # Topic input area
    st.markdown("### 🎯 Enter Research Topic")
    
    # Preset topic buttons
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    preset_topic = None
    if col_p1.button("🔋 Solid-State Batteries"):
        preset_topic = "Solid-State Batteries vs Lithium-Ion: Commercialization Timeline & Energy Density"
    if col_p2.button("🧬 CRISPR in Medicine"):
        preset_topic = "CRISPR Therapeutics: Clinical Trials, Off-Target Risks, and Commercial Viability"
    if col_p3.button("🤖 Multi-Agent AI Systems"):
        preset_topic = "Multi-Agent AI Architectures for Enterprise Process Automation"
    if col_p4.button("⚡ Nuclear Fusion"):
        preset_topic = "Commercial Nuclear Fusion: Net Energy Gain Milestones and Grid Timeline"

    topic = st.text_input(
        "Topic / Research Question",
        value=preset_topic or "Solid-State Batteries vs Lithium-Ion: Commercialization Timeline & Energy Density",
        placeholder="e.g. Next-generation geothermal energy innovations"
    )

    start_button = st.button("🚀 Start Multi-Agent Research", type="primary", use_container_width=True)

    # Orchestrator execution container
    if start_button:
        if not topic.strip():
            st.error("Please enter a valid research topic.")
            return

        st.markdown("---")
        st.markdown("### 🔄 Multi-Agent Pipeline Execution")

        progress_bar = st.progress(5)
        status_box = st.status("Initializing agents...", expanded=True)

        events_log = []

        def handle_event(event: AgentEvent):
            events_log.append(event)
            # Map events to progress bar
            if event.agent == "Research Agent":
                progress_bar.progress(35)
                status_box.write(f"🔍 **[Research Agent]** {event.step}: {event.message}")
            elif event.agent == "Analysis Agent":
                progress_bar.progress(70)
                status_box.write(f"📊 **[Analysis Agent]** {event.step}: {event.message}")
            elif event.agent == "Report Agent":
                progress_bar.progress(90)
                status_box.write(f"📝 **[Report Agent]** {event.step}: {event.message}")
            else:
                status_box.write(f"⚙️ **[Orchestrator]** {event.step}: {event.message}")

        orchestrator = ResearchOrchestrator(on_event=handle_event)
        
        try:
            report: FinalReport = orchestrator.run(topic.strip(), save_output=True)
            progress_bar.progress(100)
            status_box.update(label="✓ All agents completed successfully!", state="complete", expanded=False)
            
            # Store results in session state
            st.session_state["last_report"] = report
            st.session_state["research_packet"] = orchestrator.research_packet
            st.session_state["analysis_packet"] = orchestrator.analysis_packet

        except Exception as e:
            status_box.update(label=f"✗ Error: {e}", state="error")
            st.error(f"Execution failed: {e}")
            return

    # Render results if available
    if "last_report" in st.session_state:
        report: FinalReport = st.session_state["last_report"]
        research_pkg = st.session_state.get("research_packet")
        analysis_pkg = st.session_state.get("analysis_packet")

        st.markdown("---")
        st.markdown(f"## 📋 Research Results: *{report.topic}*")

        tab_report, tab_analysis, tab_research, tab_json = st.tabs([
            "📑 Final Dossier",
            "🔍 Analysis & Conflict Matrix",
            "🌐 Gathered Sources & Queries",
            "⚙️ Raw Structured JSON"
        ])

        # TAB 1: FINAL DOSSIER
        with tab_report:
            st.markdown(report.to_markdown())
            
            # Download actions
            st.markdown("---")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.download_button(
                    label="📥 Download Markdown Report (.md)",
                    data=report.to_markdown(),
                    file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            with col_d2:
                html_content = f"<html><body><pre>{report.to_markdown()}</pre></body></html>"
                st.download_button(
                    label="🌐 Download Plain HTML (.html)",
                    data=html_content,
                    file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                    mime="text/html",
                    use_container_width=True
                )

        # TAB 2: ANALYSIS & CONFLICT MATRIX
        with tab_analysis:
            if analysis_pkg:
                st.markdown("### 💡 Key Strategic Takeaways")
                for t in analysis_pkg.key_takeaways:
                    st.success(f"• {t}")

                st.markdown("### ⚖️ Detected Conflicts & Differing Viewpoints")
                if analysis_pkg.conflicts:
                    for cf in analysis_pkg.conflicts:
                        with st.expander(f"Dispute: {cf.topic}", expanded=True):
                            c1, c2 = st.columns(2)
                            with c1:
                                st.info(f"**Perspective A** ({', '.join(cf.side_a_sources)}):\n\n{cf.side_a}")
                            with c2:
                                st.warning(f"**Perspective B** ({', '.join(cf.side_b_sources)}):\n\n{cf.side_b}")
                            st.markdown(f"**Neutral Assessment**: {cf.resolution_or_assessment}")
                else:
                    st.info("No significant conflicting viewpoints identified across sources.")

                st.markdown("### 🧩 Thematic Findings & Corroborated Claims")
                for f in analysis_pkg.findings:
                    with st.expander(f"Theme: {f.theme}"):
                        st.markdown(f"*Consensus State: {f.consensus_summary}*")
                        for c in f.claims:
                            st.markdown(f"- **Claim [{c.claim_id}]**: {c.statement}")
                            st.caption(f"Confidence: {c.confidence} | Supporting Sources: {', '.join(c.supporting_sources)} | Evidence: {c.evidence}")

        # TAB 3: RESEARCH & SOURCES
        with tab_research:
            if research_pkg:
                st.markdown("### 🎯 Decomposed Subtopics")
                for sub in research_pkg.subtopics:
                    st.markdown(f"- {sub}")

                st.markdown("### 🔎 Generated Search Queries")
                for q in research_pkg.search_queries:
                    st.markdown(f"- **`{q.query}`** — *{q.aspect}* ({q.rationale})")

                st.markdown(f"### 📚 Discovered Sources ({len(research_pkg.sources)})")
                for s in research_pkg.sources:
                    with st.container():
                        st.markdown(f"**[{s.id}] [{s.title}]({s.url})** *(Relevance: {int(s.relevance_score * 100)}%)*")
                        st.markdown(f"> {s.snippet}")
                        st.divider()

        # TAB 4: RAW JSON
        with tab_json:
            st.json(report.model_dump())


if __name__ == "__main__":
    main()

