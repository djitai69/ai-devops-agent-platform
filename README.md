# AI DevOps Agent Platform

A local-first AI DevOps/SRE agent platform.

## Goal

Build an AI DevOps Engineer that can:

- answer questions from DevOps runbooks
- analyze logs
- inspect metrics
- investigate Kubernetes incidents
- generate RCA reports
- suggest Terraform/Kubernetes fixes
- prepare GitHub pull requests with human approval

## Labs

The platform is built up sprint by sprint. Each lab is a self-contained,
runnable stack with its own README.

| Lab | Sprint | Focus |
|---|---|---|
| [lab-01-local-agent-stack](labs/lab-01-local-agent-stack) | 1 | Local agent foundation — Dockerized stack + single LLM-node LangGraph agent |
| [lab-02-runbook-rag](labs/lab-02-runbook-rag) | 2 | Runbook RAG — Qdrant vector store, Ollama embeddings, grounded answers with sources |
| [lab-03-log-analysis-agent](labs/lab-03-log-analysis-agent) | 3 | Log analysis — runbook RAG + application log analysis over a LangGraph workflow |

`final-platform/` holds the consolidated platform (work in progress).

## Stack

- Docker Compose
- Ollama
- OpenWebUI
- LangGraph
- FastAPI
- PostgreSQL
- Qdrant

## Run locally

Each lab runs on its own. Pick one and follow its README:

```bash
cd labs/lab-02-runbook-rag
docker compose up -d --build
docker exec -it ai-devops-ollama ollama pull llama3.2:3b
```
