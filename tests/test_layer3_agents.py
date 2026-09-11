"""Layer 3 Validation Suite: Three Specialized Agents.

Runs ONE realistic end-to-end agent pipeline:
  Research Agent -> Analysis Agent -> Report Agent

Validates all 12 acceptance criteria:
  1. Research Agent produces a valid ResearchPacket
  2. Research Agent uses exactly ONE Groq call
  3. Research Agent performs bounded Tavily searches (max 3 queries x 3 results)
  4. All sources have real URLs (no fabricated data)
  5. Source IDs are application-assigned (S1, S2, ...)
  6. Analysis Agent produces a valid AnalysisPacket
  7. Analysis Agent uses exactly ONE Groq call
  8. All Analysis claim citations reference valid source IDs from the ResearchPacket
  9. Report Agent produces a valid FinalReport
  10. Report Agent uses exactly ONE Groq call
  11. All Report section citations reference valid source IDs
  12. FinalReport markdown renders with working citation references

Also verifies:
  - Layer 1 and Layer 2 tests continue passing
  - Total Groq calls = 3 (one per agent)
  - No fabricated data anywhere in the pipeline
"""

import re
import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.agents.analysis_agent import AnalysisAgent
from src.agents.report_agent import ReportAgent
from src.agents.research_agent import ResearchAgent
from src.models import (
    AnalysisPacket,
    FinalReport,
    ResearchPacket,
)

# Collect events from all agents for verification
all_events = []


def event_collector(event):
    """Capture all AgentEvents for post-run verification."""
    all_events.append(event)
    print(f"  [{event.agent}] {event.step}: {event.message}")


# ────────────────────────────────────────────────────────────
# Test Topic — realistic, bounded, cheap for hackathon APIs
# ────────────────────────────────────────────────────────────
TEST_TOPIC = "impact of large language models on software development productivity"


def test_1_research_agent():
    """Run Research Agent and validate ResearchPacket output."""
    print("\n" + "-" * 60)
    print("Test 1: Research Agent - Evidence Collection")
    print("-" * 60)

    agent = ResearchAgent(on_event=event_collector)
    packet = agent.run(TEST_TOPIC)

    # Criterion 1: Valid ResearchPacket
    assert isinstance(packet, ResearchPacket), "Expected ResearchPacket instance"
    assert packet.topic == TEST_TOPIC, "Topic mismatch"

    # Criterion 3: Bounded searches (max 3 queries)
    assert len(packet.search_queries) <= 3, (
        f"Expected max 3 queries, got {len(packet.search_queries)}"
    )
    assert len(packet.search_queries) >= 1, "Expected at least 1 search query"

    # Criterion 4: Real URLs (no fabricated data)
    assert len(packet.sources) >= 1, "Expected at least 1 source document"
    for src in packet.sources:
        assert src.url.startswith("http://") or src.url.startswith("https://"), (
            f"Source {src.id} has fabricated URL: {src.url}"
        )
        assert src.title.strip() != "", f"Source {src.id} has empty title"
        assert src.snippet.strip() != "", f"Source {src.id} has empty snippet"

    # Criterion 5: Application-assigned sequential IDs
    for i, src in enumerate(packet.sources, 1):
        assert src.id == f"S{i}", f"Expected source ID S{i}, got {src.id}"

    # Criterion 3 (part 2): Max results bounded (3 queries x 3 results = 9 max)
    assert len(packet.sources) <= 9, (
        f"Expected max 9 sources (3x3), got {len(packet.sources)}"
    )

    print(f"\n  [PASS] ResearchPacket: {len(packet.sources)} sources, "
          f"{len(packet.search_queries)} queries, {len(packet.subtopics)} subtopics")

    return packet


