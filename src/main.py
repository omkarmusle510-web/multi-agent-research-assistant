"""Command-Line Interface (CLI) entry point for the Multi-Agent Research Assistant."""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Add project root to sys.path to allow execution directly via `python src/main.py`
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import settings
from src.models import AgentEvent
from src.orchestrator import ResearchOrchestrator


def setup_logging(verbose: bool):
    """Configure terminal logging format."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )


# ANSI Color formatting for terminal output
RESET = "\033[0m"
BOLD = "\033[1m"
BLUE = "\033[94m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"

AGENT_COLORS = {
    "Orchestrator": BOLD + CYAN,
    "Research Agent": BOLD + BLUE,
    "Analysis Agent": BOLD + MAGENTA,
    "Report Agent": BOLD + GREEN,
}


def print_cli_event(event: AgentEvent):
    """Print beautifully styled live progress updates in the terminal."""
    color = AGENT_COLORS.get(event.agent, BOLD)
    status_icon = "✓" if event.status == "completed" else "→"
    if event.status == "error":
        status_icon = "✗"
    
    prefix = f"{color}[{event.agent}]{RESET} {status_icon} {BOLD}{event.step}:{RESET}"
    print(f"{prefix} {event.message}")
    
    if event.data and "queries" in event.data:
        for q in event.data["queries"]:
            print(f"    {YELLOW}• Query:{RESET} {q}")
    if event.data and "takeaways" in event.data:
        for t in event.data["takeaways"]:
            print(f"    {GREEN}• Key Takeaway:{RESET} {t}")


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Agent Research Assistant: Autonomous Research, Analysis & Dossier Synthesis."
    )
    parser.add_argument(
        "topic",
        nargs="?",
        default=None,
        help="The research topic to investigate."
    )
    parser.add_argument(
        "--topic",
        dest="topic_flag",
        default=None,
        help="Alternative flag to specify research topic."
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Force offline mock mode (runs instantaneously without requiring API keys)."
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "groq", "ollama", "mock"],
        default=None,
        help="Override LLM provider."
    )
    parser.add_argument(
        "--search",
        choices=["duckduckgo", "tavily", "mock"],
        default=None,
        help="Override web search provider."
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Custom destination path for the generated markdown report."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw structured JSON of the FinalReport to stdout."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose debugging output."
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Handle provider overrides
    if args.mock:
        settings.LLM_PROVIDER = "mock"
        settings.SEARCH_PROVIDER = "mock"
    if args.provider:
        settings.LLM_PROVIDER = args.provider
    if args.search:
        settings.SEARCH_PROVIDER = args.search

    # Determine topic
    topic = args.topic or args.topic_flag
    if not topic:
        print(f"\n{BOLD}{CYAN}=== Multi-Agent Research Assistant ==={RESET}")
        print("Agents: Research Agent ➔ Analysis Agent ➔ Report Agent\n")
        try:
            topic_input = input("Enter research topic [Default: 'Solid-State Batteries vs Lithium-Ion']: ").strip()
            topic = topic_input if topic_input else "Solid-State Batteries vs Lithium-Ion"
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

    print(f"\n{BOLD}Research Topic:{RESET} {CYAN}{topic}{RESET}")
    print(f"{BOLD}LLM Provider:{RESET} {settings.LLM_PROVIDER} | {BOLD}Search Provider:{RESET} {settings.SEARCH_PROVIDER}\n")
    print(f"{'-' * 60}\n")

    orchestrator = ResearchOrchestrator(on_event=print_cli_event)

    try:
        report = orchestrator.run(topic, save_output=True, output_path=args.output)
    except Exception as e:
        print(f"\n\033[91mError during execution: {e}\033[0m")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

    print(f"\n{'-' * 60}")
    print(f"{BOLD}{GREEN}✓ Research Pipeline Completed Successfully!{RESET}\n")

    if args.json:
        print(json.dumps(report.model_dump(), indent=2))
    else:
        print(f"{BOLD}Report Highlights:{RESET}")
        print(f"• Executive Summary length: {len(report.executive_summary.split())} words")
        print(f"• Sections generated: {len(report.sections)}")
        print(f"• Sources cited: {len(report.sources)}")
        print(f"• Conflicts identified: {len(report.conflict_analysis)}")
        print(f"\n{BOLD}Saved Dossier Location:{RESET} {args.output or settings.OUTPUT_DIR}")


if __name__ == "__main__":
    main()
