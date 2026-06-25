# Lab 07 - ChatOps Incident Reporter

This lab extends the AI DevOps/SRE platform with a ChatOps reporting layer.

The agent can now convert RCA or FinOps findings into a Slack-style operational update.

## Features

- Detects ChatOps/reporting requests
- Reuses existing RCA or FinOps analysis
- Converts technical findings into a structured stakeholder update
- Includes status, impact, evidence, next actions, owner, and next update

## Architecture

```text
User
  ↓
FastAPI /chat
  ↓
LangGraph
  ├── classify_incident
  ├── analyze_k8s
  ├── retrieve_runbooks
  ├── analyze_logs
  ├── analyze_metrics
  ├── analyze_finops
  ├── devops_agent
  └── chatops_report
  ↓
Slack-style incident update
