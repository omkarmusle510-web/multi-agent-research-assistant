"""Layer 2 Validation Suite: Real Groq Intelligence & Real Tavily Web Search.

Validates:
1. Configuration loads GROQ_API_KEY and TAVILY_API_KEY securely.
2. Real minimal Groq API call succeeds with deterministic output ('GROQ_OK').
3. Real Groq JSON mode output successfully parses into agent domain structures (SearchQuery).
4. Real minimal Tavily search call succeeds with live results.
5. Tavily results map strictly to typed SourceDocument contracts.
6. Application assigns deterministic source IDs (S1, S2...) and deduplicates by URL.
7. Bounded search constraints are respected (MAX_SEARCH_QUERIES=3, MAX_RESULTS_PER_QUERY=3).
8. Missing credentials produce explicit errors instead of silent fake research fallbacks.
9. Layer 1 contracts remain intact and backward-compatible.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.config import settings
from src.llm import llm_client
from src.models import SearchQuery, SourceDocument
from src.tools.web_search import search_tool


def test_1_credentials_loaded():
    """Verify credentials exist in configuration without printing secrets."""
    print("Test 1: Verifying credentials in environment/config...")
    assert settings.has_groq_credentials, "GROQ_API_KEY is not configured or is empty."
    assert settings.has_tavily_credentials, "TAVILY_API_KEY is not configured or is empty."
    assert len(settings.GROQ_API_KEY) > 10, "GROQ_API_KEY appears suspiciously short."
    assert len(settings.TAVILY_API_KEY) > 10, "TAVILY_API_KEY appears suspiciously short."
    print("  -> PASS: Both GROQ_API_KEY and TAVILY_API_KEY are loaded securely.")


def test_2_real_groq_minimal_call():
    """Verify a real minimal Groq call produces the deterministic response 'GROQ_OK'."""
    print("\nTest 2: Executing minimal REAL Groq API call...")
    prompt = "Respond with ONLY the exact word GROQ_OK and no other text."
    
    # Minimal token usage for free-tier budget safety
    response = llm_client.complete(
        prompt=prompt,
        temperature=0.0,
        max_tokens=10,
        json_mode=False
    )
    print(f"  -> Real Groq Response: '{response}'")
    assert "GROQ_OK" in response, f"Expected 'GROQ_OK' in response, got: '{response}'"
    print("  -> PASS: Real Groq call succeeded with verified output.")


def test_3_real_groq_structured_json():
    """Verify real Groq structured JSON parsing into agent contracts (SearchQuery)."""
    print("\nTest 3: Executing real Groq JSON mode call for agent query schema...")
    prompt = """
