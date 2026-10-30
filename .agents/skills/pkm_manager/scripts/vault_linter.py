#!/usr/bin/env python
"""Vault Constitutional Linter CLI for My-PKM (My-Wiki Rules v3.0+).

Validates Obsidian knowledge vault (My-Wiki) integrity against the Constitutional Checks
dynamically loaded via `constitution_loader.py` from `./My-Wiki/My-Wiki Rules.md`:
  C1. Core Attributes: 7 required core attributes (origin, type, domain, up, status, created, updated)
      and standard domain codes (max 2 '1+1' rule).
  C2. Ghost Links: Detects '[[]]' in frontmatter or text. Auto-repairs to clean null [] with --fix.
  C3. Orphan Notes: Flags notes with empty up: [] (exempting Root/Level 1 Master Domain Hubs,
      `My-Wiki Rules.md`, `500. Index` hubs, unanchored source notes in 300. Sources, and logs in 200. AI_logs).
  C4. Folder-Origin MECE: Verifies folder prefix matches origin attribute dynamically (`100. Concepts` -> human,
      `200. AI_logs` & `210`/`220` -> ai, `300. Sources` -> source, `400. Wiki` -> wiki, `500. Index` -> wiki,
      `600. etc` / `500. etc` -> human, `My-Wiki Rules.md` -> wiki).
  C5. Binary Infiltration: Flags heavy binaries (.pdf, .hwpx, .xlsx, .docx, .zip) inside vault
      (outside 900. config/910. Attached allowed image attachments).
  C6. Index Registration (Opt-in via `--check-index`): Verifies compiled notes in `100`, `200`, `300`, `400`
      are registered in `500. Index/_인덱스_*.md`.

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

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from constitution_loader import ConstitutionConfig, load_constitution  # noqa: E402

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
    "My-Wiki Rules.md",
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

GHOST_HUB_NAMES: Set[str] = {
    "국내 거시경제 및 정책",
    "글로벌 매크로 동향",
    "금리·채권 및 통화정책",
    "외환·원자재 및 글로벌 유동성",
    "거시경제 및 통화 이론",
    "절세 및 연금계좌 관리",
    "투자 유니버스",
    "개별 기업 마스터",
    "산업 및 섹터 밸류체인",
    "기업 거버넌스 및 주주환원 사례",
    "조간신문 주요 사건 트래커",
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


def parse_markdown_frontmatter(text: str) -> Tuple[Optional[Dict[str, Any]], str, str]:
    """Parse YAML frontmatter from markdown text.

    Returns:
        (parsed_dict_or_None, raw_fm_text, body_text)
    """
    match = re.match(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)(.*)$", text, re.DOTALL)
    if not match:
        return None, "", text
    fm_raw = match.group(1)
    body = match.group(2)
    try:
        data = yaml.safe_load(fm_raw)
        if isinstance(data, dict):
            return data, fm_raw, body
    except Exception:
        pass
    return None, fm_raw, body


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
    """Auto-fix ghost links '[[]]' (and escaped '\\---' frontmatter delimiters) in YAML frontmatter."""
    pre_modified = False
    if content.startswith("\\---"):
        content = re.sub(r"^\\---([ \t]*\r?\n)", r"---\1", content, count=1)
        content = re.sub(r"(?m)^\\---([ \t]*\r?\n)", r"---\1", content, count=1)
        pre_modified = True

    match = re.match(r"^(---\r?\n)(.*?\r?\n)?(---(?:\r?\n|$))(.*)$", content, re.DOTALL)
    if not match:
        return content, pre_modified

    header = match.group(1)
    fm_content = match.group(2) or ""
    footer = match.group(3)
    body = match.group(4)

    modified = pre_modified

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
    new_fm, count = re.subn(r"\[\[\]\]", "[]", fm_content)
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
    cfg: Optional[ConstitutionConfig] = None,
) -> List[Violation]:
    """Audit a single markdown note against checks C1 to C4."""
    violations: List[Violation] = []
    core_attrs = cfg.core_attributes if cfg else CORE_ATTRIBUTES
    std_domains = set(cfg.standard_domains) if cfg else STANDARD_DOMAINS
    l1_hubs = set(cfg.level_1_hubs) if cfg else LEVEL_1_HUBS
    max_domains = cfg.max_domains_per_note if cfg else 2
    folder_origin_map = cfg.folder_origin_map if cfg else {
        "100. Concepts": "human",
        "200. AI_logs": "ai",
        "300. Sources": "source",
        "400. Wiki": "wiki",
        "500. Index": "wiki",
        "600. etc": "human",
        "500. etc": "human",
    }

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
    for req_key in core_attrs:
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
            if len(dom_list) > max_domains:
                violations.append(
                    Violation(
                        file_path,
                        "C1",
                        dom_line,
                        f"Domain list has {len(dom_list)} items, exceeding max {max_domains} (1+1 rule): {dom_list}",
                    )
                )
            # Standard domain code verification
            for d in dom_list:
                d_str = str(d).strip()
                if d_str not in std_domains:
                    violations.append(
                        Violation(
                            file_path,
                            "C1",
                            dom_line,
                            f"Non-standard domain code '{d_str}' (must be one of {sorted(std_domains)})",
                        )
                    )

    # Check 2 (C2: Ghost Links)
    ghost_detected = False
    if '"[[]]"' in fm_text or "'[[]]'" in fm_text or " [[]]" in fm_text:
        ghost_detected = True
    else:
        for k, v in data.items():
            if isinstance(v, list):
                for item in v:
                    item_str = str(item).strip()
                    if item_str in {"[[]]", '"[[]]"', "'[[]]'"}:
                        ghost_detected = True
                        break
            elif isinstance(v, str):
                if v.strip() in {"[[]]", '"[[]]"', "'[[]]'"}:
                    ghost_detected = True
                    break
        body_text = "\n".join(lines[end_fm_idx + 1 :])
        body_no_fenced = re.sub(r"(?s)```.*?```|~~~.*?~~~", "", body_text)
        body_no_code = re.sub(r"`+[^`\n]*?`+", "", body_no_fenced)
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
                l_no_code = re.sub(r"`+[^`\n]*?`+", "", l)
                if "[[]]" in l_no_code:
                    g_line = end_fm_idx + 1 + off + 1
                    break
        violations.append(
            Violation(file_path, "C2", g_line, 'Ghost link detected: "[[]]" (must be clean empty array [])')
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
        level_val = 0
        try:
            level_val = int(data.get("level", 0) or 0)
        except (ValueError, TypeError):
            level_val = 0

        is_root_constitution = file_path.name == "My-Wiki Rules.md"
        is_index_hub = "500. Index" in file_path.parts and data.get("type") == "hub"
        is_in_wiki = "400. Wiki" in file_path.parts

        # Level 1 Master Hubs (C1_~C8_, 01_~07_, level: 1 hub, or in l1_hubs)
        is_l1_hub = is_in_wiki and (
            file_path.name in l1_hubs
            or (data.get("type") == "hub" and level_val == 1)
            or (bool(re.match(r"^C\d+_", file_path.name)) and level_val <= 1 and data.get("type") == "hub")
        )

        # Hierarchical industry wikis that MUST have up: Lv2 (C#-S#), Lv3 (산업_), Lv4 (기업_)
        is_hierarchical_industry_wiki = is_in_wiki and (
            file_path.name.startswith("산업_")
            or file_path.name.startswith("기업_")
            or bool(re.match(r"^C\d+-S", file_path.name))
        )

        # Case / Event wikis in 400. Wiki (allowed to have up: [] when parent general wiki does not exist)
        is_case_or_event_wiki = (
            is_in_wiki
            and not is_hierarchical_industry_wiki
            and not is_l1_hub
            and data.get("type") in ("analysis", "event", "case")
        )

        is_source_note = data.get("type") == "source" or "300. Sources" in file_path.parts
        is_log_note = data.get("type") == "log" or "200. AI_logs" in file_path.parts

        is_exempt = (
            is_root_constitution
            or is_index_hub
            or is_l1_hub
            or is_case_or_event_wiki
            or is_source_note
            or is_log_note
        )

        if not is_exempt:
            violations.append(
                Violation(
                    file_path,
                    "C3",
                    up_line,
                    "Orphan note detected: 'up' is empty without exemption (only Lv1 hubs, case/event wikis, sources, and logs are exempt)",
                )
            )

    # Check 4 (C4: Folder-Origin MECE Alignment)
    origin_val = str(data.get("origin", "")).strip().lower()
    origin_line = key_line_map.get("origin", 1)
    expected_origin: Optional[str] = None

    try:
        rel_parts = file_path.relative_to(vault_root).parts
    except ValueError:
        rel_parts = file_path.parts

    if len(rel_parts) == 1 and file_path.name == "My-Wiki Rules.md":
        expected_origin = "wiki"
    else:
        for part in rel_parts:
            if part in folder_origin_map:
                expected_origin = folder_origin_map[part]
                break

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


def audit_index_sync(vault_root: Path, cfg: ConstitutionConfig) -> List[Violation]:
    """Check 6 (C6: Verify compiled notes in 100/200/300/400 are registered in 500. Index)."""
    violations: List[Violation] = []
    index_dir = vault_root / "500. Index"
    if not index_dir.exists() or not index_dir.is_dir():
        return violations

    indexed_stems: Set[str] = set()
    for idx_file in index_dir.glob("_인덱스_*.md"):
        if not idx_file.is_file():
            continue
        try:
            text = idx_file.read_text(encoding="utf-8", errors="replace")
            for m in re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", text):
                indexed_stems.add(m.strip())
        except Exception:
            pass

    target_folders = ["100. Concepts", "200. AI_logs", "300. Sources", "400. Wiki"]
    for folder in target_folders:
        folder_path = vault_root / folder
        if not folder_path.exists():
            continue
        for md_file in sorted(folder_path.rglob("*.md")):
            if not md_file.is_file():
                continue
            if md_file.name in cfg.level_1_hubs:
                continue
            if md_file.stem not in indexed_stems:
                violations.append(
                    Violation(
                        md_file,
                        "C6",
                        1,
                        f"Unindexed note detected: '[[{md_file.stem}]]' in '{folder}' is missing from 500. Index tables",
                    )
                )
    return violations


def audit_astep(
    vault_root: Path,
    cfg: ConstitutionConfig,
    md_files: List[Path],
) -> List[Violation]:
    """Check 7 (C7: Clean links, ghost targets, index/self refs, fake backticks)
    and Check 8 (C8: Strict 1-hop scope, DAG cycles, transitive triangles, vertical related, non-chronological prev)."""
    violations: List[Violation] = []

    # Map of stem -> Path for all valid markdown files in vault
    all_notes: Dict[str, Path] = {p.stem: p for p in md_files}
    valid_targets: Set[str] = set(all_notes.keys())
    # Add level 1 hubs
    for h in cfg.level_1_hubs:
        valid_targets.add(Path(h).stem)
    valid_targets.add("My-Wiki Rules")

    up_graph: Dict[str, List[str]] = {}
    related_graph: Dict[str, List[str]] = {}

    # --- Pass 1: Node-level inspections (C7 & local C8) and Graph Construction ---
    for file_path in md_files:
        stem = file_path.stem
        is_index_folder = "500. Index" in file_path.parts
        is_wiki_folder = "400. Wiki" in file_path.parts

        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        lines = text.splitlines()
        fm_data, raw_fm, body = parse_markdown_frontmatter(text)
        fm_dict = fm_data if isinstance(fm_data, dict) else {}

        # 1. Collect up parents
        raw_up = fm_dict.get("up")
        up_stems: List[str] = []
        if raw_up:
            up_items = raw_up if isinstance(raw_up, list) else [raw_up]
            for u in up_items:
                s = str(u).strip().strip("'\"")
                if s.startswith("[[") and s.endswith("]]"):
                    target_name = s[2:-2].split("|")[0].split("#")[0].strip()
                    if target_name:
                        up_stems.append(target_name)
        up_graph[stem] = up_stems

        # 2. Collect related targets
        raw_related = fm_dict.get("related")
        rel_stems: List[str] = []
        if raw_related:
            rel_items = raw_related if isinstance(raw_related, list) else [raw_related]
            for r in rel_items:
                s = str(r).strip().strip("'\"")
                if s.startswith("[[") and s.endswith("]]"):
                    target_name = s[2:-2].split("|")[0].split("#")[0].strip()
                    if target_name:
                        rel_stems.append(target_name)
        related_graph[stem] = rel_stems

        # --- C7.1: Forbidden Index References in Notes (outside 500. Index) ---
        if not is_index_folder:
            # Check frontmatter
            if "_인덱스_" in raw_fm:
                for idx_m in re.finditer(r"\[\[(_인덱스_[^\]|#]+)(?:[|#][^\]]*)?\]\]|`(_인덱스_[^`\n]+)`", raw_fm):
                    val = idx_m.group(1) or idx_m.group(2)
                    violations.append(
                        Violation(
                            file_path,
                            "C7",
                            1,
                            f"Forbidden index reference detected in frontmatter: '{val}' (index references are strictly forbidden in notes)",
                        )
                    )
            # Check body
            if "_인덱스_" in body:
                for offset, b_line in enumerate(body.splitlines()):
                    if "_인덱스_" in b_line:
                        for idx_m in re.finditer(r"\[\[(_인덱스_[^\]|#]+)(?:[|#][^\]]*)?\]\]|`(_인덱스_[^`\n]+)`", b_line):
                            val = idx_m.group(1) or idx_m.group(2)
                            line_num = offset + 1
                            violations.append(
                                Violation(
                                    file_path,
                                    "C7",
                                    line_num,
                                    f"Forbidden index reference detected in body: '{val}' (index references are strictly forbidden in notes)",
                                )
                            )

        # --- C7.2: Self-References ---
        if stem in up_stems:
            violations.append(
                Violation(
                    file_path,
                    "C7",
                    1,
                    f"Self-reference detected in up: note cannot link to itself ('[[{stem}]]')",
                )
            )
        if stem in rel_stems:
            violations.append(
                Violation(
                    file_path,
                    "C7",
                    1,
                    f"Self-reference detected in related: note cannot link to itself ('[[{stem}]]')",
                )
            )
        if not is_index_folder:
            self_pattern = re.compile(rf"\[\[{re.escape(stem)}(?:[|#][^\]]*)?\]\]|`{re.escape(stem)}`")
            for off, b_line in enumerate(body.splitlines()):
                if self_pattern.search(b_line):
                    violations.append(
                        Violation(
                            file_path,
                            "C7",
                            off + 1,
                            f"Self-reference detected in body: note cannot reference itself ('[[{stem}]]' or '`{stem}`')",
                        )
                    )

        # --- C7.3: Ghost Wikilinks in Frontmatter ---
        for u_stem in up_stems:
            if u_stem not in valid_targets:
                violations.append(
                    Violation(
                        file_path,
                        "C7",
                        1,
                        f"Ghost wikilink detected in up: '[[{u_stem}]]' does not exist in vault (uncreated ghost notes are strictly forbidden)",
                    )
                )
        for r_stem in rel_stems:
            if r_stem not in valid_targets:
                violations.append(
                    Violation(
                        file_path,
                        "C7",
                        1,
                        f"Ghost wikilink detected in related: '[[{r_stem}]]' does not exist in vault",
                    )
                )

        # --- C7.4: Index filename check ---
        if is_index_folder and not file_path.name.startswith("_인덱스_"):
            violations.append(
                Violation(
                    file_path,
                    "C7",
                    1,
                    f"Index filename does not follow standard prefix '_인덱스_': '{file_path.name}'",
                )
            )

        # --- C7.5: Fake Ghost Note Backticks & C7.6: Body Ghost Wikilinks ---
        clean_body = re.sub(r"```[\s\S]*?```", "", body)
        # Scan inline backticks before code stripping
        for tick_m in re.finditer(r"`([^`\n]+)`", clean_body):
            val = tick_m.group(1).strip()
            tick_line = 1
            for orig_idx, orig_line in enumerate(lines):
                if f"`{val}`" in orig_line:
                    tick_line = orig_idx + 1
                    break
            if is_wiki_folder and re.search(r"\[\[[^\]]+\]\]", val):
                violations.append(
                    Violation(
                        file_path,
                        "C7",
                        tick_line,
                        f"Backtick-wrapped wikilink detected: '`{val}`' (wikilinks inside backticks are forbidden in 400. Wiki)",
                    )
                )
            elif val in GHOST_HUB_NAMES:
                violations.append(
                    Violation(
                        file_path,
                        "C7",
                        tick_line,
                        f"Fake ghost note backtick detected: '`{val}`' (uncreated ghost note backticks are strictly forbidden and must be deleted)",
                    )
                )
            elif bool(re.match(r"^[1234](?:-[12])?단계:", val)):
                violations.append(
                    Violation(
                        file_path,
                        "C7",
                        tick_line,
                        f"Fake stage-code backtick detected: '`{val}`' (uncreated stage-code backticks must be removed)",
                    )
                )
            elif (
                val.startswith(("산업_", "기업_"))
                or bool(re.match(r"^C\d+_", val))
                or bool(re.match(r"^C\d+-S[^_]*_", val))
            ) and not any(ch in val for ch in ("[", "]", "~")):
                if val not in valid_targets:
                    violations.append(
                        Violation(
                            file_path,
                            "C7",
                            tick_line,
                            f"Fake uncreated note backtick detected: '`{val}`' (note does not exist in vault)",
                        )
                    )

        # Strip inline code (single-line only; do not mask `[[...]]` in 400. Wiki) and image embeds for body wikilink scan
        if is_wiki_folder:
            clean_body_no_code = re.sub(r"`(?![^\n`]*\[\[)[^`\n]+`", "", clean_body)
        else:
            clean_body_no_code = re.sub(r"`[^`\n]+`", "", clean_body)
        clean_body_no_code = re.sub(r"!\[\[[^\]]+\]\]", "", clean_body_no_code)

        body_lines = clean_body_no_code.splitlines()
        for offset, b_line in enumerate(body_lines):
            matches = re.finditer(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]", b_line)
            for m in matches:
                target_stem = m.group(1).strip()
                if not target_stem or target_stem in {"", "-", "[]", "[[]]"}:
                    continue
                if target_stem not in valid_targets:
                    line_num = offset + 1
                    for orig_idx, orig_line in enumerate(lines):
                        if f"[[{target_stem}" in orig_line:
                            line_num = orig_idx + 1
                            break
                    violations.append(
                        Violation(
                            file_path,
                            "C7",
                            line_num,
                            f"Ghost wikilink detected: '[[{target_stem}]]' does not exist in vault (uncreated ghost notes are strictly forbidden)",
                        )
                    )

        # --- C8.1: Non-Chronological prev in 400. Wiki ---
        if is_wiki_folder:
            is_structural = (
                stem.startswith("산업_")
                or stem.startswith("기업_")
                or bool(re.match(r"^C\d+_", stem))
                or bool(re.match(r"^C\d+-S", stem))
                or fm_dict.get("type") in ("hub", "concept")
            )
            raw_prev = fm_dict.get("prev")
            if is_structural and raw_prev:
                prev_list = raw_prev if isinstance(raw_prev, list) else [raw_prev]
                cleaned_prev = [str(x).strip() for x in prev_list if str(x).strip() and str(x).strip() not in ("[]", "[[]]")]
                if cleaned_prev:
                    violations.append(
                        Violation(
                            file_path,
                            "C8",
                            1,
                            f"Non-chronological prev detected in '{stem}': structural concept/hub/stage notes must not use 'prev' (prev is reserved for chronological notes)",
                        )
                    )

        # --- C8.2: 1-Hop Scope Violations in 400. Wiki Body & up ---
        if is_wiki_folder:
            # Case/event wiki up constraint
            is_case_wiki = not (
                stem.startswith("산업_")
                or stem.startswith("기업_")
                or bool(re.match(r"^C\d+", stem))
            )
            if is_case_wiki:
                for u in up_stems:
                    if bool(re.match(r"^C\d+", u)):
                        violations.append(
                            Violation(
                                file_path,
                                "C8",
                                1,
                                f"1-Hop scope violation in case/event wiki '{stem}': 'up: [[{u}]]' cannot link directly to Level 1 or Level 2 (must link to Lv4 company or Lv3 sub-industry, or use clean null [])",
                            )
                        )

            # Body inline 1-hop scope
            for offset, b_line in enumerate(body_lines):
                matches = re.finditer(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]", b_line)
                for m in matches:
                    t_stem = m.group(1).strip()
                    if not t_stem or t_stem not in valid_targets:
                        continue  # Ghost wikilinks handled in C7
                    line_num = offset + 1
                    for orig_idx, orig_line in enumerate(lines):
                        if f"[[{t_stem}" in orig_line:
                            line_num = orig_idx + 1
                            break

                    # Level 1 Hub body: can only link to its own Level 2 children (C#-S#)
                    if bool(re.match(r"^C\d+_", stem)):
                        cluster_code = stem.split("_")[0]
                        if not bool(re.match(rf"^{cluster_code}-S\d+", t_stem)):
                            violations.append(
                                Violation(
                                    file_path,
                                    "C8",
                                    line_num,
                                    f"1-Hop scope violation in Level 1 wiki '{stem}': inline link '[[{t_stem}]]' is not an immediate Level 2 child",
                                )
                            )

                    # Level 2 Stage body: can only link to immediate Level 3 children (산업_)
                    elif bool(re.match(r"^C\d+-S", stem)):
                        if not t_stem.startswith("산업_"):
                            violations.append(
                                Violation(
                                    file_path,
                                    "C8",
                                    line_num,
                                    f"1-Hop scope violation in Level 2 wiki '{stem}': inline link '[[{t_stem}]]' is not an immediate Level 3 child",
                                )
                            )

                    # Level 3 Sub-industry body: cannot link to Level 1, non-parent Level 2, peer Level 3, or source reports
                    elif stem.startswith("산업_"):
                        if bool(re.match(r"^C\d+_", t_stem)):
                            violations.append(
                                Violation(
                                    file_path,
                                    "C8",
                                    line_num,
                                    f"1-Hop scope violation in Level 3 wiki '{stem}': inline link '[[{t_stem}]]' is a 2-Hop Level 1 ancestor (must use bold or remove)",
                                )
                            )
                        elif bool(re.match(r"^C\d+-S", t_stem)) and up_stems and t_stem not in up_stems:
                            violations.append(
                                Violation(
                                    file_path,
                                    "C8",
                                    line_num,
                                    f"1-Hop scope violation in Level 3 wiki '{stem}': inline link '[[{t_stem}]]' is not the immediate Level 2 parent",
                                )
                            )
                        elif t_stem.startswith("산업_"):
                            violations.append(
                                Violation(
                                    file_path,
                                    "C8",
                                    line_num,
                                    f"1-Hop scope violation in Level 3 wiki '{stem}': inline link '[[{t_stem}]]' to peer Level 3 sub-industry is forbidden in body",
                                )
                            )
                        elif t_stem.startswith(("산업분석_", "독서모임 발제_")):
                            violations.append(
                                Violation(
                                    file_path,
                                    "C8",
                                    line_num,
                                    f"1-Hop scope violation in Level 3 wiki '{stem}': inline link '[[{t_stem}]]' to source report is forbidden (must use backticks)",
                                )
                            )

                    # Level 4 Company body: cannot link to Level 1 or Level 2
                    elif stem.startswith("기업_"):
                        if bool(re.match(r"^C\d+", t_stem)):
                            violations.append(
                                Violation(
                                    file_path,
                                    "C8",
                                    line_num,
                                    f"1-Hop scope violation in Level 4 wiki '{stem}': inline link '[[{t_stem}]]' to Level 1/2 is a 2-Hop+ remote link",
                                )
                            )

    # --- Pass 2: C8 DAG Cycle Detection (DFS 3-color) ---
    color: Dict[str, int] = {}
    reported_cycle_notes: Set[str] = set()

    def dfs_cycle(node: str, path: List[str]):
        color[node] = 1
        for parent in up_graph.get(node, []):
            if parent not in up_graph:
                continue
            if color.get(parent, 0) == 1:
                cycle_start_idx = path.index(parent) if parent in path else 0
                cycle_nodes = path[cycle_start_idx:] + [parent]
                cycle_str = " -> ".join(cycle_nodes)
                for c_node in cycle_nodes:
                    if c_node not in reported_cycle_notes and c_node in all_notes:
                        reported_cycle_notes.add(c_node)
                        violations.append(
                            Violation(
                                all_notes[c_node],
                                "C8",
                                1,
                                f"DAG cycle detected in 'up' graph: {cycle_str}",
                            )
                        )
            elif color.get(parent, 0) == 0:
                dfs_cycle(parent, path + [parent])
        color[node] = 2

    for node in list(up_graph.keys()):
        if color.get(node, 0) == 0:
            dfs_cycle(node, [node])

    # --- Pass 3: C8 Transitive Triangle Reduction & Vertical Hierarchy in related ---
    def is_reachable(start: str, target: str) -> bool:
        visited: Set[str] = set()
        queue = list(up_graph.get(start, []))
        while queue:
            curr = queue.pop(0)
            if curr == target:
                return True
            if curr not in visited and curr in up_graph:
                visited.add(curr)
                queue.extend(up_graph.get(curr, []))
        return False

    for node, parents in up_graph.items():
        if len(parents) >= 2:
            unique_parents = list(dict.fromkeys(parents))
            for i in range(len(unique_parents)):
                for j in range(len(unique_parents)):
                    if i == j:
                        continue
                    b = unique_parents[i]
                    c = unique_parents[j]
                    if is_reachable(b, c):
                        if node in all_notes:
                            violations.append(
                                Violation(
                                    all_notes[node],
                                    "C8",
                                    1,
                                    f"Transitive triangle shortcut detected in '{node}': direct 'up: [[{c}]]' coexists with indirect path '{node} -> [[{b}]] -> ... -> [[{c}]]' (must prune [[{c}]] from up)",
                                )
                            )

    for node, rel_list in related_graph.items():
        if node not in all_notes:
            continue
        for r_target in rel_list:
            if is_reachable(node, r_target) or is_reachable(r_target, node):
                violations.append(
                    Violation(
                        all_notes[node],
                        "C8",
                        1,
                        f"Vertical hierarchy in related detected in '{node}': '[[{r_target}]]' is vertically related in the up-graph (related must only be used for horizontal peer notes)",
                    )
                )

    return violations


def audit_vault(
    vault_root: Path,
    auto_fix: bool = False,
    include_inbox: bool = False,
    check_index: bool = False,
    check_astep: bool = False,
    verbose: bool = False,
) -> Tuple[List[Violation], int]:
    """Audit entire vault directory for all constitutional checks."""
    all_violations: List[Violation] = []
    scanned_file_count = 0
    scanned_md_files: List[Path] = []

    if not vault_root.exists():
        raise FileNotFoundError(f"Vault path does not exist: {vault_root}")

    cfg = load_constitution(vault_root)

    all_files = sorted([p for p in vault_root.rglob("*") if p.is_file()])

    for file_path in all_files:
        # Check 5 (C5: Binary Infiltration)
        suffix = file_path.suffix.lower()
        if suffix in HEAVY_BINARY_EXTENSIONS:
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

        if suffix != ".md":
            continue

        if is_excluded_path(file_path, vault_root, include_inbox=include_inbox):
            if verbose:
                print(f"[Skipping Excluded] {file_path}")
            continue

        scanned_file_count += 1
        scanned_md_files.append(file_path)
        note_violations = audit_markdown_note(
            file_path,
            vault_root,
            auto_fix=auto_fix,
            verbose=verbose,
            cfg=cfg,
        )
        all_violations.extend(note_violations)

    if check_index:
        all_violations.extend(audit_index_sync(vault_root, cfg))

    if check_astep:
        all_violations.extend(audit_astep(vault_root, cfg, scanned_md_files))

    return all_violations, scanned_file_count


def format_report_text(
    violations: List[Violation],
    total_scanned: int,
) -> str:
    """Format audit results as readable human text."""
    failed_files = len({v.file_path for v in violations})
    passed_files = max(0, total_scanned - failed_files)
    counts = {
        "C1": sum(1 for v in violations if v.check_code == "C1"),
        "C2": sum(1 for v in violations if v.check_code == "C2"),
        "C3": sum(1 for v in violations if v.check_code == "C3"),
        "C4": sum(1 for v in violations if v.check_code == "C4"),
        "C5": sum(1 for v in violations if v.check_code == "C5"),
        "C6": sum(1 for v in violations if v.check_code == "C6"),
        "C7": sum(1 for v in violations if v.check_code == "C7"),
        "C8": sum(1 for v in violations if v.check_code == "C8"),
    }

    check_summary = (
        f"Violations by Check: C1={counts['C1']} (Core), C2={counts['C2']} (Ghost), "
        f"C3={counts['C3']} (Orphan), C4={counts['C4']} (MECE), C5={counts['C5']} (Binary)"
    )
    if counts["C6"] > 0:
        check_summary += f", C6={counts['C6']} (Index)"
    if counts["C7"] > 0 or counts["C8"] > 0:
        check_summary += f", C7={counts['C7']} (GhostTargets), C8={counts['C8']} (Topology)"

    lines = [
        "============================================================",
        "          My-PKM Vault Constitutional Audit Report          ",
        "============================================================",
        f"Scanned: {total_scanned} files | Passed: {passed_files} | Failed: {failed_files} | Total Violations: {len(violations)}",
        check_summary,
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
    for code in ("C6", "C7", "C8"):
        c_val = sum(1 for v in violations if v.check_code == code)
        if c_val > 0:
            counts[code] = c_val

    report = {
        "summary": {
            "total_scanned": total_scanned,
            "passed": max(0, total_scanned - failed_files),
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
    passed_files = max(0, total_scanned - failed_files)
    counts = {
        "C1": sum(1 for v in violations if v.check_code == "C1"),
        "C2": sum(1 for v in violations if v.check_code == "C2"),
        "C3": sum(1 for v in violations if v.check_code == "C3"),
        "C4": sum(1 for v in violations if v.check_code == "C4"),
        "C5": sum(1 for v in violations if v.check_code == "C5"),
        "C6": sum(1 for v in violations if v.check_code == "C6"),
        "C7": sum(1 for v in violations if v.check_code == "C7"),
        "C8": sum(1 for v in violations if v.check_code == "C8"),
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
    ]
    if counts["C6"] > 0:
        lines.append(f"| C6 | 500. Index Registration | {counts['C6']} |")
    if counts["C7"] > 0:
        lines.append(f"| C7 | Ghost Targets & Prefixes | {counts['C7']} |")
    if counts["C8"] > 0:
        lines.append(f"| C8 | DAG Cycles & Triangles | {counts['C8']} |")
    lines.append("")

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
        description="Vault Constitutional Linter CLI for My-PKM (Checks C1-C8)"
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
        "--check-index",
        action="store_true",
        help="Check C6: Verify compiled notes in 100/200/300/400 are registered in 500. Index",
    )
    parser.add_argument(
        "--check-astep",
        action="store_true",
        help="Check C7 & C8: Opt-in A-Step 1~3 verification (Ghost targets & prefixes, DAG cycles & transitive triangles)",
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
            check_index=args.check_index,
            check_astep=args.check_astep,
            verbose=args.verbose,
        )
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

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
