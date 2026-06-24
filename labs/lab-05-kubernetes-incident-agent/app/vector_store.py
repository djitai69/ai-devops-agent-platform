import os
import uuid
from pathlib import Path
from typing import List, Dict, Any

import requests
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "devops_runbooks")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)


def get_embedding(text: str) -> List[float]:
    response = requests.post(
        f"{OLLAMA_HOST}/api/embed",
        json={"model": OLLAMA_EMBED_MODEL, "input": text},
        timeout=120,
    )

    if response.status_code == 200:
        data = response.json()
        if "embeddings" in data and data["embeddings"]:
            return data["embeddings"][0]

    response = requests.post(
        f"{OLLAMA_HOST}/api/embeddings",
        json={"model": OLLAMA_EMBED_MODEL, "prompt": text},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["embedding"]


def chunk_text(text: str, max_chars: int = 900) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""

    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}".strip()
        else:
            if current:
                chunks.append(current)
            current = paragraph

    if current:
        chunks.append(current)

    return chunks


def ensure_collection(vector_size: int) -> None:
    client = get_qdrant_client()
    collections = client.get_collections().collections
    existing_names = [collection.name for collection in collections]

    if QDRANT_COLLECTION not in existing_names:
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


def ingest_runbooks(docs_path: str = "/docs") -> Dict[str, Any]:
    docs_dir = Path(docs_path)

    if not docs_dir.exists():
        raise FileNotFoundError(f"Docs directory not found: {docs_path}")

    markdown_files = sorted(docs_dir.glob("*.md"))

    if not markdown_files:
        return {
            "status": "no_documents",
            "message": f"No Markdown files found in {docs_path}",
            "ingested_chunks": 0,
        }

    points = []

    for file_path in markdown_files:
        text = file_path.read_text(encoding="utf-8")
        chunks = chunk_text(text)

        for index, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            ensure_collection(vector_size=len(embedding))

            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{file_path.name}-{index}"))

            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "source": file_path.name,
                        "chunk_index": index,
                        "text": chunk,
                    },
                )
            )

    client = get_qdrant_client()
    client.upsert(collection_name=QDRANT_COLLECTION, points=points)

    return {
        "status": "ok",
        "documents": len(markdown_files),
        "ingested_chunks": len(points),
        "collection": QDRANT_COLLECTION,
    }


def search_runbooks(query: str, limit: int = 4) -> List[Dict[str, Any]]:
    client = get_qdrant_client()
    query_vector = get_embedding(query)

    try:
        result = client.query_points(
            collection_name=QDRANT_COLLECTION,
            query=query_vector,
            limit=limit,
        )
        points = result.points
    except AttributeError:
        points = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=limit,
        )

    results = []

    for point in points:
        results.append(
            {
                "score": point.score,
                "source": point.payload.get("source"),
                "chunk_index": point.payload.get("chunk_index"),
                "text": point.payload.get("text"),
            }
        )

    return results
