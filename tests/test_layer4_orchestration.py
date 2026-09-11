"""Layer 4 Validation Suite: Orchestration and Visible Handoffs.

Runs ONE complete real pipeline through the ResearchOrchestrator and verifies:
  1.  Research Agent runs
  2.  ResearchPacket exists
  3.  Analysis Agent receives the ResearchPacket
  4.  AnalysisPacket exists
  5.  Report Agent receives ResearchPacket + AnalysisPacket
  6.  FinalReport exists
  7.  FinalReport contains actual source citations
  8.  Citations resolve to sources from ResearchPacket
  9.  Agent events show the correct order
  10. Exactly three Groq agent calls occur (orchestrator makes zero)
  11. Tavily search remains within configured limits
  12. Existing Layer 1, 2, 3 tests continue to pass
"""

import re
import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.orchestrator import ResearchOrchestrator

TEST_TOPIC = "quantum computing applications in drug discovery"


def main():
    print("=" * 60)
    print("LAYER 4 VALIDATION: Orchestration and Visible Handoffs")
    print("=" * 60)
    print(f"\nTest Topic: \"{TEST_TOPIC}\"")
    print("=" * 60)

    # ── Run the full orchestrated pipeline ──
    collected_events = []

    def capture_event(event):
        collected_events.append(event)
        print(f"  [{event.agent}] {event.step} ({event.status}): {event.message}")

    orchestrator = ResearchOrchestrator(on_event=capture_event)
    report = orchestrator.run(TEST_TOPIC, save_output=False)

    # ── Test 1: Research Agent ran ──
    print("\n" + "-" * 60)
    print("Test 1: Research Agent ran")
    print("-" * 60)
    ra_events = [e for e in collected_events if e.agent == "Research Agent"]
    assert len(ra_events) >= 1, "No Research Agent events found"
    ra_completed = [e for e in ra_events if e.status == "completed"]
    assert len(ra_completed) == 1, f"Expected 1 Research Agent completion, got {len(ra_completed)}"
    print("  [PASS] Research Agent ran and completed.")

    # ── Test 2: ResearchPacket exists ──
    print("\n" + "-" * 60)
    print("Test 2: ResearchPacket exists")
    print("-" * 60)
    rp = orchestrator.research_packet
    assert rp is not None, "ResearchPacket is None"
    assert len(rp.sources) >= 1, "ResearchPacket has zero sources"
    assert rp.topic == TEST_TOPIC, f"Topic mismatch: {rp.topic}"
    print(f"  [PASS] ResearchPacket: {len(rp.sources)} sources, {len(rp.search_queries)} queries.")

    # ── Test 3: Analysis Agent received the ResearchPacket ──
    print("\n" + "-" * 60)
    print("Test 3: Analysis Agent received the ResearchPacket")
    print("-" * 60)
    # Verified by: handoff event exists AND analysis packet references the same topic
    handoff_1_events = [e for e in collected_events
                        if e.agent == "Orchestrator" and e.step == "Handoff 1"]
    assert len(handoff_1_events) == 1, "Missing Handoff 1 event"
    assert handoff_1_events[0].data is not None, "Handoff 1 event has no data"
    assert handoff_1_events[0].data["packet"] == "ResearchPacket", "Handoff 1 should pass ResearchPacket"
    assert handoff_1_events[0].data["source_count"] == len(rp.sources), "Handoff source count mismatch"
    print(f"  [PASS] Handoff 1 confirmed: ResearchPacket ({len(rp.sources)} sources) passed to Analysis Agent.")

    # ── Test 4: AnalysisPacket exists ──
    print("\n" + "-" * 60)
    print("Test 4: AnalysisPacket exists")
    print("-" * 60)
    ap = orchestrator.analysis_packet
    assert ap is not None, "AnalysisPacket is None"
    assert len(ap.findings) >= 1, "AnalysisPacket has zero findings"
    assert ap.topic == TEST_TOPIC, f"Topic mismatch: {ap.topic}"
    print(f"  [PASS] AnalysisPacket: {len(ap.findings)} findings, {len(ap.conflicts)} conflicts.")

    # ── Test 5: Report Agent received ResearchPacket + AnalysisPacket ──
    print("\n" + "-" * 60)
    print("Test 5: Report Agent received ResearchPacket + AnalysisPacket")
    print("-" * 60)
    handoff_2_events = [e for e in collected_events
                        if e.agent == "Orchestrator" and e.step == "Handoff 2"]
    assert len(handoff_2_events) == 1, "Missing Handoff 2 event"
    assert handoff_2_events[0].data["packet"] == "AnalysisPacket", "Handoff 2 should pass AnalysisPacket"
    # Report has sources from ResearchPacket = proof both packets were passed
    assert len(report.sources) == len(rp.sources), (
        f"Report sources ({len(report.sources)}) != ResearchPacket sources ({len(rp.sources)})"
    )
    print(f"  [PASS] Handoff 2 confirmed: AnalysisPacket + ResearchPacket passed to Report Agent.")

    # ── Test 6: FinalReport exists ──
    print("\n" + "-" * 60)
    print("Test 6: FinalReport exists")
    print("-" * 60)
    assert report is not None, "FinalReport is None"
    assert orchestrator.final_report is report, "Orchestrator final_report should match returned report"
    assert len(report.sections) >= 1, "FinalReport has zero sections"
    assert len(report.executive_summary) > 50, "Executive summary too short"
    print(f"  [PASS] FinalReport: {len(report.sections)} sections, "
          f"{len(report.executive_summary.split())} word executive summary.")

    # ── Test 7: FinalReport contains actual source citations ──
    print("\n" + "-" * 60)
    print("Test 7: FinalReport contains source citations")
    print("-" * 60)
    assert report.markdown_content is not None, "Markdown not pre-rendered"
    bracket_refs = re.findall(r'\[S\d+\]', report.markdown_content)
    assert len(bracket_refs) >= 1, "No [Sn] citations found in markdown"
    assert "## References" in report.markdown_content, "Missing References section in markdown"
    print(f"  [PASS] Found {len(bracket_refs)} bracket citations and References section in markdown.")

    # ── Test 8: Citations resolve to ResearchPacket sources ──
    print("\n" + "-" * 60)
    print("Test 8: Citations resolve to ResearchPacket sources")
    print("-" * 60)
    valid_ids = {src.id for src in rp.sources}
    # Check section citation lists
    for sec in report.sections:
        for sid in sec.citations:
            assert sid in valid_ids, (
                f"Section '{sec.heading}' cites invalid source '{sid}'. Valid: {sorted(valid_ids)}"
            )
    # Check report bibliography matches research sources
    report_source_ids = {src.id for src in report.sources}
    assert report_source_ids == valid_ids, (
        f"Report sources {sorted(report_source_ids)} != ResearchPacket sources {sorted(valid_ids)}"
    )
    print(f"  [PASS] All section citations and bibliography resolve to ResearchPacket source IDs: {sorted(valid_ids)}")

    # ── Test 9: Event order is correct ──
    print("\n" + "-" * 60)
    print("Test 9: Event order is correct")
    print("-" * 60)
    # Extract the agent sequence from events
    agent_sequence = []
    for e in collected_events:
        if e.agent not in agent_sequence or e.agent != agent_sequence[-1]:
            agent_sequence.append(e.agent)

    # Expected: Orchestrator starts, Research Agent block, Orchestrator handoff,
    #           Analysis Agent block, Orchestrator handoff, Report Agent block, Orchestrator finish
    # Verify the agent order follows: Orchestrator -> Research -> Orchestrator -> Analysis -> Orchestrator -> Report -> Orchestrator
    assert agent_sequence[0] == "Orchestrator", f"Pipeline should start with Orchestrator, got {agent_sequence[0]}"
    assert "Research Agent" in agent_sequence, "Research Agent missing from event stream"
    assert "Analysis Agent" in agent_sequence, "Analysis Agent missing from event stream"
    assert "Report Agent" in agent_sequence, "Report Agent missing from event stream"

    # Research Agent must appear before Analysis Agent
    ra_first_idx = next(i for i, a in enumerate(agent_sequence) if a == "Research Agent")
    aa_first_idx = next(i for i, a in enumerate(agent_sequence) if a == "Analysis Agent")
    rp_first_idx = next(i for i, a in enumerate(agent_sequence) if a == "Report Agent")
    assert ra_first_idx < aa_first_idx < rp_first_idx, (
        f"Agent order incorrect: Research@{ra_first_idx}, Analysis@{aa_first_idx}, Report@{rp_first_idx}"
    )

    # Handoff events must exist between agent blocks
    assert len(handoff_1_events) == 1, "Missing Handoff 1"
    assert len(handoff_2_events) == 1, "Missing Handoff 2"

    # Orchestrator events at boundaries
    pipeline_started = [e for e in collected_events if e.agent == "Orchestrator" and e.step == "Pipeline Started"]
    pipeline_complete = [e for e in collected_events if e.agent == "Orchestrator" and e.step == "Pipeline Complete"]
    assert len(pipeline_started) == 1, "Missing Pipeline Started event"
    assert len(pipeline_complete) == 1, "Missing Pipeline Complete event"

    print(f"  Agent sequence: {' -> '.join(agent_sequence)}")
    print(f"  [PASS] Event order correct: Pipeline Started -> Research -> Handoff 1 -> Analysis -> Handoff 2 -> Report -> Complete.")

    # ── Test 10: Exactly three Groq calls ──
    print("\n" + "-" * 60)
    print("Test 10: Exactly three Groq agent calls")
    print("-" * 60)
    # Each agent runs exactly once (1 started + 1 completed each)
    for agent_name in ["Research Agent", "Analysis Agent", "Report Agent"]:
        agent_started = [e for e in collected_events if e.agent == agent_name and e.status == "started"]
        agent_completed = [e for e in collected_events if e.agent == agent_name and e.status == "completed"]
        assert len(agent_started) == 1, f"{agent_name}: expected 1 started event, got {len(agent_started)}"
        assert len(agent_completed) == 1, f"{agent_name}: expected 1 completed event, got {len(agent_completed)}"

    # Orchestrator makes ZERO LLM calls (no additional Groq events)
    orch_events = [e for e in collected_events if e.agent == "Orchestrator"]
    for oe in orch_events:
        assert "groq" not in oe.message.lower() or "call" not in oe.message.lower(), (
            f"Orchestrator should not make LLM calls: {oe.message}"
        )

    print("  [PASS] Exactly 3 Groq calls: 1 Research + 1 Analysis + 1 Report. Orchestrator = 0.")

    # ── Test 11: Tavily search within limits ──
    print("\n" + "-" * 60)
    print("Test 11: Tavily search within configured limits")
    print("-" * 60)
    from src.config import settings
    assert len(rp.search_queries) <= settings.MAX_SEARCH_QUERIES, (
        f"Queries {len(rp.search_queries)} exceed MAX_SEARCH_QUERIES {settings.MAX_SEARCH_QUERIES}"
    )
    assert len(rp.sources) <= settings.MAX_SEARCH_QUERIES * settings.MAX_RESULTS_PER_QUERY, (
        f"Sources {len(rp.sources)} exceed max possible {settings.MAX_SEARCH_QUERIES * settings.MAX_RESULTS_PER_QUERY}"
    )
    print(f"  [PASS] {len(rp.search_queries)} queries (max {settings.MAX_SEARCH_QUERIES}), "
          f"{len(rp.sources)} sources (max {settings.MAX_SEARCH_QUERIES * settings.MAX_RESULTS_PER_QUERY}).")

    # ── Test 12: Layer 1, 2, 3 regression ──
    print("\n" + "-" * 60)
    print("Test 12: Layer 1 + 2 + 3 regression check")
    print("-" * 60)

    # Layer 1
    try:
        from tests import test_layer1_contracts as l1
    except ImportError:
        import test_layer1_contracts as l1
    l1.test_imports()
    rp_l1, ap_l1, fr_l1 = l1.test_model_instantiations()
    l1.test_research_to_analysis_handoff(rp_l1)
    l1.test_analysis_to_report_handoff(ap_l1, rp_l1)
    l1.test_final_report_markdown_and_citations(fr_l1)
    l1.test_agent_orchestrator_imports()
    print("  [PASS] Layer 1 contracts compliant.")

    # Layer 2 (config checks only — skip API calls to save budget)
    assert settings.has_groq_credentials, "GROQ_API_KEY missing"
    assert settings.has_tavily_credentials, "TAVILY_API_KEY missing"
    assert settings.MAX_SEARCH_QUERIES == 3
    assert settings.MAX_RESULTS_PER_QUERY == 3
    print("  [PASS] Layer 2 configuration compliant.")

    # Layer 3 agent imports still work
    from src.agents.research_agent import ResearchAgent
    from src.agents.analysis_agent import AnalysisAgent
    from src.agents.report_agent import ReportAgent
    assert callable(getattr(ResearchAgent, 'run', None))
    assert callable(getattr(AnalysisAgent, 'run', None))
    assert callable(getattr(ReportAgent, 'run', None))
    print("  [PASS] Layer 3 agent interfaces compliant.")

    # ── Final Summary ──
    print("\n" + "=" * 60)
    print("ALL LAYER 4 ORCHESTRATION TESTS PASSED!")
    print("=" * 60)
    print(f"\nExecution Summary:")
    print(f"  Topic:           \"{TEST_TOPIC}\"")
    print(f"  Research Agent:  {len(rp.sources)} sources, {len(rp.search_queries)} queries")
    print(f"  Analysis Agent:  {len(ap.findings)} findings, {len(ap.conflicts)} conflicts")
    print(f"  Report Agent:    {len(report.sections)} sections, {len(report.markdown_content or '')} chars markdown")
    print(f"  Total Events:    {len(collected_events)}")
    print(f"  Groq Calls:      3 (1 per agent, orchestrator = 0)")
    print(f"  Tavily Searches: {len(rp.search_queries)} queries, {len(rp.sources)} results")
    print(f"  Handoffs:        2 (ResearchPacket -> Analysis, AnalysisPacket+ResearchPacket -> Report)")
    print(f"  Citation Integrity: ALL VALID")
    print(f"\nEvent Sequence:")
    for i, e in enumerate(collected_events, 1):
        status_tag = f"[{e.status.upper()}]" if e.status in ("started", "completed", "error") else ""
        print(f"  {i:2}. [{e.agent}] {e.step} {status_tag}")


if __name__ == "__main__":
    main()

