"""Phase 1 settings. Existing .env files and API credentials are preserved."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "claude").strip().lower()
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Strictly less than this price; equal to the cap is excluded.
MAX_ASKING_PRICE = int(os.getenv("MAX_ASKING_PRICE", "1000000"))
# Generate this many drafts, selecting the lowest eligible asking prices first.
MAX_DRAFTS = max(0, int(os.getenv("MAX_DRAFTS", "5")))

DATA_DIR = ROOT / "data"
DEFAULT_LISTINGS = DATA_DIR / "business_listings.json"
LOG_DIR = ROOT / "logs"
OUTPUT_DIR = ROOT / "outputs"
