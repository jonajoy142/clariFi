from sqlalchemy.orm import Session

from app.services.documents import DocumentService


class FinancialEvidenceRetriever:
    def __init__(self, db: Session):
        self.documents = DocumentService(db)

    def retrieve(self, organization_id: str, query: str, limit: int = 5) -> list[dict]:
        return self.documents.search(organization_id, query, limit)

