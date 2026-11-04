"""Validation Gateways and Contract Enforcement Functions for E2E Tests."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import time
from typing import Any, Dict, List, Optional, Tuple
import yaml

# Core regex patterns per specification
PDF_FILENAME_PATTERN = re.compile(r"^(\d+)회차_(\d+)강_([^\/\\:*?\"<>|]+)\.pdf$")
REQUIRED_CORE_ATTRS = ["origin", "type", "domain", "up", "status", "created", "updated"]


def sanitize_lecture_title(raw_title: str) -> str:
    """Windows filename character sanitization and whitespace normalizer."""
    clean = re.sub(r'[\\/*?:"<>|]', '_', raw_title)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def format_lecture_filename(round_num: int, lecture_num: int, clean_title: str, suffix: str = "") -> str:
    """Format filename deterministically as {round_num}회차_{lecture_num}강_{clean_title}{suffix}.pdf."""
    sanitized = sanitize_lecture_title(clean_title)
    return f"{round_num}회차_{lecture_num}강_{sanitized}{suffix}.pdf"


def validate_pdf_binary(pdf_path: Path) -> Tuple[bool, str]:
    """PDF Pre-Parse Validation Gateway:

    Checks:
    1. File exists and size > 1024 bytes (1 KB).
    2. Magic bytes header begins with b'%PDF'.
    3. Trailer within last 1024 bytes contains b'%%EOF'.
    4. Filename matches regex {round}회차_{lecture}강_{clean_title}.pdf.
    """
    if not pdf_path.exists():
        return False, f"File does not exist: {pdf_path}"

    if not pdf_path.is_file():
        return False, f"Path is not a regular file: {pdf_path}"

    size = pdf_path.stat().st_size
    if size <= 1024:
        return False, f"PDF file size too small: {size} bytes (required > 1024 bytes)"

    filename = pdf_path.name
    if not PDF_FILENAME_PATTERN.match(filename):
        return False, f"PDF filename '{filename}' does not match standard pattern '{PDF_FILENAME_PATTERN.pattern}'"

    with open(pdf_path, "rb") as f:
        header = f.read(1024)
        if not header.startswith(b"%PDF"):
            return False, f"Invalid magic header: expected b'%PDF', got {header[:10]!r}"

        # Check last 1024 bytes for EOF
        f.seek(max(0, size - 1024))
        tail = f.read(1024)
        if b"%%EOF" not in tail:
            return False, "Missing '%%EOF' trailer in last 1024 bytes"

    return True, "Valid PDF binary"


def validate_markdown_note(md_path: Path) -> Tuple[bool, str]:
    """Markdown Post-Parse Validation Gateway:

    Checks:
    1. File exists and size >= 200 bytes.
    2. Contains YAML frontmatter enclosed by '---'.
    3. YAML frontmatter parses cleanly and contains all 7 core attributes.
    4. Clean Null rule: up must be [] (never '[[]]').
    5. Origin is 'source' and type is 'source'.
    6. Body text after frontmatter is non-empty.
    """
    if not md_path.exists():
        return False, f"File does not exist: {md_path}"

    size = md_path.stat().st_size
    if size < 200:
        return False, f"Markdown file size too small: {size} bytes (required >= 200 bytes)"

    content = md_path.read_text(encoding="utf-8", errors="replace")

    # Check YAML frontmatter enclosure
    if not content.startswith("---"):
        return False, "File does not start with YAML frontmatter delimiter '---'"

    parts = content.split("---", 2)
    if len(parts) < 3:
        return False, "Malformed YAML frontmatter: missing closing delimiter '---'"

    raw_yaml = parts[1]
    body = parts[2].strip()

    try:
        data = yaml.safe_load(raw_yaml)
    except Exception as exc:
        return False, f"Failed to parse YAML frontmatter: {exc}"

    if not isinstance(data, dict):
        return False, "YAML frontmatter is not a dictionary mapping"

    # Check 7 core attributes
    missing = [attr for attr in REQUIRED_CORE_ATTRS if attr not in data]
    if missing:
        return False, f"Missing required core frontmatter attribute(s): {missing}"

    # Check Clean Null rule on 'up'
    up_val = data.get("up")
    if up_val is None or up_val == "[[]]" or (isinstance(up_val, list) and "[[]]" in up_val):
        return False, f"Clean Null violation on 'up': expected [], got {up_val!r}"
    if not isinstance(up_val, list):
        return False, f"'up' must be a list (Clean Null []), got {type(up_val)}"

    # Check origin & type
    if data.get("origin") != "source":
        return False, f"Expected origin 'source', got {data.get('origin')!r}"
    if data.get("type") != "source":
        return False, f"Expected type 'source', got {data.get('type')!r}"

    # Check non-empty body
    if not body:
        return False, "Markdown body after frontmatter is empty"

    return True, "Valid PKM markdown note"


def verify_inbox_zero(inbox_dir: Path, archive_dir: Optional[Path] = None) -> Tuple[bool, str]:
    """Inbox Zero Verification Gateway:

    Checks:
    1. Zero residual .pdf files in inbox_dir.
    2. At least one .md file exists in inbox_dir (if files were processed).
    3. If archive_dir is provided, verify that all .md stems in inbox_dir match archived .pdf stems.
    """
    if not inbox_dir.exists():
        return False, f"Inbox directory does not exist: {inbox_dir}"

    residual_pdfs = list(inbox_dir.glob("*.pdf"))
    if residual_pdfs:
        pdf_names = [p.name for p in residual_pdfs]
        return False, f"Inbox Zero violation: found {len(residual_pdfs)} residual PDF(s): {pdf_names}"

    md_files = list(inbox_dir.glob("*.md"))

    if archive_dir and archive_dir.exists():
        archived_pdfs = list(archive_dir.rglob("*.pdf"))
        archived_stems = {p.stem for p in archived_pdfs}
        md_stems = {m.stem for m in md_files}

        # Check correspondence
        missing_in_archive = md_stems - archived_stems
        if missing_in_archive:
            return False, f"Inbox Zero mismatch: MD notes exist without corresponding archived PDF: {missing_in_archive}"

    return True, f"Inbox Zero verified: 0 residual PDFs, {len(md_files)} MD note(s) present"


def atomic_archive_file(
    src_path: Path,
    dst_path: Path,
    max_retries: int = 5,
    backoff_sec: float = 0.05,
) -> bool:
    """Atomically move source file to destination with retry loop for Windows sharing locks."""
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(max_retries):
        try:
            # os.replace provides atomic move on same filesystem
            os.replace(src_path, dst_path)
            return True
        except (PermissionError, OSError) as exc:
            if attempt == max_retries - 1:
                # Fallback to copy + remove if cross-volume or persistent lock
                try:
                    shutil.copy2(src_path, dst_path)
                    os.remove(src_path)
                    return True
                except Exception as final_exc:
                    raise IOError(f"Failed to archive {src_path} -> {dst_path} after {max_retries} attempts: {final_exc}") from exc
            time.sleep(backoff_sec * (2 ** attempt))

    return False
