"""Layer 1 Validation Suite: Domain Models, Contracts, Configuration, and Agent Compatibility."""

import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))


def test_imports():
    """1. Verify all relevant Python modules import successfully."""
    print("Test 1: Verifying module imports...")
    from src.models import (
        AgentEvent,
        AnalysisPacket,
        Claim,
        Conflict,
        FinalReport,
        Finding,
        ReportSection,
        ResearchPacket,
        SearchQuery,
        Source,
        SourceDocument,
    )
    from src.config import settings
    from src.agents.research_agent import ResearchAgent
    from src.agents.analysis_agent import AnalysisAgent
    from src.agents.report_agent import ReportAgent
    from src.orchestrator import ResearchOrchestrator

    assert SourceDocument is not None
    assert Source is SourceDocument
    assert settings is not None
    assert ResearchAgent is not None
    assert AnalysisAgent is not None
    assert ReportAgent is not None
    assert ResearchOrchestrator is not None
    print("  -> PASS: All modules imported successfully.")


def test_model_instantiations():
    """2. Instantiate representative models for all required domain concepts."""
    print("\nTest 2: Instantiating representative domain models...")
    from src.models import (
        AgentEvent,
        AnalysisPacket,
        Claim,
        Conflict,
        FinalReport,
        Finding,
        ReportSection,
        ResearchPacket,
        SearchQuery,
        SourceDocument,
    )

    # 1. SearchQuery
    sq = SearchQuery(
        query="solid state battery energy density benchmark",
        aspect="Energy Density",
        rationale="Establish baseline gravimetric and volumetric benchmarks."
    )
    assert sq.query == "solid state battery energy density benchmark"
    assert sq.aspect == "Energy Density"

    # 2. SourceDocument
    doc1 = SourceDocument(
        id="S1",
        title="Solid-State Lithium Battery Benchmarks 2026",
        url="https://example.org/solid-state-benchmark",
        snippet="Empirical cell tests achieve 450 Wh/kg with silicon-composite anodes.",
        published_date="2026-02",
        relevance_score=0.92
    )
    doc2 = SourceDocument(
        id="S2",
        title="Manufacturing Cost & Scaling Roadblocks in Solid-State Cells",
        url="https://example.org/scaling-roadblocks",
        snippet="Dry-electrode coating and high interfacial resistance increase initial pack costs by 35%.",
        published_date="2025-11",
        relevance_score=0.85
    )
    assert doc1.id == "S1"
    assert doc1.relevance == 0.92

    # 3. ResearchPacket
    rp = ResearchPacket(
        topic="Solid-State vs Lithium-Ion Commercialization",
        subtopics=["Energy Density", "Manufacturing Scaling", "Safety Profile"],
        search_queries=[sq],
        sources=[doc1, doc2],
        summary="Initial source discovery indicates significant energy density advantage tempered by near-term manufacturing cost premiums."
    )
    assert len(rp.sources) == 2
    assert rp.queries == [sq.query]

    # 4. Claim
    c1 = Claim(
        claim_id="C1",
        statement="Solid-state cells achieve 30-50% higher gravimetric energy density than standard NMC811 cells.",
        supporting_sources=["S1"],
        confidence="High",
        evidence="Lab test data indicates 450 Wh/kg vs 300 Wh/kg baseline."
    )
    c2 = Claim(
        claim_id="C2",
        statement="Near-term unit economics remain uncompetitive for budget EV segments before 2029.",
        supporting_sources=["S2"],
        confidence="Medium",
        evidence="Manufacturing audits project 35% higher pack cost at sub-gigawatt production scale."
    )
    assert c1.supporting_sources == ["S1"]

    # 5. Finding
    finding1 = Finding(
        theme="Performance Metrics & Energy Density",
        claims=[c1],
        consensus_summary="High literature consensus that solid-state unlocks superior energy density."
    )
    finding2 = Finding(
        theme="Economic Viability & Cost Parity",
        claims=[c2],
        consensus_summary="Consensus that cost parity lags performance by several years."
    )
    assert finding1.theme == "Performance Metrics & Energy Density"

    # 6. Conflict
    conflict1 = Conflict(
        conflict_id="CF1",
        topic="Timeline to Commercial Vehicle Fleet Deployment",
        side_a="Automotive OEMs project commercial premium vehicle deployment by 2026-2027.",
        side_a_sources=["S1"],
        side_b="Materials scientists project volume commercialization delayed until 2030 due to separator dendrite formation.",
        side_b_sources=["S2"],
        resolution_or_assessment="Divergence reflects low-volume luxury pilot models versus high-volume mass-market vehicle adoption."
    )
    assert conflict1.side_a_sources == ["S1"]
    assert conflict1.side_b_sources == ["S2"]

    # 7. AnalysisPacket
    ap = AnalysisPacket(
        topic="Solid-State vs Lithium-Ion Commercialization",
        findings=[finding1, finding2],
        conflicts=[conflict1],
        key_takeaways=[
            "Solid-state delivers proven energy density gains.",
            "Manufacturing scalability remains the chief economic bottleneck.",
            "Initial deployment will bifurcate into premium niche fleets before mass adoption."
        ]
    )
    assert len(ap.findings) == 2
    assert len(ap.conflicts) == 1

    # 8. ReportSection
    sec1 = ReportSection(
        heading="Energy Density Advancements",
        content="Testing demonstrates solid-state electrolytes overcome theoretical liquid electrolyte limits [S1].",
        citations=["S1"]
    )
    sec2 = ReportSection(
        heading="Cost and Manufacturing Barriers",
        content="High-yield roll-to-roll manufacturing remains unproven at terawatt scale, sustaining pack premiums [S2].",
        citations=["S2"]
    )
    assert sec1.citations == ["S1"]

    # 9. FinalReport
    fr = FinalReport(
        topic="Solid-State vs Lithium-Ion Commercialization",
        executive_summary="Solid-state batteries represent the premier next-generation electrochemical frontier, offering higher energy density at the expense of near-term cost parity.",
        sections=[sec1, sec2],
        key_findings=[
            "Energy density gains reach 450 Wh/kg [S1].",
            "Initial pack production cost is 35% higher than mature Li-ion [S2]."
        ],
        conflict_analysis=[conflict1],
        conclusions=[
            "Solid-state will not immediately displace Lithium-Ion across all price points.",
            "Hybrid co-existence with advanced LFP/NMC cells will persist into the 2030s."
        ],
        recommendations=[
            "Target initial adoption in premium luxury and aerospace applications.",
            "Invest in dry-electrode processing to bridge the cost differential."
        ],
        sources=[doc1, doc2]
    )
    assert len(fr.sources) == 2

    # 10. AgentEvent
    event = AgentEvent(
        agent="Research Agent",
        step="Query Generation",
        status="completed",
        message="Formulated 3 targeted queries across technical and economic facets.",
        data={"query_count": 3, "topic": "Solid-State Batteries"}
    )
    assert event.agent == "Research Agent"
    assert event.status == "completed"

    print("  -> PASS: All 10 domain models instantiated and validated.")
    return rp, ap, fr