Respond strictly with valid JSON conforming to this format:
{
  "subtopics": ["Solar Photovoltaics", "Wind Energy"],
  "queries": [
    {
      "query": "solar photovoltaic efficiency advances 2026",
      "aspect": "Efficiency Metrics",
      "rationale": "Identify recent cell efficiency benchmarks"
    }
  ]
}
Topic: Renewable Energy.
"""
    # Use max_tokens=150 to keep free-tier token usage bounded and cheap
    parsed = llm_client.complete_json(
        prompt=prompt,
        temperature=0.1,
        max_tokens=150
    )
    assert isinstance(parsed, dict), "Groq response did not parse as a dict."
    assert "queries" in parsed, "JSON missing 'queries' key."
    assert len(parsed["queries"]) > 0, "JSON queries list is empty."

    # Validate mapping directly into Layer 1 SearchQuery contract
    first_q = parsed["queries"][0]
    sq = SearchQuery(
        query=first_q.get("query", ""),
        aspect=first_q.get("aspect", "General"),
        rationale=first_q.get("rationale", "")
    )
    assert sq.query != "", "SearchQuery query string cannot be empty."
    assert sq.aspect != "", "SearchQuery aspect cannot be empty."
    print(f"  -> Successfully parsed into SearchQuery: '{sq.query}' [{sq.aspect}]")
    print("  -> PASS: Real Groq structured JSON parses cleanly into Layer 1 models.")


def test_4_real_tavily_minimal_call():
    """Verify a real minimal Tavily search call returns live evidence and maps to SourceDocument."""
    print("\nTest 4: Executing minimal REAL Tavily search call...")
    query = "Python programming language python.org"
    
    # Bounded query with max_results=2 for budget safety
    docs = search_tool.search(query=query, max_results=2)
    
    assert isinstance(docs, list), "Expected list of SourceDocument from search."
    assert len(docs) >= 1, "Tavily returned 0 results for factual query."
    
    doc = docs[0]
    assert isinstance(doc, SourceDocument), f"Expected SourceDocument instance, got {type(doc)}"
    assert doc.id == "S1", f"Expected first source ID to be 'S1', got '{doc.id}'"
    assert doc.title != "", "SourceDocument title is empty."
    assert doc.url.startswith("http://") or doc.url.startswith("https://"), f"Invalid real URL: {doc.url}"
    assert "python" in doc.url.lower() or "python" in doc.title.lower(), "Result does not match query domain."
    assert doc.snippet != "", "SourceDocument snippet is empty."
    assert 0.0 <= doc.relevance_score <= 1.0, f"Invalid relevance score: {doc.relevance_score}"

    print(f"  -> Discovered Real Source [{doc.id}]: '{doc.title}' ({doc.url})")
    print("  -> PASS: Real Tavily search succeeded and mapped into SourceDocument contract.")
    return docs


def test_5_source_id_determinism_and_deduplication():
    """Verify application source ID assignment and URL deduplication."""
    print("\nTest 5: Verifying URL deduplication and deterministic source IDs...")
    seen_urls = set()

    # Query 1
    docs1 = search_tool.search("Python language official site", max_results=2, start_id=1, seen_urls=seen_urls)
    count1 = len(docs1)
    assert count1 >= 1

    # Query 2 with overlapping expected URLs (should deduplicate)
    docs2 = search_tool.search("Python software foundation python.org", max_results=2, start_id=count1 + 1, seen_urls=seen_urls)
    
    # Verify IDs are sequential
    for i, d in enumerate(docs1, 1):
        assert d.id == f"S{i}", f"Expected ID S{i}, got {d.id}"
    
    for j, d in enumerate(docs2, count1 + 1):
        assert d.id == f"S{j}", f"Expected ID S{j}, got {d.id}"

    # Verify no duplicate URLs exist between docs1 and docs2
    urls1 = {d.url for d in docs1}
    urls2 = {d.url for d in docs2}
    intersection = urls1.intersection(urls2)
    assert len(intersection) == 0, f"Found duplicate URLs across searches: {intersection}"

    print(f"  -> Query 1 yielded {count1} sources, Query 2 yielded {len(docs2)} unique sources (no overlap).")
    print("  -> PASS: Deduplication and sequential ID assignment verified.")


def test_6_search_limits_bounded():
    """Verify search limits adhere strictly to MAX_SEARCH_QUERIES=3 and MAX_RESULTS_PER_QUERY=3."""
    print("\nTest 6: Verifying bounded execution limits...")
    assert settings.MAX_SEARCH_QUERIES == 3, f"Expected MAX_SEARCH_QUERIES=3, got {settings.MAX_SEARCH_QUERIES}"
    assert settings.MAX_RESULTS_PER_QUERY == 3, f"Expected MAX_RESULTS_PER_QUERY=3, got {settings.MAX_RESULTS_PER_QUERY}"
    print("  -> PASS: Execution bounds locked at 3 queries x 3 results.")


def test_7_missing_credentials_raise_explicit_errors():
    """Verify missing credentials raise clear ValueErrors rather than generating fake research."""
    print("\nTest 7: Verifying explicit error handling on missing credentials...")
    from src.config import Settings

    dummy_settings = Settings()
    dummy_settings.GROQ_API_KEY = None
    dummy_settings.TAVILY_API_KEY = ""

    # Test Groq validation
    groq_failed = False
    try:
        dummy_settings.validate_groq_credentials()
    except ValueError as e:
        groq_failed = True
        assert "Missing GROQ_API_KEY" in str(e)

    assert groq_failed, "Expected ValueError when GROQ_API_KEY is missing."

    # Test Tavily validation
    tavily_failed = False
    try:
        dummy_settings.validate_tavily_credentials()
    except ValueError as e:
        tavily_failed = True
        assert "Missing TAVILY_API_KEY" in str(e)

    assert tavily_failed, "Expected ValueError when TAVILY_API_KEY is missing."

    print("  -> PASS: Explicit ValueErrors raised without silent fallbacks or fake research.")


def test_8_layer_1_regression_check():
    """Run Layer 1 contracts validation to guarantee zero regressions."""
    print("\nTest 8: Running Layer 1 contract regression verification...")
    try:
        from tests import test_layer1_contracts as l1
    except ImportError:
        import test_layer1_contracts as l1

    l1.test_imports()
    rp, ap, fr = l1.test_model_instantiations()
    l1.test_research_to_analysis_handoff(rp)
    l1.test_analysis_to_report_handoff(ap, rp)
    l1.test_final_report_markdown_and_citations(fr)
    l1.test_agent_orchestrator_imports()
    print("  -> PASS: Layer 1 contracts 100% compliant.")


def main():
    print("=" * 60)
    print("LAYER 2 VALIDATION SUITE: Real Groq Intelligence + Real Tavily Search")
    print("=" * 60)
    test_1_credentials_loaded()
    test_2_real_groq_minimal_call()
    test_3_real_groq_structured_json()
    test_4_real_tavily_minimal_call()
    test_5_source_id_determinism_and_deduplication()
    test_6_search_limits_bounded()
    test_7_missing_credentials_raise_explicit_errors()
    test_8_layer_1_regression_check()
    print("\n" + "=" * 60)
    print("ALL LAYER 2 REAL INTELLIGENCE & SEARCH TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    main()
