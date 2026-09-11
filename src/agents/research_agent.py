"""Research Agent (Layer 3): Topic decomposition, query generation, and live evidence collection.

Role: EVIDENCE COLLECTOR
- Decomposes the user's research question into focused subtopics
- Generates precise, targeted search queries (ONE Groq call)
- Executes bounded web searches via Tavily (MAX 3 queries x 3 results)
- Produces a structured ResearchPacket with application-assigned source IDs
- NEVER fabricates URLs, titles, or source content
- Does NOT analyze or synthesize — that is the Analysis Agent's job
"""

import json
import logging
from typing import Callable, List, Optional

from src.config import settings
from src.llm import llm_client
from src.models import AgentEvent, ResearchPacket, SearchQuery, SourceDocument
from src.tools.web_search import search_tool

logger = logging.getLogger(__name__)


class ResearchAgent:
    """Evidence Collector: decomposes topics, generates queries, gathers real web sources."""

    def __init__(self, on_event: Optional[Callable[[AgentEvent], None]] = None):
        self.on_event = on_event or (lambda ev: None)

    def _notify(self, step: str, message: str, status: str = "running", data: Optional[dict] = None):
        event = AgentEvent(
            agent="Research Agent",
            step=step,
            status=status,
            message=message,
            data=data
        )
        self.on_event(event)

    def run(self, topic: str) -> ResearchPacket:
        """Execute the complete evidence collection pipeline for the given topic.

        Pipeline:
            1. [Groq call] Decompose topic into subtopics and generate search queries
            2. [Tavily calls] Execute bounded web searches across queries
            3. [Local] Re-index sources with deterministic IDs (S1, S2, ...)
            4. Package everything into a ResearchPacket

        Args:
            topic: The user's research question or topic.

        Returns:
            ResearchPacket with real web evidence, never fabricated data.

        Raises:
            RuntimeError: If Groq fails to produce parseable query plan.
        """
        logger.info(f"Research Agent starting for topic: {topic}")
        self._notify("Started", f"Research Agent activated for: '{topic}'", status="started")

        # ── Step 1: Topic Decomposition & Query Generation (ONE Groq call) ──
        self._notify(
            "Planning",
            f"Decomposing topic into subtopics and generating search queries...",
            status="running"
        )

        prompt = f"""You are a Research Planning specialist. Your ONLY job is to break down a research topic into focused subtopics and generate precise web search queries. You do NOT analyze or synthesize — you plan the evidence collection.

Task: Decompose the following research topic into 3 distinct investigation angles and generate one focused web search query for each angle.

Topic: "{topic}"

Rules:
- Each query should target a different dimension of the topic (e.g., technical foundations, real-world adoption, challenges/risks)
- Queries must be specific enough to return high-quality, recent results
- Do NOT generate generic queries — each must investigate a distinct facet

Respond strictly with valid JSON conforming to this exact schema:
{{
  "subtopics": ["subtopic 1", "subtopic 2", "subtopic 3"],
  "queries": [
    {{
      "query": "specific web search query string",
      "aspect": "dimension being investigated",
      "rationale": "why this query is essential for the research"
    }}
  ],
  "summary": "One-sentence overview of the research scope"
}}"""

        response_raw = llm_client.complete(prompt, json_mode=True)

        subtopics: List[str] = []
        queries: List[SearchQuery] = []
        preliminary_summary = ""

        try:
            parsed = json.loads(response_raw)
            subtopics = parsed.get("subtopics", [])
            for q_dict in parsed.get("queries", []):
                queries.append(SearchQuery(
                    query=q_dict.get("query", topic),
                    aspect=q_dict.get("aspect", "General"),
                    rationale=q_dict.get("rationale", "Provide background context")
                ))
            preliminary_summary = parsed.get("summary", f"Research breakdown for {topic}")
            if not queries:
                raise ValueError("Groq returned an empty query list in response JSON.")
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Research Agent: Groq returned unparseable JSON for topic decomposition: {e}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Research Agent failed to process Groq breakdown: {e}") from e

        # Enforce bounded query count (MAX_SEARCH_QUERIES, default 3)
        bounded_queries = queries[:settings.MAX_SEARCH_QUERIES]

        self._notify(
            "Planning Complete",
            f"Generated {len(bounded_queries)} targeted queries across {len(subtopics)} subtopics.",
            status="running",
            data={"queries": [q.query for q in bounded_queries], "subtopics": subtopics}
        )

        # ── Step 2: Live Web Evidence Gathering (Tavily, bounded) ──
        self._notify(
            "Searching",
            f"Executing {len(bounded_queries)} web searches (max {settings.MAX_RESULTS_PER_QUERY} results each)...",
            status="running"
        )

        raw_documents: List[SourceDocument] = []
        seen_urls: set = set()

        for i, q in enumerate(bounded_queries, 1):
            logger.info(f"Search {i}/{len(bounded_queries)}: {q.query}")
            try:
                results = search_tool.search(
                    q.query,
                    max_results=settings.MAX_RESULTS_PER_QUERY,
                    start_id=len(raw_documents) + 1,
                    seen_urls=seen_urls
                )
                raw_documents.extend(results)
            except RuntimeError as e:
                logger.error(f"Search failed for query '{q.query}': {e}")
                # Continue with remaining queries rather than aborting entirely
                continue

        if not raw_documents:
            raise RuntimeError(
                "Research Agent: All web searches returned zero results. "
                "Cannot proceed without evidence."
            )

        # ── Step 3: Re-index Sources with Deterministic IDs ──
        self._notify(
            "Indexing",
            f"Indexing and de-duplicating {len(raw_documents)} source documents...",
            status="running"
        )

        curated_sources: List[SourceDocument] = []
        for idx, doc in enumerate(raw_documents, 1):
            curated_sources.append(SourceDocument(
                id=f"S{idx}",
                title=doc.title,
                url=doc.url,
                snippet=doc.snippet,
                published_date=doc.published_date,
                relevance_score=doc.relevance_score
            ))

        # ── Step 4: Package into ResearchPacket ──
        packet = ResearchPacket(
            topic=topic,
            subtopics=subtopics,
            search_queries=bounded_queries,
            sources=curated_sources,
            summary=preliminary_summary
        )

        self._notify(
            "Completed",
            f"Evidence collection complete: {len(curated_sources)} sources across {len(bounded_queries)} queries.",
            status="completed",
            data={
                "source_count": len(curated_sources),
                "query_count": len(bounded_queries),
                "sources": [f"[{s.id}] {s.title}" for s in curated_sources]
            }
        )

        return packet
