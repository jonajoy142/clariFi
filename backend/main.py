from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router
from app.core.config import settings
from app.core.observability import configure_observability
from app.db.session import engine
from app.models.finance import Base
from app.services.seed import ensure_seed_data

app = FastAPI(
    title="clariFi CFO OS API",
    description="Autonomous CFO Operating System backed by deterministic financial engines.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

configure_observability(app)
app.include_router(router)

@app.on_event("startup")
def startup() -> None:
    if settings.environment == "test" or settings.seed_on_startup:
        Base.metadata.create_all(bind=engine)
        ensure_seed_data()

@app.get("/")
def root():
    return {"status": "clariFi CFO OS API running", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}
