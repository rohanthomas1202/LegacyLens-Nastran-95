import pytest
from backend.ingestion.chunker import (
    chunk_fortran, chunk_c, chunk_fixed_size, chunk_file,
    is_f77_comment, is_f77_continuation, get_code_area,
    extract_fortran_dependencies, estimate_tokens,
)


class TestFortranHelpers:
    def test_comment_c(self):
        assert is_f77_comment("C     THIS IS A COMMENT") is True

    def test_comment_star(self):
        assert is_f77_comment("*     ANOTHER COMMENT") is True

    def test_comment_bang(self):
        assert is_f77_comment("!     INLINE COMMENT") is True

    def test_not_comment(self):
        assert is_f77_comment("      CALL SUBR1") is False

    def test_empty_not_comment(self):
        assert is_f77_comment("") is False

    def test_continuation(self):
        assert is_f77_continuation("     +  CONTINUED") is True

    def test_continuation_any_char(self):
        assert is_f77_continuation("     1  CONTINUED") is True

    def test_not_continuation_space(self):
        assert is_f77_continuation("      REGULAR CODE") is False

    def test_not_continuation_zero(self):
        assert is_f77_continuation("     0  NOT CONT") is False

    def test_not_continuation_short(self):
        assert is_f77_continuation("SHORT") is False

    def test_comment_not_continuation(self):
        assert is_f77_continuation("C     COMMENT") is False

    def test_code_area(self):
        line = "      SUBROUTINE TEST(A,B,C)"
        assert get_code_area(line) == "SUBROUTINE TEST(A,B,C)"

    def test_code_area_short_line(self):
        assert get_code_area("SHORT") == ""

    def test_code_area_strips(self):
        line = "      X = 1   "
        assert get_code_area(line) == "X = 1"


class TestFortranDependencies:
    def test_extracts_calls(self):
        code = "      CALL SDR2A(X,Y)\n      CALL GINO(A,B)"
        deps = extract_fortran_dependencies(code)
        assert "CALL:SDR2A" in deps
        assert "CALL:GINO" in deps

    def test_extracts_common(self):
        code = "      COMMON /XNSTRN/ CORE(1)"
        deps = extract_fortran_dependencies(code)
        assert "COMMON:XNSTRN" in deps

    def test_extracts_include(self):
        code = "      INCLUDE 'COMMON.INC'"
        deps = extract_fortran_dependencies(code)
        assert "INCLUDE:COMMON.INC" in deps

    def test_skips_comments(self):
        code = "C     CALL FAKE(X)"
        deps = extract_fortran_dependencies(code)
        assert len(deps) == 0

    def test_deduplicates(self):
        code = "      CALL FOO(1)\n      CALL FOO(2)"
        deps = extract_fortran_dependencies(code)
        assert deps.count("CALL:FOO") == 1


