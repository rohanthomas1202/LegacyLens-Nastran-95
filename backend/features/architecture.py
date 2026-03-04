"""Generate a module-level architecture map of the NASTRAN-95 codebase."""
from __future__ import annotations
from collections import defaultdict
from backend.features.graph_builder import load_or_build_graph


def get_architecture() -> dict:
    graph = load_or_build_graph()
    
    module_nodes = defaultdict(list)
    node_to_module = {}
    
    for name, info in graph.nodes.items():
        fp = info.get("file_path", "")
        module = fp.split("/")[0] if "/" in fp else "root"
        module_nodes[module].append(name)
        node_to_module[name] = module
    
    inter_module_edges = defaultdict(int)
    intra_module_edges = defaultdict(int)
    
    for caller, callees in graph.edges.items():
        src_mod = node_to_module.get(caller)
        if not src_mod:
            continue
        for callee in callees:
            tgt_mod = node_to_module.get(callee)
            if not tgt_mod:
                continue
            if src_mod == tgt_mod:
                intra_module_edges[src_mod] += 1
            else:
                key = tuple(sorted([src_mod, tgt_mod]))
                inter_module_edges[key] += 1
    
    module_connections = defaultdict(lambda: defaultdict(int))
    for caller, callees in graph.edges.items():
        src_mod = node_to_module.get(caller)
        if not src_mod:
            continue
        for callee in callees:
            tgt_mod = node_to_module.get(callee)
            if tgt_mod and src_mod != tgt_mod:
                module_connections[src_mod][tgt_mod] += 1

    modules = []
    for mod_name, routines in sorted(module_nodes.items()):
        types = defaultdict(int)
        routine_details = []
        for rname in sorted(routines):
            info = graph.nodes.get(rname, {})
            ctype = info.get("chunk_type", "unknown")
            types[ctype] += 1
            routine_details.append({
                "name": rname,
                "chunk_type": ctype,
                "file_path": info.get("file_path", ""),
                "start_line": info.get("start_line", 0),
                "end_line": info.get("end_line", 0),
                "calls_out": len(graph.edges.get(rname, set())),
                "called_by": len(graph.reverse_edges.get(rname, set())),
            })

        connects_to = [
            {"module": tgt, "calls": count}
            for tgt, count in sorted(module_connections[mod_name].items(), key=lambda x: -x[1])
        ]

        modules.append({
            "name": mod_name,
            "routine_count": len(routines),
            "types": dict(types),
            "internal_edges": intra_module_edges.get(mod_name, 0),
            "routines": routine_details,
            "connects_to": connects_to,
        })

    modules.sort(key=lambda m: -m["routine_count"])

    edges = []
    for (src, tgt), weight in sorted(inter_module_edges.items(), key=lambda x: -x[1]):
        edges.append({"source": src, "target": tgt, "weight": weight})

    return {
        "modules": modules,
        "edges": edges,
        "total_modules": len(modules),
        "total_inter_module_edges": sum(inter_module_edges.values()),
    }
