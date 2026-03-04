import pytest
from backend.ingestion.preprocessor import (
    preprocess_fortran77, normalize_whitespace, preprocess_file,
)


class TestFortran77Preprocessing:
    def test_truncates_at_col72(self):
        line = "      X = 1" + " " * 62 + "12345678"
        result = preprocess_fortran77(line)
        # Each line should be <= 72 chars (before trailing strip)
        for l in result.split("\n"):
            assert len(l) <= 72

    def test_preserves_short_lines(self):
        line = "      CALL FOO(X)"
        result = preprocess_fortran77(line)
        assert "CALL FOO(X)" in result

    def test_strips_trailing_whitespace(self):
        line = "      X = 1   "
        result = preprocess_fortran77(line)
        for l in result.split("\n"):
            assert l == l.rstrip()

    def test_multiline(self):
        content = "      LINE 1\n      LINE 2\n      LINE 3"
        result = preprocess_fortran77(content)
        assert len(result.split("\n")) == 3


class TestNormalizeWhitespace:
    def test_normalizes_line_endings(self):
        result = normalize_whitespace("A\r\nB\rC\n")
        assert "\r" not in result

    def test_strips_trailing(self):
        result = normalize_whitespace("code   \nmore   ")
        for line in result.split("\n"):
            assert line == line.rstrip()

    def test_collapses_blank_lines(self):
        content = "A\n\n\n\n\nB"
        result = normalize_whitespace(content)
        # Should have at most 2 consecutive blank lines (3 newlines = 2 blank lines)
        assert "\n\n\n\n" not in result

    def test_empty_string(self):
        assert normalize_whitespace("") == ""


class TestPreprocessFile:
    def test_fortran_applies_f77(self):
        long_line = "      X = 1" + " " * 70 + "SEQ12345"
        result = preprocess_file(long_line, "fortran")
        for l in result.split("\n"):
            assert len(l) <= 72

    def test_other_language_normalizes(self):
        content = "code   \r\n"
        result = preprocess_file(content, "c")
        assert "\r" not in result
