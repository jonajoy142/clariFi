import hashlib
import math
from typing import Any

from sqlalchemy.orm import Session

from app.models.finance import Document, DocumentChunk
from app.repositories.finance import DocumentRepository


class EmbeddingProvider:
    dimensions = 384

    def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = []
        for index in range(self.dimensions):
            byte = digest[index % len(digest)]
            values.append((byte / 255.0) - 0.5)
        norm = math.sqrt(sum(value * value for value in values)) or 1
        return [round(value / norm, 6) for value in values]


class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DocumentRepository(db)
        self.embeddings = EmbeddingProvider()

    def ingest(self, organization_id: str, *, title: str, text: str, document_type: str = "note", source: str = "manual") -> Document:
        document = Document(
            organization_id=organization_id,
            title=title,
            document_type=document_type,
            source=source,
            extracted_text=text,
            extracted_json={},
            status="processed",
        )
        chunks = [
            DocumentChunk(
                organization_id=organization_id,
                document_id="pending",
                chunk_index=index,
                content=chunk,
                embedding=self.embeddings.embed(chunk),
                metadata_json={"title": title, "source": source, "document_type": document_type},
            )
            for index, chunk in enumerate(_chunk_text(text))
        ]
        return self.repo.add_document(document, chunks)

    def search(self, organization_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        query_terms = {term.lower() for term in query.split() if len(term) > 2}
        query_embedding = self.embeddings.embed(query)
        scored = []
        for chunk in self.repo.chunks(organization_id):
            content_lower = chunk.content.lower()
            lexical_score = sum(1 for term in query_terms if term in content_lower)
            vector_score = _cosine(query_embedding, _embedding_values(chunk.embedding))
            score = lexical_score + vector_score
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "source_type": "document_chunk",
                "source_id": chunk.id,
                "title": chunk.metadata_json.get("title", "Document"),
                "excerpt": chunk.content[:360],
                "score": score,
                "metadata": chunk.metadata_json,
            }
            for score, chunk in scored[:limit]
        ]


def _chunk_text(text: str, chunk_size: int = 700) -> list[str]:
    clean = " ".join(text.split())
    if not clean:
        return []
    return [clean[index:index + chunk_size] for index in range(0, len(clean), chunk_size)]


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    length = min(len(left), len(right))
    dot = sum(left[index] * right[index] for index in range(length))
    left_norm = math.sqrt(sum(value * value for value in left[:length])) or 1
    right_norm = math.sqrt(sum(value * value for value in right[:length])) or 1
    return dot / (left_norm * right_norm)


def _embedding_values(value) -> list[float]:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        return [float(item) for item in value.tolist()]
    return [float(item) for item in value]