def test_research_to_analysis_handoff(rp):
    """3. Verify ResearchPacket structurally represents Research Agent -> Analysis Agent handoff."""
    print("\nTest 3: Verifying Research Agent -> Analysis Agent handoff contract...")
    
    # Analysis agent expects topic, sources with id, title, snippet, relevance, and subtopics
    assert rp.topic != ""
    assert isinstance(rp.sources, list)
    assert len(rp.sources) > 0
    for src in rp.sources:
        assert src.id.startswith("S")
        assert src.title
        assert src.url.startswith("http")
        assert src.snippet
        assert 0.0 <= src.relevance_score <= 1.0

    # Ensure Analysis Agent prompt formatter logic works with ResearchPacket
    source_lines = [
        f"[{s.id}] Title: {s.title}\n    Snippet: {s.snippet}\n    Relevance: {s.relevance_score}"
        for s in rp.sources
    ]
    formatted = "\n\n".join(source_lines)
    assert "[S1]" in formatted
    assert "[S2]" in formatted
    print("  -> PASS: ResearchPacket cleanly supplies all data required by Analysis Agent.")


def test_analysis_to_report_handoff(ap, rp):
    """4. Verify AnalysisPacket structurally represents Analysis Agent -> Report Agent handoff."""
    print("\nTest 4: Verifying Analysis Agent -> Report Agent handoff contract...")
    
    # Report Agent expects topic, findings, conflicts, key_takeaways, and source bibliography
    assert ap.topic != ""
    assert len(ap.findings) > 0
    assert len(ap.conflicts) > 0
    assert len(ap.key_takeaways) > 0

    # Verify claim citations reference valid source IDs
    all_source_ids = {s.id for s in rp.sources}
    for f in ap.findings:
        for c in f.claims:
            for s_id in c.supporting_sources:
                assert s_id in all_source_ids, f"Claim references unknown source {s_id}"

    # Verify conflict citations reference valid source IDs
    for cf in ap.conflicts:
        for s_id in cf.side_a_sources:
            assert s_id in all_source_ids, f"Conflict side A references unknown source {s_id}"
        for s_id in cf.side_b_sources:
            assert s_id in all_source_ids, f"Conflict side B references unknown source {s_id}"

    print("  -> PASS: AnalysisPacket and claim/conflict citations adhere strictly to source IDs.")


