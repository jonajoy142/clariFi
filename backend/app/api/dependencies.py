from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.finance import OrganizationRepository


DbSession = Annotated[Session, Depends(get_db)]


def get_current_organization_id(
    db: DbSession,
    x_org_id: Annotated[str | None, Header(alias="x-org-id")] = None,
) -> str:
    if x_org_id:
        org = OrganizationRepository(db).get(x_org_id)
        if org is None:
            raise HTTPException(status_code=404, detail="Organization not found")
        return x_org_id
    org = OrganizationRepository(db).by_user_type("startup")
    if org is None:
        raise HTTPException(status_code=404, detail="No organization seeded. Call /auth/dev-login first.")
    return org.id


CurrentOrgId = Annotated[str, Depends(get_current_organization_id)]

