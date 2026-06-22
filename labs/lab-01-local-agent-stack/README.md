# Lab 01 — Local Agent Stack

Sprint 1 of the AI DevOps Agent Platform. Stands up the local-first foundation:
a Dockerized stack (Ollama, OpenWebUI, Postgres, Qdrant) and a minimal LangGraph
DevOps agent served over FastAPI. No tools and no RAG yet — the agent answers
from the model's general knowledge only.

## Goal

Lay the groundwork for an AI DevOps Engineer. This lab gets a single LLM agent
running locally end-to-end; later sprints add runbook RAG (Lab 02), tools, and
real cluster/log inspection.

The platform roadmap:

- answer questions from DevOps runbooks
- analyze logs
- inspect metrics
- investigate Kubernetes incidents
- generate RCA reports
- suggest Terraform/Kubernetes fixes
- prepare GitHub pull requests with human approval

## Architecture

```
question
   │
   ▼
devops_agent   ── single LLM node, general knowledge only
   │
   ▼
answer
```

- `app/main.py` — FastAPI app (`/`, `/health`, `POST /chat`)
- `app/graph.py` — LangGraph: single `devops_agent` node
- `docker-compose.yml` — Ollama, OpenWebUI, Postgres, Qdrant, agent-api

Qdrant and Postgres run in the stack but are not used by the agent yet — they're
provisioned here so Lab 02 onward can build on them.

## Stack

- Docker Compose
- Ollama
- OpenWebUI
- LangGraph
- FastAPI
- PostgreSQL
- Qdrant

## Run locally

```bash
docker compose up -d --build

# Pull the chat model
docker exec -it ai-devops-ollama ollama pull llama3.2:3b
```

## Try it

```bash
curl -s http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What does a pod in CrashLoopBackOff usually mean?"}'
```

Response:

```json
{ "answer": "..." }
```

## Services

| Service | URL |
|---|---|
| Agent API | http://localhost:8000 |
| OpenWebUI | http://localhost:3000 |
| Qdrant | http://localhost:6333 |
| Ollama | http://localhost:11434 |
| Postgres | localhost:5432 |

## Configuration

Copy `.env.example` to `.env`. Key vars:

- `OLLAMA_MODEL` — chat model (`llama3.2:3b`)
- `OLLAMA_BASE_URL` — Ollama OpenAI-compatible endpoint
- `POSTGRES_*` — database credentials
- `QDRANT_URL` — vector store (unused until Lab 02)

## Next

Lab 02 adds runbook RAG: ingest docs into Qdrant and ground answers with
retrieved context + sources.