class TestFortranChunking:
    def test_single_subroutine(self):
        content = """      SUBROUTINE TEST(A,B,C)
C     A TEST SUBROUTINE
      INTEGER A,B,C
      A = B + C
      RETURN
      END"""
        chunks = chunk_fortran(content, "test.f")
        assert len(chunks) >= 1
        sub_chunks = [c for c in chunks if c.chunk_type == "subroutine"]
        assert len(sub_chunks) == 1
        assert sub_chunks[0].name == "TEST"
        assert sub_chunks[0].language == "fortran"

    def test_multiple_routines(self):
        content = """      SUBROUTINE FIRST(X)
      INTEGER X
      X = 1
      END
      SUBROUTINE SECOND(Y)
      INTEGER Y
      Y = 2
      END"""
        chunks = chunk_fortran(content, "multi.f")
        sub_chunks = [c for c in chunks if c.chunk_type == "subroutine"]
        assert len(sub_chunks) == 2
        names = {c.name for c in sub_chunks}
        assert names == {"FIRST", "SECOND"}

    def test_function_detection(self):
        content = """      FUNCTION CALC(X)
      REAL X, CALC
      CALC = X * 2.0
      RETURN
      END"""
        chunks = chunk_fortran(content, "func.f")
        func_chunks = [c for c in chunks if c.chunk_type == "function"]
        assert len(func_chunks) == 1
        assert func_chunks[0].name == "CALC"

    def test_block_data(self):
        content = """      BLOCK DATA MYDATA
      COMMON /BLK1/ A, B, C
      DATA A, B, C /1.0, 2.0, 3.0/
      END"""
        chunks = chunk_fortran(content, "bd.f")
        bd_chunks = [c for c in chunks if c.chunk_type == "block-data"]
        assert len(bd_chunks) == 1
        assert bd_chunks[0].name == "MYDATA"

    def test_program_detection(self):
        content = """      PROGRAM MAIN
      PRINT *, 'HELLO'
      END"""
        chunks = chunk_fortran(content, "main.f")
        prog_chunks = [c for c in chunks if c.chunk_type == "program"]
        assert len(prog_chunks) == 1
        assert prog_chunks[0].name == "MAIN"

    def test_dependencies_in_chunks(self):
        content = """      SUBROUTINE CALLER(X)
      CALL TARGET1(X)
      CALL TARGET2(X)
      COMMON /SHARED/ Y
      END"""
        chunks = chunk_fortran(content, "caller.f")
        sub = [c for c in chunks if c.chunk_type == "subroutine"][0]
        assert "CALL:TARGET1" in sub.dependencies
        assert "CALL:TARGET2" in sub.dependencies
        assert "COMMON:SHARED" in sub.dependencies

    def test_empty_content_no_crash(self):
        chunks = chunk_fortran("", "empty.f")
        assert isinstance(chunks, list)

    def test_comments_only_fallback(self):
        content = "C     JUST COMMENTS\nC     NOTHING ELSE"
        chunks = chunk_fortran(content, "comments.f")
        # Should fall back to fixed-size or return empty
        assert isinstance(chunks, list)

    def test_line_numbers_correct(self):
        content = """      SUBROUTINE A
      X = 1
      END
      SUBROUTINE B
      Y = 2
      END"""
        chunks = chunk_fortran(content, "lines.f")
        subs = sorted([c for c in chunks if c.chunk_type == "subroutine"], key=lambda c: c.start_line)
        assert subs[0].start_line == 1
        assert subs[1].start_line == 4


class TestCChunking:
    def test_simple_function(self):
        content = """int add(int a, int b) {
    return a + b;
}"""
        chunks = chunk_c(content, "math.c")
        assert len(chunks) >= 1

    def test_empty_file(self):
        chunks = chunk_c("", "empty.c")
        assert chunks == []


class TestFixedSize:
    def test_creates_chunks(self):
        content = "\n".join([f"      LINE {i}" for i in range(100)])
        chunks = chunk_fixed_size(content, "big.f", "fortran")
        assert len(chunks) > 1

    def test_overlap(self):
        content = "\n".join([f"      LINE {i}" for i in range(100)])
        chunks = chunk_fixed_size(content, "big.f", "fortran", chunk_size=40, overlap=10)
        if len(chunks) >= 2:
            # Second chunk should start before first chunk ends
            assert chunks[1].start_line <= chunks[0].end_line

    def test_empty_content(self):
        chunks = chunk_fixed_size("", "empty.f", "fortran")
        assert chunks == []

    def test_small_file_single_chunk(self):
        content = "\n".join(["      LINE"] * 10)
        chunks = chunk_fixed_size(content, "small.f", "fortran")
        assert len(chunks) == 1


class TestChunkFile:
    def test_routes_fortran(self):
        content = "      SUBROUTINE X\n      END"
        chunks = chunk_file(content, "test.f", "fortran")
        assert all(c.language == "fortran" for c in chunks)

    def test_routes_c(self):
        content = "void foo() { return; }"
        chunks = chunk_file(content, "test.c", "c")
        assert all(c.language == "c" for c in chunks)

    def test_unknown_falls_back(self):
        content = "some unknown content\n" * 50
        chunks = chunk_file(content, "test.txt", "unknown")
        assert len(chunks) >= 1
        assert all(c.chunk_type == "fixed-size" for c in chunks)


class TestTokenEstimation:
    def test_returns_int(self):
        assert isinstance(estimate_tokens("hello world"), int)

    def test_longer_text_more_tokens(self):
        short = estimate_tokens("hello")
        long = estimate_tokens("hello world this is a longer piece of text")
        assert long > short
