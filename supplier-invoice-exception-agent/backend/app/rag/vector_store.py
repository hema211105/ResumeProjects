from functools import lru_cache

from langchain_chroma import Chroma

from app.core.config import get_settings
from app.rag.embeddings import get_embeddings


@lru_cache
def get_vector_store() -> Chroma:
    settings = get_settings()
    return Chroma(
        collection_name="supplier_invoice_policies",
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_persist_directory,
    )


def add_documents(documents) -> int:
    store = get_vector_store()
    ids = [f"{document.metadata.get('document_id', 'doc')}:{document.metadata.get('start_index', index)}" for index, document in enumerate(documents)]
    store.add_documents(documents, ids=ids)
    return len(documents)


def delete_document(document_id: str) -> None:
    get_vector_store().delete(where={"document_id": document_id})


def update_document(document_id: str, documents) -> int:
    delete_document(document_id)
    return add_documents(documents)
