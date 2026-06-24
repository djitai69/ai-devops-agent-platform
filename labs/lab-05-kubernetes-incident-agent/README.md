# Lab 05 - Kubernetes Incident Agent

This lab extends Lab 04 by adding Kubernetes incident evidence.

The agent now uses:

- DevOps runbooks from `docs/`
- application logs from `data/logs/`
- service metrics from `data/metrics/`
- Kubernetes snapshots from `data/k8s/`
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
  ├── analyze_k8s
  └── devops_agent
  ↓
RCA-style answer with sources
