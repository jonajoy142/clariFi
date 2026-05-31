from app.db.session import SessionLocal
from app.repositories.finance import OrganizationRepository
from app.services.connectors import ConnectorService


def ensure_seed_data() -> None:
    db = SessionLocal()
    try:
        seed_user_type(db, "startup")
        seed_user_type(db, "freelancer")
        db.commit()
    finally:
        db.close()


def seed_user_type(db, user_type: str):
    org_repo = OrganizationRepository(db)
    existing = org_repo.by_user_type(user_type)
    if existing is not None:
        return existing
    email = f"{user_type}@clarifi.local"
    name = "Seed Capital OS" if user_type == "startup" else "Studio Finance OS"
    _, org = org_repo.create_with_owner(user_type=user_type, name=name, email=email)
    service = ConnectorService(db)
    for item in service.catalog(org.id):
        if not item["available"]:
            continue
        connector = service.connect(org.id, item["type"])
        service.sync(org.id, connector.id)
    return org
