import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "nastran95")

# Embedding config
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
EMBEDDING_BATCH_SIZE = 100

# LLM config
LLM_MODEL = "claude-sonnet-4-20250514"
LLM_MAX_TOKENS = 2000

# Chunking config
CHUNK_SIZE_TOKENS = 800
CHUNK_OVERLAP_TOKENS = 200
CHUNK_SIZE_LINES = 40
CHUNK_OVERLAP_LINES = 10

# Retrieval config
TOP_K = 5

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CODEBASES_DIR = PROJECT_ROOT / "codebases"
LOGS_DIR = PROJECT_ROOT / "logs"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
GRAPH_CACHE_PATH = PROJECT_ROOT / "backend" / "graph_cache.json"

# Language detection by file extension
LANGUAGE_MAP = {
    ".f": "fortran",
    ".f77": "fortran",
    ".f90": "fortran",
    ".f95": "fortran",
    ".for": "fortran",
    ".fpp": "fortran",
    ".c": "c",
    ".h": "c",
    ".cob": "cobol",
    ".cbl": "cobol",
    ".cpy": "cobol",
}

# Directories to skip during file discovery
SKIP_DIRS = {"bin", "inp", "um", ".git", "__pycache__", "node_modules"}
