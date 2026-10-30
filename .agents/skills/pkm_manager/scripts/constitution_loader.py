#!/usr/bin/env python
"""Dynamic SSOT Constitution Loader for My-PKM (My-Wiki Rules.md v3.0+).

Parses `./My-Wiki/My-Wiki Rules.md` at runtime so that any updates made manually
or via the Gemini App (Spark) to folder structures, domain codes, core attributes,
status/type enums, or `500. Index` partitioned indexes are immediately reflected
across Antigravity (`agy`) skills and Python CLI tools.

Provides safe v3.0 fallback defaults when invoked on minimal test fixtures that
do not contain a `My-Wiki Rules.md` file.

Usage:
    python constitution_loader.py --vault ./My-Wiki [--format text|json]
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import hashlib
import json
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


DEFAULT_CORE_ATTRIBUTES: List[str] = [
    "origin",
    "type",
    "domain",
    "up",
    "status",
    "created",
    "updated",
]

DEFAULT_STANDARD_DOMAINS: List[str] = [
    "theory",
    "macro",
    "equity",
    "portfolio",
    "quant",
    "work",
    "life",
    "ai-pkm",
    "education",
]

DEFAULT_ALLOWED_ORIGINS: List[str] = [
    "human",
    "ai",
    "source",
    "wiki",
]

DEFAULT_ALLOWED_TYPES: List[str] = [
    "hub",
    "concept",
    "analysis",
    "entity",
    "source",
    "project",
    "log",
]

DEFAULT_ALLOWED_STATUSES: List[str] = [
    "active",
    "completed",
    "archived",
    "seed",
    "growing",
    "evergreen",
]

DEFAULT_LEVEL_1_HUBS: List[str] = [
    "My-Wiki Rules.md",
    "01_경제 및 금융 이론.md",
    "02_매크로 분석.md",
    "03_산업 및 기업분석.md",
    "04_가족 투자 포트폴리오.md",
    "05_회사업무 (자산운용).md",
    "06_AI 활용 및 PKM 구축.md",
    "07_자녀교육.md",
]

DEFAULT_FOLDER_ORIGIN_MAP: Dict[str, str] = {
    "100. Concepts": "human",
    "200. AI_logs": "ai",
    "210. 뉴스 큐레이팅": "ai",
    "220. 산업분석": "ai",
    "300. Sources": "source",
    "400. Wiki": "wiki",
    "500. Index": "wiki",
    "600. etc": "human",
    "500. etc": "human",  # Legacy v2.1 backward compatibility
}

DEFAULT_FOLDER_IDS: Dict[str, str] = {
    "My-Wiki": "1HXQNL3Cya-uTa6jdBn7-L--5rV_9ocx0",
    "000. Inbox": "1AwWl9IIwLZtHjMwQJ8s3GzE4dyrZs5aD",
    "100. Concepts": "17HT-Cx1PLOsdAv4km--_4M97COXtWjgv",
    "200. AI_logs": "1orZv1n4hFb7aLwOYlhd2Pu2O2hcnheGF",
    "210. 뉴스 큐레이팅": "159QFTTwSEbrzEIaOtX-QhyN4Wnf7p_Gk",
    "220. 산업분석": "1psFmNnFK-6POa_3UZcwp__rfUCFfLuW3",
    "300. Sources": "1p_k37R8S5V7cwdrqGSjjtM89zQ-QdS3m",
    "400. Wiki": "10cpcWEZQSolOn4gqLIHFQ1hx69YU0rXr",
    "500. Index": "1i08DUwmEzPgjGgy9T7hJTDTizW-q7Ly8",
    ".trash": "1CdvjN7YReah5WCGkD-SfQlnXnRrVZxgD",
}

DEFAULT_INDEX_FILES: List[str] = [
    "_인덱스_400_Wiki.md",
    "_인덱스_100_Concepts.md",
    "_인덱스_200_AI_logs.md",
    "_인덱스_300_Sources.md",
    "_인덱스_210_뉴스큐레이팅.md",
    "_인덱스_220_산업분석.md",
]

DEFAULT_STANDARD_PREFIXES: List[str] = [
    "C#_",
    "C#-S#_",
    "산업_",
    "기업_",
    "_인덱스_",
]


@dataclass
class ConstitutionConfig:
    """Structured representation of the My-Wiki Rules SSOT constitution."""

    ssot_path: Optional[str] = None
    ssot_exists: bool = False
    version: str = "v3.0"
    updated: str = ""
    sha256: str = ""
    core_attributes: List[str] = field(default_factory=lambda: list(DEFAULT_CORE_ATTRIBUTES))
    standard_domains: List[str] = field(default_factory=lambda: list(DEFAULT_STANDARD_DOMAINS))
    allowed_origins: List[str] = field(default_factory=lambda: list(DEFAULT_ALLOWED_ORIGINS))
    allowed_types: List[str] = field(default_factory=lambda: list(DEFAULT_ALLOWED_TYPES))
    allowed_statuses: List[str] = field(default_factory=lambda: list(DEFAULT_ALLOWED_STATUSES))
    level_1_hubs: List[str] = field(default_factory=lambda: list(DEFAULT_LEVEL_1_HUBS))
    folder_origin_map: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_FOLDER_ORIGIN_MAP))
    folder_ids: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_FOLDER_IDS))
    index_files: List[str] = field(default_factory=lambda: list(DEFAULT_INDEX_FILES))
    standard_prefixes: List[str] = field(default_factory=lambda: list(DEFAULT_STANDARD_PREFIXES))
    max_domains_per_note: int = 2

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def __getitem__(self, key: str) -> Any:
        if key == "allowed_domains":
            return self.standard_domains
        if key in ("prefixes", "standard_prefixes"):
            return self.standard_prefixes
        return getattr(self, key)


def _extract_backtick_tokens(line: str) -> List[str]:
    """Extract all `token` values inside backticks from a line."""
    return [m.strip() for m in re.findall(r"`([^`]+)`", line) if m.strip()]


def load_constitution(vault_root: Path | str = "./My-Wiki") -> ConstitutionConfig:
    """Load and dynamically parse `./My-Wiki/My-Wiki Rules.md` into a ConstitutionConfig."""
    vault_path = Path(vault_root).resolve()
    rules_path = vault_path / "My-Wiki Rules.md"

    if not rules_path.exists():
        candidates = [
            p for p in vault_path.glob("My-Wiki Rules*.md")
            if p.is_file() and not p.name.startswith(".")
        ]
        if candidates:
            # Pick latest by modification time, then filename
            candidates.sort(key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
            picked = candidates[0]
            rules_path = picked
            print(
                f"[WARNING] Exact 'My-Wiki Rules.md' not found in {vault_path}. "
                f"Falling back to latest matching file '{picked.name}'",
                file=sys.stderr,
            )

    cfg = ConstitutionConfig(
        ssot_path=str(rules_path),
        ssot_exists=rules_path.exists(),
    )

    if not rules_path.exists():
        # Still scan 500. Index if present on disk
        index_dir = vault_path / "500. Index"
        if index_dir.exists() and index_dir.is_dir():
            discovered = sorted(p.name for p in index_dir.glob("_인덱스_*.md") if p.is_file())
            if discovered:
                for idx_name in discovered:
                    if idx_name not in cfg.index_files:
                        cfg.index_files.append(idx_name)
        return cfg

    raw_bytes = rules_path.read_bytes()
    cfg.sha256 = hashlib.sha256(raw_bytes).hexdigest()

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = raw_bytes.decode("utf-8", errors="replace")

    # 1. Parse YAML frontmatter for updated date
    fm_match = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.DOTALL)
    if fm_match:
        try:
            fm_data = yaml.safe_load(fm_match.group(1))
            if isinstance(fm_data, dict) and "updated" in fm_data:
                cfg.updated = str(fm_data["updated"]).strip()
        except Exception:
            pass

    # 2. Parse version string from H1 title (e.g. "# 📜 My-Wiki Rules (지식관리헌법 v3.0)")
    ver_match = re.search(
        r"(?:지식\s*관리\s*헌법|^#\s+.*?)\s*\(?(v\d+(?:\.\d+)*)\)?",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if ver_match:
        cfg.version = ver_match.group(1)

    # 3. Parse Section 0.1 / Rule 1 Folder Registry Table
    # Matches rows like: | **`100. Concepts`** | `17HT-...` | `human` | ... |
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue

        folder_tokens = _extract_backtick_tokens(cells[0])
        if not folder_tokens:
            continue
        folder_name = folder_tokens[0]

        # Scan remaining cells for Google Drive Folder ID (>=15 alphanumeric chars) and origin enum
        for cell in cells[1:]:
            tokens = _extract_backtick_tokens(cell)
            for tok in tokens:
                tok_clean = re.sub(r"^origin:\s*", "", tok.strip(), flags=re.IGNORECASE)
                if re.match(r"^[A-Za-z0-9_-]{20,}$", tok_clean):
                    cfg.folder_ids[folder_name] = tok_clean
                elif tok_clean.lower() in {"human", "ai", "source", "wiki", "config"}:
                    origin_candidate = tok_clean.lower()
                    cfg.folder_origin_map[folder_name] = origin_candidate
                    if origin_candidate not in cfg.allowed_origins:
                        cfg.allowed_origins.append(origin_candidate)

    # Also detect `600. etc` on disk in vault_path
    if (vault_path / "600. etc").exists():
        cfg.folder_origin_map["600. etc"] = "human"

    # 4. Parse Rule 2: 7 Core Attributes & Enum values (origin, type, domain, status)
    rule2_match = re.search(
        r"1\.\s*\*\*(?:절대 지우지 않는\s*)?(?:\d+대\s*)?(?:필수\s*)?코어 속성.*?(?=\n\d+\.\s*\*\*|####\s*규칙\s*3\.|\Z)",
        text,
        re.DOTALL,
    )
    if rule2_match:
        rule2_block = rule2_match.group(0)
        discovered_core: List[str] = []
        for line in rule2_block.splitlines():
            # e.g. "   - `origin` (출처: `human` | `ai` | `source` | `wiki`)"
            bullet_match = re.match(r"^\s*-\s*`([a-zA-Z0-9_-]+)`\s*[:(](.+)", line)
            if not bullet_match:
                continue
            attr_name = bullet_match.group(1).strip()
            attr_desc = bullet_match.group(2)
            if attr_name not in discovered_core:
                discovered_core.append(attr_name)

            enum_tokens = _extract_backtick_tokens(attr_desc)
            if attr_name == "origin" and enum_tokens:
                for tok in enum_tokens:
                    if tok not in cfg.allowed_origins:
                        cfg.allowed_origins.append(tok)
            elif attr_name == "type" and enum_tokens:
                for tok in enum_tokens:
                    if tok not in cfg.allowed_types:
                        cfg.allowed_types.append(tok)
            elif attr_name == "domain" and enum_tokens:
                # SSOT Deletion Sync: replace completely with parsed list, do not append
                cfg.standard_domains = list(enum_tokens)
            elif attr_name == "status" and enum_tokens:
                for tok in enum_tokens:
                    if not re.match(r"^YYYY", tok) and tok not in cfg.allowed_statuses:
                        cfg.allowed_statuses.append(tok)

        if len(discovered_core) >= 7:
            cfg.core_attributes = discovered_core

    # 5. Parse Section <3> Level 1 Master Domain Root Anchors
    # Matches `[[01_경제 및 금융 이론]]` etc.
    l1_matches = re.findall(r"\[\[(\d{2}_[^\]|]+)\]\]", text)
    for l1_name in l1_matches:
        md_name = f"{l1_name.strip()}.md"
        if md_name not in cfg.level_1_hubs:
            cfg.level_1_hubs.append(md_name)

    # 6. Parse Rule 10 & Scan `500. Index` for `_인덱스_*.md` files
    idx_matches = re.findall(r"`(_인덱스_[^`]+\.md)`", text)
    for idx_name in idx_matches:
        if "[" not in idx_name and idx_name not in cfg.index_files:
            cfg.index_files.append(idx_name)

    index_dir = vault_path / "500. Index"
    if index_dir.exists() and index_dir.is_dir():
        for p in sorted(index_dir.glob("_인덱스_*.md")):
            if p.is_file() and p.name not in cfg.index_files:
                cfg.index_files.append(p.name)

    # 7. Parse Rule 9.3 A-Step 1 Standard Filename Prefixes
    prefix_match = re.search(r"표준\s*접두사\s*\(([^)]+)\)", text)
    if prefix_match:
        parsed_prefixes = _extract_backtick_tokens(prefix_match.group(1))
        if parsed_prefixes:
            cfg.standard_prefixes = parsed_prefixes

    return cfg


def format_config_text(cfg: ConstitutionConfig) -> str:
    """Format the parsed ConstitutionConfig as human-readable text."""
    lines = [
        "============================================================",
        f"  My-PKM Dynamic SSOT Constitution Loader ({cfg.version})",
        "============================================================",
        f"SSOT Path    : {cfg.ssot_path}",
        f"SSOT Exists  : {cfg.ssot_exists}",
        f"Updated Date : {cfg.updated or 'N/A'}",
        f"SHA-256      : {cfg.sha256[:16]}..." if cfg.sha256 else "SHA-256      : N/A (Fallback Mode)",
        "------------------------------------------------------------",
        f"Core Keys ({len(cfg.core_attributes)}) : {', '.join(cfg.core_attributes)}",
        f"Domains ({len(cfg.standard_domains)})   : {', '.join(cfg.standard_domains)} (max {cfg.max_domains_per_note})",
        f"Origins ({len(cfg.allowed_origins)})   : {', '.join(cfg.allowed_origins)}",
        f"Types ({len(cfg.allowed_types)})     : {', '.join(cfg.allowed_types)}",
        f"Statuses ({len(cfg.allowed_statuses)})  : {', '.join(cfg.allowed_statuses)}",
        f"Prefixes ({len(cfg.standard_prefixes)})  : {', '.join(cfg.standard_prefixes)}",
        "------------------------------------------------------------",
        "Folder -> Origin Mapping:",
    ]
    for folder, origin in cfg.folder_origin_map.items():
        lines.append(f"  - {folder:<22} -> {origin}")
    lines.append("------------------------------------------------------------")
    lines.append(f"Partitioned Indexes in 500. Index ({len(cfg.index_files)}):")
    for idx_file in cfg.index_files:
        lines.append(f"  - {idx_file}")
    lines.append("============================================================")
    return "\n".join(lines)


PREDEFINED_SECTIONS: Dict[str, Tuple[str, str]] = {
    "overview": ("## <0>", "에이전트 공용 지침 및 동적 폴더 해석 체계"),
    "schema": ("### [Part 1.", "물리적 공간과 메타데이터 구조 (규칙 1~3, 7대 코어, Clean Null)"),
    "links": ("### [Part 2.", "링크 방향성(O / B / C)과 단계적 추상화 위계 설계 (규칙 4~8)"),
    "compile": ("##### 9.1", "1차 프로세스: 000. Inbox 기점 4단계 원천 메모 컴파일 (Step 1~4)"),
    "mstep": ("##### 9.2", "2차 프로세스: 상위 추상 위키 상향 메타 컴파일 (M-Step 1~5)"),
    "astep": ("##### 9.3", "3차 프로세스: 헌법 전 조항 통합 사후 감사 프로토콜 (A-Step 1~5)"),
    "index": ("#### 규칙 10.", "500. Index 분할 인덱스 아키텍처"),
    "templates": ("#### 규칙 11.", "주제 성격에 따른 400. Wiki 적응형 내부 컴파일 구조 (5대 위키 아키타입)"),
    "cases": ("## <5>", "복합 지식 아키텍처 실전 적용 규격 (Case 1~3)"),
    "all": ("", "전체 헌법 원문"),
}


def extract_section(text: str, key_or_keyword: str) -> Optional[Tuple[str, str]]:
    """Extract section text from constitution markdown based on predefined key or heading keyword.

    Returns (matched_heading_line, section_content) or None if not found.
    """
    key_norm = key_or_keyword.strip().lower()
    if key_norm == "all":
        first_line = text.splitlines()[0] if text.splitlines() else "My-Wiki Rules"
        return (first_line, text.strip())

    target_prefix = None
    if key_norm in PREDEFINED_SECTIONS:
        target_prefix = PREDEFINED_SECTIONS[key_norm][0]

    lines = text.splitlines()
    start_idx = None
    matched_heading = None
    heading_level = 0

    for idx, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped.startswith("#"):
            continue

        h_match = re.match(r"^(#{1,6})\s+(.*)", line_stripped)
        if not h_match:
            continue
        level = len(h_match.group(1))

        if target_prefix and line_stripped.startswith(target_prefix):
            start_idx = idx
            matched_heading = line_stripped
            heading_level = level
            break
        elif not target_prefix and key_norm in line_stripped.lower():
            start_idx = idx
            matched_heading = line_stripped
            heading_level = level
            break

    if start_idx is None:
        return None

    end_idx = len(lines)
    for idx in range(start_idx + 1, len(lines)):
        line_stripped = lines[idx].strip()
        if line_stripped.startswith("#"):
            h_match = re.match(r"^(#{1,6})\s+", line_stripped)
            if h_match and len(h_match.group(1)) <= heading_level:
                end_idx = idx
                break

    section_text = "\n".join(lines[start_idx:end_idx]).strip()
    return (matched_heading, section_text)


def list_sections_dict(text: str) -> Dict[str, Any]:
    """Return dictionary of predefined section keys and all markdown headings."""
    predefined = {}
    for k, (prefix, desc) in PREDEFINED_SECTIONS.items():
        predefined[k] = {
            "target_prefix": prefix,
            "description": desc,
        }
    headings = []
    lines = text.splitlines()
    for idx, line in enumerate(lines, 1):
        line_stripped = line.strip()
        if line_stripped.startswith("#"):
            h_match = re.match(r"^(#{1,6})\s+(.*)", line_stripped)
            if h_match:
                level = len(h_match.group(1))
                headings.append(
                    {
                        "line": idx,
                        "level": level,
                        "heading": line_stripped,
                        "title": h_match.group(2).strip(),
                    }
                )
    return {
        "predefined_sections": predefined,
        "headings": headings,
    }


def list_sections(text: str) -> str:
    """Format and return a listing of predefined keys and all markdown headings."""
    out = [
        "============================================================",
        "  My-PKM Constitution Section Directory",
        "============================================================",
        "Predefined Section Keys:",
    ]
    for k, (prefix, desc) in PREDEFINED_SECTIONS.items():
        out.append(f"  - {k:<12} : {desc} (Target: '{prefix}')")
    out.append("------------------------------------------------------------")
    out.append("All Headings in My-Wiki Rules.md:")
    lines = text.splitlines()
    for idx, line in enumerate(lines, 1):
        line_stripped = line.strip()
        if line_stripped.startswith("#"):
            h_match = re.match(r"^(#{1,6})\s+(.*)", line_stripped)
            if h_match:
                level = len(h_match.group(1))
                indent = "  " * (level - 1)
                out.append(f"  Line {idx:4d} {indent}{line_stripped}")
    out.append("============================================================")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dynamic SSOT Constitution Loader for My-PKM (My-Wiki Rules.md)"
    )
    parser.add_argument(
        "--vault",
        type=str,
        default="./My-Wiki",
        help="Path to Obsidian vault root directory (default: ./My-Wiki)",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="text",
        choices=["text", "json"],
        help="Output format: text (default) or json",
    )
    parser.add_argument(
        "--section",
        type=str,
        default=None,
        help="Extract a specific constitution section by predefined key (overview, schema, links, compile, mstep, astep, index, templates, cases, all) or heading keyword",
    )
    parser.add_argument(
        "--list-sections",
        action="store_true",
        help="List all available predefined section keys and all document headings in My-Wiki Rules.md",
    )

    args = parser.parse_args()
    cfg = load_constitution(args.vault)

    # Read raw text of constitution if available
    rules_text = ""
    if cfg.ssot_path and Path(cfg.ssot_path).exists():
        rules_text = Path(cfg.ssot_path).read_text(encoding="utf-8", errors="replace")

    if args.list_sections:
        if not rules_text:
            print(f"[ERROR] Constitution file not found in {args.vault}", file=sys.stderr)
            return 1
        if args.format == "json":
            print(json.dumps(list_sections_dict(rules_text), indent=2, ensure_ascii=False))
        else:
            print(list_sections(rules_text))
        return 0

    if args.section:
        if not rules_text:
            print(f"[ERROR] Constitution file not found in {args.vault}", file=sys.stderr)
            return 1
        result = extract_section(rules_text, args.section)
        if not result:
            print(f"[ERROR] Section '{args.section}' not found in constitution", file=sys.stderr)
            return 1
        matched_heading, content = result
        if args.format == "json":
            print(
                json.dumps(
                    {
                        "section": args.section,
                        "heading": matched_heading,
                        "content": content,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            print(content)
        return 0

    if args.format == "json":
        print(json.dumps(cfg.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(format_config_text(cfg))

    return 0


if __name__ == "__main__":
    sys.exit(main())
