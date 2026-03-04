import re
from dataclasses import dataclass, field
import tiktoken

from backend.config import CHUNK_SIZE_LINES, CHUNK_OVERLAP_LINES


@dataclass
class Chunk:
    content: str
    file_path: str
    start_line: int
    end_line: int
    chunk_type: str  # "subroutine", "function", "program", "block-data", "file-header", "fixed-size"
    name: str
    language: str
    dependencies: list[str] = field(default_factory=list)

    @property
    def line_count(self) -> int:
        return self.end_line - self.start_line + 1


# ---------- Token estimation ----------

_encoder = None


def _get_encoder():
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding("cl100k_base")
    return _encoder


def estimate_tokens(text: str) -> int:
    return len(_get_encoder().encode(text))


# ---------- Fortran 77 helpers ----------

def is_f77_comment(line: str) -> bool:
    """Check if a line is a Fortran 77 comment (C or * in column 1)."""
    if not line:
        return False
    return line[0] in ("C", "c", "*", "!")


def is_f77_continuation(line: str) -> bool:
    """Check if a line is a continuation line (non-blank/non-zero in column 6)."""
    if len(line) < 6:
        return False
    if is_f77_comment(line):
        return False
    col6 = line[5]
    return col6 != " " and col6 != "0"


def get_code_area(line: str) -> str:
    """Extract the code area (columns 7-72) from a Fortran 77 line."""
    if len(line) < 7:
        return ""
    return line[6:72].strip() if len(line) > 6 else ""


# Patterns for routine boundaries
_ROUTINE_START = re.compile(
    r"^\s*(SUBROUTINE|FUNCTION|BLOCK\s*DATA|PROGRAM|ENTRY)"
    r"\s+(\w+)",
    re.IGNORECASE,
)
_BARE_END = re.compile(r"^\s*END\s*$", re.IGNORECASE)
_TYPED_FUNCTION = re.compile(
    r"^\s*(INTEGER|REAL|DOUBLE\s*PRECISION|COMPLEX|LOGICAL|CHARACTER)"
    r"\s+FUNCTION\s+(\w+)",
    re.IGNORECASE,
)


def extract_fortran_dependencies(content: str) -> list[str]:
    """Extract CALL targets, COMMON blocks, and INCLUDE files from Fortran code."""
    deps = []
    for line in content.split("\n"):
        if is_f77_comment(line):
            continue
        code = get_code_area(line).upper()

        # CALL targets
        call_match = re.findall(r"CALL\s+(\w+)", code, re.IGNORECASE)
        for target in call_match:
            deps.append(f"CALL:{target}")

        # COMMON blocks
        common_match = re.findall(r"COMMON\s*/\s*(\w+)\s*/", code, re.IGNORECASE)
        for block in common_match:
            deps.append(f"COMMON:{block}")

        # INCLUDE files
        include_match = re.findall(r"INCLUDE\s+['\"]([^'\"]+)['\"]", code, re.IGNORECASE)
        for inc in include_match:
            deps.append(f"INCLUDE:{inc}")

    return list(set(deps))


def chunk_fortran(content: str, file_path: str) -> list[Chunk]:
    """Syntax-aware chunking for Fortran 77 source code."""
    lines = content.split("\n")
    chunks = []
    current_lines = []
    current_name = None
    current_type = None
    current_start = 1

    def flush_chunk():
        nonlocal current_lines, current_name, current_type, current_start
        if not current_lines:
            return
        # Skip chunks that are only blank lines or comments
        has_code = any(
            l.strip() and not is_f77_comment(l)
            for l in current_lines
        )
        if not has_code and current_type == "file-header":
            # Keep file headers even if just comments (they describe the file)
            pass
        elif not has_code:
            current_lines = []
            return

        chunk_content = "\n".join(current_lines)
        deps = extract_fortran_dependencies(chunk_content)

        chunks.append(Chunk(
            content=chunk_content,
            file_path=file_path,
            start_line=current_start,
            end_line=current_start + len(current_lines) - 1,
            chunk_type=current_type or "file-header",
            name=current_name or _derive_name(file_path),
            language="fortran",
            dependencies=deps,
        ))
        current_lines = []

    for i, line in enumerate(lines, start=1):
        code_area = get_code_area(line) if not is_f77_comment(line) else ""

        # Check for routine start
        match = _ROUTINE_START.match(code_area)
        if not match:
            match = _TYPED_FUNCTION.match(code_area)

        if match:
            # Flush previous chunk
            flush_chunk()
            keyword = match.group(1).upper().replace(" ", "")
            current_name = match.group(2).upper()
            if "SUBROUTINE" in keyword:
                current_type = "subroutine"
            elif "FUNCTION" in keyword:
                current_type = "function"
            elif "BLOCKDATA" in keyword:
                current_type = "block-data"
            elif "PROGRAM" in keyword:
                current_type = "program"
            elif "ENTRY" in keyword:
                current_type = "entry"
            else:
                current_type = "routine"
            current_start = i
            current_lines = [line]
            continue

        # Check for bare END statement
        if _BARE_END.match(code_area):
            current_lines.append(line)
            flush_chunk()
            current_name = None
            current_type = None
            current_start = i + 1
            continue

        # Regular line — add to current chunk
        if not current_lines:
            current_start = i
            if current_type is None:
                current_type = "file-header"
                current_name = _derive_name(file_path)
        current_lines.append(line)

    # Flush remaining
    flush_chunk()

    # If no syntax-aware chunks were found, fall back to fixed-size
    if not chunks:
        return chunk_fixed_size(content, file_path, "fortran")

    return chunks


