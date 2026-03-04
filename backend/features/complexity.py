"""Compute code complexity metrics for NASTRAN-95 routines."""
from __future__ import annotations
import re
from backend.features.graph_builder import load_or_build_graph
from backend.ingestion.preprocessor import read_file_with_encoding
from backend.config import CODEBASES_DIR


def get_complexity(name: str = None, top_n: int = 20) -> dict:
    graph = load_or_build_graph()
    
    if name:
        name = name.upper()
        if name not in graph.nodes:
            return {"error": f"Routine '{name}' not found"}
        metrics = _compute_metrics(name, graph.nodes[name])
        return {"routine": metrics}
    
    all_metrics = []
    for rname, info in graph.nodes.items():
        m = _compute_metrics(rname, info)
        if m:
            all_metrics.append(m)
    
    all_metrics.sort(key=lambda x: -x["complexity_score"])
    
    return {
        "routines": all_metrics[:top_n],
        "total_analyzed": len(all_metrics),
        "stats": {
            "avg_loc": round(sum(m["loc"] for m in all_metrics) / max(len(all_metrics), 1), 1),
            "avg_complexity": round(sum(m["complexity_score"] for m in all_metrics) / max(len(all_metrics), 1), 1),
            "max_complexity": all_metrics[0]["complexity_score"] if all_metrics else 0,
            "most_complex": all_metrics[0]["name"] if all_metrics else "",
        },
    }


def _compute_metrics(name: str, info: dict) -> dict | None:
    content = _read_routine_content(info)
    if not content:
        loc = info.get("end_line", 0) - info.get("start_line", 0) + 1
        return {
            "name": name,
            "file_path": info.get("file_path", ""),
            "start_line": info.get("start_line", 0),
            "end_line": info.get("end_line", 0),
            "chunk_type": info.get("chunk_type", ""),
            "loc": loc,
            "goto_count": 0,
            "call_count": 0,
            "if_count": 0,
            "do_count": 0,
            "common_count": 0,
            "complexity_score": loc,
        }
    
    lines = content.split("\n")
    loc = len(lines)
    upper = content.upper()
    
    goto_count = len(re.findall(r"\bGO\s*TO\b", upper))
    call_count = len(re.findall(r"\bCALL\s+\w+", upper))
    if_count = len(re.findall(r"\bIF\s*\(", upper))
    do_count = len(re.findall(r"\bDO\s+\d+", upper))
    common_count = len(re.findall(r"\bCOMMON\s*/", upper))
    
    complexity_score = loc + goto_count * 3 + if_count * 2 + do_count * 2 + call_count
    
    return {
        "name": name,
        "file_path": info.get("file_path", ""),
        "start_line": info.get("start_line", 0),
        "end_line": info.get("end_line", 0),
        "chunk_type": info.get("chunk_type", ""),
        "loc": loc,
        "goto_count": goto_count,
        "call_count": call_count,
        "if_count": if_count,
        "do_count": do_count,
        "common_count": common_count,
        "complexity_score": complexity_score,
    }


def _read_routine_content(info: dict) -> str | None:
    try:
        codebases = [d for d in CODEBASES_DIR.iterdir() if d.is_dir()]
        for cb in codebases:
            fpath = cb / info["file_path"]
            if not fpath.exists():
                continue
            all_lines = read_file_with_encoding(str(fpath)).split("\n")
            start = max(0, info["start_line"] - 1)
            end = info["end_line"]
            return "\n".join(all_lines[start:end])
    except Exception:
        return None
