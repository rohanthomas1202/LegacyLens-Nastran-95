"""Trace the shortest call path between two routines in the NASTRAN-95 codebase."""

from __future__ import annotations

from collections import deque

from backend.features.graph_builder import load_or_build_graph


def trace_flow(source: str, target: str) -> dict:
    """BFS shortest path from source to target through call graph edges."""
    graph = load_or_build_graph()
    source = source.upper()
    target = target.upper()

    if source not in graph.nodes:
        return {"error": f"Source '{source}' not found in call graph"}
    if target not in graph.nodes:
        return {"error": f"Target '{target}' not found in call graph"}
    if source == target:
        return {"error": "Source and target are the same routine"}

    # BFS
    visited = {source}
    queue = deque([(source, [source])])

    while queue:
        node, path = queue.popleft()

        for callee in graph.edges.get(node, set()):
            if callee == target:
                final_path = path + [callee]
                steps = []
                for name in final_path:
                    info = graph.nodes.get(name, {})
                    steps.append({
                        "name": name,
                        "chunk_type": info.get("chunk_type", "unknown"),
                        "file_path": info.get("file_path", ""),
                        "start_line": info.get("start_line", 0),
                        "end_line": info.get("end_line", 0),
                    })
                return {
                    "source": source,
                    "target": target,
                    "path": steps,
                    "length": len(final_path),
                }

            if callee not in visited and callee in graph.nodes:
                visited.add(callee)
                queue.append((callee, path + [callee]))

    return {
        "source": source,
        "target": target,
        "path": [],
        "length": 0,
        "error": f"No call path found from '{source}' to '{target}'",
    }
