"""Ingestion orchestrator: discover → preprocess → chunk → embed → store."""

import sys
import time
from pathlib import Path

from backend.ingestion.file_discovery import discover_files
from backend.ingestion.preprocessor import read_file_with_encoding, preprocess_file
from backend.ingestion.chunker import chunk_file, Chunk
from backend.ingestion.embedder import embed_chunks
from backend.vector_store.pinecone_client import PineconeStore
from backend.utils.logger import logger, CostTracker


def ingest_codebase(codebase_path: str, namespace: str = "") -> dict:
    """Run the full ingestion pipeline on a codebase directory."""
    start_time = time.time()
    cost_tracker = CostTracker()

    # Step 1: Discover files
    logger.info(f"Discovering files in {codebase_path}...")
    files = discover_files(codebase_path)
    total_loc = sum(f["line_count"] for f in files)
    logger.info(f"Found {len(files)} files, {total_loc:,} total lines of code")

    # Step 2 & 3: Preprocess and chunk each file
    all_chunks: list[Chunk] = []
    for i, file_info in enumerate(files):
        try:
            content = read_file_with_encoding(file_info["file_path"])
            content = preprocess_file(content, file_info["language"])
            chunks = chunk_file(content, file_info["relative_path"], file_info["language"])
            all_chunks.extend(chunks)

            if (i + 1) % 100 == 0:
                logger.info(f"  Processed {i + 1}/{len(files)} files, {len(all_chunks)} chunks so far")
        except Exception as e:
            logger.warning(f"  Failed to process {file_info['relative_path']}: {e}")

    logger.info(f"Created {len(all_chunks)} chunks from {len(files)} files")

    if not all_chunks:
        logger.error("No chunks created. Aborting ingestion.")
        return {"error": "No chunks created"}

    # Step 4: Generate embeddings
    logger.info("Generating embeddings...")
    embedded_chunks, total_tokens = embed_chunks(all_chunks)
    logger.info(f"Generated {len(embedded_chunks)} embeddings using {total_tokens:,} tokens")
    cost_tracker.track_embedding(total_tokens)

    # Step 5: Store in Pinecone
    logger.info("Storing in Pinecone...")
    store = PineconeStore()
    upserted = store.upsert_chunks(embedded_chunks, namespace=namespace)
    logger.info(f"Upserted {upserted} vectors to Pinecone")

    elapsed = time.time() - start_time
    cost_tracker.track_ingestion()

    result = {
        "files_processed": len(files),
        "total_loc": total_loc,
        "chunks_created": len(all_chunks),
        "embeddings_generated": len(embedded_chunks),
        "embedding_tokens": total_tokens,
        "vectors_upserted": upserted,
        "elapsed_seconds": round(elapsed, 2),
    }
    logger.info(f"Ingestion complete in {elapsed:.1f}s: {result}")
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m backend.ingest <codebase_path>")
        sys.exit(1)

    codebase_path = sys.argv[1]
    if not Path(codebase_path).exists():
        print(f"Error: Path not found: {codebase_path}")
        sys.exit(1)

    result = ingest_codebase(codebase_path)
    print(f"\nIngestion Result: {result}")


if __name__ == "__main__":
    main()
