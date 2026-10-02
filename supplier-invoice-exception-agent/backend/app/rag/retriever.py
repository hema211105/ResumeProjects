import logging

from app.rag.loaders import load_documents
from app.rag.reranker import rerank
from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)


def search_documents(query: str, k: int = 4, metadata_filter: dict | None = None) -> list[dict]:
    try:
        results = get_vector_store().similarity_search(query, k=k, filter=metadata_filter)
        if results:
            return [{**document.metadata, "excerpt": document.page_content[:1200], "citation": f"{document.metadata.get('document_id', 'document')}:{document.metadata.get('section', 'General')}"} for document in results]
    except Exception:
        logger.exception("Chroma retrieval unavailable; using lexical fallback")
    query_terms = {term.lower() for term in query.split() if len(term) > 2}
    matches = []
    for document in load_documents():
        metadata = document.metadata
        if metadata_filter and any(metadata.get(key) != value for key, value in metadata_filter.items()):
            continue
        content = document.page_content
        score = sum(term in content.lower() for term in query_terms)
        if score:
            matches.append({**metadata, "excerpt": content[:1200], "citation": f"{metadata.get('document_id', 'document')}:{metadata.get('section', 'General')}", "_score": score})
    return rerank(query, matches, k)
