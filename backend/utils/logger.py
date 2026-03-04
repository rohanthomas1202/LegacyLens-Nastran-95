import json
import logging
from pathlib import Path
from datetime import datetime

from backend.config import LOGS_DIR

# Ensure logs directory exists
LOGS_DIR.mkdir(exist_ok=True)

# Setup logger
logger = logging.getLogger("nastran95")
logger.setLevel(logging.INFO)

if not logger.handlers:
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(ch)

    # File handler
    fh = logging.FileHandler(LOGS_DIR / "nastran95.log")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)


# Pricing constants (per 1M tokens)
EMBEDDING_COST_PER_1M = 0.02  # text-embedding-3-small
LLM_INPUT_COST_PER_1M = 3.00  # Claude Sonnet input
LLM_OUTPUT_COST_PER_1M = 15.00  # Claude Sonnet output

COSTS_FILE = LOGS_DIR / "costs.json"


class CostTracker:
    """Track API usage costs and persist to file."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._data = self._load()
        self._initialized = True

    def _load(self) -> dict:
        if COSTS_FILE.exists():
            try:
                return json.loads(COSTS_FILE.read_text())
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "embedding_tokens": 0,
            "llm_input_tokens": 0,
            "llm_output_tokens": 0,
            "query_count": 0,
            "ingestion_count": 0,
            "last_updated": None,
        }

    def _save(self):
        self._data["last_updated"] = datetime.now().isoformat()
        COSTS_FILE.write_text(json.dumps(self._data, indent=2))

    def track_embedding(self, tokens: int):
        self._data["embedding_tokens"] += tokens
        self._save()

    def track_llm(self, input_tokens: int, output_tokens: int):
        self._data["llm_input_tokens"] += input_tokens
        self._data["llm_output_tokens"] += output_tokens
        self._save()

    def track_query(self):
        self._data["query_count"] += 1
        self._save()

    def track_ingestion(self):
        self._data["ingestion_count"] += 1
        self._save()

    def get_costs(self) -> dict:
        embedding_cost = (self._data["embedding_tokens"] / 1_000_000) * EMBEDDING_COST_PER_1M
        llm_input_cost = (self._data["llm_input_tokens"] / 1_000_000) * LLM_INPUT_COST_PER_1M
        llm_output_cost = (self._data["llm_output_tokens"] / 1_000_000) * LLM_OUTPUT_COST_PER_1M

        return {
            "embedding_tokens": self._data["embedding_tokens"],
            "llm_input_tokens": self._data["llm_input_tokens"],
            "llm_output_tokens": self._data["llm_output_tokens"],
            "embedding_cost": round(embedding_cost, 4),
            "llm_input_cost": round(llm_input_cost, 4),
            "llm_output_cost": round(llm_output_cost, 4),
            "total_cost": round(embedding_cost + llm_input_cost + llm_output_cost, 4),
            "query_count": self._data["query_count"],
            "ingestion_count": self._data["ingestion_count"],
            "last_updated": self._data["last_updated"],
        }
