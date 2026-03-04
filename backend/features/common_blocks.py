"""Inspect COMMON blocks across the NASTRAN-95 codebase."""
from __future__ import annotations
import re
from backend.features.graph_builder import load_or_build_graph
from backend.ingestion.preprocessor import read_file_with_encoding
from backend.config import CODEBASES_DIR


def get_common_blocks() -> dict:
    graph = load_or_build_graph()
    blocks = []
    
    for block_name, routines in sorted(graph.common_blocks.items()):
        routine_list = []
        for rname in sorted(routines):
            info = graph.nodes.get(rname, {})
            routine_list.append({"name": rname, **info})
        
        variables = _parse_block_variables(block_name, routines, graph)
        
        blocks.append({
            "name": block_name,
            "routines": routine_list,
            "routine_count": len(routine_list),
            "variables": variables,
        })
    
    blocks.sort(key=lambda b: -b["routine_count"])
    
    return {
        "blocks": blocks,
        "total_blocks": len(blocks),
        "stats": {
            "total_blocks": len(blocks),
            "avg_routines_per_block": round(sum(b["routine_count"] for b in blocks) / max(len(blocks), 1), 1),
            "max_coupling": blocks[0]["routine_count"] if blocks else 0,
            "most_coupled_block": blocks[0]["name"] if blocks else "",
        },
    }


def _parse_block_variables(block_name: str, routines: set, graph) -> list[str]:
    """Try to extract variable names from a COMMON block declaration in source files."""
    pattern = re.compile(
        rf"COMMON\s*/\s*{re.escape(block_name)}\s*/\s*(.+)", re.IGNORECASE
    )
    
    for rname in list(routines)[:5]:
        info = graph.nodes.get(rname)
        if not info:
            continue
        try:
            codebases = [d for d in CODEBASES_DIR.iterdir() if d.is_dir()]
            for cb in codebases:
                fpath = cb / info["file_path"]
                if not fpath.exists():
                    continue
                content = read_file_with_encoding(str(fpath))
                for line in content.split("\n"):
                    m = pattern.search(line)
                    if m:
                        var_str = m.group(1).strip()
                        var_str = var_str.split("!")[0].strip()
                        variables = []
                        depth = 0
                        current = ""
                        for ch in var_str:
                            if ch == "(":
                                depth += 1
                                current += ch
                            elif ch == ")":
                                depth -= 1
                                current += ch
                            elif ch == "," and depth == 0:
                                name = current.strip().split("(")[0].strip()
                                if name:
                                    variables.append(name)
                                current = ""
                            else:
                                current += ch
                        name = current.strip().split("(")[0].strip()
                        if name:
                            variables.append(name)
                        return variables
        except Exception:
            continue
    return []