def test_final_report_markdown_and_citations(fr):
    """5. Verify FinalReport preserves source IDs and renders a structured Markdown report."""
    print("\nTest 5: Verifying FinalReport Markdown rendering and citation integrity...")
    
    md = fr.to_markdown()
    assert isinstance(md, str)
    assert len(md) > 100
    assert f"# Research Dossier: {fr.topic}" in md
    assert "## Executive Summary" in md
    assert "## Key Findings" in md
    assert "## Conflict & Disagreement Analysis" in md
    assert "## Conclusions" in md
    assert "## Strategic Recommendations" in md
    assert "## References & Sources" in md

    # Verify critical source rule: [S1], [S2] must map back to actual URLs collected
    for src in fr.sources:
        expected_citation = f"**[{src.id}]** [{src.title}]({src.url})"
        assert expected_citation in md, f"Citation header {expected_citation} not found in markdown"

    print("  -> PASS: FinalReport rendered valid Markdown preserving all source citations.")


def test_agent_orchestrator_imports():
    """6. Verify existing agent/orchestrator imports do not fail because of model mismatches."""
    print("\nTest 6: Verifying orchestrator and agent signatures...")
    from src.orchestrator import ResearchOrchestrator
    from src.agents.research_agent import ResearchAgent
    from src.agents.analysis_agent import AnalysisAgent
    from src.agents.report_agent import ReportAgent

    events = []
    orch = ResearchOrchestrator(on_event=lambda e: events.append(e))
    assert hasattr(orch, "run")
    assert orch.research_packet is None
    assert orch.analysis_packet is None
    assert orch.final_report is None

    ragent = ResearchAgent(on_event=lambda e: None)
    assert hasattr(ragent, "run")

    aagent = AnalysisAgent(on_event=lambda e: None)
    assert hasattr(aagent, "run")

    repagent = ReportAgent(on_event=lambda e: None)
    assert hasattr(repagent, "run")

    print("  -> PASS: Orchestrator and agent class signatures and interfaces verified.")


def main():
    print("=" * 60)
    print("LAYER 1 VALIDATION SUITE: Multi-Agent Research Assistant")
    print("=" * 60)
    test_imports()
    rp, ap, fr = test_model_instantiations()
    test_research_to_analysis_handoff(rp)
    test_analysis_to_report_handoff(ap, rp)
    test_final_report_markdown_and_citations(fr)
    test_agent_orchestrator_imports()
    print("\n" + "=" * 60)
    print("ALL LAYER 1 TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()

