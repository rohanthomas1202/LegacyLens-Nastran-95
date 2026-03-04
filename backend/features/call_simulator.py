"""Simulate call stack execution from an entry point in NASTRAN-95."""
from __future__ import annotations
from backend.features.graph_builder import load_or_build_graph


def simulate_calls(entry_point: str, max_steps: int = 200) -> dict:
    graph = load_or_build_graph()
    entry_point = entry_point.upper()
    
    if entry_point not in graph.nodes:
        return {"error": f"Entry point '{entry_point}' not found in call graph"}
    
    steps = []
    visited_count = {}
    stack_depth = 0
    
    def dfs(node: str, depth: int):
        nonlocal stack_depth
        if len(steps) >= max_steps:
            return
        
        visited_count[node] = visited_count.get(node, 0) + 1
        if visited_count[node] > 2:
            return
        
        info = graph.nodes.get(node, {})
        steps.append({
            "step": len(steps) + 1,
            "name": node,
            "depth": depth,
            "action": "call",
            "file_path": info.get("file_path", ""),
            "start_line": info.get("start_line", 0),
            "end_line": info.get("end_line", 0),
            "chunk_type": info.get("chunk_type", ""),
        })
        
        callees = sorted(graph.edges.get(node, set()))
        for callee in callees:
            if callee in graph.nodes and len(steps) < max_steps:
                dfs(callee, depth + 1)
        
        if len(steps) < max_steps:
            steps.append({
                "step": len(steps) + 1,
                "name": node,
                "depth": depth,
                "action": "return",
                "file_path": info.get("file_path", ""),
                "start_line": info.get("start_line", 0),
                "end_line": info.get("end_line", 0),
                "chunk_type": info.get("chunk_type", ""),
            })
    
    dfs(entry_point, 0)
    
    unique_routines = set(s["name"] for s in steps if s["action"] == "call")
    max_depth = max((s["depth"] for s in steps), default=0)
    
    return {
        "entry_point": entry_point,
        "steps": steps,
        "total_steps": len(steps),
        "unique_routines": len(unique_routines),
        "max_depth": max_depth,
        "truncated": len(steps) >= max_steps,
    }
