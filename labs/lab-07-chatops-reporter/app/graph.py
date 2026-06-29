import os
import json

from typing import TypedDict, List
from chatops_tools import detect_report_type, format_chatops_update
from finops_tools import analyze_finops, format_finops_report


from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

from vector_store import search_runbooks
from log_tools import search_relevant_logs
from metrics_tools import analyze_relevant_metrics
from k8s_tools import format_k8s_evidence


class AgentState(TypedDict):
    question: str
    incident_type: str
    report_type: str
    runbook_context: str
    log_context: str
    metrics_context: str
    k8s_context: str
    finops_context: str
    sources: List[str]
    answer: str


def get_llm():
    return ChatOpenAI(
        model=os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/v1"),
        api_key="ollama",
        temperature=0,
    )


def classify_incident_node(state: AgentState) -> AgentState:
    question = state["question"].lower()
    report_type = detect_report_type(question)

    finops_terms = [
        "cost",
        "save money",
        "saving",
        "savings",
        "finops",
        "rightsizing",
        "rightsize",
        "overprovisioned",
        "idle",
        "waste",
        "utilization",
        "expensive",
    ]

    k8s_terms = [
        "pod",
        "deployment",
        "kubectl",
        "not starting",
        "createcontainerconfigerror",
        "secret",
        "configmap",
        "imagepullbackoff",
        "crashloopbackoff",
    ]

    if any(term in question for term in finops_terms):
        incident_type = "finops"
    elif any(term in question for term in k8s_terms):
        incident_type = "kubernetes"
    else:
        incident_type = "general"

    return {
        **state,
        "incident_type": incident_type,
        "report_type": report_type,
    }



def analyze_k8s_node(state: AgentState) -> AgentState:
    if state.get("incident_type") != "kubernetes":
        return state

    k8s_result = format_k8s_evidence(state["question"])

    sources = list(state.get("sources", []))

    for source in k8s_result["sources"]:
        sources.append(f"k8s:{source}")

    return {
        **state,
        "k8s_context": k8s_result["context"],
        "sources": sorted(set(sources)),
    }


def retrieve_runbooks_node(state: AgentState) -> AgentState:
    if state.get("incident_type") == "kubernetes":
        query = "Kubernetes CreateContainerConfigError missing Secret ConfigMap pod troubleshooting"
        limit = 1
    else:
        query = state["question"]
        limit = 2

    results = search_runbooks(query, limit=limit)

    context_blocks = []
    sources = list(state.get("sources", []))

    for item in results:
        source = item["source"]
        chunk_index = item["chunk_index"]
        text = item["text"]

        if state.get("incident_type") == "kubernetes" and source == "crashloopbackoff.md":
            continue

        sources.append(f"runbook:{source}#chunk-{chunk_index}")
        context_blocks.append(f"Source: {source} | Chunk: {chunk_index}\n{text}")

    return {
        **state,
        "runbook_context": "\n\n---\n\n".join(context_blocks),
        "sources": sorted(set(sources)),
    }

def analyze_logs_node(state: AgentState) -> AgentState:
    if state.get("incident_type") in ["kubernetes", "finops"]:
        return {
            **state,
            "log_context": f"Skipped: {state.get('incident_type')} issue.",
        }

    results = search_relevant_logs(state["question"], limit=10)


    log_blocks = []
    sources = list(state.get("sources", []))

    for item in results:
        source = item["source"]
        line = item["line"]

        sources.append(f"log:{source}")
        log_blocks.append(f"Source: {source}\n{line}")

    return {
        **state,
        "log_context": "\n\n".join(log_blocks),
        "sources": sorted(set(sources)),
    }

def retrieve_runbooks_node(state: AgentState) -> AgentState:
    if state.get("incident_type") == "finops":
        query = "Kubernetes FinOps rightsizing cost optimization idle resources overprovisioned workloads"
        limit = 1
    elif state.get("incident_type") == "kubernetes":
        query = "Kubernetes CreateContainerConfigError missing Secret ConfigMap pod troubleshooting"
        limit = 1
    else:
        query = state["question"]
        limit = 2

    results = search_runbooks(query, limit=limit)

    context_blocks = []
    sources = list(state.get("sources", []))

    for item in results:
        source = item["source"]
        chunk_index = item["chunk_index"]
        text = item["text"]

        if state.get("incident_type") == "kubernetes" and source == "crashloopbackoff.md":
            continue

        if state.get("incident_type") == "finops" and source != "kubernetes-finops-rightsizing.md":
            continue

        sources.append(f"runbook:{source}#chunk-{chunk_index}")
        context_blocks.append(f"Source: {source} | Chunk: {chunk_index}\n{text}")

    return {
        **state,
        "runbook_context": "\n\n---\n\n".join(context_blocks),
        "sources": sorted(set(sources)),
    }


def analyze_metrics_node(state: AgentState) -> AgentState:
    if state.get("incident_type") in ["kubernetes", "finops"]:
        return {
            **state,
            "metrics_context": f"Skipped: {state.get('incident_type')} issue.",
        }


    metrics_result = analyze_relevant_metrics(
        question=state["question"],
        log_context=state.get("log_context", ""),
    )

    sources = list(state.get("sources", []))

    for service in metrics_result["services"]:
        sources.append(f"metrics:{service}.json")

    return {
        **state,
        "metrics_context": json.dumps(metrics_result, indent=2),
        "sources": sorted(set(sources)),
    }


