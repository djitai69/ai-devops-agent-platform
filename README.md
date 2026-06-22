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

## Current Sprint

Sprint 1: Local agent foundation.

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
docker exec -it ai-devops-ollama ollama pull llama3.2:3b