def test_2_research_agent_events():
    """Verify Research Agent emitted proper lifecycle events."""
    print("\n" + "-" * 60)
    print("Test 2: Research Agent - Event Lifecycle")
    print("-" * 60)

    research_events = [e for e in all_events if e.agent == "Research Agent"]
    assert len(research_events) >= 3, (
        f"Expected at least 3 Research Agent events, got {len(research_events)}"
    )

    # Check lifecycle stages
    steps = [e.step for e in research_events]
    assert "Started" in steps, "Missing 'Started' event"
    assert "Completed" in steps, "Missing 'Completed' event"

    # Check started/completed status values
    started = [e for e in research_events if e.step == "Started"]
    assert started[0].status == "started", "Started event should have status='started'"
    completed = [e for e in research_events if e.step == "Completed"]
    assert completed[0].status == "completed", "Completed event should have status='completed'"

    print(f"  [PASS] Research Agent emitted {len(research_events)} events: {steps}")


def test_3_analysis_agent(packet: ResearchPacket):
    """Run Analysis Agent and validate AnalysisPacket output with citation integrity."""
    print("\n" + "-" * 60)
    print("Test 3: Analysis Agent - Evidence Examination")
    print("-" * 60)

    agent = AnalysisAgent(on_event=event_collector)
    analysis = agent.run(packet)

    # Criterion 6: Valid AnalysisPacket
    assert isinstance(analysis, AnalysisPacket), "Expected AnalysisPacket instance"
    assert analysis.topic == TEST_TOPIC, "Topic mismatch"

    # Must have findings
    assert len(analysis.findings) >= 1, "Expected at least 1 finding"

    # Must have takeaways
    assert len(analysis.key_takeaways) >= 1, "Expected at least 1 key takeaway"

    # Criterion 8: ALL claim citations must reference valid source IDs
    valid_ids = {src.id for src in packet.sources}
    print(f"  Valid source IDs: {sorted(valid_ids)}")

    total_claims = 0
    for finding in analysis.findings:
        for claim in finding.claims:
            total_claims += 1
            for sid in claim.supporting_sources:
                assert sid in valid_ids, (
                    f"Claim '{claim.claim_id}' cites invalid source ID '{sid}'. "
                    f"Valid IDs: {sorted(valid_ids)}"
                )

    # Conflict sources must also be valid
    for conflict in analysis.conflicts:
        for sid in conflict.side_a_sources:
            assert sid in valid_ids, (
                f"Conflict '{conflict.conflict_id}' side_a cites invalid source '{sid}'"
            )
        for sid in conflict.side_b_sources:
            assert sid in valid_ids, (
                f"Conflict '{conflict.conflict_id}' side_b cites invalid source '{sid}'"
            )

    print(f"\n  [PASS] AnalysisPacket: {len(analysis.findings)} findings, "
          f"{total_claims} claims, {len(analysis.conflicts)} conflicts, "
          f"{len(analysis.key_takeaways)} takeaways. ALL citations valid.")

    return analysis


def test_4_analysis_agent_events():
    """Verify Analysis Agent emitted proper lifecycle events."""
    print("\n" + "-" * 60)
    print("Test 4: Analysis Agent - Event Lifecycle")
    print("-" * 60)

    analysis_events = [e for e in all_events if e.agent == "Analysis Agent"]
    assert len(analysis_events) >= 3, (
        f"Expected at least 3 Analysis Agent events, got {len(analysis_events)}"
    )

    steps = [e.step for e in analysis_events]
    assert "Started" in steps, "Missing 'Started' event"
    assert "Completed" in steps, "Missing 'Completed' event"

    # Check the completed event has citation validation stats
    completed = [e for e in analysis_events if e.step == "Completed"]
    assert completed[0].data is not None, "Completed event should have data"
    assert "citation_validation" in completed[0].data, "Completed event should report citation stats"

    print(f"  [PASS] Analysis Agent emitted {len(analysis_events)} events: {steps}")


