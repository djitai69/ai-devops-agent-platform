# Lab 03 - Log Analysis Agent

This lab extends Lab 02 by adding application log analysis.

The agent now uses:

- DevOps runbooks from `docs/`
- application logs from `data/logs/`
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
  └── devops_agent
  ↓
Answer with sources
