#!/usr/bin/env python
"""Vault Constitutional Linter CLI for My-PKM.

Validates Obsidian knowledge vault (My-Wiki) integrity against the 5 Constitutional Checks:
  C1. Core Attributes: 7 required core attributes (origin, type, domain, up, status, created, updated)
      and standard domain codes (max 2 '1+1' rule).
  C2. Ghost Links: Detects '[[]]' in frontmatter or text. Auto-repairs to clean null [] with --fix.
  C3. Orphan Notes: Flags notes with empty up: [] (exempting Level 1 Master Domain Hubs,
      unanchored source notes in 300. Sources, and logs in 200. AI_logs).
  C4. Folder-Origin MECE: Verifies folder prefix matches origin attribute (100 -> human, 200 -> ai,
      300 -> source, 400 -> wiki).
  C5. Binary Infiltration: Flags heavy binaries (.pdf, .hwpx, .xlsx, .docx, .zip) inside vault
      (outside 900. config/910. Attached allowed image attachments).

Usage:
    python vault_linter.py [OPTIONS]
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple
import yaml

# Ensure standard streams use UTF-8 regardless of Windows console codepage
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

STANDARD_DOMAINS: Set[str] = {
    "theory",
    "macro",
    "equity",
    "portfolio",
    "work",
    "ai-pkm",
    "education",
}

LEVEL_1_HUBS: Set[str] = {
    "01_경제 및 금융 이론.md",
    "02_매크로 분석.md",
    "03_산업 및 기업분석.md",
    "04_가족 투자 포트폴리오.md",
    "05_회사업무 (자산운용).md",
    "06_AI 활용 및 PKM 구축.md",
    "07_자녀교육.md",
}

HEAVY_BINARY_EXTENSIONS: Set[str] = {
    ".pdf",
    ".hwpx",
    ".hwp",
    ".hwpml",
    ".xlsx",
    ".xls",
    ".docx",
    ".doc",
    ".pptx",
    ".ppt",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
}

ALLOWED_ATTACHMENT_EXTENSIONS: Set[str] = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".excalidraw",
    ".canvas",
}

CORE_ATTRIBUTES: List[str] = [
    "origin",
    "type",
    "domain",
    "up",
    "status",
    "created",
    "updated",
]


class Violation:
    """Represents a single constitutional violation."""

    def __init__(self, file_path: Path, check_code: str, line_number: int, message: str):
        self.file_path = file_path
        self.check_code = check_code
        self.line_number = line_number
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": str(self.file_path),
            "filename": self.file_path.name,
            "check": self.check_code,
            "line": self.line_number,
            "message": self.message,
        }

    def __str__(self) -> str:
        return f"{self.file_path.name}:{self.line_number} [{self.check_code}] {self.message}"


def is_excluded_path(path: Path, vault_root: Path, include_inbox: bool = False) -> bool:
    """Determine whether a path belongs to an excluded vault directory."""
    try:
        rel = path.relative_to(vault_root)
        parts = rel.parts
    except ValueError:
        parts = path.parts

    for part in parts:
        if part.startswith(".") and part != ".":
            return True
        if part == "000. Inbox" and not include_inbox:
            return True
        if part in ["900. config", "Notion", ".obsidian", ".trash"]:
            return True
    return False


def fix_ghost_links(content: str) -> Tuple[str, bool]:
    """Auto-fix ghost links '[[]]' by replacing them with clean null [] strictly in YAML frontmatter."""
    # Match frontmatter strictly between opening and closing '---' lines
    match = re.match(r"^(---\r?\n)(.*?\r?\n)?(---(?:\r?\n|$))(.*)$", content, re.DOTALL)
    if not match:
        return content, False

    header = match.group(1)
    fm_content = match.group(2) or ""
    footer = match.group(3)
    body = match.group(4)

    modified = False

    # 1. Multi-line list item: key:\n  - "[[]]" or key:\n  - [[]] -> key: []
    new_fm, count = re.subn(
        r'(?m)^([ \t]*[\w_-]+:)[ \t]*\r?\n[ \t]*-[ \t]*["\']?\[\[\]\]["\']?[ \t\r]*$',
        r"\1 []",
        fm_content,
    )
    if count > 0:
        modified = True
        fm_content = new_fm

    # 2. Single line key: "[[]]", key: '[[]]', or unquoted key: [[]] -> key: []
    new_fm, count = re.subn(
        r'(?m)^([ \t]*[\w_-]+:)[ \t]*["\']?\[\[\]\]["\']?[ \t\r]*$',
        r"\1 []",
        fm_content,
    )
    if count > 0:
        modified = True
        fm_content = new_fm

    # 3. Inline list key: ["[[]]"] or key: [[[]]] -> key: []
    new_fm, count = re.subn(
        r'(?m)^([ \t]*[\w_-]+:)[ \t]*\[\s*["\']?\[\[\]\]["\']?\s*\][ \t\r]*$',
        r"\1 []",
        fm_content,
    )
    if count > 0:
        modified = True
        fm_content = new_fm

    # 4. Multi-line list items within list: - "[[]]" or - [[]] -> - []
    new_fm, count = re.subn(
        r'(?m)^([ \t]*-[ \t]*)["\']?\[\[\]\]["\']?[ \t\r]*$',
        r"\1[]",
        fm_content,
    )
    if count > 0:
        modified = True
        fm_content = new_fm

    # 5. Any remaining quoted "[[]]" or '[[]]' in frontmatter
    new_fm, count = re.subn(r'["\']\[\[\]\]["\']', "[]", fm_content)
    if count > 0:
        modified = True
        fm_content = new_fm

    # 6. Any remaining unquoted [[]] in frontmatter
    new_fm, count = re.subn(r'\[\[\]\]', "[]", fm_content)
    if count > 0:
        modified = True
        fm_content = new_fm

    if modified:
        return header + fm_content + footer + body, True
    return content, False


def audit_markdown_note(
    file_path: Path,
    vault_root: Path,
    auto_fix: bool = False,
    verbose: bool = False,
) -> List[Violation]:
    """Audit a single markdown note against checks C1 to C4."""
    violations: List[Violation] = []

    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            raw_text = file_path.read_text(encoding="cp949")
        except Exception as exc:
            violations.append(
                Violation(file_path, "C1", 1, f"Failed to read file encoding: {exc}")
            )
            return violations

    # Auto-fix pass if requested
    if auto_fix:
        fixed_text, was_modified = fix_ghost_links(raw_text)
        if was_modified:
            file_path.write_text(fixed_text, encoding="utf-8")
            raw_text = fixed_text
            if verbose:
                print(f"[Auto-Fixed] Repaired ghost links in {file_path.name}")

    lines = raw_text.splitlines()

    # Locate YAML frontmatter
    if not lines or lines[0].strip() != "---":
        violations.append(Violation(file_path, "C1", 1, "Missing YAML frontmatter delimiter '---'"))
        return violations

    end_fm_idx = -1
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_fm_idx = idx
            break

    if end_fm_idx == -1:
        violations.append(Violation(file_path, "C1", 1, "Unclosed YAML frontmatter (missing closing '---')"))
        return violations

    fm_lines = lines[1:end_fm_idx]
    fm_text = "\n".join(fm_lines)

    # Line number lookup helper for frontmatter keys
    key_line_map: Dict[str, int] = {}
    for offset, line in enumerate(fm_lines):
        match = re.match(r"^[ \t]*([\w_-]+):", line)
        if match:
            k = match.group(1)
            if k not in key_line_map:
                key_line_map[k] = offset + 2  # 1-indexed (line 1 is '---')

    try:
        data = yaml.safe_load(fm_text)
    except Exception as exc:
        violations.append(Violation(file_path, "C1", 1, f"Invalid YAML frontmatter syntax: {exc}"))
        return violations

    if not isinstance(data, dict):
        violations.append(Violation(file_path, "C1", 1, "YAML frontmatter must be a key-value mapping"))
        return violations

    # Check 1 (C1: Core Attributes & Domain Validation)
    for req_key in CORE_ATTRIBUTES:
        if req_key not in data:
            violations.append(
                Violation(file_path, "C1", 1, f"Missing core attribute: '{req_key}'")
            )
        else:
            val = data[req_key]
            line_no = key_line_map.get(req_key, 1)
            if req_key in ["origin", "type", "status", "created", "updated"]:
                if val is None or str(val).strip() == "":
                    violations.append(
                        Violation(file_path, "C1", line_no, f"Core attribute '{req_key}' cannot be empty")
                    )

    # Domain Validation (under C1)
    if "domain" in data:
        dom_val = data["domain"]
        dom_line = key_line_map.get("domain", 1)
        if dom_val is None or (isinstance(dom_val, list) and not dom_val):
            violations.append(
                Violation(file_path, "C1", dom_line, "Core attribute 'domain' cannot be empty")
            )
        else:
            dom_list = dom_val if isinstance(dom_val, list) else [dom_val]
            # Max 2 domains rule
            if len(dom_list) > 2:
                violations.append(
                    Violation(
                        file_path,
                        "C1",
                        dom_line,
                        f"Domain list has {len(dom_list)} items, exceeding max 2 (1+1 rule): {dom_list}",
                    )
                )
            # Standard domain code verification
            for d in dom_list:
                d_str = str(d).strip()
                if d_str not in STANDARD_DOMAINS:
                    violations.append(
                        Violation(
                            file_path,
                            "C1",
                            dom_line,
                            f"Non-standard domain code '{d_str}' (must be one of {sorted(STANDARD_DOMAINS)})",
                        )
                    )

    # Check 2 (C2: Ghost Links)
    ghost_detected = False
    # Check raw frontmatter text for ghost link representations
    if '"[[]]"' in fm_text or "'[[]]'" in fm_text or " [[]]" in fm_text:
        ghost_detected = True
    else:
        # Check parsed dict values
        for k, v in data.items():
            if isinstance(v, list):
                for item in v:
                    item_str = str(item).strip()
                    if item_str == "[[]]" or item_str == '"[[]]"' or item_str == "'[[]]'":
                        ghost_detected = True
                        break
            elif isinstance(v, str):
                if v.strip() in ["[[]]", '"[[]]"', "'[[]]'"]:
                    ghost_detected = True
                    break
        # Also check body for literal [[]] ghost links outside code blocks and inline code
        body_text = "\n".join(lines[end_fm_idx + 1 :])
        body_no_fenced = re.sub(r'(?s)```.*?```|~~~.*?~~~', '', body_text)
        body_no_code = re.sub(r'`+[^`\n]*?`+', '', body_no_fenced)
        if "[[]]" in body_no_code:
            ghost_detected = True

    if ghost_detected:
        g_line = 1
        for off, l in enumerate(fm_lines):
            if "[[]]" in l:
                g_line = off + 2
                break
        else:
            for off, l in enumerate(lines[end_fm_idx + 1 :]):
                l_no_code = re.sub(r'`+[^`\n]*?`+', '', l)
                if "[[]]" in l_no_code:
                    g_line = end_fm_idx + 1 + off + 1
                    break
        violations.append(
            Violation(file_path, "C2", g_line, "Ghost link detected: \"[[]]\" (must be clean empty array [])")
        )

    # Check 3 (C3: Orphan Notes)
    up_val = data.get("up")
    up_line = key_line_map.get("up", 1)
    is_up_empty = False
    if up_val is None:
        is_up_empty = True
    elif isinstance(up_val, list):
        cleaned = [
            str(x).strip()
            for x in up_val
            if str(x).strip() and str(x).strip() not in ["", "[]", "[[]]"]
        ]
        if not cleaned:
            is_up_empty = True
    elif isinstance(up_val, str):
        if not up_val.strip() or up_val.strip() in ["[]", "[[]]"]:
            is_up_empty = True

    if is_up_empty:
        # Check exemptions:
        level_val = 0
        try:
            level_val = int(data.get("level", 0) or 0)
        except (ValueError, TypeError):
            level_val = 0

        is_l1_hub = "400. Wiki" in file_path.parts and (
            file_path.name in LEVEL_1_HUBS
            or (data.get("type") == "hub" and level_val == 1)
        )
        # 2. Unanchored source notes in 300. Sources (or type: source)
        is_source_note = data.get("type") == "source" or "300. Sources" in file_path.parts
        # 3. Log notes in 200. AI_logs (or type: log)
        is_log_note = data.get("type") == "log" or "200. AI_logs" in file_path.parts

        if not (is_l1_hub or is_source_note or is_log_note):
            violations.append(
                Violation(
                    file_path,
                    "C3",
                    up_line,
                    "Orphan note detected: 'up' is empty without Level 1 Master Hub exemption",
                )
            )

    # Check 4 (C4: Folder-Origin MECE Alignment)
    origin_val = str(data.get("origin", "")).strip().lower()
    origin_line = key_line_map.get("origin", 1)
    expected_origin: Optional[str] = None

    if "100. Concepts" in file_path.parts:
        expected_origin = "human"
    elif "200. AI_logs" in file_path.parts:
        expected_origin = "ai"
    elif "300. Sources" in file_path.parts:
        expected_origin = "source"
    elif "400. Wiki" in file_path.parts:
        expected_origin = "wiki"
    elif "500. etc" in file_path.parts:
        expected_origin = "human"

    if expected_origin and origin_val != expected_origin:
        violations.append(
            Violation(
                file_path,
                "C4",
                origin_line,
                f"Folder-Origin mismatch in '{file_path.name}': folder requires origin '{expected_origin}', but found '{origin_val}'",
            )
        )

    return violations


def audit_vault(
    vault_root: Path,
    auto_fix: bool = False,
    include_inbox: bool = False,
    verbose: bool = False,
) -> Tuple[List[Violation], int]:
    """Audit entire vault directory for all 5 constitutional checks."""
    all_violations: List[Violation] = []
    scanned_file_count = 0

    if not vault_root.exists():
        raise FileNotFoundError(f"Vault path does not exist: {vault_root}")

    # Gather all files
    all_files = sorted([p for p in vault_root.rglob("*") if p.is_file()])

    for file_path in all_files:
        # Check 5 (C5: Binary Infiltration)
        suffix = file_path.suffix.lower()
        if suffix in HEAVY_BINARY_EXTENSIONS:
            # Check if heavy binary is located anywhere inside vault
            all_violations.append(
                Violation(
                    file_path,
                    "C5",
                    1,
                    f"Heavy binary infiltration detected: '{file_path.name}' (raw binaries must reside in Inbox_Raw / Archive_Sources)",
                )
            )
            scanned_file_count += 1
            continue

        # Skip non-markdown files (unless inside config/attached)
        if suffix != ".md":
            continue

        # Check exclusion rules
        if is_excluded_path(file_path, vault_root, include_inbox=include_inbox):
            if verbose:
                print(f"[Skipping Excluded] {file_path}")
            continue

        scanned_file_count += 1
        note_violations = audit_markdown_note(
            file_path,
            vault_root,
            auto_fix=auto_fix,
            verbose=verbose,
        )
        all_violations.extend(note_violations)

    return all_violations, scanned_file_count


def format_report_text(
    violations: List[Violation],
    total_scanned: int,
) -> str:
    """Format audit results as readable human text."""
    failed_files = len({v.file_path for v in violations})
    passed_files = total_scanned - failed_files
    counts = {
        "C1": sum(1 for v in violations if v.check_code == "C1"),
        "C2": sum(1 for v in violations if v.check_code == "C2"),
        "C3": sum(1 for v in violations if v.check_code == "C3"),
        "C4": sum(1 for v in violations if v.check_code == "C4"),
        "C5": sum(1 for v in violations if v.check_code == "C5"),
    }

    lines = [
        "============================================================",
        "          My-PKM Vault Constitutional Audit Report          ",
        "============================================================",
        f"Scanned: {total_scanned} files | Passed: {passed_files} | Failed: {failed_files} | Total Violations: {len(violations)}",
        f"Violations by Check: C1={counts['C1']} (Core), C2={counts['C2']} (Ghost), C3={counts['C3']} (Orphan), C4={counts['C4']} (MECE), C5={counts['C5']} (Binary)",
        "------------------------------------------------------------",
    ]

    if not violations:
        lines.append("CONSTITUTIONAL COMPLIANCE: 100% PASS (0 violations)")
    else:
        lines.append("Violations Detail:")
        for v in violations:
            lines.append(f"  - {v}")
    lines.append("============================================================")
    return "\n".join(lines)


def format_report_json(
    violations: List[Violation],
    total_scanned: int,
) -> str:
    """Format audit results as JSON."""
    failed_files = len({v.file_path for v in violations})
    counts = {
        "C1": sum(1 for v in violations if v.check_code == "C1"),
        "C2": sum(1 for v in violations if v.check_code == "C2"),
        "C3": sum(1 for v in violations if v.check_code == "C3"),
        "C4": sum(1 for v in violations if v.check_code == "C4"),
        "C5": sum(1 for v in violations if v.check_code == "C5"),
    }

    report = {
        "summary": {
            "total_scanned": total_scanned,
            "passed": total_scanned - failed_files,
            "failed": failed_files,
            "total_violations": len(violations),
            "violations_by_check": counts,
        },
        "violations": [v.to_dict() for v in violations],
    }
    return json.dumps(report, indent=2, ensure_ascii=False)


def format_report_markdown(
    violations: List[Violation],
    total_scanned: int,
) -> str:
    """Format audit results as Markdown."""
    failed_files = len({v.file_path for v in violations})
    passed_files = total_scanned - failed_files
    counts = {
        "C1": sum(1 for v in violations if v.check_code == "C1"),
        "C2": sum(1 for v in violations if v.check_code == "C2"),
        "C3": sum(1 for v in violations if v.check_code == "C3"),
        "C4": sum(1 for v in violations if v.check_code == "C4"),
        "C5": sum(1 for v in violations if v.check_code == "C5"),
    }

    lines = [
        "# My-PKM Vault Constitutional Audit Report",
        "",
        "| Metric | Count |",
        "|---|---|",
        f"| Total Scanned | {total_scanned} |",
        f"| Passed | {passed_files} |",
        f"| Failed | {failed_files} |",
        f"| Total Violations | {len(violations)} |",
        "",
        "## Violations by Check Code",
        "",
        "| Code | Check Name | Violations |",
        "|---|---|---|",
        f"| C1 | Core Attributes & Domain | {counts['C1']} |",
        f"| C2 | Ghost Links (`\"[[]]\"`) | {counts['C2']} |",
        f"| C3 | Orphan Notes (`up: []`) | {counts['C3']} |",
        f"| C4 | Folder-Origin MECE | {counts['C4']} |",
        f"| C5 | Binary Infiltration | {counts['C5']} |",
        "",
    ]

    if violations:
        lines.extend([
            "## Violation Details",
            "",
            "| File | Line | Check | Description |",
            "|---|---|---|---|",
        ])
        for v in violations:
            lines.append(f"| `{v.file_path.name}` | {v.line_number} | `{v.check_code}` | {v.message} |")
    else:
        lines.append("## Result: 100% Compliant (0 errors)")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Vault Constitutional Linter CLI for My-PKM (Checks C1-C5)"
    )
    parser.add_argument(
        "--vault",
        type=str,
        default="./My-Wiki",
        help="Path to Obsidian vault directory (default: ./My-Wiki)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix safe violations (replace '[[]]' with clean null [] in YAML)",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="text",
        choices=["text", "json", "markdown"],
        help="Report output format: text (default), json, or markdown",
    )
    parser.add_argument(
        "--exit-zero",
        action="store_true",
        help="Force exit code 0 even if violations are found",
    )
    parser.add_argument(
        "--include-inbox",
        action="store_true",
        help="Include 000. Inbox in audit (default: excluded)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output logging",
    )

    args = parser.parse_args()
    vault_path = Path(args.vault).resolve()

    try:
        violations, total_scanned = audit_vault(
            vault_root=vault_path,
            auto_fix=args.fix,
            include_inbox=args.include_inbox,
            verbose=args.verbose,
        )
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Output report in requested format
    if args.format == "json":
        print(format_report_json(violations, total_scanned))
    elif args.format == "markdown":
        print(format_report_markdown(violations, total_scanned))
    else:
        print(format_report_text(violations, total_scanned))

    if args.exit_zero:
        return 0
    return 1 if len(violations) > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
