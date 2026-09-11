"""Orchestrator (Layer 4): Coordinates the three-agent pipeline with visible handoffs.

Owns every transition between agents:
    ResearchAgent -> ResearchPacket -> AnalysisAgent -> AnalysisPacket -> ReportAgent -> FinalReport

The orchestrator:
- Initializes all three agents with a shared event callback
- Runs them in strict sequence, explicitly passing packets at each handoff
- Emits handoff events at every transition so the UI can display the workflow
- Accumulates ALL AgentEvents (from agents + handoffs) in preserved order
- Makes ZERO LLM calls itself
- On agent failure: stops the pipeline, preserves events, surfaces a clear error
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from src.agents.analysis_agent import AnalysisAgent
from src.agents.report_agent import ReportAgent
from src.agents.research_agent import ResearchAgent
from src.config import settings
from src.models import (
    AgentEvent,
    AnalysisPacket,
    FinalReport,
    ResearchPacket,
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Complete execution state returned by the orchestrator.

    Provides the final report plus all intermediate artifacts and events
    so the UI can display the full workflow.
    """
    final_report: FinalReport
    research_packet: ResearchPacket
    analysis_packet: AnalysisPacket
    events: List[AgentEvent] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None


class ResearchOrchestrator:
    """Coordinates the 3-stage agent pipeline: Research -> Analysis -> Report.

    The orchestrator owns every transition. Agents never invoke each other directly.
    """

    def __init__(self, on_event: Optional[Callable[[AgentEvent], None]] = None):
        self._external_callback = on_event or (lambda ev: None)
        self.events: List[AgentEvent] = []
        self.research_packet: Optional[ResearchPacket] = None
        self.analysis_packet: Optional[AnalysisPacket] = None
        self.final_report: Optional[FinalReport] = None

    def _emit(self, agent: str, step: str, message: str, status: str = "running", data: Optional[dict] = None):
        """Create an AgentEvent, store it, and forward to the external callback."""
        event = AgentEvent(
            agent=agent,
            step=step,
            status=status,
            message=message,
            data=data
        )
        self.events.append(event)
        self._external_callback(event)

    def _on_agent_event(self, event: AgentEvent):
        """Receive an event from an agent, store it, and forward to the external callback."""
        self.events.append(event)
        self._external_callback(event)

    def run(self, topic: str, save_output: bool = True, output_path: Optional[str] = None) -> FinalReport:
        """Execute the full three-agent research pipeline.

        Args:
            topic: The user's research question.
            save_output: Whether to save the markdown report to disk.
            output_path: Optional custom file path for the report.

        Returns:
            FinalReport containing the complete research dossier.

        Raises:
            ValueError: If topic is empty.
            RuntimeError: If any agent fails during execution.
        """
        clean_topic = topic.strip()
        if not clean_topic:
            raise ValueError("Research topic cannot be empty.")

        logger.info(f"Orchestrator starting pipeline for: '{clean_topic}'")
        self.events.clear()
        self.research_packet = None
        self.analysis_packet = None
        self.final_report = None

        self._emit(
            "Orchestrator", "Pipeline Started",
            f"Starting research pipeline for: '{clean_topic}'",
            status="started"
        )

        # ── Stage 1: Research Agent ──
        self._emit(
            "Orchestrator", "Stage 1",
            "Dispatching topic to Research Agent for evidence collection...",
            status="running"
        )

        try:
            research_agent = ResearchAgent(on_event=self._on_agent_event)
            self.research_packet = research_agent.run(clean_topic)
        except Exception as e:
            self._emit(
                "Orchestrator", "Pipeline Failed",
                f"Research Agent failed: {e}",
                status="error"
            )
            raise RuntimeError(f"Pipeline aborted: Research Agent failed — {e}") from e

        if not self.research_packet.sources:
            self._emit(
                "Orchestrator", "Pipeline Failed",
                "Research Agent returned zero sources. Cannot proceed without evidence.",
                status="error"
            )
            raise RuntimeError(
                "Pipeline aborted: Research Agent returned zero sources. "
                "Cannot produce a research report without evidence."
            )

        # ── Handoff: ResearchPacket -> Analysis Agent ──
        self._emit(
            "Orchestrator", "Handoff 1",
            f"ResearchPacket produced: {len(self.research_packet.sources)} sources, "
            f"{len(self.research_packet.search_queries)} queries. "
            f"Passing to Analysis Agent...",
            status="running",
            data={
                "packet": "ResearchPacket",
                "source_count": len(self.research_packet.sources),
                "query_count": len(self.research_packet.search_queries),
                "source_ids": [s.id for s in self.research_packet.sources]
            }
        )

        # ── Stage 2: Analysis Agent ──
        try:
            analysis_agent = AnalysisAgent(on_event=self._on_agent_event)
            self.analysis_packet = analysis_agent.run(self.research_packet)
        except Exception as e:
            self._emit(
                "Orchestrator", "Pipeline Failed",
                f"Analysis Agent failed: {e}",
                status="error"
            )
            raise RuntimeError(f"Pipeline aborted: Analysis Agent failed — {e}") from e

        # ── Handoff: AnalysisPacket -> Report Agent ──
        self._emit(
            "Orchestrator", "Handoff 2",
            f"AnalysisPacket produced: {len(self.analysis_packet.findings)} findings, "
            f"{len(self.analysis_packet.conflicts)} conflicts. "
            f"Passing AnalysisPacket + ResearchPacket to Report Agent...",
            status="running",
            data={
                "packet": "AnalysisPacket",
                "finding_count": len(self.analysis_packet.findings),
                "conflict_count": len(self.analysis_packet.conflicts),
                "takeaway_count": len(self.analysis_packet.key_takeaways)
            }
        )

        # ── Stage 3: Report Agent ──
        try:
            report_agent = ReportAgent(on_event=self._on_agent_event)
            self.final_report = report_agent.run(self.analysis_packet, self.research_packet)
        except Exception as e:
            self._emit(
                "Orchestrator", "Pipeline Failed",
                f"Report Agent failed: {e}",
                status="error"
            )
            raise RuntimeError(f"Pipeline aborted: Report Agent failed — {e}") from e

        # ── Final Report Produced ──
        self._emit(
            "Orchestrator", "Report Produced",
            f"FinalReport ready: {len(self.final_report.sections)} sections, "
            f"{len(self.final_report.sources)} sources, "
            f"{len(self.final_report.markdown_content or '')} chars markdown.",
            status="running",
            data={
                "section_count": len(self.final_report.sections),
                "source_count": len(self.final_report.sources),
                "markdown_length": len(self.final_report.markdown_content or "")
            }
        )

        # ── Persist to Disk ──
        if save_output:
            out_file = self._save_report_to_disk(clean_topic, self.final_report, output_path)
            self._emit(
                "Orchestrator", "Report Saved",
                f"Saved research dossier to: {out_file}",
                status="running",
                data={"output_file": str(out_file)}
            )

        self._emit(
            "Orchestrator", "Pipeline Complete",
            f"Research pipeline finished successfully for: '{clean_topic}'",
            status="completed"
        )

        return self.final_report

    def run_with_state(self, topic: str, save_output: bool = True, output_path: Optional[str] = None) -> PipelineResult:
        """Execute the pipeline and return full execution state.

        Convenience method that wraps run() and returns a PipelineResult
        containing the final report, all intermediate packets, and events.
        """
        try:
            report = self.run(topic, save_output=save_output, output_path=output_path)
            return PipelineResult(
                final_report=report,
                research_packet=self.research_packet,
                analysis_packet=self.analysis_packet,
                events=list(self.events),
                success=True
            )
        except Exception as e:
            # Return partial state with error info
            raise  # Re-raise; caller can inspect self.events for partial state

    def _save_report_to_disk(self, topic: str, report: FinalReport, custom_path: Optional[str] = None) -> Path:
        """Save formatted markdown report to disk."""
        if custom_path:
            dest = Path(custom_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
        else:
            safe_slug = "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in topic.lower()])[:40]
            dest = settings.OUTPUT_DIR / f"report_{safe_slug}.md"

        content = report.markdown_content or report.to_markdown()
        with open(dest, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Report saved to: {dest.resolve()}")
        return dest.resolve()
