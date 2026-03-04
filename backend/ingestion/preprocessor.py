import chardet


def read_file_with_encoding(file_path: str) -> str:
    """Read a file, detecting encoding with chardet."""
    with open(file_path, "rb") as f:
        raw = f.read()

    detected = chardet.detect(raw)
    encoding = detected.get("encoding", "utf-8") or "utf-8"

    try:
        return raw.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        return raw.decode("utf-8", errors="replace")


def preprocess_fortran77(content: str) -> str:
    """Preprocess Fortran 77 source: truncate sequence numbers, normalize."""
    lines = content.split("\n")
    processed = []
    for line in lines:
        # Truncate columns 73-80 (sequence numbers) if line is long enough
        if len(line) > 72:
            line = line[:72]
        # Strip trailing whitespace
        line = line.rstrip()
        processed.append(line)
    return "\n".join(processed)


def preprocess_file(content: str, language: str) -> str:
    """Preprocess source file based on language."""
    if language == "fortran":
        content = preprocess_fortran77(content)

    # General normalization
    content = normalize_whitespace(content)
    return content


def normalize_whitespace(content: str) -> str:
    """Normalize whitespace: convert tabs, strip trailing spaces, normalize line endings."""
    # Normalize line endings
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    # Strip trailing whitespace per line
    lines = [line.rstrip() for line in content.split("\n")]
    # Remove excessive blank lines (more than 2 consecutive)
    result = []
    blank_count = 0
    for line in lines:
        if line == "":
            blank_count += 1
            if blank_count <= 2:
                result.append(line)
        else:
            blank_count = 0
            result.append(line)
    return "\n".join(result)
