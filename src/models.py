"""Data models and contract schemas for the Multi-Agent Research Assistant."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    """Represents an external information source discovered during research."""
    id: str = Field(..., description="Unique source identifier, e.g. S1, S2")
    title: str = Field(..., description="Title of the article or resource")
    url: str = Field(..., description="Direct URL of the source")
    snippet: str = Field(..., description="Extracted relevant summary or snippet")
    content: Optional[str] = Field(None, description="Full or extended text if fetched")
    published_date: Optional[str] = Field(None, description="Publication date or estimated recency")
    relevance_score: float = Field(default=0.8, ge=0.0, le=1.0, description="Estimated relevance score from 0 to 1")


class SearchQuery(BaseModel):
    """Represents a targeted search query produced during topic decomposition."""
    query: str = Field(..., description="Search query string")
    aspect: str = Field(..., description="Aspect investigated, e.g. technical, economic, challenges")
    rationale: str = Field(..., description="Why this query is crucial for the research")


class ResearchPacket(BaseModel):
    """The structured output contract produced by the Research Agent."""
    topic: str = Field(..., description="The main research topic")
    subtopics: List[str] = Field(default_factory=list, description="Decomposed research facets")
    search_queries: List[SearchQuery] = Field(default_factory=list, description="Executed search queries")
    sources: List[SourceDocument] = Field(default_factory=list, description="Discovered and validated sources")
    summary: str = Field(..., description="High-level synthesis of collected raw information")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Claim(BaseModel):
    """An individual assertion extracted from source documents."""
    claim_id: str = Field(..., description="Unique claim identifier, e.g. C1, C2")
    statement: str = Field(..., description="The core factual or predictive assertion")
    supporting_sources: List[str] = Field(default_factory=list, description="IDs of sources supporting this claim")
    confidence: str = Field(default="Medium", description="Confidence level: High, Medium, or Low")
    evidence: str = Field(..., description="Direct quote or corroborated data points")


class Conflict(BaseModel):
    """Represents opposing or disputed perspectives discovered across sources."""
    conflict_id: str = Field(..., description="Unique conflict ID, e.g. CF1")
    topic: str = Field(..., description="Subject of the dispute or divergence")
    side_a: str = Field(..., description="Perspective or claim A")
    side_a_sources: List[str] = Field(default_factory=list, description="Sources backing side A")
    side_b: str = Field(..., description="Perspective or claim B")
    side_b_sources: List[str] = Field(default_factory=list, description="Sources backing side B")
    resolution_or_assessment: str = Field(..., description="Synthesized neutral evaluation of the conflict")


class Finding(BaseModel):
    """A thematic cluster of synthesized claims."""
    theme: str = Field(..., description="Thematic title of this finding")
    claims: List[Claim] = Field(default_factory=list, description="Underlying verified claims")
    consensus_summary: str = Field(..., description="Overall consensus state across literature")


class AnalysisPacket(BaseModel):
    """The structured output contract produced by the Analysis Agent."""
    topic: str = Field(..., description="Research topic analyzed")
    findings: List[Finding] = Field(default_factory=list, description="Identified factual themes and claims")
    conflicts: List[Conflict] = Field(default_factory=list, description="Contradictions and opposing views")
    key_takeaways: List[str] = Field(default_factory=list, description="High-impact distilled insights")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ReportSection(BaseModel):
    """A discrete structured section of the final research dossier."""
    heading: str = Field(..., description="Section title")
    content: str = Field(..., description="Section markdown body")
    citations: List[str] = Field(default_factory=list, description="Referenced source IDs, e.g. ['S1', 'S3']")


class FinalReport(BaseModel):
    """The complete research dossier produced by the Report Agent."""
    topic: str = Field(..., description="Research topic")
    executive_summary: str = Field(..., description="Concise executive brief")
    sections: List[ReportSection] = Field(default_factory=list, description="Detailed thematic sections")
    key_findings: List[str] = Field(default_factory=list, description="Bulleted key findings")
    conflict_analysis: List[Conflict] = Field(default_factory=list, description="Detected controversies or disputes")
    conclusions: List[str] = Field(default_factory=list, description="Synthesis conclusions")
    recommendations: List[str] = Field(default_factory=list, description="Actionable future recommendations")
    sources: List[SourceDocument] = Field(default_factory=list, description="Full bibliography of cited sources")
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    markdown_content: Optional[str] = Field(None, description="Pre-rendered full markdown document")

    def to_markdown(self) -> str:
        """Render the complete report into structured, publication-ready GitHub Flavored Markdown."""
        lines: List[str] = []
        lines.append(f"# Research Dossier: {self.topic}")
        lines.append(f"\n*Generated by Multi-Agent Research Assistant on {self.generated_at}*\n")
        lines.append("---\n")

        lines.append("## Executive Summary\n")
        lines.append(self.executive_summary.strip() + "\n")

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

        if self.conclusions:
            lines.append("## Conclusions\n")
            for conc in self.conclusions:
                lines.append(f"- {conc}")
            lines.append("")

        if self.recommendations:
            lines.append("## Strategic Recommendations\n")
            for rec in self.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

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
    """Event emitted during execution steps for real-time progress observation."""
    agent: str = Field(..., description="Agent emitting the event")
    step: str = Field(..., description="Current step name")
    status: str = Field(default="running", description="Status: started, running, completed, error")
    message: str = Field(..., description="Human-readable status message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Optional payload or preview data")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
