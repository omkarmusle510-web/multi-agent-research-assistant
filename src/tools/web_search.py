"""Real Tavily Web Search implementation (Layer 2).

Provides live web search via the official Tavily Python SDK, mapping real web evidence
into typed SourceDocument contracts with deterministic application-assigned source IDs
and URL deduplication. No mock or fallback search providers.
"""

import logging
from typing import List, Optional, Set
from tavily import TavilyClient

from src.config import settings
from src.models import SourceDocument

logger = logging.getLogger(__name__)


class WebSearchTool:
    """Real web search tool powered exclusively by Tavily API."""

    def __init__(self):
        self._client: Optional[TavilyClient] = None

    def _get_client(self) -> TavilyClient:
        """Lazily initialize and return the Tavily client, validating credentials."""
        settings.validate_tavily_credentials()
        if self._client is None or self._client.api_key != settings.TAVILY_API_KEY:
            self._client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        return self._client

    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        start_id: int = 1,
        seen_urls: Optional[Set[str]] = None,
    ) -> List[SourceDocument]:
        """Execute a live search query via Tavily and return validated SourceDocuments.
        
        Args:
            query: The search query string.
            max_results: Maximum results to return (bounded to settings.MAX_RESULTS_PER_QUERY).
            start_id: Starting integer for assigning sequential source IDs (e.g. 1 -> S1).
            seen_urls: Optional set of already-seen URLs to avoid duplication across queries.
            
        Returns:
            List of SourceDocument instances with application-assigned IDs (S1, S2...).
            
        Raises:
            ValueError: If TAVILY_API_KEY is missing or query is empty.
            RuntimeError: If Tavily API call fails.
        """
        clean_query = query.strip()
        if not clean_query:
            raise ValueError("Search query cannot be empty.")

        client = self._get_client()
        limit = min(max_results or settings.MAX_RESULTS_PER_QUERY, 5)

        logger.info(f"Executing real Tavily search for: '{clean_query}' (limit={limit})")

        try:
            raw_response = client.search(
                query=clean_query,
                max_results=limit,
                search_depth="basic",
                include_answer=False,
                include_raw_content=False,
            )
        except Exception as e:
            error_msg = str(e)
            if "unauthorized" in error_msg.lower() or "api key" in error_msg.lower():
                raise RuntimeError(
                    f"Tavily Authentication Error: Invalid or expired TAVILY_API_KEY. Details: {e}"
                ) from e
            raise RuntimeError(f"Tavily API request failed for query '{clean_query}': {e}") from e

        results = raw_response.get("results", [])
        if not results:
            logger.warning(f"Tavily returned 0 results for query: '{clean_query}'")
            return []

        if seen_urls is None:
            seen_urls = set()

        documents: List[SourceDocument] = []
        current_id_counter = start_id

        for item in results:
            url = item.get("url", "").strip()
            if not url or url in seen_urls:
                continue

            seen_urls.add(url)
            title = item.get("title", "").strip() or "Untitled Document"
            snippet = item.get("content", "").strip()
            published_date = item.get("published_date")
            raw_score = item.get("score")
            
            # Normalize relevance score between 0.0 and 1.0
            relevance = 0.8
            if raw_score is not None:
                try:
                    relevance = max(0.0, min(1.0, float(raw_score)))
                except (ValueError, TypeError):
                    relevance = 0.8

            doc = SourceDocument(
                id=f"S{current_id_counter}",
                title=title,
                url=url,
                snippet=snippet,
                content=None,
                published_date=str(published_date) if published_date else None,
                relevance_score=relevance,
            )
            documents.append(doc)
            current_id_counter += 1

        return documents

    def search_bounded_queries(
        self,
        queries: List[str],
        max_queries: Optional[int] = None,
        max_results_per_query: Optional[int] = None,
    ) -> List[SourceDocument]:
        """Execute a bounded batch of queries, deduplicating across the batch.
        
        Enforces MAX_SEARCH_QUERIES (default 3) and MAX_RESULTS_PER_QUERY (default 3).
        """
        query_cap = min(max_queries or settings.MAX_SEARCH_QUERIES, len(queries))
        per_query_limit = max_results_per_query or settings.MAX_RESULTS_PER_QUERY

        bounded_queries = queries[:query_cap]
        all_documents: List[SourceDocument] = []
        seen_urls: Set[str] = set()

        for q in bounded_queries:
            docs = self.search(
                query=q,
                max_results=per_query_limit,
                start_id=len(all_documents) + 1,
                seen_urls=seen_urls,
            )
            all_documents.extend(docs)

        return all_documents


# Singleton search tool instance
search_tool = WebSearchTool()
