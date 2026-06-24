# Lab 06 - FinOps Agent

This lab extends the AI DevOps/SRE platform with Kubernetes FinOps analysis.

The agent now analyzes:

- Kubernetes CPU and memory requests vs usage
- overprovisioned workloads
- idle resources
- underutilized nodes
- estimated monthly savings
- risk and validation plans

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
  └── devops_agent
  ↓
FinOps recommendation with sources
