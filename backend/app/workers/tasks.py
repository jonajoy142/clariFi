from app.ai.workflows.financial_analysis_workflow import FinancialAnalysisWorkflow
from app.db.session import SessionLocal
from app.services.connectors import ConnectorService
from app.workers.celery_app import celery_app


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def run_financial_analysis(self, organization_id: str) -> dict:
    db = SessionLocal()
    try:
        return FinancialAnalysisWorkflow(db).run(organization_id)
    finally:
        db.close()


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def sync_connector(self, organization_id: str, connector_id: str) -> dict:
    db = SessionLocal()
    try:
        return ConnectorService(db).sync(organization_id, connector_id)
    finally:
        db.close()

