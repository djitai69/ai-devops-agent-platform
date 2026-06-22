import os
from typing import TypedDict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

from vector_store import search_runbooks


class AgentState(TypedDict):
    question: str
    context: str
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
    sources = []

    for item in results:
        source = item["source"]
        chunk_index = item["chunk_index"]
        text = item["text"]

        sources.append(f"{source}#chunk-{chunk_index}")
        context_blocks.append(f"Source: {source} | Chunk: {chunk_index}\n{text}")

    return {
        "question": state["question"],
        "context": "\n\n---\n\n".join(context_blocks),
        "sources": sources,
        "answer": "",
    }


def devops_agent_node(state: AgentState) -> AgentState:
    llm = get_llm()

    system_prompt = """
You are an AI DevOps/SRE assistant.

You help investigate:
- Kubernetes incidents
- logs
- metrics
- CI/CD problems
- Terraform issues
- AWS infrastructure
- FinOps optimization

Use the provided runbook context as your primary source.

Rules:
1. If the answer exists in the context, use it.
2. If the context is not enough, say what is missing.
3. Give practical DevOps steps.
4. Prefer clear checklists.
5. Do not pretend you inspected real logs or a real cluster yet.
6. End with "Suggested next check".
"""

    user_prompt = f"""
Question:
{state["question"]}

Runbook Context:
{state["context"]}

Answer as a practical DevOps/SRE assistant.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = llm.invoke(messages)

    return {
        "question": state["question"],
        "context": state["context"],
        "sources": state["sources"],
        "answer": response.content,
    }


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("retrieve_runbooks", retrieve_runbooks_node)
    graph.add_node("devops_agent", devops_agent_node)

    graph.add_edge(START, "retrieve_runbooks")
    graph.add_edge("retrieve_runbooks", "devops_agent")
    graph.add_edge("devops_agent", END)

    return graph.compile()


agent_graph = build_graph()
