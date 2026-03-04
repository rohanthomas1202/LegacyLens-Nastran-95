import time
from openai import OpenAI, RateLimitError

from backend.config import OPENAI_API_KEY, EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE
from backend.ingestion.chunker import Chunk, estimate_tokens
from backend.utils.logger import logger

_client = None

# text-embedding-3-small max context is 8191 tokens
MAX_EMBEDDING_TOKENS = 8000  # Leave some margin


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def _build_embedding_text(chunk: Chunk) -> str:
    """Prepend metadata header to chunk content for better embedding quality."""
    header = f"[{chunk.language.upper()} {chunk.chunk_type.upper()} '{chunk.name}' in {chunk.file_path}:{chunk.start_line}-{chunk.end_line}]"
    text = f"{header}\n{chunk.content}"

    # Truncate if too long for the embedding model
    tokens = estimate_tokens(text)
    if tokens > MAX_EMBEDDING_TOKENS:
        # Rough truncation: take first ~80% of lines to stay under limit
        lines = text.split("\n")
        while estimate_tokens("\n".join(lines)) > MAX_EMBEDDING_TOKENS and len(lines) > 5:
            lines = lines[: int(len(lines) * 0.8)]
        text = "\n".join(lines)

    return text


def _embed_batch_with_retry(client, texts: list[str], max_retries: int = 5):
    """Embed a batch with exponential backoff on rate limits."""
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts,
            )
            return response
        except RateLimitError:
            wait = 2 ** attempt + 1
            logger.warning(f"Rate limit hit, waiting {wait}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(wait)
    # Final attempt without catching
    return client.embeddings.create(model=EMBEDDING_MODEL, input=texts)


def embed_chunks(chunks: list[Chunk]) -> tuple:
    """Generate embeddings for a list of chunks in batches. Returns (results, total_tokens)."""
    client = _get_client()
    results = []
    total_tokens = 0

    total_batches = (len(chunks) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE

    for i in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        batch = chunks[i : i + EMBEDDING_BATCH_SIZE]
        batch_num = i // EMBEDDING_BATCH_SIZE + 1
        texts = [_build_embedding_text(c) for c in batch]

        response = _embed_batch_with_retry(client, texts)

        batch_tokens = response.usage.total_tokens
        total_tokens += batch_tokens

        for j, embedding_data in enumerate(response.data):
            results.append({
                "chunk": batch[j],
                "embedding": embedding_data.embedding,
            })

        if batch_num % 5 == 0 or batch_num == total_batches:
            logger.info(f"  Embedded batch {batch_num}/{total_batches} ({len(results)} chunks, {total_tokens:,} tokens)")

        # Small delay between batches to avoid rate limits (1M TPM limit)
        time.sleep(0.5)

    return results, total_tokens
