"""Orchestrator: Coordinates multi-agent pipeline execution and intermediate state transitions."""

import logging
from pathlib import Path
from typing import Callable, Optional

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


class ResearchOrchestrator:
    """Master orchestrator executing the 3-stage agent workflow: Research -> Analysis -> Report."""

    def __init__(self, on_event: Optional[Callable[[AgentEvent], None]] = None):
        self.on_event = on_event or (lambda ev: None)
        self.research_packet: Optional[ResearchPacket] = None
        self.analysis_packet: Optional[AnalysisPacket] = None
        self.final_report: Optional[FinalReport] = None

    def _notify(self, agent: str, step: str, message: str, status: str = "running", data: Optional[dict] = None):
        event = AgentEvent(
            agent=agent,
            step=step,
            status=status,
            message=message,
            data=data
        )
        self.on_event(event)

    def run(self, topic: str, save_output: bool = True, output_path: Optional[str] = None) -> FinalReport:
        """Execute the full end-to-end multi-agent research workflow.
        
        Args:
            topic: The research subject query provided by the user.
            save_output: Whether to automatically save the markdown report to disk.
            output_path: Optional specific file path for report destination.
            
        Returns:
            FinalReport object containing structured sections, citations, and markdown.
        """
        clean_topic = topic.strip()
        if not clean_topic:
            raise ValueError("Research topic cannot be empty.")

        logger.info(f"Starting Multi-Agent Research workflow for: '{clean_topic}'")
        self._notify(
            "Orchestrator",
            "Pipeline Initialization",
            f"Initiating research lifecycle for: '{clean_topic}'",
            status="started"
        )

        # Stage 1: Research Agent (Breakdown, Search, Source Gathering)
        self._notify("Orchestrator", "Stage 1", "Dispatching task to Research Agent...", status="running")
        research_agent = ResearchAgent(on_event=self.on_event)
        self.research_packet = research_agent.run(clean_topic)

        if not self.research_packet.sources:
            logger.warning("Research Agent returned no sources. Continuing with fallback synthesis.")

        # Stage 2: Analysis Agent (Comparison, Claims, Conflict Detection)
        self._notify(
            "Orchestrator",
            "Stage 2",
            f"Passing ResearchPacket ({len(self.research_packet.sources)} sources) to Analysis Agent...",
            status="running"
        )
        analysis_agent = AnalysisAgent(on_event=self.on_event)
        self.analysis_packet = analysis_agent.run(self.research_packet)

        # Stage 3: Report Agent (Synthesis, Citations, Final Dossier)
        self._notify(
            "Orchestrator",
            "Stage 3",
            f"Passing AnalysisPacket ({len(self.analysis_packet.findings)} findings) to Report Agent...",
            status="running"
        )
        report_agent = ReportAgent(on_event=self.on_event)
        self.final_report = report_agent.run(self.analysis_packet, self.research_packet)

        # Optional: Persist Report to File
        if save_output:
            out_file = self._save_report_to_disk(clean_topic, self.final_report, output_path)
            self._notify(
                "Orchestrator",
                "Persistence",
                f"Saved final research dossier to: {out_file}",
                status="completed",
                data={"output_file": str(out_file)}
            )

        self._notify(
            "Orchestrator",
            "Pipeline Complete",
            f"Multi-agent research pipeline finished successfully for: '{clean_topic}'",
            status="completed"
        )

        return self.final_report

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