def _derive_name(file_path: str) -> str:
    """Derive a chunk name from the file path."""
    from pathlib import Path
    return Path(file_path).stem.upper()


# ---------- C chunking ----------

def chunk_c(content: str, file_path: str) -> list[Chunk]:
    """Basic function-level chunking for C code."""
    lines = content.split("\n")
    chunks = []
    current_lines = []
    current_start = 1
    brace_depth = 0
    in_function = False
    func_name = "unknown"

    func_pattern = re.compile(r"^(\w[\w\s\*]+)\s+(\w+)\s*\(")

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Detect function start
        if brace_depth == 0 and not in_function:
            match = func_pattern.match(stripped)
            if match and "{" not in stripped:
                func_name = match.group(2)
            elif match and "{" in stripped:
                func_name = match.group(2)

        current_lines.append(line)

        brace_depth += stripped.count("{") - stripped.count("}")

        if in_function and brace_depth == 0:
            chunk_content = "\n".join(current_lines)
            chunks.append(Chunk(
                content=chunk_content,
                file_path=file_path,
                start_line=current_start,
                end_line=i,
                chunk_type="function",
                name=func_name,
                language="c",
                dependencies=[],
            ))
            current_lines = []
            current_start = i + 1
            in_function = False
            func_name = "unknown"

        if brace_depth > 0:
            in_function = True

    # Flush remaining
    if current_lines:
        chunk_content = "\n".join(current_lines)
        has_code = any(l.strip() for l in current_lines)
        if has_code:
            chunks.append(Chunk(
                content=chunk_content,
                file_path=file_path,
                start_line=current_start,
                end_line=current_start + len(current_lines) - 1,
                chunk_type="file-header",
                name=_derive_name(file_path),
                language="c",
                dependencies=[],
            ))

    if not chunks:
        return chunk_fixed_size(content, file_path, "c")

    return chunks


# ---------- Fixed-size fallback ----------

def chunk_fixed_size(
    content: str,
    file_path: str,
    language: str,
    chunk_size: int = CHUNK_SIZE_LINES,
    overlap: int = CHUNK_OVERLAP_LINES,
) -> list[Chunk]:
    """Split content into fixed-size chunks with overlap."""
    lines = content.split("\n")
    if not lines or not any(l.strip() for l in lines):
        return []

    chunks = []
    start = 0
    while start < len(lines):
        end = min(start + chunk_size, len(lines))
        chunk_lines = lines[start:end]

        if any(l.strip() for l in chunk_lines):
            chunks.append(Chunk(
                content="\n".join(chunk_lines),
                file_path=file_path,
                start_line=start + 1,
                end_line=end,
                chunk_type="fixed-size",
                name=_derive_name(file_path),
                language=language,
                dependencies=[],
            ))

        start += chunk_size - overlap
        if start >= len(lines):
            break

    return chunks


# ---------- Main entry point ----------

def chunk_file(content: str, file_path: str, language: str) -> list[Chunk]:
    """Chunk a file based on its language."""
    if language == "fortran":
        return chunk_fortran(content, file_path)
    elif language == "c":
        return chunk_c(content, file_path)
    else:
        return chunk_fixed_size(content, file_path, language)
