"""Cross-reference variables across NASTRAN-95 routines."""
from __future__ import annotations
import re
from backend.features.graph_builder import load_or_build_graph
from backend.ingestion.preprocessor import read_file_with_encoding
from backend.config import CODEBASES_DIR


def cross_reference(variable: str, limit: int = 50) -> dict:
    graph = load_or_build_graph()
    variable = variable.upper().strip()
    
    if not variable or len(variable) < 2:
        return {"error": "Variable name must be at least 2 characters"}
    
    pattern = re.compile(rf"\b{re.escape(variable)}\b", re.IGNORECASE)
    assign_pattern = re.compile(
        rf"^\s{{6}}\s*{re.escape(variable)}\s*(\([^)]*\))?\s*=", re.IGNORECASE | re.MULTILINE
    )
    common_pattern = re.compile(
        rf"COMMON\s*/\s*\w+\s*/[^'\n]*\b{re.escape(variable)}\b", re.IGNORECASE
    )
    
    references = []
    common_blocks_found = set()
    
    for rname, info in graph.nodes.items():
        content = _read_routine(info)
        if not content:
            continue
        
        if not pattern.search(content):
            continue
        
        is_write = bool(assign_pattern.search(content))
        is_read = bool(pattern.search(content)) and not is_write or (
            is_write and content.upper().count(variable) > len(assign_pattern.findall(content))
        )
        
        for m in common_pattern.finditer(content):
            block_match = re.search(r"COMMON\s*/\s*(\w+)\s*/", m.group(), re.IGNORECASE)
            if block_match:
                common_blocks_found.add(block_match.group(1).upper())
        
        access = "read-write" if (is_read and is_write) else ("write" if is_write else "read")
        
        references.append({
            "name": rname,
            "file_path": info.get("file_path", ""),
            "start_line": info.get("start_line", 0),
            "end_line": info.get("end_line", 0),
            "chunk_type": info.get("chunk_type", ""),
            "access": access,
        })
        
        if len(references) >= limit:
            break
    
    references.sort(key=lambda r: (r["access"] != "write", r["file_path"], r["name"]))
    
    return {
        "variable": variable,
        "references": references,
        "total_references": len(references),
        "common_blocks": sorted(common_blocks_found),
        "writers": sum(1 for r in references if r["access"] in ("write", "read-write")),
        "readers": sum(1 for r in references if r["access"] in ("read", "read-write")),
    }


def _read_routine(info: dict) -> str | None:
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
