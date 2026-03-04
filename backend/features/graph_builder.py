"""Build and cache a call graph from the NASTRAN-95 codebase."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Optional

from backend.config import CODEBASES_DIR, GRAPH_CACHE_PATH
from backend.ingestion.file_discovery import discover_files
from backend.ingestion.preprocessor import read_file_with_encoding, preprocess_file
from backend.ingestion.chunker import chunk_file
from backend.utils.logger import logger


class CallGraph:
    """In-memory call graph with forward and reverse edges."""

    def __init__(self):
        self.nodes = {}            # name -> {file_path, start_line, end_line, chunk_type}
        self.edges = defaultdict(set)          # caller -> {callees}
        self.reverse_edges = defaultdict(set)  # callee -> {callers}
        self.common_blocks = defaultdict(set)  # block_name -> {routines}

    def add_node(self, name, file_path, start_line, end_line, chunk_type):
        if name not in self.nodes:
            self.nodes[name] = {
                "file_path": file_path,
                "start_line": start_line,
                "end_line": end_line,
                "chunk_type": chunk_type,
            }

    def add_edge(self, caller, callee):
        self.edges[caller].add(callee)
        self.reverse_edges[callee].add(caller)

    def add_common(self, block_name, routine_name):
        self.common_blocks[block_name].add(routine_name)

    def to_dict(self):
        return {
            "nodes": self.nodes,
            "edges": {k: sorted(v) for k, v in self.edges.items()},
            "reverse_edges": {k: sorted(v) for k, v in self.reverse_edges.items()},
            "common_blocks": {k: sorted(v) for k, v in self.common_blocks.items()},
            "all_names": sorted(self.nodes.keys()),
            "stats": {
                "total_routines": len(self.nodes),
                "total_edges": sum(len(v) for v in self.edges.values()),
                "total_common_blocks": len(self.common_blocks),
            },
        }

    @classmethod
    def from_dict(cls, data):
        graph = cls()
        graph.nodes = data.get("nodes", {})
        for caller, callees in data.get("edges", {}).items():
            graph.edges[caller] = set(callees)
        for callee, callers in data.get("reverse_edges", {}).items():
            graph.reverse_edges[callee] = set(callers)
        for block, routines in data.get("common_blocks", {}).items():
            graph.common_blocks[block] = set(routines)
        return graph


def build_call_graph(codebase_path: str = None) -> CallGraph:
    """Scan all source files and build a call graph from dependencies."""
    if codebase_path is None:
        # Auto-detect: use first subdirectory in codebases/
        if not CODEBASES_DIR.exists():
            raise FileNotFoundError(f"Codebases directory not found: {CODEBASES_DIR}")
        subdirs = [d for d in CODEBASES_DIR.iterdir() if d.is_dir()]
        if not subdirs:
            raise FileNotFoundError("No codebase found in codebases/")
        codebase_path = str(subdirs[0])

    logger.info(f"Building call graph from {codebase_path}...")
    files = discover_files(codebase_path)
    graph = CallGraph()

    for i, file_info in enumerate(files):
        try:
            content = read_file_with_encoding(file_info["file_path"])
            content = preprocess_file(content, file_info["language"])
            chunks = chunk_file(content, file_info["relative_path"], file_info["language"])

            for chunk in chunks:
                # Skip file-header and fixed-size chunks for the graph
                if chunk.chunk_type in ("file-header", "fixed-size"):
                    continue

                graph.add_node(
                    chunk.name,
                    chunk.file_path,
                    chunk.start_line,
                    chunk.end_line,
                    chunk.chunk_type,
                )

                # Parse dependencies
                for dep in chunk.dependencies:
                    if dep.startswith("CALL:"):
                        target = dep.split(":", 1)[1]
                        graph.add_edge(chunk.name, target)
                    elif dep.startswith("COMMON:"):
                        block = dep.split(":", 1)[1]
                        graph.add_common(block, chunk.name)

        except Exception as e:
            logger.warning(f"Graph builder: failed to process {file_info['relative_path']}: {e}")

        if (i + 1) % 200 == 0:
            logger.info(f"  Graph builder: processed {i + 1}/{len(files)} files")

    logger.info(
        f"Call graph built: {len(graph.nodes)} routines, "
        f"{sum(len(v) for v in graph.edges.values())} edges, "
        f"{len(graph.common_blocks)} COMMON blocks"
    )

    # Cache to disk
    save_graph(graph)
    return graph


def save_graph(graph: CallGraph):
    """Persist graph to JSON cache file."""
    GRAPH_CACHE_PATH.write_text(json.dumps(graph.to_dict(), indent=2))
    logger.info(f"Graph cached to {GRAPH_CACHE_PATH}")


def load_graph() -> CallGraph | None:
    """Load graph from cache, returns None if not cached."""
    if not GRAPH_CACHE_PATH.exists():
        return None
    try:
        data = json.loads(GRAPH_CACHE_PATH.read_text())
        return CallGraph.from_dict(data)
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Failed to load graph cache: {e}")
        return None


def load_or_build_graph(codebase_path: str = None) -> CallGraph:
    """Load cached graph or build it if not available."""
    graph = load_graph()
    if graph is not None:
        return graph
    return build_call_graph(codebase_path)


def get_subgraph(center: str, depth: int = 2, include_common: bool = False) -> dict:
    """Return a subgraph centered on a node, expanding to the given depth via BFS."""
    graph = load_or_build_graph()
    center = center.upper()

    if center not in graph.nodes:
        return {"error": f"Entity '{center}' not found", "nodes": {}, "edges": []}

    # BFS from center
    visited = set()
    queue = [(center, 0)]
    subgraph_nodes = {}
    subgraph_edges = []

    while queue:
        node, d = queue.pop(0)
        if node in visited or d > depth:
            continue
        visited.add(node)

        if node in graph.nodes:
            subgraph_nodes[node] = graph.nodes[node]

            # Forward edges (callees)
            for callee in graph.edges.get(node, set()):
                subgraph_edges.append({"source": node, "target": callee, "type": "calls"})
                if d + 1 <= depth and callee not in visited:
                    queue.append((callee, d + 1))

            # Reverse edges (callers)
            for caller in graph.reverse_edges.get(node, set()):
                subgraph_edges.append({"source": caller, "target": node, "type": "calls"})
                if d + 1 <= depth and caller not in visited:
                    queue.append((caller, d + 1))

        # Include COMMON block connections if requested
        if include_common:
            for block, routines in graph.common_blocks.items():
                if node in routines:
                    for routine in routines:
                        if routine != node:
                            subgraph_edges.append({
                                "source": node, "target": routine,
                                "type": "common", "block": block,
                            })
                            if d + 1 <= depth and routine not in visited:
                                queue.append((routine, d + 1))

    # Ensure all edge endpoints have node info
    for edge in subgraph_edges:
        for key in ("source", "target"):
            name = edge[key]
            if name not in subgraph_nodes and name in graph.nodes:
                subgraph_nodes[name] = graph.nodes[name]

    return {
        "center": center,
        "nodes": subgraph_nodes,
        "edges": subgraph_edges,
        "node_count": len(subgraph_nodes),
        "edge_count": len(subgraph_edges),
    }
