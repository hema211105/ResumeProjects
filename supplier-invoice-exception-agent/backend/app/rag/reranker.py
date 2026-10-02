def rerank(query: str, documents: list[dict], limit: int = 4) -> list[dict]:
    terms = {term.lower() for term in query.split() if len(term) > 2}
    return sorted(
        documents,
        key=lambda item: sum(term in item.get("excerpt", "").lower() for term in terms),
        reverse=True,
    )[:limit]
