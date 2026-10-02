import json
from pathlib import Path

from langchain_core.documents import Document
from langchain_community.document_loaders import DirectoryLoader, TextLoader

ROOT = Path(__file__).resolve().parents[3]
KNOWLEDGE_DIR = ROOT / "data" / "knowledge_base"


def load_documents() -> list[Document]:
    source_file = KNOWLEDGE_DIR / "documents.json"
    documents = []
    if source_file.exists():
        records = json.loads(source_file.read_text(encoding="utf-8"))
        documents.extend(Document(page_content=record["content"], metadata={key: value for key, value in record.items() if key != "content"}) for record in records)
    if not KNOWLEDGE_DIR.exists():
        return documents
    files = []
    for pattern in ("**/*.md", "**/*.txt"):
        files.extend(DirectoryLoader(str(KNOWLEDGE_DIR), glob=pattern, loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"}).load())
    for document in files:
        source = Path(document.metadata.get("source", "policy"))
        document.metadata.update({"document_id": f"UPLOAD-{source.stem}", "title": source.stem.replace("_", " "), "category": "uploaded", "version": "1.0", "effective_date": "2026-01-01", "page": 1, "section": "General"})
    return [*documents, *files]
