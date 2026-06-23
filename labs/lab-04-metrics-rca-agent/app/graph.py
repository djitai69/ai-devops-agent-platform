import os
import json
from typing import TypedDict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

from vector_store import search_runbooks
from log_tools import search_relevant_logs
from metrics_tools import analyze_relevant_metrics


class AgentState(TypedDict):
    question: str
    runbook_context: str
    log_context: str
    metrics_context: str
    sources: List[str]
    answer: str


def get_llm():
    return ChatOpenAI(
        model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/v1"),
        api_key="ollama",
        temperature=0,
    )


def retrieve_runbooks_node(state: AgentState) -> AgentState:
    results = search_runbooks(state["question"], limit=4)

    context_blocks = []
    sources = list(state.get("sources", []))

    for item in results:
        source = item["source"]
        chunk_index = item["chunk_index"]
        text = item["text"]

        sources.append(f"runbook:{source}#chunk-{chunk_index}")
        context_blocks.append(f"Source: {source} | Chunk: {chunk_index}\n{text}")

    return {
        "question": state["question"],
        "runbook_context": "\n\n---\n\n".join(context_blocks),
        "log_context": state.get("log_context", ""),
        "metrics_context": state.get("metrics_context", ""),
        "sources": sources,
        "answer": "",
    }


def analyze_logs_node(state: AgentState) -> AgentState:
    results = search_relevant_logs(state["question"], limit=40)

    log_blocks = []
    sources = list(state.get("sources", []))

    for item in results:
        source = item["source"]
        line = item["line"]

        sources.append(f"log:{source}")
        log_blocks.append(f"Source: {source}\n{line}")

    unique_sources = sorted(set(sources))

    return {
        "question": state["question"],
        "runbook_context": state.get("runbook_context", ""),
        "log_context": "\n\n".join(log_blocks),
        "metrics_context": state.get("metrics_context", ""),
        "sources": unique_sources,
        "answer": "",
    }


def analyze_metrics_node(state: AgentState) -> AgentState:
    metrics_result = analyze_relevant_metrics(
        question=state["question"],
        log_context=state.get("log_context", ""),
    )

    sources = list(state.get("sources", []))

    for service in metrics_result["services"]:
        sources.append(f"metrics:{service}.json")

    metrics_context = json.dumps(metrics_result, indent=2)

    return {
        "question": state["question"],
        "runbook_context": state.get("runbook_context", ""),
        "log_context": state.get("log_context", ""),
        "metrics_context": metrics_context,
        "sources": sorted(set(sources)),
        "answer": "",
    }


def devops_agent_node(state: AgentState) -> AgentState:
    llm = get_llm()

    system_prompt = """
You are an AI DevOps/SRE assistant.

You investigate incidents using:
- DevOps runbooks
- application logs
- service metrics
- practical SRE reasoning

You must produce an RCA-style answer.

Required structure:
1. Incident Summary
2. Evidence
3. Probable Root Cause
4. Impact
5. Recommended Fix
6. Validation Steps
7. Suggested Next Check

Rules:
- Use logs as evidence.
- Use metrics as evidence.
- Use runbooks as operational guidance.
- Do not claim you checked real Kubernetes or real CloudWatch yet.
- If evidence is insufficient, say what is missing.
- Be specific and practical.
"""

    user_prompt = f"""
Question:
{state["question"]}

Runbook Context:
{state["runbook_context"]}

Log Evidence:
{state["log_context"]}

Metrics Evidence:
{state["metrics_context"]}

Create an RCA-style DevOps/SRE incident analysis.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = llm.invoke(messages)

    return {
        "question": state["question"],
        "runbook_context": state["runbook_context"],
        "log_context": state["log_context"],
        "metrics_context": state["metrics_context"],
        "sources": state["sources"],
        "answer": response.content,
    }


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("retrieve_runbooks", retrieve_runbooks_node)
    graph.add_node("analyze_logs", analyze_logs_node)
    graph.add_node("analyze_metrics", analyze_metrics_node)
    graph.add_node("devops_agent", devops_agent_node)

    graph.add_edge(START, "retrieve_runbooks")
    graph.add_edge("retrieve_runbooks", "analyze_logs")
    graph.add_edge("analyze_logs", "analyze_metrics")
    graph.add_edge("analyze_metrics", "devops_agent")
    graph.add_edge("devops_agent", END)

    return graph.compile()


agent_graph = build_graph()
