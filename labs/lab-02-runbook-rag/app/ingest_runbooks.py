from vector_store import ingest_runbooks


if __name__ == "__main__":
    result = ingest_runbooks("/docs")
    print(result)
