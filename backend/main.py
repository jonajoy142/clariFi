from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import tax, investment, loans, allocation, chat, profile

app = FastAPI(
    title="ClariFi API",
    description="Agentic Personal CFO for India — verifiable financial intelligence",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile.router, prefix="/api/profile", tags=["Profile"])
app.include_router(tax.router,        prefix="/api/tax",        tags=["Tax"])
app.include_router(investment.router, prefix="/api/investment", tags=["Investment"])
app.include_router(loans.router,      prefix="/api/loans",      tags=["Loans"])
app.include_router(allocation.router, prefix="/api/allocation", tags=["Allocation"])
app.include_router(chat.router,       prefix="/api/chat",       tags=["AI CFO Chat"])

@app.get("/")
def root():
    return {"status": "ClariFi API running", "docs": "/docs"}
