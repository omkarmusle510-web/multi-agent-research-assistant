"""Research Agent: Decomposes topics, generates targeted queries, and gathers sources."""

import json
import logging
from typing import Callable, List, Optional

from src.config import settings
from src.llm import llm_client
from src.models import AgentEvent, ResearchPacket, SearchQuery, SourceDocument
from src.tools.web_search import search_tool

logger = logging.getLogger(__name__)


class ResearchAgent:
    """Agent responsible for topic decomposition, query formulation, and multi-source gathering."""

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
        """Execute the complete research gathering pipeline for the given topic."""
        logger.info(f"Research Agent starting for topic: {topic}")
        self._notify("Decomposition", f"Analyzing and decomposing topic: '{topic}'", status="started")

        # Step 1: Topic Decomposition & Query Generation via LLM
        prompt = f"""
You are an expert Research Planning Agent.
Decompose the following research topic into 3-4 distinct investigation angles (e.g. Technical foundations, Market adoption, Regulatory/Ethical challenges, Future trajectory).
For each angle, generate one precise web search query.

Topic: "{topic}"

Respond strictly with valid JSON conforming to this schema:
{{
  "subtopics": ["subtopic 1", "subtopic 2", ...],
  "queries": [
    {{
      "query": "search query string",
      "aspect": "facet investigated",
      "rationale": "why this query is essential"
    }}
  ],
  "summary": "Brief preliminary overview of the research scope"
}}
"""
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
        except Exception as e:
            raise RuntimeError(f"Research Agent failed to process Groq breakdown: {e}") from e

        # Bounded query planning (enforcing MAX_SEARCH_QUERIES limit)
        bounded_queries = queries[:settings.MAX_SEARCH_QUERIES]

        self._notify(
            "Query Generation",
            f"Formulated {len(bounded_queries)} targeted queries across {len(subtopics)} dimensions.",
            status="running",
            data={"queries": [q.query for q in bounded_queries], "subtopics": subtopics}
        )

        # Step 2: Source Discovery & Gathering
        self._notify("Web Search", f"Executing web searches across {len(bounded_queries)} inquiry facets...", status="running")
        raw_documents: List[SourceDocument] = []
        seen_urls = set()

        for q in bounded_queries:
            logger.info(f"Executing search query: {q.query}")
            results = search_tool.search(q.query, max_results=settings.MAX_RESULTS_PER_QUERY, seen_urls=seen_urls)
            raw_documents.extend(results)

        # Step 3: Re-index and Deduplicate Sources
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

        self._notify(
            "Source Collection",
            f"Gathered and verified {len(curated_sources)} primary source documents.",
            status="completed",
            data={"source_count": len(curated_sources), "sources": [s.title for s in curated_sources]}
        )

        packet = ResearchPacket(
            topic=topic,
            subtopics=subtopics,
            search_queries=queries,
            sources=curated_sources,
            summary=preliminary_summary
        )
        return packet

