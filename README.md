# Business Interest Agent — Phase 1

Adapted from [daphnecharles/zero-to-running-agent](https://github.com/daphnecharles/zero-to-running-agent/tree/step-3) (the All Things Open 2026 workshop's `step-3` branch).

**What it does:** Reads business listings from a local JSON file or a browser-uploaded JSON file, finds active listings with a numeric asking price **strictly below $1,000,000**, sorts them by price, drafts up to **five** non-binding inquiry emails, and pauses for human review. Approved drafts are saved locally as Markdown and JSON. **It never sends emails or contacts brokers.**

**What it doesn't do (yet):** Search for fresh listings, visit/verify listing pages, detect broker email addresses, assess investment quality, or calculate all-in costs for price ranges and inventory/real-estate extras. Uncertain records go into `manual_review` instead of being guessed eligible.

## Apply the ZIP to an existing step-3 clone (Windows PowerShell)

See **[PHASE1_SETUP.md](PHASE1_SETUP.md)** for backup advice and the complete instructions. The ZIP is an overlay, **not a standalone clone**. It contains updated and new files at their existing repo-relative paths. It does not include `.git`, `.venv`, your `.env`, or the untouched workshop files.

```powershell
cd "C:\path\to\zero-to-running-agent"
# Check branch and any local changes before overwriting files:
git branch --show-current
git status --short

Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\business_interest_phase1_overlay.zip" -DestinationPath . -Force
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q tests/test_business_phase1.py tests/test_business_graph.py
```

Use the `step-3` branch as the base. **Existing `.env` remains untouched**, so your Gemini or Anthropic key should still be available.

## Run in PowerShell

```powershell
# Terminal interface, bundled dataset:
.\.venv\Scripts\python.exe run.py

# Or choose another local JSON file:
.\.venv\Scripts\python.exe run.py .\data\business_listings.json

# Browser interface:
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open `http://127.0.0.1:8000`. Upload a `.json` file or leave the file field empty to use the bundled data. You will see eligible, manual-review, and excluded records. Edit, approve or reject drafts. Approved files appear under `outputs/` (gitignored).

To preview without a model API call, set `MODEL_PROVIDER=mock` in `.env` or only for one PowerShell session:

```powershell
$env:MODEL_PROVIDER = "mock"
.\.venv\Scripts\python.exe run.py
Remove-Item Env:MODEL_PROVIDER
```

Mock mode creates complete, editable template emails. If the configured real model fails to initialize or draft, the agent also uses a **labeled fallback template** instead of silently pretending to have generated an AI email.

## Listing input format

The supplied `data/business_listings.json` is a JSON array of 118 listing objects. Each entry can include:

```json
{
  "id": 1,
  "source": "Brokerage Name",
  "title": "Example Business",
  "listing_url": "https://example.com/listing/123",
  "status": "Active",
  "asking_price": "$300,000",
  "asking_price_usd": 300000,
  "location": "Raleigh, NC",
  "industry": "Business Services",
  "includes": "Business"
}
```

A wrapped JSON object `{ "listings": [...] }` is also accepted. `asking_price_usd` must be a *number*, not a formatted string. Prices that are absent, ranges, ambiguous, or include extra costs are flagged for manual review. `asking_price_usd == 1000000` is excluded. Sold, pending, under-contract and coming-soon listings are excluded.

The default snapshot results (tested against the supplied file): **56 eligible**, **24 manual review**, **38 excluded**. One of the 57 initially price-matching records is a real-estate-only listing and is therefore held for manual review. The five least expensive eligible listings receive drafts by default. **No source website is checked live.**

## What changed

The existing LangGraph orchestration still follows Gather → Check → Reason (price sort) → Decide → Draft → Review → Save. The conference-specific nodes, schemas, terminal runner, API and UI were replaced. The unchanged `agent/llm.py`, `agent/log.py` and `requirements.txt` remain part of your existing repository.

- `agent/listings.py`: normalized source records, deduplication, strict filter and manual-review handling.
- `agent/drafting.py`: deterministic emails, review decisions, Markdown/JSON saving.
- `agent/gather.py`, `check.py`, `reason.py`, `decide.py`, `act.py`, `graph.py`, `state.py`, `config.py`: Phase 1 workflow.
- `run.py`: CLI input and approval flow.
- `main.py` and `ui/index.html`: browser JSON upload, listing results and editable approvals.
- `tests/test_business_phase1.py`: offline unit tests.
- `tests/test_business_graph.py`: integration tests using LangGraph in mock mode.

The workshop's old `EXERCISES.md` and original conference tests (if present) are no longer applicable to the adapted workflow; run the Phase 1 tests shown above. The run checkpoint is in memory: restarting the API clears pending approvals. Saved output files remain on disk.

## Safety and data

Listing records are untrusted and may be stale. Human review is required before saving drafts, and the draft may still contain errors or unsupported claims. Do not send an outreach message without verifying the actual listing and filling in the correct broker contact and your own identity. Model providers may receive public listing data for drafting. No email integration or SMTP sending code is included.
