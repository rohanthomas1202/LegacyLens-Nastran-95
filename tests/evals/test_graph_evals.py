"""
Eval 2 — Call Graph Integrity
Tests that the call graph is correctly built and queryable.
Covers: node/edge counts, subgraph BFS, flow tracing, dead code, autocomplete.
"""

import pytest
from backend.features.graph_builder import get_subgraph, load_or_build_graph


# ---------------------------------------------------------------------------
# E2.1  Graph statistics and structure
# ---------------------------------------------------------------------------

class TestGraphStructure:
    def test_minimum_node_count(self, graph_data):
        """NASTRAN-95 has ~2000+ routines; graph should reflect that."""
        assert graph_data["stats"]["total_routines"] >= 1500, \
            f"Only {graph_data['stats']['total_routines']} routines — expected >= 1500"

    def test_minimum_edge_count(self, graph_data):
        """Call graph should have substantial edges."""
        assert graph_data["stats"]["total_edges"] >= 5000, \
            f"Only {graph_data['stats']['total_edges']} edges — expected >= 5000"

    def test_common_blocks_detected(self, graph_data):
        assert graph_data["stats"]["total_common_blocks"] >= 50, \
            f"Only {graph_data['stats']['total_common_blocks']} COMMON blocks — expected >= 50"

    def test_all_names_sorted(self, graph_data):
        names = graph_data.get("all_names", [])
        assert names == sorted(names), "all_names should be sorted"
        assert len(names) == graph_data["stats"]["total_routines"]

    def test_every_node_has_required_fields(self, graph_data):
        required = {"file_path", "start_line", "end_line", "chunk_type"}
        bad = []
        for name, info in graph_data["nodes"].items():
            missing = required - set(info.keys())
            if missing:
                bad.append(f"{name}: missing {missing}")
        assert len(bad) == 0, f"{len(bad)} nodes with missing fields: {bad[:5]}"

    def test_edge_targets_exist_as_nodes(self, graph_data):
        """Most edge callers should be known nodes (some call external routines)."""
        nodes = set(graph_data["nodes"].keys())
        callers = set(graph_data["edges"].keys())
        unknown_callers = callers - nodes
        ratio = len(unknown_callers) / max(len(callers), 1)
        assert ratio < 0.05, \
            f"{len(unknown_callers)}/{len(callers)} callers not in nodes ({ratio:.0%})"


# ---------------------------------------------------------------------------
# E2.2  Subgraph extraction
# ---------------------------------------------------------------------------

class TestSubgraph:
    def test_center_node_present(self):
        result = get_subgraph("NASTRN", depth=1)
        assert "NASTRN" in result["nodes"]
        assert result["center"] == "NASTRN"

    def test_nonexistent_node_returns_error(self):
        result = get_subgraph("ZZZZNOTREAL", depth=1)
        assert "error" in result

    def test_depth1_includes_callees(self):
        result = get_subgraph("NASTRN", depth=1)
        assert result["node_count"] > 1, "Depth 1 should include at least NASTRN + callees"

    def test_depth2_larger_than_depth1(self):
        r1 = get_subgraph("NASTRN", depth=1)
        r2 = get_subgraph("NASTRN", depth=2)
        assert r2["node_count"] >= r1["node_count"], \
            f"Depth 2 ({r2['node_count']}) should be >= depth 1 ({r1['node_count']})"

    def test_depth3_larger_than_depth2(self):
        r2 = get_subgraph("NASTRN", depth=2)
        r3 = get_subgraph("NASTRN", depth=3)
        assert r3["node_count"] >= r2["node_count"]

    def test_edges_reference_known_nodes(self):
        """Edge endpoints should overwhelmingly exist in the nodes dict.
        A few external system calls (GETENV, ITIME, etc.) may not have definitions."""
        result = get_subgraph("NASTRN", depth=1)
        nodes = set(result["nodes"].keys())
        bad = []
        for edge in result["edges"]:
            if edge["source"] not in nodes:
                bad.append(edge["source"])
            if edge["target"] not in nodes:
                bad.append(edge["target"])
        ratio = len(bad) / max(len(result["edges"]) * 2, 1)
        assert ratio < 0.02, \
            f"{len(bad)} unknown edge endpoints ({ratio:.1%}): {list(set(bad))[:10]}"

    def test_case_insensitive_lookup(self):
        upper = get_subgraph("NASTRN", depth=1)
        lower = get_subgraph("nastrn", depth=1)
        assert upper["node_count"] == lower["node_count"]

    def test_include_common_adds_nodes(self):
        without = get_subgraph("NASTRN", depth=1, include_common=False)
        with_common = get_subgraph("NASTRN", depth=1, include_common=True)
        assert with_common["node_count"] >= without["node_count"]


# ---------------------------------------------------------------------------
# E2.3  Flow tracer
# ---------------------------------------------------------------------------

class TestFlowTracer:
    def test_known_direct_call(self):
        """NASTRN calls routines — tracing to a direct callee should find a 2-step path."""
        from backend.features.flow_tracer import trace_flow
        graph = load_or_build_graph()
        callees = list(graph.edges.get("NASTRN", set()))
        if not callees:
            pytest.skip("NASTRN has no callees")
        result = trace_flow("NASTRN", callees[0])
        assert "path" in result, f"Expected path, got: {result}"
        assert result["length"] == 2

    def test_same_node_error(self):
        from backend.features.flow_tracer import trace_flow
        result = trace_flow("NASTRN", "NASTRN")
        assert "error" in result

    def test_nonexistent_source(self):
        from backend.features.flow_tracer import trace_flow
        result = trace_flow("ZZZZFAKE", "NASTRN")
        assert "error" in result

    def test_path_nodes_have_metadata(self):
        from backend.features.flow_tracer import trace_flow
        graph = load_or_build_graph()
        callees = list(graph.edges.get("NASTRN", set()))
        if not callees:
            pytest.skip("NASTRN has no callees")
        result = trace_flow("NASTRN", callees[0])
        if "path" not in result:
            pytest.skip("No path found")
        required = {"name", "chunk_type", "file_path", "start_line", "end_line"}
        for step in result["path"]:
            missing = required - set(step.keys())
            assert not missing, f"Step missing fields: {missing}"


# ---------------------------------------------------------------------------
# E2.4  Dead code detection
# ---------------------------------------------------------------------------

class TestDeadCode:
    def test_returns_expected_structure(self):
        from backend.features.dead_code import detect_dead_code
        result = detect_dead_code()
        assert "dead_routines" in result
        assert "stats" in result
        assert isinstance(result["dead_routines"], list)

    def test_stats_are_consistent(self):
        from backend.features.dead_code import detect_dead_code
        result = detect_dead_code()
        s = result["stats"]
        assert s["dead_count"] + s["reachable_count"] == s["callable_routines"]
        assert s["entry_points"] + s["callable_routines"] == s["total_routines"]
        assert 0 <= s["coverage_pct"] <= 100

    def test_dead_routines_have_metadata(self):
        from backend.features.dead_code import detect_dead_code
        result = detect_dead_code()
        required = {"name", "chunk_type", "file_path", "start_line", "end_line"}
        for routine in result["dead_routines"][:20]:
            missing = required - set(routine.keys())
            assert not missing, f"{routine.get('name','?')} missing {missing}"

    def test_nastrn_is_not_dead(self):
        from backend.features.dead_code import detect_dead_code
        result = detect_dead_code()
        dead_names = {r["name"] for r in result["dead_routines"]}
        assert "NASTRN" not in dead_names, "NASTRN should not be detected as dead code"
