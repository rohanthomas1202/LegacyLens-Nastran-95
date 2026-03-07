import json
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from backend.config import LOGS_DIR

LOGS_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("nastran95")
logger.setLevel(logging.INFO)

if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(ch)

    fh = logging.FileHandler(LOGS_DIR / "nastran95.log")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)


EMBEDDING_COST_PER_1M = 0.02
LLM_INPUT_COST_PER_1M = 3.00
LLM_OUTPUT_COST_PER_1M = 15.00

COSTS_FILE = LOGS_DIR / "costs.json"


class CostTracker:
    """Track API usage costs, per-query history, and persist to file."""

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
                data = json.loads(COSTS_FILE.read_text())
                data.setdefault("query_history", [])
                return data
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "embedding_tokens": 0,
            "llm_input_tokens": 0,
            "llm_output_tokens": 0,
            "query_count": 0,
            "ingestion_count": 0,
            "last_updated": None,
            "query_history": [],
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

    def track_query_detail(
        self,
        query: str,
        mode: str,
        latency_ms: int,
        cost: float,
        top_score: float,
        chunks_count: int,
    ):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query[:120],
            "mode": mode,
            "latency_ms": latency_ms,
            "cost": round(cost, 4),
            "top_score": round(top_score, 4),
            "chunks": chunks_count,
        }
        self._data["query_history"].append(entry)
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

    def get_dashboard_stats(self) -> dict:
        """Compute enriched dashboard metrics from query history."""
        costs = self.get_costs()
        history = self._data.get("query_history", [])

        total_tokens = (
            self._data["embedding_tokens"]
            + self._data["llm_input_tokens"]
            + self._data["llm_output_tokens"]
        )

        avg_latency = 0
        avg_score = 0
        score_buckets = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8+": 0}
        mode_counts = defaultdict(int)
        latency_series = []

        if history:
            latencies = [h["latency_ms"] for h in history]
            scores = [h["top_score"] for h in history]
            avg_latency = round(sum(latencies) / len(latencies))
            avg_score = round(sum(scores) / len(scores) * 100) if scores else 0

            for h in history:
                mode_counts[h["mode"]] += 1
                s = h["top_score"]
                if s < 0.2:
                    score_buckets["0.0-0.2"] += 1
                elif s < 0.4:
                    score_buckets["0.2-0.4"] += 1
                elif s < 0.6:
                    score_buckets["0.4-0.6"] += 1
                elif s < 0.8:
                    score_buckets["0.6-0.8"] += 1
                else:
                    score_buckets["0.8+"] += 1

                latency_series.append({
                    "time": h["timestamp"],
                    "latency": h["latency_ms"],
                })

        high_score = sum(1 for h in history if h["top_score"] >= 0.5)
        satisfaction = round(high_score / len(history) * 100) if history else 100

        return {
            **costs,
            "total_tokens": total_tokens,
            "avg_latency": avg_latency,
            "avg_score": avg_score,
            "satisfaction": satisfaction,
            "score_distribution": score_buckets,
            "usage_by_mode": dict(mode_counts),
            "latency_series": latency_series[-50:],
            "recent_queries": list(reversed(history[-20:])),
        }
