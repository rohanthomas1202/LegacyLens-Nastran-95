"""Batch modernization: translate multiple routines with dependency ordering."""
from __future__ import annotations
from collections import deque
from backend.features.graph_builder import load_or_build_graph
from backend.features.modernizer import modernize_code
from backend.utils.logger import logger


def batch_modernize(names: list[str] = None, directory: str = None, target_language: str = "python") -> dict:
    graph = load_or_build_graph()
    
    if directory:
        directory = directory.rstrip("/")
        selected = [
            name for name, info in graph.nodes.items()
            if info["file_path"].startswith(directory + "/") or info["file_path"].startswith(directory + "\\")
        ]
    elif names:
        selected = [n.upper() for n in names if n.upper() in graph.nodes]
    else:
        return {"error": "Provide either 'names' or 'directory'"}
    
    if not selected:
        return {"error": "No matching routines found"}
    
    selected_set = set(selected)
    
    in_degree = {n: 0 for n in selected}
    adj = {n: [] for n in selected}
    for n in selected:
        for callee in graph.edges.get(n, set()):
            if callee in selected_set:
                adj[n].append(callee)
                in_degree[callee] = in_degree.get(callee, 0) + 1
    
    queue = deque(n for n in selected if in_degree.get(n, 0) == 0)
    ordered = []
    while queue:
        node = queue.popleft()
        ordered.append(node)
        for dep in adj.get(node, []):
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                queue.append(dep)
    remaining = [n for n in selected if n not in set(ordered)]
    ordered.extend(remaining)
    
    shared_state = []
    for block_name, routines in graph.common_blocks.items():
        overlap = routines & selected_set
        if len(overlap) >= 2:
            shared_state.append({
                "block": block_name,
                "routines": sorted(overlap),
                "count": len(overlap),
            })
    shared_state.sort(key=lambda x: -x["count"])
    
    results = []
    for name in ordered:
        info = graph.nodes.get(name, {})
        try:
            mod_result = modernize_code(name, target_language, top_k=3)
            results.append({
                "name": name,
                "file_path": info.get("file_path", ""),
                "status": "success" if "error" not in mod_result else "error",
                "translated_code": mod_result.get("translated_code", ""),
                "migration_notes": mod_result.get("migration_notes", ""),
                "error": mod_result.get("error"),
            })
        except Exception as e:
            logger.warning(f"Batch modernize failed for {name}: {e}")
            results.append({
                "name": name,
                "file_path": info.get("file_path", ""),
                "status": "error",
                "error": str(e),
            })
    
    return {
        "target_language": target_language,
        "migration_order": ordered,
        "results": results,
        "shared_state": shared_state,
        "total_routines": len(ordered),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] == "error"),
    }
