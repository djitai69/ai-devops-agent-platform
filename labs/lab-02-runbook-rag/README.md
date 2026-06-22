# Lab 02 — Runbook RAG Agent

Sprint 2 of the AI DevOps Agent Platform. Builds on top of Lab 01 (local agent
stack) by adding **Retrieval-Augmented Generation (RAG)**: instead of answering
from the model's weights alone, the agent retrieves relevant DevOps runbook
chunks and grounds its answers in them.

## What's new vs Lab 01

| | Lab 01 | Lab 02 |
|---|---|---|
| Answer source | Model only | Model **+ runbook docs (RAG)** |
| Vector store | unused | Qdrant (`devops_runbooks` collection) |
| Embeddings | none | Ollama `nomic-embed-text` |
| Agent graph | single LLM node | `retrieve_runbooks` → `devops_agent` |
| API | basic | `/chat` returns `answer` + `sources` |

## Goal

An AI DevOps Engineer that answers from your runbooks instead of guessing —
cites which doc/chunk it used, and falls back to stating what's missing when the
context isn't enough.

## Architecture

```
question
   │
   ▼
retrieve_runbooks   ── embeds question, searches Qdrant (top 4 chunks)
   │
   ▼
devops_agent        ── LLM answers using retrieved runbook context
   │
   ▼
answer + sources
```

- `app/main.py` — FastAPI app (`/`, `/health`, `POST /chat`)
- `app/graph.py` — LangGraph: retrieve node → agent node
- `app/vector_store.py` — chunking, Ollama embeddings, Qdrant ingest/search
- `app/ingest_runbooks.py` — one-shot ingest entrypoint
- `docs/` — runbooks ingested into the vector store

## Stack

- Docker Compose
- Ollama (chat + embeddings)
- OpenWebUI
- LangGraph
- FastAPI
- PostgreSQL
- Qdrant

## Run locally

```bash
docker compose up -d --build

# Pull the chat model and the embedding model
docker exec -it ai-devops-ollama ollama pull llama3.2:3b
docker exec -it ai-devops-ollama ollama pull nomic-embed-text

# Ingest the runbooks in docs/ into Qdrant
docker exec -it ai-devops-agent-api python ingest_runbooks.py
```

## Try it

```bash
curl -s http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I debug a pod stuck in CrashLoopBackOff?"}'
```

Response:

```json
{
  "answer": "...",
  "sources": ["crashloopbackoff.md#chunk-0", "..."]
}
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

Copy `.env.example` to `.env`. Key RAG vars:

- `OLLAMA_MODEL` — chat model (`llama3.2:3b`)
- `OLLAMA_EMBED_MODEL` — embedding model (`nomic-embed-text`)
- `QDRANT_URL` / `QDRANT_COLLECTION` — vector store target
- `OLLAMA_HOST` — base URL used for the embeddings API
