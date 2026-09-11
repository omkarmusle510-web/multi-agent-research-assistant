                         USER
                           │
                           ▼
                    ┌─────────────┐
                    │ ORCHESTRATOR│
                    └──────┬──────┘
                           │
                    research topic
                           │
                           ▼
              ┌────────────────────────┐
              │  1. RESEARCH AGENT     │
              │                        │
              │ • break topic down     │
              │ • generate queries     │
              │ • web search           │
              │ • collect sources      │
              └───────────┬────────────┘
                          │
                    ResearchPacket
                          │
                          ▼
              ┌────────────────────────┐
              │  2. ANALYSIS AGENT     │
              │                        │
              │ • compare sources      │
              │ • identify findings     │
              │ • detect conflicts     │
              │ • assess evidence      │
              └───────────┬────────────┘
                          │
                    AnalysisPacket
                          │
                          ▼
              ┌────────────────────────┐
              │  3. REPORT AGENT       │
              │                        │
              │ • synthesize findings  │
              │ • executive summary    │
              │ • key findings         │
              │ • evidence/citations   │
              │ • conclusion           │
              └───────────┬────────────┘
                          │
                          ▼
                    FINAL REPORT