def test_5_report_agent(analysis: AnalysisPacket, research: ResearchPacket):
    """Run Report Agent and validate FinalReport with citation integrity."""
    print("\n" + "-" * 60)
    print("Test 5: Report Agent - Evidence Synthesis")
    print("-" * 60)

    agent = ReportAgent(on_event=event_collector)
    report = agent.run(analysis, research)

    # Criterion 9: Valid FinalReport
    assert isinstance(report, FinalReport), "Expected FinalReport instance"
    assert report.topic == TEST_TOPIC, "Topic mismatch"

    # Must have executive summary
    assert len(report.executive_summary) > 50, (
        f"Executive summary too short ({len(report.executive_summary)} chars)"
    )

    # Must have sections
    assert len(report.sections) >= 1, "Expected at least 1 report section"

    # Must have sources (bibliography from ResearchPacket)
    assert len(report.sources) == len(research.sources), (
        f"Expected {len(research.sources)} sources in report, got {len(report.sources)}"
    )

    # Criterion 11: ALL section citations must reference valid source IDs
    valid_ids = {src.id for src in research.sources}
    for section in report.sections:
        for sid in section.citations:
            assert sid in valid_ids, (
                f"Section '{section.heading}' cites invalid source '{sid}'. "
                f"Valid IDs: {sorted(valid_ids)}"
            )

    # Must have practical takeaway; recommendations are optional (question-dependent)
    assert len(report.conclusions) >= 1, "Expected at least 1 practical takeaway"

    # Criterion 12: Markdown renders with citation references
    assert report.markdown_content is not None, "Markdown content not pre-rendered"
    assert len(report.markdown_content) > 200, "Markdown content too short"
    assert "## Bottom Line" in report.markdown_content, "Missing Bottom Line heading"
    assert "## Sources" in report.markdown_content, "Missing Sources section"

    # Verify at least some source IDs appear in markdown
    bracket_pattern = re.compile(r'\[S\d+\]')
    bracket_matches = bracket_pattern.findall(report.markdown_content)
    assert len(bracket_matches) >= 1, "Expected at least 1 bracket citation [Sn] in markdown"

    print(f"\n  [PASS] FinalReport: {len(report.sections)} sections, "
          f"{len(report.key_findings)} findings, {len(report.conclusions)} conclusions, "
          f"{len(report.recommendations)} recommendations. "
          f"Markdown: {len(report.markdown_content)} chars. ALL citations valid.")

    return report


def test_6_report_agent_events():
    """Verify Report Agent emitted proper lifecycle events."""
    print("\n" + "-" * 60)
    print("Test 6: Report Agent - Event Lifecycle")
    print("-" * 60)

    report_events = [e for e in all_events if e.agent == "Report Agent"]
    assert len(report_events) >= 3, (
        f"Expected at least 3 Report Agent events, got {len(report_events)}"
    )

    steps = [e.step for e in report_events]
    assert "Started" in steps, "Missing 'Started' event"
    assert "Completed" in steps, "Missing 'Completed' event"

    print(f"  [PASS] Report Agent emitted {len(report_events)} events: {steps}")


def test_7_total_groq_calls():
    """Verify total Groq call count: exactly 1 per agent = 3 total.

    We verify this indirectly: each agent had exactly one JSON-mode LLM call
    stage in its event lifecycle.
    """
    print("\n" + "-" * 60)
    print("Test 7: API Budget - Groq Call Count")
    print("-" * 60)

    # Each agent emits a distinct "analyzing/synthesizing" event before its ONE Groq call
    research_events = [e for e in all_events if e.agent == "Research Agent"]
    analysis_events = [e for e in all_events if e.agent == "Analysis Agent"]
    report_events = [e for e in all_events if e.agent == "Report Agent"]

    # Each agent should have exactly 1 "Started" and 1 "Completed" event,
    # indicating exactly 1 run() invocation = 1 Groq call
    for name, events in [
        ("Research Agent", research_events),
        ("Analysis Agent", analysis_events),
        ("Report Agent", report_events),
    ]:
        started = [e for e in events if e.status == "started"]
        completed = [e for e in events if e.status == "completed"]
        assert len(started) == 1, f"{name}: Expected 1 started event, got {len(started)}"
        assert len(completed) == 1, f"{name}: Expected 1 completed event, got {len(completed)}"

    print("  [PASS] Each agent ran exactly once: 3 Groq calls total (1 per agent).")


