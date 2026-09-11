from pydantic import BaseModel
from typing import List


class Source(BaseModel):
    title: str
    url: str
    snippet: str
    relevance: float = 0.0


class ResearchPacket(BaseModel):
    topic: str
    queries: List[str]
    sources: List[Source]


class AnalysisPacket(BaseModel):
    key_findings: List[str]
    evidence: List[str]
    contradictions: List[str]
    confidence: str


class FinalReport(BaseModel):
    title: str
    executive_summary: str
    key_findings: List[str]
    evidence: List[str]
    limitations: List[str]
    conclusion: str