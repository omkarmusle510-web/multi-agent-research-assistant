"""Report Agent (Layer 3): Final synthesis and structured report generation.

Role: EVIDENCE SYNTHESIZER
- Receives AnalysisPacket AND ResearchPacket (via Orchestrator)
- Treats AnalysisPacket as the primary analytical input
- Produces a concise, evidence-first research briefing (not academic prose)
- PRESERVES citation integrity: all [S1], [S2] references map to real SourceDocuments
- VALIDATES all citations against the ResearchPacket source IDs
- Does NOT invent facts beyond AnalysisPacket + ResearchPacket
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
        """Synthesize analysis and research into a concise FinalReport briefing.

        Pipeline:
            1. Build context from AnalysisPacket findings/conflicts and ResearchPacket sources
            2. [Groq call] Generate evidence-first briefing mapped onto FinalReport fields
            3. [Local] Validate all citations against ResearchPacket source IDs
            4. Package into FinalReport with source bibliography

        Field mapping (existing FinalReport contract preserved):
            executive_summary -> Bottom Line
            key_findings      -> Key Evidence
            sections          -> Consensus + Why Results Differ
            conflict_analysis -> Where the Evidence Conflicts (from AnalysisPacket)
            conclusions       -> Practical Takeaway
            recommendations   -> Recommendations (optional)
            sources           -> Sources

        Args:
            analysis: AnalysisPacket produced by the Analysis Agent.
            research: ResearchPacket produced by the Research Agent.

        Returns:
            FinalReport with validated citations and pre-rendered markdown.

        Raises:
            RuntimeError: If Groq fails or returns empty report structure.
        """
        logger.info(f"Report Agent drafting briefing for: {analysis.topic}")
        self._notify(
            "Started",
            f"Report Agent activated: drafting evidence-first briefing for '{analysis.topic}'",
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
            "Drafting evidence-first briefing: bottom line, key evidence, consensus, and takeaways...",
            status="running"
        )

        prompt = f"""You are a Research Briefing Writer. Your ONLY job is to turn pre-analyzed evidence into a concise, decision-friendly research briefing that is easy to scan in 30–60 seconds. You do NOT search for new information. You do NOT invent facts. You do NOT re-analyze beyond what the AnalysisPacket already established.

Topic / user question: "{analysis.topic}"

PRIMARY INPUT — ANALYZED FINDINGS (AnalysisPacket):
{findings_block}

PRIMARY INPUT — IDENTIFIED CONFLICTS (AnalysisPacket):
{conflicts_block}

PRIMARY INPUT — KEY TAKEAWAYS (AnalysisPacket):
{chr(10).join(['- ' + t for t in analysis.key_takeaways])}

SOURCE BIBLIOGRAPHY (cite with [S1], [S2], etc.):
{source_ref_block}

CRITICAL EVIDENCE RULES:
- Treat the AnalysisPacket above as the primary analytical input.
- Every factual claim MUST be supported by AnalysisPacket and/or ResearchPacket sources.
- Cite only these source IDs: [{available_ids}]. Never invent IDs or URLs.
- Do NOT fabricate statistics, percentages, study results, or quotes.
- Prefer specific numbers/facts from the analysis when present; otherwise keep claims qualitative and cited.
- Distinguish CONSENSUS from CONFLICTING EVIDENCE from CONTEXTUAL DIFFERENCES.
- NEVER describe conflicting evidence as unanimous consensus.
- If sources disagree, surface the disagreement explicitly. Do not suppress minority/contradictory findings.

STYLE:
- Concise bullets and short paragraphs. No academic wall of text.
- No filler, no generic AI language, no repeating the same conclusion.
- Answer: "What should I know after reading this?"

Map the briefing into this JSON (existing FinalReport fields):

1) executive_summary = BOTTOM LINE
   - 1–3 concise sentences that directly answer the user's question.

2) key_findings = KEY EVIDENCE
   - 3–6 compact evidence-backed findings.
   - Each finding: one crisp line with the important number/fact when available, plus source IDs in brackets.
   - Good examples:
     - "+26% developers completed more tasks [S1]"
     - "Experienced developers took 19% longer on complex tasks [S3]"
   - Do not invent numbers.

3) sections = exactly these two sections (use these exact headings):
   a) "What the Evidence Agrees On"
      - Short bullets summarizing genuine consensus across the analyzed evidence.
      - Cite supporting source IDs inline.
   b) "Why the Results Differ"
      - Explain contextual differences ONLY when supported by the AnalysisPacket
        (task type, experience level, study design, environment, tool/model differences, etc.).
      - If the analysis does not support contextual explanations, say so briefly — do not invent.
      - Keep this short.

   Do NOT add a separate conflicts section here — conflicts are rendered from structured conflict_analysis.

4) conclusions = PRACTICAL TAKEAWAY
   - 1–3 short bullets: what the evidence means for the user.

5) recommendations = RECOMMENDATIONS
   - Include ONLY if the user's question reasonably calls for advice/actions.
   - If recommendations are not appropriate, return an empty list [].
   - When included: 2–4 concise, evidence-grounded recommendations with citations where relevant.

Respond strictly with valid JSON conforming to this exact schema:
{{
  "executive_summary": "1-3 sentence bottom-line answer...",
  "sections": [
    {{
      "heading": "What the Evidence Agrees On",
      "content": "- Consensus point with citations [S1]\\n- Another consensus point [S2]",
      "citations": ["S1", "S2"]
    }},
    {{
      "heading": "Why the Results Differ",
      "content": "- Contextual difference explained from analysis [S1][S3]\\n- Or a brief note if context is unclear",
      "citations": ["S1", "S3"]
    }}
  ],
  "key_findings": [
    "Compact evidence finding with fact/number [S1]",
    "Another compact evidence finding [S2]"
  ],
  "conclusions": [
    "Practical takeaway 1",
    "Practical takeaway 2"
  ],
  "recommendations": []
}}"""

        response_raw = llm_client.complete(prompt, json_mode=True, max_tokens=900)

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
                raise ValueError("Groq returned report JSON without a bottom-line summary.")

            # Normalize recommendations: omit empty/whitespace-only items
            recommendations = [r.strip() for r in recommendations if isinstance(r, str) and r.strip()]

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
