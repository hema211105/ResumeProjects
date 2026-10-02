from app.rag.chunking import chunk_documents
from app.rag.loaders import load_documents
from app.rag.vector_store import add_documents


def ingest() -> dict[str, int]:
    documents = load_documents()
    chunks = chunk_documents(documents)
    return {"documents": len(documents), "chunks": add_documents(chunks)}
