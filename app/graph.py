import os
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END


class AgentState(TypedDict):
    question: str
    answer: str


def get_llm():
    return ChatOpenAI(
        model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/v1"),
        api_key="ollama",
        temperature=0,
    )


def devops_agent_node(state: AgentState) -> AgentState:
    llm = get_llm()

    messages = [
        SystemMessage(
            content=(
                "You are an AI DevOps/SRE assistant. "
                "You help investigate infrastructure, Kubernetes, logs, metrics, "
                "CI/CD, Terraform, AWS, and FinOps issues. "
                "For now, you do not have tools yet, so be honest when you are reasoning "
                "only from general knowledge."
            )
        ),
        HumanMessage(content=state["question"]),
    ]

    response = llm.invoke(messages)

    return {
        "question": state["question"],
        "answer": response.content,
    }


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("devops_agent", devops_agent_node)

    graph.add_edge(START, "devops_agent")
    graph.add_edge("devops_agent", END)

    return graph.compile()


agent_graph = build_graph()
