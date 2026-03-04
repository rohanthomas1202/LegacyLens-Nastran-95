"""Analyze the impact of changing a routine in the NASTRAN-95 codebase."""
from __future__ import annotations
from collections import deque
from backend.features.graph_builder import load_or_build_graph


def analyze_impact(name: str, max_depth: int = 5) -> dict:
    graph = load_or_build_graph()
    name = name.upper()
    
    if name not in graph.nodes:
        return {"error": f"Routine '{name}' not found in call graph"}
    
    levels = {}
    visited = {name}
    queue = deque()
    
    for caller in graph.reverse_edges.get(name, set()):
        if caller in graph.nodes and caller not in visited:
            queue.append((caller, 1))
            visited.add(caller)
    
    while queue:
        node, depth = queue.popleft()
        if depth > max_depth:
            continue
        
        info = graph.nodes.get(node, {})
        if depth not in levels:
            levels[depth] = []
        levels[depth].append({"name": node, **info})
        
        if depth < max_depth:
            for caller in graph.reverse_edges.get(node, set()):
                if caller in graph.nodes and caller not in visited:
                    visited.add(caller)
                    queue.append((caller, depth + 1))
    
    common_impact = []
    for block_name, routines in graph.common_blocks.items():
        if name in routines:
            for routine in sorted(routines):
                if routine != name and routine not in visited:
                    info = graph.nodes.get(routine, {})
                    if info:
                        common_impact.append({
                            "name": routine,
                            "block": block_name,
                            **info,
                        })
    
    impact_by_level = []
    for depth in sorted(levels.keys()):
        items = sorted(levels[depth], key=lambda x: x["name"])
        impact_by_level.append({"depth": depth, "label": f"{'Direct' if depth == 1 else f'{depth}-hop'} callers", "routines": items, "count": len(items)})
    
    total_affected = len(visited) - 1 + len(common_impact)
    
    return {
        "name": name,
        "impact_by_level": impact_by_level,
        "common_block_impact": common_impact,
        "total_affected": total_affected,
        "max_depth_reached": max(levels.keys()) if levels else 0,
    }
