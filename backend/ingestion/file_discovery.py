import os
from pathlib import Path
from backend.config import LANGUAGE_MAP, SKIP_DIRS


def discover_files(codebase_path: str) -> list[dict]:
    """Recursively scan a codebase directory for supported source files."""
    codebase = Path(codebase_path)
    if not codebase.exists():
        raise FileNotFoundError(f"Codebase path not found: {codebase_path}")

    files = []
    for root, dirs, filenames in os.walk(codebase):
        # Skip unwanted directories
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]

        for filename in filenames:
            ext = Path(filename).suffix.lower()
            if ext not in LANGUAGE_MAP:
                continue

            file_path = Path(root) / filename
            relative_path = file_path.relative_to(codebase)

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                line_count = content.count("\n") + 1
            except Exception:
                line_count = 0

            files.append({
                "file_path": str(file_path),
                "relative_path": str(relative_path),
                "filename": filename,
                "language": LANGUAGE_MAP[ext],
                "size_bytes": file_path.stat().st_size,
                "line_count": line_count,
            })

    files.sort(key=lambda f: f["relative_path"])
    return files
