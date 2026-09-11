"""Report Agent: Synthesizes analysis and research into a publication-ready research dossier."""

import json
import logging
from typing import Callable, List, Optional

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
    """Agent responsible for drafting executive-ready research dossiers with rigorous citations."""

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

    def run(self, analysis: AnalysisPacket, research: ResearchPacket) -> FinalReport:
        """Synthesize analysis findings and source bibliography into a comprehensive FinalReport."""
        logger.info(f"Report Agent drafting final dossier for: {analysis.topic}")
        self._notify("Structuring", f"Structuring research dossier for: '{analysis.topic}'", status="started")

        # Format analysis findings for context
        findings_summary = []
        for f in analysis.findings:
            claims_text = "; ".join([f"{c.statement} (Sources: {', '.join(c.supporting_sources)})" for c in f.claims])
            findings_summary.append(f"Theme: {f.theme}\nClaims: {claims_text}\nConsensus: {f.consensus_summary}")
        findings_block = "\n\n".join(findings_summary)

        # Format conflicts
        conflicts_summary = []
        for cf in analysis.conflicts:
            conflicts_summary.append(
                f"Conflict on {cf.topic}:\n"
                f"- View A ({', '.join(cf.side_a_sources)}): {cf.side_a}\n"
                f"- View B ({', '.join(cf.side_b_sources)}): {cf.side_b}\n"
                f"- Assessment: {cf.resolution_or_assessment}"
            )
        conflicts_block = "\n\n".join(conflicts_summary) if conflicts_summary else "No severe conflicts detected."

        prompt = f"""
You are a Principal Research Director and Lead Technical Author.
Synthesize a comprehensive, executive-ready research dossier for the topic: "{analysis.topic}".

Key Analysis Findings:
{findings_block}

Identified Conflicts / Controversies:
{conflicts_block}

Key Strategic Takeaways:
{chr(10).join(['- ' + t for t in analysis.key_takeaways])}

Produce a complete, highly articulate research report containing:
1. Executive Summary: High-impact synthesis of current reality, opportunities, and risks.
2. Sections: 3 thematic sections with thorough markdown prose. Attribute specific points using bracket citations like [S1], [S2].
3. Key Findings: 3-5 concise bulleted facts.
4. Conclusions: 2-3 definitive summary conclusions.
5. Strategic Recommendations: 3 actionable recommendations for practitioners or decision-makers.

Respond strictly with valid JSON conforming to this schema:
{{
  "executive_summary": "Executive summary paragraph...",
  "sections": [
    {{
      "heading": "Section Heading",
      "content": "Section body with citations [S1]...",
      "citations": ["S1", "S2"]
    }}
  ],
  "key_findings": ["Finding 1", "Finding 2"],
  "conclusions": ["Conclusion 1", "Conclusion 2"],
  "recommendations": ["Recommendation 1", "Recommendation 2"]
}}
"""
        self._notify("Synthesis", "Drafting executive summary, narrative sections, and recommendations...", status="running")
        response_raw = llm_client.complete(prompt, json_mode=True)

        exec_summary = ""
        sections: List[ReportSection] = []
        key_findings: List[str] = []
        conclusions: List[str] = []
        recommendations: List[str] = []

        try:
            parsed = json.loads(response_raw)
            exec_summary = parsed.get("executive_summary", f"Executive summary on {analysis.topic}.")
            
            for s_data in parsed.get("sections", []):
                sections.append(ReportSection(
                    heading=s_data.get("heading", "Analysis"),
                    content=s_data.get("content", ""),
                    citations=s_data.get("citations", [])
                ))

            key_findings = parsed.get("key_findings", analysis.key_takeaways)
            conclusions = parsed.get("conclusions", [
                f"{analysis.topic} is characterized by significant innovation and accelerating adoption.",
                "Strategic governance and cross-functional coordination remain critical success factors."
            ])
            recommendations = parsed.get("recommendations", [
                "Establish structured milestone tracking for adoption phases.",
                "Continuously monitor emerging regulatory frameworks."
            ])

            if not exec_summary:
                raise ValueError("Groq returned report JSON without an executive summary.")
        except Exception as e:
            raise RuntimeError(f"Report Agent failed to parse Groq synthesis: {e}") from e

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

        # Generate and cache formatted markdown
        final_report.to_markdown()

        self._notify(
            "Finalization",
            f"Successfully compiled research dossier with {len(sections)} sections and {len(research.sources)} citations.",
            status="completed",
            data={"section_count": len(sections), "markdown_length": len(final_report.markdown_content or "")}
        )

        return final_report

