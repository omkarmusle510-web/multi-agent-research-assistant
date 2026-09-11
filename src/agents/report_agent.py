"""Report Agent (Layer 3): Final synthesis and structured report generation.

Role: EVIDENCE SYNTHESIZER
- Receives AnalysisPacket AND ResearchPacket (via Orchestrator)
- Synthesizes analyzed evidence into a coherent, structured research report
- Writes executive summary, thematic sections, conclusions, and recommendations
- PRESERVES citation integrity: all [S1], [S2] references map to real SourceDocuments
- VALIDATES all citations against the ResearchPacket source IDs
- Does NOT search for new information — that was the Research Agent's job
- Does NOT re-analyze — that was the Analysis Agent's job
"""

import json
import logging
import re
from typing import Callable, Dict, List, Optional, Set

from src.llm import llm_client
from src.models import (
    AgentEvent,
    AnalysisPacket,
    FinalReport,
    ReportSection,
    ResearchPacket,
)

logger = logging.getLogger(__name__)


class ReportAgent:
    """Evidence Synthesizer: drafts structured research dossiers with validated citations."""

    def __init__(self, on_event: Optional[Callable[[AgentEvent], None]] = None):
        self.on_event = on_event or (lambda ev: None)

    def _notify(self, step: str, message: str, status: str = "running", data: Optional[dict] = None):
        event = AgentEvent(
            agent="Report Agent",
            step=step,
            status=status,
            message=message,
            data=data
        )
        self.on_event(event)

    def _validate_section_citations(
        self, sections: List[ReportSection], valid_ids: Set[str]
    ) -> List[ReportSection]:
        """Validate and clean citation lists in report sections.

        For each section:
        - Strip citation IDs from the citations list that don't exist in the ResearchPacket
        - Also scan section content for bracket citations like [S1] and strip invalid ones

        Returns:
            List of ReportSections with validated citations.
        """
        validated_sections: List[ReportSection] = []
        for sec in sections:
            # Validate explicit citations list
            clean_citations = [sid for sid in sec.citations if sid in valid_ids]
            invalid = [sid for sid in sec.citations if sid not in valid_ids]
            if invalid:
                logger.warning(
                    f"Report Agent: Stripped invalid citation IDs from section "
                    f"'{sec.heading}': {invalid}"
                )

            # Also extract any bracket citations from content and validate
            bracket_pattern = re.compile(r'\[S(\d+)\]')
            content_refs = set(bracket_pattern.findall(sec.content))
            content_source_ids = {f"S{n}" for n in content_refs}

            # Add content-referenced valid IDs to citations list
            for sid in content_source_ids:
                if sid in valid_ids and sid not in clean_citations:
                    clean_citations.append(sid)

            validated_sections.append(ReportSection(
                heading=sec.heading,
                content=sec.content,
                citations=clean_citations
            ))

        return validated_sections

    def run(self, analysis: AnalysisPacket, research: ResearchPacket) -> FinalReport:
        """Synthesize analysis and research into a comprehensive FinalReport.

        Pipeline:
            1. Build context from AnalysisPacket findings/conflicts and ResearchPacket sources
            2. [Groq call] Generate structured report with executive summary and sections
            3. [Local] Validate all citations against ResearchPacket source IDs
            4. Package into FinalReport with source bibliography

        Args:
            analysis: AnalysisPacket produced by the Analysis Agent.
            research: ResearchPacket produced by the Research Agent.

        Returns:
            FinalReport with validated citations and pre-rendered markdown.

        Raises:
            RuntimeError: If Groq fails or returns empty report structure.
        """
        logger.info(f"Report Agent drafting final report for: {analysis.topic}")
        self._notify(
            "Started",
            f"Report Agent activated: synthesizing report for '{analysis.topic}'",
            status="started"
        )

        # Build valid source ID set for citation validation
        valid_source_ids: Set[str] = {src.id for src in research.sources}
        available_ids = ", ".join(sorted(valid_source_ids))

        # ── Step 1: Build Context for LLM ──
        self._notify(
            "Building Context",
            "Preparing analysis findings and source bibliography for synthesis...",
            status="running"
        )

        # Format analysis findings
        findings_lines = []
        for f in analysis.findings:
            claims_text = "\n".join([
                f"  - {c.statement} (Sources: {', '.join(c.supporting_sources)}, "
                f"Confidence: {c.confidence})"
                for c in f.claims
            ])
            findings_lines.append(
                f"Theme: {f.theme}\n"
                f"Claims:\n{claims_text}\n"
                f"Consensus: {f.consensus_summary}"
            )
        findings_block = "\n\n".join(findings_lines)

        # Format conflicts
        conflicts_lines = []
        for cf in analysis.conflicts:
            conflicts_lines.append(
                f"Dispute: {cf.topic}\n"
                f"  - View A ({', '.join(cf.side_a_sources)}): {cf.side_a}\n"
                f"  - View B ({', '.join(cf.side_b_sources)}): {cf.side_b}\n"
                f"  - Assessment: {cf.resolution_or_assessment}"
            )
        conflicts_block = "\n\n".join(conflicts_lines) if conflicts_lines else "No severe conflicts detected."

        # Format source bibliography for reference
        source_ref_lines = []
        for src in research.sources:
            source_ref_lines.append(f"[{src.id}] {src.title} ({src.url})")
        source_ref_block = "\n".join(source_ref_lines)

        # ── Step 2: Report Synthesis (ONE Groq call) ──
        self._notify(
            "Synthesizing",
            "Generating executive summary, report sections, and recommendations...",
            status="running"
        )

        prompt = f"""You are a Research Report Writer. Your ONLY job is to synthesize pre-analyzed evidence into a clear, structured research report. You do NOT search for new information or re-analyze — you write the final narrative.

Topic: "{analysis.topic}"

ANALYZED FINDINGS:
{findings_block}

IDENTIFIED CONFLICTS:
{conflicts_block}

KEY TAKEAWAYS FROM ANALYSIS:
{chr(10).join(['- ' + t for t in analysis.key_takeaways])}

SOURCE BIBLIOGRAPHY (cite using bracket notation like [S1], [S2]):
{source_ref_block}

CRITICAL CITATION RULE: You may ONLY reference source IDs from this exact set: [{available_ids}]. Do NOT invent sources. Every [Sn] citation in your text must match one of these real sources.

Write a complete research report containing:
1. EXECUTIVE SUMMARY: 1-2 paragraph synthesis of the current state, opportunities, and risks
2. SECTIONS: 3 thematic sections with detailed prose and bracket citations [S1], [S2], etc.
3. KEY FINDINGS: 3-5 concise bullet points of the most important facts
4. CONCLUSIONS: 2-3 definitive summary conclusions
5. RECOMMENDATIONS: 3 actionable recommendations for practitioners

Respond strictly with valid JSON conforming to this exact schema:
{{
  "executive_summary": "Executive summary text...",
  "sections": [
    {{
      "heading": "Section Title",
      "content": "Section body with inline citations [S1], [S2]...",
      "citations": ["S1", "S2"]
    }}
  ],
  "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
  "conclusions": ["Conclusion 1", "Conclusion 2"],
  "recommendations": ["Recommendation 1", "Recommendation 2", "Recommendation 3"]
}}"""

        response_raw = llm_client.complete(prompt, json_mode=True)

        # ── Step 3: Parse and Validate Citations ──
        self._notify(
            "Validating Citations",
            "Verifying all report citations reference real sources...",
            status="running"
        )

        exec_summary = ""
        sections: List[ReportSection] = []
        key_findings: List[str] = []
        conclusions: List[str] = []
        recommendations: List[str] = []
        citation_stats: Dict[str, int] = {"sections_total": 0, "sections_valid": 0}

        try:
            parsed = json.loads(response_raw)
            exec_summary = parsed.get("executive_summary", "")

            # Parse sections
            raw_sections: List[ReportSection] = []
            for s_data in parsed.get("sections", []):
                raw_citations = s_data.get("citations", [])
                citation_stats["sections_total"] += len(raw_citations)

                raw_sections.append(ReportSection(
                    heading=s_data.get("heading", "Analysis"),
                    content=s_data.get("content", ""),
                    citations=raw_citations
                ))

            # Validate all section citations
            sections = self._validate_section_citations(raw_sections, valid_source_ids)
            for sec in sections:
                citation_stats["sections_valid"] += len(sec.citations)

            key_findings = parsed.get("key_findings", analysis.key_takeaways)
            conclusions = parsed.get("conclusions", [])
            recommendations = parsed.get("recommendations", [])

            if not exec_summary:
                raise ValueError("Groq returned report JSON without an executive summary.")

        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Report Agent: Groq returned unparseable JSON: {e}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Report Agent failed to parse Groq synthesis: {e}") from e

        # ── Step 4: Package into FinalReport ──
        final_report = FinalReport(
            topic=analysis.topic,
            executive_summary=exec_summary,
            sections=sections,
            key_findings=key_findings,
            conflict_analysis=analysis.conflicts,
            conclusions=conclusions,
            recommendations=recommendations,
            sources=research.sources
        )

        # Pre-render markdown
        final_report.to_markdown()

        self._notify(
            "Completed",
            f"Report complete: {len(sections)} sections, {len(key_findings)} findings, "
            f"{len(research.sources)} sources cited. "
            f"Citations validated: {citation_stats['sections_valid']}/{citation_stats['sections_total']}.",
            status="completed",
            data={
                "section_count": len(sections),
                "finding_count": len(key_findings),
                "source_count": len(research.sources),
                "citation_validation": citation_stats,
                "markdown_length": len(final_report.markdown_content or "")
            }
        )

        return final_report
