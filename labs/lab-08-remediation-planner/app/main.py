
import os
from chatops_tools import send_to_slack

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from typing import List

from fastapi import FastAPI
from pydantic import BaseModel

from graph import agent_graph


app = FastAPI(
    title="AI DevOps Agent Platform",
    description="Local-first AI DevOps/SRE agent platform.",
    version="0.5.0",
)


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[str]


@app.get("/")
def root():
    return {
        "service": "AI DevOps Agent Platform",
        "status": "running",
        "version": "0.6.0",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/simple-chat", response_model=ChatResponse)
def simple_chat(request: ChatRequest):
    llm = ChatOpenAI(
        model=os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/v1"),
        api_key="ollama",
        temperature=0,
    )

    response = llm.invoke([HumanMessage(content=request.question)])

    return ChatResponse(
        answer=response.content,
        sources=["direct-llm:no-tools"],
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    result = agent_graph.invoke(
        {
            "question": request.question,
            "incident_type": "",
            "report_type": "",
            "remediation_requested": False,
            "runbook_context": "",
            "log_context": "",
            "metrics_context": "",
            "k8s_context": "",
            "finops_context": "",
            "sources": [],
            "answer": "",
        }
    )

    return ChatResponse(
        answer=result["answer"],
        sources=result.get("sources", []),
    )


@app.post("/chatops/send", response_model=ChatResponse)
def send_chatops_update(request: ChatRequest):
    result = agent_graph.invoke(
        {
            "question": request.question,
            "incident_type": "",
            "report_type": "",
            "remediation_requested": False,
            "runbook_context": "",
            "log_context": "",
            "metrics_context": "",
            "k8s_context": "",
            "finops_context": "",
            "sources": [],
            "answer": "",
        }
    )

    slack_result = send_to_slack(result["answer"])

    if slack_result["sent"]:
        send_status = "Slack delivery: sent."
    else:
        send_status = f"Slack delivery: skipped. Reason: {slack_result['reason']}"

    return ChatResponse(
        answer=f'{result["answer"]}\n\n{send_status}',
        sources=result["sources"],
    )
