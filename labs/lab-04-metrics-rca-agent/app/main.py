from typing import List

from fastapi import FastAPI
from pydantic import BaseModel

from graph import agent_graph


app = FastAPI(
    title="AI DevOps Agent Platform",
    description="Local-first AI DevOps/SRE agent platform.",
    version="0.4.0",
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
        "version": "0.4.0",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    result = agent_graph.invoke(
        {
            "question": request.question,
            "runbook_context": "",
            "log_context": "",
            "metrics_context": "",
            "sources": [],
            "answer": "",
        }
    )

    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
    )
