import json
import hashlib
from pinecone import Pinecone, ServerlessSpec

from backend.config import PINECONE_API_KEY, PINECONE_INDEX_NAME, EMBEDDING_DIMENSIONS


class PineconeStore:
    """Singleton wrapper around a Pinecone index."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._pc = Pinecone(api_key=PINECONE_API_KEY)
        self._ensure_index()
        self._index = self._pc.Index(PINECONE_INDEX_NAME)
        self._initialized = True

    def _ensure_index(self):
        """Create the index if it doesn't exist."""
        existing = [idx.name for idx in self._pc.list_indexes()]
        if PINECONE_INDEX_NAME not in existing:
            self._pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=EMBEDDING_DIMENSIONS,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )

    def upsert_chunks(self, embedded_chunks: list[dict], namespace: str = "") -> int:
        """Upsert embedded chunks in batches of 100. Returns count upserted."""
        vectors = []
        for item in embedded_chunks:
            chunk = item["chunk"]
            embedding = item["embedding"]

            # Build vector ID from file path + line range
            id_str = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
            vector_id = hashlib.md5(id_str.encode()).hexdigest()

            # Build metadata (stay under 40KB limit)
            metadata = {
                "file_path": chunk.file_path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "chunk_type": chunk.chunk_type,
                "name": chunk.name,
                "language": chunk.language,
                "content": chunk.content[:8000],  # Truncate to stay under limit
                "dependencies": json.dumps(chunk.dependencies[:50]),
            }

            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": metadata,
            })

        # Upsert in batches of 100
        count = 0
        for i in range(0, len(vectors), 100):
            batch = vectors[i : i + 100]
            self._index.upsert(vectors=batch, namespace=namespace)
            count += len(batch)

        return count

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        namespace: str = "",
        language: str = None,
        file_path: str = None,
    ) -> list[dict]:
        """Search for similar chunks. Returns list of results with metadata and scores."""
        filter_dict = {}
        if language:
            filter_dict["language"] = language
        if file_path:
            filter_dict["file_path"] = {"$eq": file_path}

        results = self._index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            namespace=namespace,
            filter=filter_dict if filter_dict else None,
        )

        matches = []
        for match in results.matches:
            meta = match.metadata or {}
            # Parse dependencies back from JSON
            deps = meta.get("dependencies", "[]")
            if isinstance(deps, str):
                try:
                    deps = json.loads(deps)
                except json.JSONDecodeError:
                    deps = []

            matches.append({
                "score": match.score,
                "file_path": meta.get("file_path", ""),
                "start_line": meta.get("start_line", 0),
                "end_line": meta.get("end_line", 0),
                "chunk_type": meta.get("chunk_type", ""),
                "name": meta.get("name", ""),
                "language": meta.get("language", ""),
                "content": meta.get("content", ""),
                "dependencies": deps,
            })

        return matches

    def get_stats(self) -> dict:
        """Return index statistics."""
        stats = self._index.describe_index_stats()
        return {
            "total_vectors": stats.total_vector_count,
            "namespaces": {ns: data.vector_count for ns, data in stats.namespaces.items()},
            "dimension": stats.dimension,
        }
