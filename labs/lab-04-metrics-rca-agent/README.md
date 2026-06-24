# Lab 04 - Metrics + RCA Agent

This lab extends Lab 03 by adding service metrics and RCA-style incident analysis.

The agent now uses:

- DevOps runbooks from `docs/`
- application logs from `data/logs/`
- service metrics from `data/metrics/`
- LangGraph workflow orchestration
- Qdrant for runbook retrieval
- Ollama for local LLM and embeddings

## Architecture

```text
User
  ↓
FastAPI /chat
  ↓
LangGraph
  ├── retrieve_runbooks
  ├── analyze_logs
  ├── analyze_metrics
  └── devops_agent
  ↓
RCA-style answer with sources
