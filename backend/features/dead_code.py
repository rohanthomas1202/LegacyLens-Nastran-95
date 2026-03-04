"""Detect potentially dead (unreachable) routines in the NASTRAN-95 codebase."""

from __future__ import annotations

from backend.features.graph_builder import load_or_build_graph


def detect_dead_code() -> dict:
    """Find routines with zero incoming call edges.

    Excludes PROGRAM and BLOCK DATA entries since they are entry points
    by definition and won't have callers.
    """
    graph = load_or_build_graph()

    # Entry-point types that are expected to have no callers
    entry_types = {"program", "block-data"}

    dead = []
    for name, info in graph.nodes.items():
        if info["chunk_type"] in entry_types:
            continue
        callers = graph.reverse_edges.get(name, set())
        if len(callers) == 0:
            dead.append({
                "name": name,
                "chunk_type": info["chunk_type"],
                "file_path": info["file_path"],
                "start_line": info["start_line"],
                "end_line": info["end_line"],
            })

    # Sort by file path then name
    dead.sort(key=lambda d: (d["file_path"], d["name"]))

    total = len(graph.nodes)
    entry_count = sum(1 for info in graph.nodes.values() if info["chunk_type"] in entry_types)
    callable_total = total - entry_count

    return {
        "dead_routines": dead,
        "stats": {
            "total_routines": total,
            "entry_points": entry_count,
            "callable_routines": callable_total,
            "dead_count": len(dead),
            "reachable_count": callable_total - len(dead),
            "coverage_pct": round((callable_total - len(dead)) / max(callable_total, 1) * 100, 1),
        },
        "disclaimer": (
            "Some routines may be called dynamically via DMAP sequences or "
            "computed GOTOs, which static analysis cannot detect. "
            "Review before removing any code."
        ),
    }
