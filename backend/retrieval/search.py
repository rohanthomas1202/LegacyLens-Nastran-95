from openai import OpenAI

from backend.config import OPENAI_API_KEY, EMBEDDING_MODEL, TOP_K
from backend.vector_store.pinecone_client import PineconeStore

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def embed_query(query: str) -> list[float]:
    """Embed a search query using the same model as ingestion."""
    client = _get_client()
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query,
    )
    return response.data[0].embedding


def semantic_search(
    query: str,
    top_k: int = TOP_K,
    language: str = None,
    file_path: str = None,
) -> list[dict]:
    """Embed a query and search Pinecone for similar chunks."""
    query_embedding = embed_query(query)
    store = PineconeStore()
    results = store.search(
        query_embedding=query_embedding,
        top_k=top_k,
        language=language,
        file_path=file_path,
    )
    return results
