# ClariFi — Agentic Personal CFO for India

> Verifiable financial intelligence. AI reasons, Python calculates, you audit every rupee.

**Live demo:** [to be updated]  
**Built by:** Jona Joy · [jonajoy142@gmail.com](mailto:jonajoy142@gmail.com) · [LinkedIn](https://linkedin.com/in/jona-joy-b30b44203)

---

## What is ClariFi?

ClariFi is an agentic Personal CFO for India — inspired by Hiro Finance (acquired by OpenAI, April 2026).

Unlike generic AI financial tools, ClariFi:
- **Never guesses numbers** — Python runs all calculations, AI only explains
- **Reasons over real tax rules** — LLM reads the current tax knowledge base, not a hardcoded config
- **Iterates to find optimal** — tries multiple deduction combinations, not just 80C every time
- **Shows full working** — every calculation is auditable, line by line

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend                       │
│  Profile → Tax → Investment → Loans → AI CFO Chat       │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────────────┐
│               FastAPI Backend                            │
│                                                          │
│  ┌─────────────────┐    ┌──────────────────────────┐    │
│  │  Calculation    │    │     AI Agent Layer        │    │
│  │  Engines        │    │   (LangChain + Claude)    │    │
│  │                 │    │                           │    │
│  │ tax_engine.py   │◄───│  Reads tax knowledge base │    │
│  │ investment_     │    │  Reasons which rules apply│    │
│  │   engine.py     │    │  Calls engines for math   │    │
│  │ loan_allocation │    │  Explains verified output │    │
│  │   _engine.py    │    │                           │    │
│  │ chat_engine.py  │    │  NEVER calculates itself  │    │
│  └─────────────────┘    └──────────────────────────┘    │
│                                                          │
│  Key principle: AI reasons → Python calculates → AI explains
└─────────────────────────────────────────────────────────┘
```

---

## Features

### Tax Optimisation Engine
- Old regime vs new regime — full comparison with every deduction line item
- 80C basket optimiser — ELSS, PPF, NPS, EPF, insurance ranked for your situation
- HRA exemption — all 3 formula comparison with working shown
- Section 24B, 80D, 80CCD(1B), 80TTA
- AI iterates over deduction combinations to find optimal — not just default 80C
- Tax rules live in a **knowledge base updated each Budget**, not hardcoded configs

### Investment Planning
- SIP projection (10yr, 20yr) with step-up SIP modelling
- Goal-based SIP calculator — retirement, child education, house
- FIRE number calculator (4% withdrawal rule)
- Loan vs invest — exact IRR comparison
- AI portfolio health assessment

### Loan & Debt Analysis
- Full amortisation schedule
- Prepayment impact — months saved + interest saved
- Debt avalanche order (highest rate first)
- EMI-to-income ratio health check

### Monthly Fund Allocation
- Surplus calculation after all fixed costs
- Emergency fund adequacy check
- Advance tax provision
- AI-generated monthly CFO report

### AI CFO Chat
- Full profile context — answers specific to YOUR numbers
- Handles general questions ("what if I get ₹100Cr?") and personal questions
- Quick question starters built in
- Claude API with India-specific system prompt

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, Uvicorn |
| AI | Anthropic Claude API, custom prompt engineering |
| Frontend | Vue.js 3 (CDN), vanilla CSS |
| Deploy | Render (backend), GitHub Pages / Netlify (frontend) |
| No database | In-memory session store (portfolio demo) |

---

## Local Setup

### Backend

```bash
cd backend
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment and run
poetry run uvicorn main:app --reload
# API runs at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Frontend

```bash
# Just open frontend/index.html in your browser
# Or serve with:
cd frontend
python3 -m http.server 3000
# Open http://localhost:3000
```

---

## Deploy to Render (Free)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your GitHub repo
4. Set root directory: `backend`
5. Build command: `poetry install --no-dev`
6. Start command: `poetry run uvicorn main:app --host 0.0.0.0 --port $PORT`
7. Add env var: `ANTHROPIC_API_KEY = your_key`
8. Deploy → get your URL
9. Update `API` variable in `frontend/index.html` to your Render URL
10. Deploy frontend to GitHub Pages or Netlify

---

## Why This Project

I built ClariFi to solve a problem I personally faced: when my salary increased, I had no idea whether to pick old vs new regime, where to put the extra money (ULIP vs MF vs NPS), how to optimise 80C without just blindly maxing it, or whether to prepay my loan or invest the surplus.

Every existing tool either gave generic advice or hardcoded tax rules in config files. ClariFi is different — it reasons intelligently over the actual tax rulebook, runs verifiable calculations, and gives personalised advice specific to your actual numbers.

The architecture (AI reasons → Python calculates → AI explains) is directly inspired by Hiro Finance, acquired by OpenAI in April 2026 for their verifiable financial reasoning engine.

---

## Project Structure

```
clarifi/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── pyproject.toml             # Poetry configuration
│   ├── .env.example
│   └── app/
│       ├── core/config.py         # Settings
│       ├── models/profile.py      # UserFinancialProfile (master data model)
│       ├── engines/
│       │   ├── tax_engine.py      # Intelligent tax analysis
│       │   ├── investment_engine.py
│       │   ├── loan_allocation_engine.py
│       │   └── chat_engine.py     # AI CFO chat
│       └── api/
│           ├── profile.py         # Profile save/load/demo
│           ├── tax.py
│           ├── investment.py
│           ├── loans.py
│           ├── allocation.py
│           └── chat.py
├── frontend/
│   └── index.html                 # Complete Vue.js SPA
├── render.yaml                    # Render deployment config
└── README.md
```

---

## Contact

Built by **Jona Joy** — Founding Engineer at KIREAP Technologies  
Payments · Blockchain · Backend · AI/ML  
[jonajoy142@gmail.com](mailto:jonajoy142@gmail.com) · [GitHub](https://github.com/jonajoy142) · [LinkedIn](https://linkedin.com/in/jona-joy-b30b44203)
