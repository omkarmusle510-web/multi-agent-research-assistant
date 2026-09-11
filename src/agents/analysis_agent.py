"""Analysis Agent (Layer 3): Cross-source evidence examination and claim extraction.

Role: EVIDENCE EXAMINER
- Receives a ResearchPacket from the Research Agent (via Orchestrator)
- Compares evidence ACROSS sources — does NOT invent new evidence
- Extracts verifiable claims, each citing only source IDs that exist in the ResearchPacket
- Identifies consensus, conflicts, and divergent perspectives
- Produces a structured AnalysisPacket
- VALIDATES all cited source IDs against the incoming ResearchPacket
- Does NOT search the web — that was the Research Agent's job
- Does NOT write reports — that is the Report Agent's job
"""

import json
import logging
from typing import Callable, Dict, List, Optional, Set

from src.llm import llm_client
from src.models import (
    AgentEvent,
    AnalysisPacket,
    Claim,
    Conflict,
    Finding,
    ResearchPacket,
)

logger = logging.getLogger(__name__)


class AnalysisAgent:
    """Evidence Examiner: cross-references sources, extracts claims, validates citations."""

    def __init__(self, on_event: Optional[Callable[[AgentEvent], None]] = None):
        self.on_event = on_event or (lambda ev: None)

    def _notify(self, step: str, message: str, status: str = "running", data: Optional[dict] = None):
        event = AgentEvent(
            agent="Analysis Agent",
            step=step,
            status=status,
            message=message,
            data=data
        )
        self.on_event(event)

    def _validate_source_ids(self, cited_ids: List[str], valid_ids: Set[str]) -> List[str]:
        """Strip any cited source IDs that do not exist in the ResearchPacket.

        Args:
            cited_ids: Source IDs cited by the LLM (e.g., ["S1", "S2", "S99"])
            valid_ids: Set of source IDs that actually exist in the ResearchPacket

        Returns:
            List of only the valid source IDs, preserving order.
        """
        validated = [sid for sid in cited_ids if sid in valid_ids]
        invalid = [sid for sid in cited_ids if sid not in valid_ids]
        if invalid:
            logger.warning(
                f"Analysis Agent: Stripped invalid source IDs not in ResearchPacket: {invalid}"
            )
        return validated

    def run(self, packet: ResearchPacket) -> AnalysisPacket:
        """Execute evidence examination on a ResearchPacket.

        Pipeline:
            1. Build source context from ResearchPacket sources
            2. [Groq call] Extract claims, findings, and conflicts
            3. [Local] Validate ALL cited source IDs against ResearchPacket
            4. Package into AnalysisPacket

        Args:
            packet: ResearchPacket produced by the Research Agent.

        Returns:
            AnalysisPacket with validated claims and conflicts.

        Raises:
            RuntimeError: If Groq fails or returns empty analysis.
        """
        logger.info(f"Analysis Agent starting for topic: {packet.topic} ({len(packet.sources)} sources)")
        self._notify(
            "Started",
            f"Analysis Agent activated: examining {len(packet.sources)} sources for '{packet.topic}'",
            status="started"
        )

        # Build the set of valid source IDs from the ResearchPacket
        valid_source_ids: Set[str] = {src.id for src in packet.sources}
        logger.info(f"Valid source IDs: {sorted(valid_source_ids)}")

        # ── Step 1: Format source context for LLM ──
        self._notify(
            "Preparing Context",
            f"Formatting {len(packet.sources)} source documents for cross-examination...",
            status="running"
        )

        source_lines = []
        for src in packet.sources:
            source_lines.append(
                f"[{src.id}] Title: {src.title}\n"
                f"    URL: {src.url}\n"
                f"    Snippet: {src.snippet}\n"
                f"    Relevance: {src.relevance_score:.2f} | Published: {src.published_date or 'N/A'}"
            )
        sources_text = "\n\n".join(source_lines)

        available_ids = ", ".join(sorted(valid_source_ids))

        # ── Step 2: Cross-Source Analysis (ONE Groq call) ──
        self._notify(
            "Analyzing",
            "Extracting claims, identifying consensus, and detecting conflicts...",
            status="running"
        )

        prompt = f"""You are an Evidence Examination specialist. Your ONLY job is to cross-reference and compare the source documents below. You do NOT search for new information — you examine what the Research Agent already collected.

Topic: "{packet.topic}"

Available Source Documents (ONLY cite these IDs: {available_ids}):
{sources_text}

CRITICAL CITATION RULE: You may ONLY cite source IDs from this exact set: [{available_ids}]. Do NOT invent source IDs like S99 or S10 that are not listed above.

Tasks:
1. FINDINGS: Group the evidence into 2-3 thematic findings. For each finding, extract specific claims supported by the sources. Each claim must cite real source IDs from the list above.
2. CONFLICTS: Identify at least 1 area where sources disagree, present different perspectives, or emphasize different aspects of the topic. Cite real source IDs for each side.
3. KEY TAKEAWAYS: Provide 3 concise, high-impact insights distilled from the evidence.

Respond strictly with valid JSON conforming to this exact schema:
{{
  "findings": [
    {{
      "theme": "Thematic title",
      "claims": [
        {{
          "claim_id": "C1",
          "statement": "Specific factual assertion from the sources",
          "supporting_sources": ["S1", "S2"],
          "confidence": "High",
          "evidence": "Specific data point or quote supporting this claim"
        }}
      ],
      "consensus_summary": "Summary of what sources agree on under this theme"
    }}
  ],
  "conflicts": [
    {{
      "conflict_id": "CF1",
      "topic": "What the disagreement is about",
      "side_a": "First perspective",
      "side_a_sources": ["S1"],
      "side_b": "Opposing perspective",
      "side_b_sources": ["S2"],
      "resolution_or_assessment": "Why this disagreement exists"
    }}
  ],
  "key_takeaways": [
    "Takeaway 1",
    "Takeaway 2",
    "Takeaway 3"
  ]
}}"""

        response_raw = llm_client.complete(prompt, json_mode=True)

        # ── Step 3: Parse and Validate Citations ──
        self._notify(
            "Validating Citations",
            "Verifying all cited source IDs exist in the ResearchPacket...",
            status="running"
        )

        findings: List[Finding] = []
        conflicts: List[Conflict] = []
        takeaways: List[str] = []
        citation_stats: Dict[str, int] = {"total_cited": 0, "valid": 0, "stripped": 0}

        try:
            parsed = json.loads(response_raw)

            # Parse findings with citation validation
            for f_data in parsed.get("findings", []):
                validated_claims: List[Claim] = []
                for i, c in enumerate(f_data.get("claims", [])):
                    raw_sources = c.get("supporting_sources", [])
                    validated_sources = self._validate_source_ids(raw_sources, valid_source_ids)

                    citation_stats["total_cited"] += len(raw_sources)
                    citation_stats["valid"] += len(validated_sources)
                    citation_stats["stripped"] += len(raw_sources) - len(validated_sources)

                    # Only include claims that still have at least one valid source
                    if validated_sources:
                        validated_claims.append(Claim(
                            claim_id=c.get("claim_id", f"C{i+1}"),
                            statement=c.get("statement", ""),
                            supporting_sources=validated_sources,
                            confidence=c.get("confidence", "Medium"),
                            evidence=c.get("evidence", "")
                        ))
                    else:
                        logger.warning(
                            f"Dropped claim '{c.get('statement', '')[:50]}...' — "
                            f"no valid source IDs after validation"
                        )

                if validated_claims:
                    findings.append(Finding(
                        theme=f_data.get("theme", "General Findings"),
                        claims=validated_claims,
                        consensus_summary=f_data.get("consensus_summary", "")
                    ))

            # Parse conflicts with citation validation
            for cf in parsed.get("conflicts", []):
                side_a_sources = self._validate_source_ids(
                    cf.get("side_a_sources", []), valid_source_ids
                )
                side_b_sources = self._validate_source_ids(
                    cf.get("side_b_sources", []), valid_source_ids
                )

                conflicts.append(Conflict(
                    conflict_id=cf.get("conflict_id", "CF1"),
                    topic=cf.get("topic", "Divergent perspectives"),
                    side_a=cf.get("side_a", ""),
                    side_a_sources=side_a_sources,
                    side_b=cf.get("side_b", ""),
                    side_b_sources=side_b_sources,
                    resolution_or_assessment=cf.get("resolution_or_assessment", "")
                ))

            takeaways = parsed.get("key_takeaways", [])

            if not findings:
                raise ValueError("Groq returned analysis JSON with empty findings after citation validation.")

        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Analysis Agent: Groq returned unparseable JSON: {e}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Analysis Agent failed to parse Groq analysis: {e}") from e

        # ── Step 4: Package into AnalysisPacket ──
        analysis = AnalysisPacket(
            topic=packet.topic,
            findings=findings,
            conflicts=conflicts,
            key_takeaways=takeaways
        )

        self._notify(
            "Completed",
            f"Evidence examination complete: {len(findings)} findings, "
            f"{len(conflicts)} conflicts, {len(takeaways)} takeaways. "
            f"Citations validated: {citation_stats['valid']}/{citation_stats['total_cited']} "
            f"({citation_stats['stripped']} invalid stripped).",
            status="completed",
            data={
                "finding_count": len(findings),
                "conflict_count": len(conflicts),
                "takeaway_count": len(takeaways),
                "citation_validation": citation_stats
            }
        )

        return analysis