def analyze_finops_node(state: AgentState) -> AgentState:
    if state.get("incident_type") != "finops":
        return {
            **state,
            "finops_context": state.get("finops_context", ""),
        }

    finops_result = analyze_finops()

    sources = list(state.get("sources", []))
    sources.extend(
        [
            "finops:k8s-requests-usage.csv",
            "finops:idle-resources.csv",
            "finops:node-utilization.csv",
        ]
    )

    return {
        **state,
        "finops_context": json.dumps(finops_result, indent=2),
        "sources": sorted(set(sources)),
    }


#def devops_agent_node(state: AgentState) -> AgentState:
def devops_agent_node(state: AgentState) -> AgentState:
    if state.get("incident_type") == "finops":
        return {
            **state,
            "answer": format_finops_report(),
        }

    llm = get_llm()

    if state.get("incident_type") == "finops":
        system_prompt = """
You are an AI FinOps assistant for Kubernetes cost optimization.

Use ONLY the FinOps Evidence and FinOps runbook context.

Rules:
- Do not use application logs.
- Do not use latency or error-rate RCA.
- Do not mention HPA unless the FinOps evidence explicitly mentions HPA.
- Do not recommend increasing replicas as a cost-saving action.
- Focus on overprovisioned CPU/memory requests, idle resources, underutilized nodes, and estimated savings.
- Prioritize highest estimated monthly savings.
- Include risk level.
- Do not recommend automatic production changes.
- Include a safe validation plan.
- Do not add a Conclusion section.

Required structure:
1. Cost Summary
2. Top Savings Opportunities
3. Recommended Actions
4. Risk and Safety Notes
5. Validation Plan
"""

    elif state.get("incident_type") == "kubernetes":
        system_prompt = """

You are an AI DevOps/SRE assistant.

Write a concise Kubernetes RCA using only the Structured Kubernetes Diagnosis.

Rules:
- The Structured Kubernetes Diagnosis is the source of truth.
- Do not invent additional causes.
- Do not say CrashLoopBackOff unless the diagnosis says CrashLoopBackOff.
- Do not call Kubernetes events "logs".
- Do not include kubectl logs unless the diagnosis explicitly mentions container logs.
- Do not add Additional Considerations.
- Do not add Conclusion.
- Use exact Secret name, Secret key, namespace, and pod name if provided.
- Include concrete kubectl validation commands.

Output exactly these sections and no others:

1. Incident Summary
2. Evidence
3. Probable Root Cause
4. Recommended Fix
5. Validation Commands
6. Suggested Next Check

In the Evidence section, list observed facts, not commands.
"""



    else:
        system_prompt = """
You are an AI DevOps/SRE assistant.

Use the provided runbooks, logs, and metrics to produce a concise RCA.

Required structure:
1. Incident Summary
2. Evidence
3. Probable Root Cause
4. Recommended Fix
5. Suggested Next Check
"""

    user_prompt = f"""
Question:
{state["question"]}

Incident Type:
{state["incident_type"]}

FinOps Evidence:
{state["finops_context"]}

Runbook Context:
{state["runbook_context"]}

Kubernetes Evidence:
{state["k8s_context"]}

Log Evidence:
{state["log_context"]}

Metrics Evidence:
{state["metrics_context"]}

Write the answer now.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = llm.invoke(messages)

    return {
        **state,
        "answer": response.content,
    }


def chatops_report_node(state: AgentState) -> AgentState:
    if state.get("report_type") != "chatops":
        return state

    report = format_chatops_update(
        question=state["question"],
        incident_type=state["incident_type"],
        answer=state["answer"],
        sources=state["sources"],
    )

    return {
        **state,
        "answer": report["message"],
        "sources": report["sources"],
    }




def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("classify_incident", classify_incident_node)
    graph.add_node("analyze_k8s", analyze_k8s_node)
    graph.add_node("retrieve_runbooks", retrieve_runbooks_node)
    graph.add_node("analyze_logs", analyze_logs_node)
    graph.add_node("analyze_metrics", analyze_metrics_node)
    graph.add_node("devops_agent", devops_agent_node)
    graph.add_node("analyze_finops", analyze_finops_node)
    graph.add_node("chatops_report", chatops_report_node)

    graph.add_edge(START, "classify_incident")
    graph.add_edge("classify_incident", "analyze_k8s")
    graph.add_edge("analyze_k8s", "retrieve_runbooks")
    graph.add_edge("retrieve_runbooks", "analyze_logs")
    graph.add_edge("analyze_logs", "analyze_metrics")
    graph.add_edge("analyze_metrics", "analyze_finops")
    graph.add_edge("analyze_finops", "devops_agent")
    graph.add_edge("devops_agent", "chatops_report")
    graph.add_edge("chatops_report", END)

    return graph.compile()


agent_graph = build_graph()
