"""
Eval 1 — Chunker Quality
Tests that the ingestion chunker correctly parses real NASTRAN-95 Fortran files.
Covers: boundary detection, name extraction, dependency extraction, line accuracy.
"""

import pytest
from backend.ingestion.chunker import chunk_file, chunk_fortran, extract_fortran_dependencies
from backend.ingestion.preprocessor import read_file_with_encoding, preprocess_file


# ---------------------------------------------------------------------------
# E1.1  Real-file parsing produces non-empty, well-formed chunks
# ---------------------------------------------------------------------------

class TestRealFileParsing:
    def test_all_files_produce_chunks(self, sample_fortran_files):
        """Every discovered Fortran file should produce at least one chunk."""
        failures = []
        for finfo in sample_fortran_files[:200]:
            try:
                content = read_file_with_encoding(finfo["file_path"])
                content = preprocess_file(content, finfo["language"])
                chunks = chunk_file(content, finfo["relative_path"], finfo["language"])
                if len(chunks) == 0:
                    failures.append(finfo["relative_path"])
            except Exception as e:
                failures.append(f"{finfo['relative_path']}: {e}")
        assert len(failures) == 0, f"{len(failures)} files produced 0 chunks: {failures[:10]}"

    def test_no_empty_chunk_content(self, sample_fortran_files):
        """Code chunks (subroutine, function, etc.) should not have empty content.
        file-header and block-data chunks may legitimately be empty."""
        SKIP_TYPES = {"file-header", "block-data"}
        empty = []
        for finfo in sample_fortran_files[:200]:
            try:
                content = read_file_with_encoding(finfo["file_path"])
                content = preprocess_file(content, finfo["language"])
                for ch in chunk_file(content, finfo["relative_path"], finfo["language"]):
                    if ch.chunk_type in SKIP_TYPES:
                        continue
                    if not ch.content.strip():
                        empty.append(f"{finfo['relative_path']}:{ch.name}")
            except Exception:
                pass
        assert len(empty) == 0, f"{len(empty)} empty chunks: {empty[:10]}"

    def test_line_numbers_monotonic(self, sample_fortran_files):
        """start_line <= end_line for every chunk, and start_line >= 1."""
        bad = []
        for finfo in sample_fortran_files[:200]:
            try:
                content = read_file_with_encoding(finfo["file_path"])
                content = preprocess_file(content, finfo["language"])
                for ch in chunk_file(content, finfo["relative_path"], finfo["language"]):
                    if ch.start_line < 1 or ch.end_line < ch.start_line:
                        bad.append(f"{ch.file_path}:{ch.name} ({ch.start_line}-{ch.end_line})")
            except Exception:
                pass
        assert len(bad) == 0, f"{len(bad)} bad line ranges: {bad[:10]}"


# ---------------------------------------------------------------------------
# E1.2  Known subroutine extraction
# ---------------------------------------------------------------------------

KNOWN_ROUTINES = {
    "NASTRN": "program",
    "SDR2A": "subroutine",
    "XSORT": "subroutine",
}

class TestKnownRoutines:
    def test_known_routines_found_in_graph(self, graph_data):
        """Key NASTRAN routines must appear in the call graph nodes."""
        nodes = graph_data.get("nodes", {})
        for name in KNOWN_ROUTINES:
            assert name in nodes, f"Expected routine '{name}' not found in graph nodes"

    def test_known_routine_types(self, graph_data):
        """Key routines must have the correct chunk_type."""
        nodes = graph_data.get("nodes", {})
        for name, expected_type in KNOWN_ROUTINES.items():
            if name in nodes:
                assert nodes[name]["chunk_type"] == expected_type, \
                    f"{name}: expected type '{expected_type}', got '{nodes[name]['chunk_type']}'"


# ---------------------------------------------------------------------------
# E1.3  Dependency extraction accuracy
# ---------------------------------------------------------------------------

class TestDependencyExtraction:
    def test_call_extraction(self):
        code = """\
      SUBROUTINE DRIVER
      CALL ALPHA(X)
      CALL BETA(Y,Z)
      CALL GAMMA
      RETURN
      END"""
        deps = extract_fortran_dependencies(code)
        for target in ["CALL:ALPHA", "CALL:BETA", "CALL:GAMMA"]:
            assert target in deps, f"Missing dependency {target}"

    def test_common_extraction(self):
        code = """\
      SUBROUTINE SHARED
      COMMON /BLK1/ A,B
      COMMON /BLK2/ C,D
      END"""
        deps = extract_fortran_dependencies(code)
        assert "COMMON:BLK1" in deps
        assert "COMMON:BLK2" in deps

    def test_ignores_commented_calls(self):
        code = """\
C     CALL DISABLED(X)
      CALL ENABLED(Y)
      END"""
        deps = extract_fortran_dependencies(code)
        assert "CALL:DISABLED" not in deps
        assert "CALL:ENABLED" in deps

    def test_no_duplicate_deps(self):
        code = """\
      CALL REPEAT(A)
      CALL REPEAT(B)
      CALL REPEAT(C)"""
        deps = extract_fortran_dependencies(code)
        assert deps.count("CALL:REPEAT") == 1

    def test_nested_parens_handled(self):
        code = "      CALL COMPLEX(A(1,2), B(3))"
        deps = extract_fortran_dependencies(code)
        assert "CALL:COMPLEX" in deps