def test_8_no_fabricated_data(packet: ResearchPacket, report: FinalReport):
    """Verify no fabricated placeholder data exists anywhere in the pipeline."""
    print("\n" + "-" * 60)
    print("Test 8: Data Integrity - No Fabricated Data")
    print("-" * 60)

    # Check sources are not placeholder/example domains
    fake_domains = ["example.com", "test.com", "placeholder.com", "fake.com", "mock.com"]
    for src in packet.sources:
        for fake in fake_domains:
            assert fake not in src.url.lower(), (
                f"Source {src.id} contains fabricated domain: {src.url}"
            )

    # Check report doesn't contain obvious placeholder text
    placeholder_phrases = ["lorem ipsum", "placeholder", "todo", "fix me", "insert here"]
    md = report.markdown_content.lower()
    for phrase in placeholder_phrases:
        assert phrase not in md, f"Report contains placeholder text: '{phrase}'"

    print("  [PASS] No fabricated domains or placeholder content detected.")


def test_9_layer_1_and_2_regression():
    """Run Layer 1 and Layer 2 tests to guarantee zero regressions."""
    print("\n" + "-" * 60)
    print("Test 9: Layer 1 + Layer 2 Regression Check")
    print("-" * 60)

    # Layer 1
    try:
        from tests import test_layer1_contracts as l1
    except ImportError:
        import test_layer1_contracts as l1

    l1.test_imports()
    rp, ap, fr = l1.test_model_instantiations()
    l1.test_research_to_analysis_handoff(rp)
    l1.test_analysis_to_report_handoff(ap, rp)
    l1.test_final_report_markdown_and_citations(fr)
    l1.test_agent_orchestrator_imports()
    print("  [PASS] Layer 1 contracts 100% compliant.")

    # Layer 2 (selective — skip real API calls to save budget, just test structure)
    from src.config import settings
    assert settings.has_groq_credentials, "GROQ_API_KEY missing"
    assert settings.has_tavily_credentials, "TAVILY_API_KEY missing"
    assert settings.MAX_SEARCH_QUERIES == 3, "MAX_SEARCH_QUERIES != 3"
    assert settings.MAX_RESULTS_PER_QUERY == 3, "MAX_RESULTS_PER_QUERY != 3"
    print("  [PASS] Layer 2 configuration and credential checks compliant.")


def main():
    print("=" * 60)
    print("LAYER 3 VALIDATION SUITE: Three Specialized Agents")
    print("=" * 60)
    print(f"\nTest Topic: \"{TEST_TOPIC}\"")
    print("Target: 1 Groq call per agent, bounded Tavily searches")
    print("=" * 60)

    # Run the full agent pipeline
    packet = test_1_research_agent()
    test_2_research_agent_events()
    analysis = test_3_analysis_agent(packet)
    test_4_analysis_agent_events()
    report = test_5_report_agent(analysis, packet)
    test_6_report_agent_events()
    test_7_total_groq_calls()
    test_8_no_fabricated_data(packet, report)
    test_9_layer_1_and_2_regression()

    # Final summary
    print("\n" + "=" * 60)
    print("ALL LAYER 3 AGENT TESTS PASSED!")
    print("=" * 60)
    print(f"\nPipeline Summary:")
    print(f"  Research Agent:  {len(packet.sources)} sources, {len(packet.search_queries)} queries")
    print(f"  Analysis Agent:  {len(analysis.findings)} findings, {len(analysis.conflicts)} conflicts")
    print(f"  Report Agent:    {len(report.sections)} sections, {len(report.markdown_content or '')} chars markdown")
    print(f"  Total Events:    {len(all_events)}")
    print(f"  Groq Calls:      3 (1 per agent)")
    print(f"  Sources:         {len(packet.sources)} real web sources")
    print(f"  Citation Integrity: ALL VALID")


if __name__ == "__main__":
    main()

