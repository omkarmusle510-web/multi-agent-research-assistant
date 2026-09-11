"""Data models and typed contracts for the Multi-Agent Research Assistant (Layer 1).

Establishes the typed contract shared across:
- Research Agent (produces ResearchPacket)
- Analysis Agent (ingests ResearchPacket, produces AnalysisPacket)
- Report Agent (ingests AnalysisPacket & ResearchPacket, produces FinalReport)
- Orchestrator (manages handoffs and emits AgentEvents)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    """Represents a real external research source collected during web investigation.
    
    Citations throughout the entire pipeline ([S1], [S2]...) map directly to
    these identifiers and their underlying URLs.
    """
    id: str = Field(..., description="Stable deterministic source ID, e.g. S1, S2")
    title: str = Field(..., description="Title of the research source or article")
    url: str = Field(..., description="Canonical source URL")
    snippet: str = Field(..., description="Extracted content snippet or summary from the source")
    content: Optional[str] = Field(default=None, description="Extended full text content if fetched")
    published_date: Optional[str] = Field(default=None, description="Publication date or recency indicator")
    relevance_score: float = Field(default=0.8, ge=0.0, le=1.0, description="Relevance score between 0.0 and 1.0")

    @property
    def relevance(self) -> float:
        """Alias for backward compatibility."""
        return self.relevance_score


# Source alias for existing code compatibility
Source = SourceDocument


class SearchQuery(BaseModel):
    """Represents a focused query planned by the Research Agent during topic breakdown."""
    query: str = Field(..., description="Search query string dispatched to search provider")
    aspect: str = Field(default="General", description="Research dimension/subtopic being investigated")
    rationale: str = Field(default="", description="Why this query is essential to answer the topic")


class ResearchPacket(BaseModel):
    """Structured handoff artifact: Research Agent -> Analysis Agent."""
    topic: str = Field(..., description="Original user research topic")
    subtopics: List[str] = Field(default_factory=list, description="Decomposed research dimensions")
    search_queries: List[SearchQuery] = Field(default_factory=list, description="Targeted queries planned & executed")
    sources: List[SourceDocument] = Field(default_factory=list, description="Collected and deduplicated sources")
    summary: str = Field(default="", description="Concise research-stage overview of raw findings")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def queries(self) -> List[str]:
        """Convenience property returning query strings for legacy consumers."""
        return [sq.query for sq in self.search_queries]


class Claim(BaseModel):
    """An evidence-backed assertion extracted and verified from source documents."""
    claim_id: str = Field(..., description="Unique claim identifier, e.g. C1, C2")
    statement: str = Field(..., description="The verified assertion or empirical claim")
    supporting_sources: List[str] = Field(
        default_factory=list,
        description="SourceDocument IDs supporting this claim, e.g. ['S1', 'S2']"
    )
    confidence: str = Field(default="Medium", description="Confidence assessment: High, Medium, or Low")
    evidence: str = Field(default="", description="Corroborating excerpt, metric, or explanation from sources")


class Conflict(BaseModel):
    """Represents disagreement, contradiction, or disputed perspectives across sources."""
    conflict_id: str = Field(..., description="Unique conflict identifier, e.g. CF1")
    topic: str = Field(..., description="Subject or facet of the disagreement")
    side_a: str = Field(..., description="First viewpoint or argument")
    side_a_sources: List[str] = Field(default_factory=list, description="SourceDocument IDs backing Side A")
    side_b: str = Field(..., description="Opposing viewpoint or argument")
    side_b_sources: List[str] = Field(default_factory=list, description="SourceDocument IDs backing Side B")
    resolution_or_assessment: str = Field(
        default="",
        description="Analysis Agent's objective evaluation explaining why this divergence exists"
    )


class Finding(BaseModel):
    """A higher-level analytical cluster containing related claims and a consensus assessment."""
    theme: str = Field(..., description="Thematic title of this analytical finding")
    claims: List[Claim] = Field(default_factory=list, description="Evidence-backed claims under this theme")
    consensus_summary: str = Field(default="", description="Summary of consensus or divergence across literature")


class AnalysisPacket(BaseModel):
    """Structured handoff artifact: Analysis Agent -> Report Agent."""
    topic: str = Field(..., description="Original research topic analyzed")
    findings: List[Finding] = Field(default_factory=list, description="Thematic clusters of corroborated claims")
    conflicts: List[Conflict] = Field(default_factory=list, description="Detected disagreements across sources")
    key_takeaways: List[str] = Field(default_factory=list, description="High-impact distilled strategic insights")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def key_findings(self) -> List[str]:
        """Backward compatibility accessor."""
        return self.key_takeaways

    @property
    def contradictions(self) -> List[str]:
        """Backward compatibility accessor for conflict topics."""
        return [c.topic for c in self.conflicts]


class ReportSection(BaseModel):
    """A discrete structured narrative section of the final research dossier."""
    heading: str = Field(..., description="Section title")
    content: str = Field(..., description="Section markdown body text")
    citations: List[str] = Field(
        default_factory=list,
        description="SourceDocument IDs cited in this section, e.g. ['S1', 'S2']"
    )


class FinalReport(BaseModel):
    """The final research product returned to the user by the Report Agent."""
    topic: str = Field(..., description="Research topic investigated")
    executive_summary: str = Field(..., description="Executive brief synthesizing the entire dossier")
    sections: List[ReportSection] = Field(default_factory=list, description="Detailed thematic sections")
    key_findings: List[str] = Field(default_factory=list, description="Key empirical findings")
    conflict_analysis: List[Conflict] = Field(default_factory=list, description="Evaluated conflicts and disputes")
    conclusions: List[str] = Field(default_factory=list, description="Definitive synthesis conclusions")
    recommendations: List[str] = Field(default_factory=list, description="Actionable strategic recommendations")
    sources: List[SourceDocument] = Field(
        default_factory=list,
        description="Bibliography of actual collected sources mapping to [S1], [S2]..."
    )
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    markdown_content: Optional[str] = Field(default=None, description="Pre-rendered full markdown dossier")

    # Optional fields for compatibility with earlier drafts
    title: Optional[str] = None
    evidence: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    conclusion: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.title and self.topic:
            self.title = f"Research Dossier: {self.topic}"
        if not self.topic and self.title:
            self.topic = self.title
        if not self.conclusions and self.conclusion:
            self.conclusions = [self.conclusion]
        elif not self.conclusion and self.conclusions:
            self.conclusion = " ".join(self.conclusions)

    def to_markdown(self) -> str:
        """Render the complete dossier into clean, publication-ready GitHub Flavored Markdown."""
        lines: List[str] = []
        topic_title = self.topic or self.title or "Research Dossier"
        lines.append(f"# Research Dossier: {topic_title}")
        lines.append(f"\n*Generated by Multi-Agent Research Assistant on {self.generated_at}*\n")
        lines.append("---\n")

        lines.append("## Executive Summary\n")
        lines.append(self.executive_summary.strip() + "\n")

        if self.key_findings:
            lines.append("## Key Findings\n")
            for finding in self.key_findings:
                lines.append(f"- {finding}")
            lines.append("")

        for sec in self.sections:
            lines.append(f"## {sec.heading}\n")
            lines.append(sec.content.strip() + "\n")
            if sec.citations:
                cites = ", ".join([f"[{c}]" for c in sec.citations])
                lines.append(f"*Citations: {cites}*\n")

        if self.conflict_analysis:
            lines.append("## Conflict & Disagreement Analysis\n")
            for c in self.conflict_analysis:
                lines.append(f"### Dispute: {c.topic}")
                side_a_cites = f" (Sources: {', '.join(c.side_a_sources)})" if c.side_a_sources else ""
                side_b_cites = f" (Sources: {', '.join(c.side_b_sources)})" if c.side_b_sources else ""
                lines.append(f"- **Viewpoint A**: {c.side_a}{side_a_cites}")
                lines.append(f"- **Viewpoint B**: {c.side_b}{side_b_cites}")
                lines.append(f"- **Assessment**: {c.resolution_or_assessment}\n")

        conclusions_list = self.conclusions or ([self.conclusion] if self.conclusion else [])
        if conclusions_list:
            lines.append("## Conclusions\n")
            for conc in conclusions_list:
                lines.append(f"- {conc}")
            lines.append("")

        if self.limitations:
            lines.append("## Limitations & Caveats\n")
            for lim in self.limitations:
                lines.append(f"- {lim}")
            lines.append("")

        if self.recommendations:
            lines.append("## Strategic Recommendations\n")
            for rec in self.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        if self.sources:
            lines.append("## References & Sources\n")
            for src in self.sources:
                date_str = f" ({src.published_date})" if src.published_date else ""
                lines.append(f"- **[{src.id}]** [{src.title}]({src.url}){date_str}")
                lines.append(f"  > *\"{src.snippet}\"*")
                lines.append(f"  *Relevance: {int(src.relevance_score * 100)}%*\n")

        full_md = "\n".join(lines)
        self.markdown_content = full_md
        return full_md


class AgentEvent(BaseModel):
    """Represents visible workflow activity emitted by agents for UI/CLI progress tracking."""
    agent: str = Field(..., description="Name of the agent emitting the event (e.g. Research Agent)")
    step: str = Field(..., description="Current lifecycle step name")
    status: str = Field(default="running", description="Step status: started, running, completed, error")
    message: str = Field(..., description="Human-readable event message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Optional structured metadata")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())