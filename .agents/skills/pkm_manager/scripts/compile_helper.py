#!/usr/bin/env python
"""Inbox & Wiki Compilation Helper CLI for My-PKM (My-Wiki Rules v3.0).

Assists the AI agent during:
  - 1st-Tier Inbox Compilation (Step 1~4):
      * `inbox-status`: Inspects `000. Inbox` queue, legacy Notion frontmatter keys, and series classification.
      * `normalize-fm`: Step 1 — Strips legacy Notion properties and normalizes 2-tier v3.0 YAML frontmatter
                        (7 core attributes, 4 time attributes, multi-`up`, Clean Null `[]`, sparse properties).
      * `scan-index`  : Step 2 & Step 4 — Searches `_인덱스_400_Wiki.md` (Step 2 wiki matching) and all
                        partitioned indexes in `500. Index` (Step 4 retroactive re-compilation candidates).
      * `upsert-index`: Step 2, 3, 4 — Appends or updates markdown table rows in `500. Index/_인덱스_*.md`
                        (including `--add-up` for Step 4 retroactive link injection).
      * `move-note`   : Step 3 — Moves compiled notes from `000. Inbox` to `100. Concepts`, `200. AI_logs`
                        (`210. 뉴스 큐레이팅`, `220. 산업분석`), or `300. Sources` via native in-place `shutil.move`.
  - 2nd-Tier Upward Meta Compilation (M-Step 1~5):
      * `detect-mstep`: Analyzes `400. Wiki` and `_인덱스_400_Wiki.md` to detect bottom-up cluster promotion
                        candidates (3~5+ sibling wikis / 7+ overcrowded children) and M-Step 5 lazy roll-up
                        candidates (`child.updated > parent.updated`).

Usage:
    python compile_helper.py --vault ./My-Wiki <subcommand> [OPTIONS]
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any, Dict, List, Optional, Tuple
import yaml

# Ensure standard streams use UTF-8 regardless of Windows console codepage
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Import dynamic SSOT constitution loader from same directory
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from constitution_loader import ConstitutionConfig, load_constitution  # noqa: E402

LEGACY_NOTION_KEYS = {
    "base",
    "주제",
    "상태",
    "구분",
    "날짜",
    "생성일",
    "수정일",
    "태그",
    "카테고리",
    "분류",
}


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


def normalize_date_str(val: Any, fallback: Optional[str] = None) -> str:
    """Normalize a date or ISO datetime value into YYYY-MM-DD."""
    if val is None:
        return fallback or datetime.now().strftime("%Y-%m-%d")
    s = str(val).strip()
    m = re.match(r"^(\d{4})[.\-/]\s*(\d{1,2})[.\-/]\s*(\d{1,2})", s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return fallback or datetime.now().strftime("%Y-%m-%d")


def normalize_wikilink_list(raw_val: Any) -> List[str]:
    """Normalize a string or list of strings into clean wikilinks `[[Target]]`, enforcing Clean Null."""
    if not raw_val:
        return []
    if isinstance(raw_val, list):
        items = [str(x) for x in raw_val]
    else:
        s = str(raw_val).strip()
        if s in {"[]", "[[]]", '""', "''"}:
            return []
        # Split on comma only outside [[...]]
        items = [p.strip() for p in re.split(r",(?![^\[]*\]\])", s) if p.strip()]

    result: List[str] = []
    for item in items:
        clean = item.strip().strip("'\"")
        if not clean or clean in {"[]", "[[]]"}:
            continue
        if clean.startswith("[[") and clean.endswith("]]"):
            inner = clean[2:-2].strip()
            if not inner:
                continue
            link = f"[[{inner}]]"
        else:
            clean_inner = clean.strip("[]").strip()
            if not clean_inner:
                continue
            link = f"[[{clean_inner}]]"
        if link not in result:
            result.append(link)
    return result


def build_v3_frontmatter(
    origin: str,
    note_type: str,
    domains: List[str],
    up_links: List[str],
    status: str = "active",
    created: Optional[str] = None,
    updated: Optional[str] = None,
    extended: Optional[Dict[str, Any]] = None,
) -> str:
    """Serialize v3.0 2-tier YAML frontmatter with Clean Null and sparse property rules."""
    today = datetime.now().strftime("%Y-%m-%d")
    created_str = normalize_date_str(created, today)
    updated_str = normalize_date_str(updated, today)

    clean_domains = [d.strip() for d in domains if d and str(d).strip()][:2]
    if not clean_domains:
        clean_domains = ["macro"]

    clean_up = normalize_wikilink_list(up_links)

    lines: List[str] = [
        "---",
        f"origin: {origin}",
        f"type: {note_type}",
        "domain:",
    ]
    for d in clean_domains:
        lines.append(f"  - {d}")

    if not clean_up:
        lines.append("up: []")
    else:
        lines.append("up:")
        for u in clean_up:
            escaped_u = u.replace('"', '\\"')
            lines.append(f'  - "{escaped_u}"')

    lines.extend([
        f"status: {status}",
        f"created: {created_str}",
        f"updated: {updated_str}",
    ])

    if extended:
        link_array_keys = {"prev", "source", "related", "author", "org", "sector"}
        for k, v in extended.items():
            if v is None:
                continue
            if k in link_array_keys:
                links = normalize_wikilink_list(v)
                if not links:
                    continue
                lines.append(f"{k}:")
                for lk in links:
                    escaped_lk = lk.replace('"', '\\"')
                    lines.append(f'  - "{escaped_lk}"')
            elif isinstance(v, list):
                clean_list = [str(x).strip() for x in v if x is not None and str(x).strip() and str(x).strip() not in {"[]", "[[]]"}]
                if not clean_list:
                    continue
                lines.append(f"{k}:")
                for item in clean_list:
                    escaped_item = item.replace("\\", "\\\\").replace('"', '\\"')
                    lines.append(f'  - "{escaped_item}"')
            elif isinstance(v, bool):
                lines.append(f"{k}: {'true' if v else 'false'}")
            elif isinstance(v, (int, float)):
                lines.append(f"{k}: {v}")
            else:
                s_val = str(v).strip()
                if not s_val or s_val in {"[]", "[[]]"}:
                    continue
                clean_s = s_val.replace("\r\n", " ").replace("\n", " ")
                if any(ch in clean_s for ch in [":", '"', "#", "[", "]", "{", "}", "|", ">"]) or clean_s.startswith("-"):
                    escaped_s = clean_s.replace("\\", "\\\\").replace('"', '\\"')
                    lines.append(f'{k}: "{escaped_s}"')
                else:
                    lines.append(f"{k}: {clean_s}")

    lines.append("---")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Subcommand 1: inbox-status
# ---------------------------------------------------------------------------
def cmd_inbox_status(vault_path: Path, cfg: ConstitutionConfig, fmt: str = "text") -> int:
    """Inspect `000. Inbox` uncompiled queue without modifying any files."""
    inbox_dir = vault_path / "000. Inbox"
    if not inbox_dir.exists():
        if fmt == "json":
            print(json.dumps({"total": 0, "notes": []}, ensure_ascii=False))
        else:
            print("000. Inbox directory does not exist.")
        return 0

    md_files = sorted(p for p in inbox_dir.glob("*.md") if p.is_file())
    notes_info: List[Dict[str, Any]] = []

    for p in md_files:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            text = ""
        fm, _, _ = parse_markdown_frontmatter(text)
        has_fm = fm is not None
        fm_keys = list(fm.keys()) if fm else []
        legacy_keys = [k for k in fm_keys if k in LEGACY_NOTION_KEYS]
        missing_core = [k for k in cfg.core_attributes if not fm or k not in fm]

        # Classify series or note category
        series_hint = "general"
        if p.name.startswith("산업분석_C"):
            series_hint = "220. 산업분석"
        elif "조간신문" in p.name or "뉴스 큐레이팅" in p.name:
            series_hint = "210. 뉴스 큐레이팅"
        elif "독서모임" in p.name:
            series_hint = "독서모임 (5차원 직교)"
        elif "밸리AI 산업 딥다이브" in p.name:
            series_hint = "산업 딥다이브"

        inferred_ref_date = None
        if fm:
            if "ref_date" in fm:
                inferred_ref_date = normalize_date_str(fm["ref_date"])
            elif "날짜" in fm:
                inferred_ref_date = normalize_date_str(fm["날짜"])

        notes_info.append({
            "filename": p.name,
            "stem": p.stem,
            "has_frontmatter": has_fm,
            "v3_ready": has_fm and len(missing_core) == 0 and len(legacy_keys) == 0,
            "legacy_notion_keys": legacy_keys,
            "missing_core_keys": missing_core,
            "series_hint": series_hint,
            "inferred_ref_date": inferred_ref_date,
        })

    summary = {
        "vault": str(vault_path),
        "total_inbox_notes": len(notes_info),
        "v3_ready_count": sum(1 for n in notes_info if n["v3_ready"]),
        "legacy_notion_count": sum(1 for n in notes_info if n["legacy_notion_keys"]),
        "industry_series_count": sum(1 for n in notes_info if n["series_hint"] == "220. 산업분석"),
        "notes": notes_info,
    }

    if fmt == "json":
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print("============================================================")
        print(f"  000. Inbox Queue Status ({summary['total_inbox_notes']} uncompiled notes)")
        print("============================================================")
        print(
            f"v3.0 FM Ready: {summary['v3_ready_count']} | "
            f"Legacy Notion FM: {summary['legacy_notion_count']} | "
            f"220. 산업분석 Series: {summary['industry_series_count']}"
        )
        print("------------------------------------------------------------")
        for idx, n in enumerate(notes_info, start=1):
            status_tag = "v3-Ready" if n["v3_ready"] else ("Legacy-Notion" if n["legacy_notion_keys"] else "Needs-FM")
            print(f"{idx:2d}. [{status_tag:<13}] [{n['series_hint']:<14}] {n['filename']}")
        print("============================================================")
    return 0


# ---------------------------------------------------------------------------
# Subcommand 2: normalize-fm (Step 1)
# ---------------------------------------------------------------------------
def _parse_replace_up_args(replace_arg: Any) -> Optional[Tuple[str, str]]:
    """Parse --replace-up argument which can be ['OLD', 'NEW'] or ['OLD->NEW'] or 'OLD->NEW'."""
    if not replace_arg:
        return None
    if isinstance(replace_arg, (list, tuple)):
        if len(replace_arg) == 2:
            return str(replace_arg[0]).strip(), str(replace_arg[1]).strip()
        elif len(replace_arg) == 1 and "->" in str(replace_arg[0]):
            parts = str(replace_arg[0]).split("->", 1)
            return parts[0].strip(), parts[1].strip()
    elif isinstance(replace_arg, str) and "->" in replace_arg:
        parts = replace_arg.split("->", 1)
        return parts[0].strip(), parts[1].strip()
    return None


def cmd_normalize_fm(args: argparse.Namespace, vault_path: Path, cfg: ConstitutionConfig) -> int:
    """Step 1: Strip legacy Notion properties and normalize v3.0 2-tier YAML frontmatter."""
    target = Path(args.file)
    if not target.is_absolute() and not target.exists():
        candidate = vault_path / args.file
        if candidate.exists():
            target = candidate
        else:
            inbox_candidate = vault_path / "000. Inbox" / args.file
            if inbox_candidate.exists():
                target = inbox_candidate

    if not target.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1

    raw_text = target.read_text(encoding="utf-8", errors="replace")
    existing_fm, _, body = parse_markdown_frontmatter(raw_text)
    existing_fm = existing_fm or {}

    today = datetime.now().strftime("%Y-%m-%d")

    # Determine 7 core attributes (CLI args override existing FM)
    origin = (args.origin or existing_fm.get("origin") or "human").strip()
    note_type = (args.type or existing_fm.get("type") or "analysis").strip()

    if args.domain:
        raw_dom_args = args.domain if isinstance(args.domain, list) else [args.domain]
        domains = [d.strip() for item in raw_dom_args for d in str(item).split(",") if d.strip()]
    elif "domain" in existing_fm:
        raw_dom = existing_fm["domain"]
        domains = [str(x).strip() for x in raw_dom] if isinstance(raw_dom, list) else [str(raw_dom).strip()]
    else:
        domains = ["macro"]

    if args.up is not None:
        up_links = normalize_wikilink_list(args.up)
    else:
        up_links = normalize_wikilink_list(existing_fm.get("up"))

    replace_pair = _parse_replace_up_args(getattr(args, "replace_up", None))
    if replace_pair:
        old_norm = normalize_wikilink_list(replace_pair[0])
        new_norm = normalize_wikilink_list(replace_pair[1])
        if old_norm and new_norm:
            old_target = old_norm[0]
            new_target = new_norm[0]
            up_links = [new_target if u == old_target else u for u in up_links]

    if getattr(args, "remove_up", None):
        remove_targets = set(normalize_wikilink_list(args.remove_up))
        up_links = [u for u in up_links if u not in remove_targets]

    status = (args.status or existing_fm.get("status") or "active").strip()
    if status not in cfg.allowed_statuses:
        status = "active"

    # Extract legacy Notion date if present for ref_date / created
    legacy_date = existing_fm.get("날짜") or existing_fm.get("생성일")
    created_str = normalize_date_str(
        args.created or existing_fm.get("created") or legacy_date,
        today,
    )
    updated_str = normalize_date_str(args.updated or today, today)

    # Collect Tier 2 sparse extended attributes (preserving non-legacy existing keys)
    extended: Dict[str, Any] = {}
    for k, v in existing_fm.items():
        if k in cfg.core_attributes or k in LEGACY_NOTION_KEYS:
            continue
        extended[k] = v

    if legacy_date and "ref_date" not in extended and not args.ref_date:
        extended["ref_date"] = normalize_date_str(legacy_date)
    if args.ref_date:
        extended["ref_date"] = normalize_date_str(args.ref_date)
    if args.period:
        extended["period"] = args.period.strip()
    if args.summary:
        extended["summary"] = args.summary.strip()
    if args.aliases:
        extended["aliases"] = [a.strip() for a in args.aliases.split(",") if a.strip()]
    if args.stance:
        extended["stance"] = args.stance.strip()
    if args.prev is not None:
        extended["prev"] = normalize_wikilink_list(args.prev)
    if args.source is not None:
        extended["source"] = normalize_wikilink_list(args.source)
    if args.related is not None:
        extended["related"] = normalize_wikilink_list(args.related)
    if args.author is not None:
        extended["author"] = normalize_wikilink_list(args.author)
    if args.org is not None:
        extended["org"] = normalize_wikilink_list(args.org)
    if args.source_url:
        extended["source_url"] = args.source_url.strip()

    new_fm = build_v3_frontmatter(
        origin=origin,
        note_type=note_type,
        domains=domains,
        up_links=up_links,
        status=status,
        created=created_str,
        updated=updated_str,
        extended=extended,
    )

    clean_body = body.lstrip("\r\n")
    new_full_text = f"{new_fm}\n{clean_body}"
    if not new_full_text.endswith("\n"):
        new_full_text += "\n"

    if args.dry_run:
        print(f"[DRY-RUN] Normalized frontmatter for {target.name}:\n{new_fm}")
        return 0

    target.write_text(new_full_text, encoding="utf-8")
    print(f"Normalized v3.0 frontmatter: {target}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand 3: scan-index (Step 2 & Step 4)
# ---------------------------------------------------------------------------
def _parse_index_tables(index_file: Path) -> List[Dict[str, Any]]:
    """Parse markdown table rows from a `500. Index/_인덱스_*.md` file."""
    if not index_file.exists():
        return []
    text = index_file.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    rows: List[Dict[str, Any]] = []
    headers: List[str] = []
    current_section = ""

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            current_section = stripped.lstrip("#").strip()
            headers = []
            continue

        if not stripped.startswith("|"):
            continue

        cells = [c.strip() for c in stripped.strip("|").split("|")]
        # Check if separator row `| :--- | :---: |`
        if all(re.match(r"^:?-{2,}:?$", c.replace(" ", "")) for c in cells if c):
            if i > 0 and lines[i - 1].strip().startswith("|"):
                headers = [
                    c.strip()
                    for c in lines[i - 1].strip().strip("|").split("|")
                ]
            continue

        # Skip header row itself
        if i + 1 < len(lines):
            next_stripped = lines[i + 1].strip()
            if next_stripped.startswith("|"):
                next_cells = [c.strip() for c in next_stripped.strip("|").split("|")]
                if all(re.match(r"^:?-{2,}:?$", c.replace(" ", "")) for c in next_cells if c):
                    continue

        links_in_row = re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", stripped)
        primary_note = links_in_row[0].strip() if links_in_row else ""

        rows.append({
            "index_file": index_file.name,
            "section": current_section,
            "line_number": i + 1,
            "primary_note": primary_note,
            "all_links": links_in_row,
            "headers": headers,
            "cells": cells,
            "raw_row": stripped,
        })
    return rows


def cmd_scan_index(args: argparse.Namespace, vault_path: Path, cfg: ConstitutionConfig) -> int:
    """Step 2 & Step 4: Search `_인덱스_400_Wiki.md` or all `500. Index` partitioned indexes."""
    index_dir = vault_path / "500. Index"
    if not index_dir.exists():
        print(f"Error: 500. Index directory not found at {index_dir}", file=sys.stderr)
        return 1

    if args.scope == "wiki":
        target_files = [index_dir / "_인덱스_400_Wiki.md"]
    elif args.scope == "origins":
        target_files = [
            index_dir / fname
            for fname in cfg.index_files
            if fname != "_인덱스_400_Wiki.md" and (index_dir / fname).exists()
        ]
    else:
        target_files = [
            index_dir / fname
            for fname in cfg.index_files
            if (index_dir / fname).exists()
        ]

    keywords: List[str] = []
    if args.query:
        keywords = [
            k.strip().lower()
            for k in re.split(r"[,;\s]+", args.query)
            if k.strip()
        ]

    domain_filter = args.domain.strip().lower() if args.domain else None

    matched_rows: List[Dict[str, Any]] = []
    for idx_file in target_files:
        for row in _parse_index_tables(idx_file):
            haystack = row["raw_row"].lower()
            if domain_filter and domain_filter not in haystack:
                continue
            if keywords:
                hits = [kw for kw in keywords if kw in haystack]
                if not hits:
                    continue
                row["matched_keywords"] = hits
                row["match_score"] = len(hits)
            else:
                row["matched_keywords"] = []
                row["match_score"] = 1
            matched_rows.append(row)

    matched_rows.sort(key=lambda r: (-r["match_score"], r["index_file"], r["line_number"]))

    if args.format == "json":
        print(json.dumps({
            "scope": args.scope,
            "query": args.query,
            "domain": args.domain,
            "total_matches": len(matched_rows),
            "matches": matched_rows,
        }, indent=2, ensure_ascii=False))
    else:
        print("============================================================")
        print(
            f"  500. Index Scan Results (scope={args.scope}, query={args.query or '*'}, matches={len(matched_rows)})"
        )
        print("============================================================")
        for r in matched_rows:
            note_label = f"[[{r['primary_note']}]]" if r["primary_note"] else "(table row)"
            print(f"- [{r['index_file']}:{r['line_number']}] {note_label}")
            print(f"    {r['raw_row'][:140]}{'...' if len(r['raw_row']) > 140 else ''}")
        print("============================================================")
    return 0


# ---------------------------------------------------------------------------
# Subcommand 4: upsert-index (Step 2, 3, 4)
# ---------------------------------------------------------------------------
def _update_index_frontmatter_date(text: str, today: str) -> str:
    """Update `updated: YYYY-MM-DD` in index file YAML frontmatter."""
    return re.sub(
        r"(?m)^(updated:\s*)\d{4}-\d{2}-\d{2}\s*$",
        f"\\g<1>{today}",
        text,
        count=1,
    )


def cmd_upsert_index(args: argparse.Namespace, vault_path: Path) -> int:
    """Append or update a markdown table row in `500. Index/<index_file>`."""
    index_dir = vault_path / "500. Index"
    idx_path = index_dir / args.index
    if not idx_path.exists():
        print(f"Error: Index file not found: {idx_path}", file=sys.stderr)
        return 1

    text = idx_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    today = datetime.now().strftime("%Y-%m-%d")

    note_clean = args.note.strip().strip("[]")
    note_pattern = re.compile(r"\[\[" + re.escape(note_clean) + r"(?:\|[^\]]+)?\]\]")

    # Case A: Existing row for `--note` found -> update in-place
    found_line_idx = -1
    for i, line in enumerate(lines):
        if line.strip().startswith("|") and note_pattern.search(line):
            found_line_idx = i
            break

    if found_line_idx != -1:
        old_line = lines[found_line_idx]
        cells = [c.strip() for c in old_line.strip().strip("|").split("|")]

        if args.add_up:
            new_up_links = normalize_wikilink_list(args.add_up)
            last_cell = cells[-1]
            for lk in new_up_links:
                if lk not in last_cell:
                    if last_cell in {"-", "", "[]"}:
                        last_cell = f"`{lk}`"
                    else:
                        last_cell = f"{last_cell}<br>`{lk}`"
            cells[-1] = last_cell

        replace_pair = _parse_replace_up_args(getattr(args, "replace_up", None))
        if replace_pair:
            old_norm = normalize_wikilink_list(replace_pair[0])
            new_norm = normalize_wikilink_list(replace_pair[1])
            if old_norm and new_norm:
                old_target = old_norm[0]
                new_target = new_norm[0]
                old_stem = old_target.strip("[]")
                new_stem = new_target.strip("[]")
                for c_idx in range(len(cells)):
                    if old_target in cells[c_idx]:
                        cells[c_idx] = cells[c_idx].replace(old_target, new_target)
                    elif f"`{old_stem}`" in cells[c_idx]:
                        cells[c_idx] = cells[c_idx].replace(f"`{old_stem}`", f"`{new_stem}`")

        if getattr(args, "remove_up", None):
            remove_targets = normalize_wikilink_list(args.remove_up)
            for rt in remove_targets:
                rt_stem = rt.strip("[]")
                for c_idx in range(len(cells)):
                    cell_val = cells[c_idx]
                    if rt in cell_val or rt_stem in cell_val:
                        is_br = bool(re.search(r"<br\s*/?>", cell_val))
                        if is_br:
                            parts = [p.strip() for p in re.split(r"<br\s*/?>", cell_val)]
                            joiner = "<br>"
                        elif "," in cell_val:
                            parts = [p.strip() for p in cell_val.split(",")]
                            joiner = ", "
                        else:
                            parts = [cell_val.strip()]
                            joiner = " "
                        new_parts = [
                            p for p in parts
                            if rt not in p and f"[[{rt_stem}]]" not in p and f"`{rt_stem}`" not in p and p != rt_stem and p != f"`{rt}`"
                        ]
                        cells[c_idx] = joiner.join(new_parts) if new_parts else "-"

        if args.summary:
            if len(cells) >= 2:
                cells[-2] = args.summary.strip()

        if args.row_cells:
            custom_cells = [c.strip() for c in args.row_cells.split("|") if c.strip()]
            if custom_cells:
                cells = custom_cells

        new_line = "| " + " | ".join(cells) + " |"
        lines[found_line_idx] = new_line
        updated_text = _update_index_frontmatter_date("\n".join(lines) + "\n", today)

        if args.dry_run:
            print(f"[DRY-RUN] Would update row at {idx_path.name}:{found_line_idx + 1}:\n  {new_line}")
            return 0

        idx_path.write_text(updated_text, encoding="utf-8")
        print(f"Updated existing row for [[{note_clean}]] in {idx_path.name}:{found_line_idx + 1}")
        return 0

    # Case B: Append new row to target table in `idx_path`
    # Locate the last row of the primary markdown table (or table under `--section`)
    target_table_end = -1
    last_row_num = 0
    in_target_section = args.section is None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") and args.section:
            in_target_section = args.section.lower() in stripped.lower()
            continue

        if in_target_section and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            is_sep = all(re.match(r"^:?-{2,}:?$", c.replace(" ", "")) for c in cells if c)
            if not is_sep:
                if cells and re.match(r"^\d+$", cells[0]):
                    last_row_num = max(last_row_num, int(cells[0]))
            target_table_end = i
        elif in_target_section and target_table_end != -1 and not stripped.startswith("|") and stripped != "":
            if args.section:
                break

    if target_table_end == -1:
        print(f"Error: Could not locate markdown table in {idx_path.name}", file=sys.stderr)
        return 1

    if args.row_cells:
        raw_cells = [c.strip() for c in args.row_cells.strip().strip("|").split("|")]
        if raw_cells and raw_cells[0] == "AUTO_NUM":
            raw_cells[0] = str(last_row_num + 1)
        new_row = "| " + " | ".join(raw_cells) + " |"
    else:
        next_num = last_row_num + 1
        date_col = args.date or today
        meta_col = args.meta or "`analysis`<br>`macro`"
        summary_col = args.summary or "-"
        up_links = normalize_wikilink_list(args.add_up or args.up)
        replace_pair = _parse_replace_up_args(getattr(args, "replace_up", None))
        if replace_pair:
            old_norm = normalize_wikilink_list(replace_pair[0])
            new_norm = normalize_wikilink_list(replace_pair[1])
            if old_norm and new_norm:
                up_links = [new_norm[0] if u == old_norm[0] else u for u in up_links]
        if getattr(args, "remove_up", None):
            remove_targets = set(normalize_wikilink_list(args.remove_up))
            up_links = [u for u in up_links if u not in remove_targets]
        up_col = "<br>".join(f"`{u}`" for u in up_links) if up_links else "-"
        new_row = f"| {next_num} | **[[{note_clean}]]** | {date_col} | {meta_col} | {summary_col} | {up_col} |"

    lines.insert(target_table_end + 1, new_row)
    updated_text = _update_index_frontmatter_date("\n".join(lines) + "\n", today)

    if args.dry_run:
        print(f"[DRY-RUN] Would append row to {idx_path.name} after line {target_table_end + 1}:\n  {new_row}")
        return 0

    idx_path.write_text(updated_text, encoding="utf-8")
    print(f"Appended new row for [[{note_clean}]] in {idx_path.name}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand 5: move-note (Step 3)
# ---------------------------------------------------------------------------
def cmd_move_note(args: argparse.Namespace, vault_path: Path, cfg: Optional[ConstitutionConfig] = None) -> int:
    """Step 3: Move a compiled note from `000. Inbox` to its permanent origin folder."""
    src = Path(args.file)
    if not src.is_absolute() and not src.exists():
        candidate = vault_path / args.file
        if candidate.exists():
            src = candidate
        else:
            inbox_candidate = vault_path / "000. Inbox" / args.file
            if inbox_candidate.exists():
                src = inbox_candidate

    if not src.exists():
        print(f"Error: Source note not found: {args.file}", file=sys.stderr)
        return 1

    text = src.read_text(encoding="utf-8", errors="replace")
    fm, _, _ = parse_markdown_frontmatter(text)
    origin = (args.origin or (fm.get("origin") if fm else None) or "").strip().lower()

    origin_to_folder: Dict[str, str] = {}
    if cfg and cfg.folder_origin_map:
        for folder, org in cfg.folder_origin_map.items():
            if re.match(r"^\d{3}\.", folder) and org not in origin_to_folder:
                origin_to_folder[org] = folder
    origin_to_folder.setdefault("human", "100. Concepts")
    origin_to_folder.setdefault("ai", "200. AI_logs")
    origin_to_folder.setdefault("source", "300. Sources")
    origin_to_folder.setdefault("wiki", "400. Wiki")

    if origin not in origin_to_folder:
        print(
            f"Error: Invalid or missing origin '{origin}'. Must be one of {list(origin_to_folder.keys())}",
            file=sys.stderr,
        )
        return 1

    dest_dir = vault_path / origin_to_folder[origin]
    if args.subfolder:
        dest_dir = dest_dir / args.subfolder.strip().strip("/\\")
    elif origin == "ai" and src.name.startswith("산업분석_C"):
        dest_dir = dest_dir / "220. 산업분석"
    elif origin == "ai" and "3대 조간신문 통합 큐레이팅" in src.name:
        dest_dir = dest_dir / "210. 뉴스 큐레이팅"

    dest_file = dest_dir / src.name

    if args.dry_run:
        print(f"[DRY-RUN] Would move {src} -> {dest_file}")
        return 0

    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest_file))
    print(f"Moved note: {src} -> {dest_file}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand 6: detect-mstep (M-Step 1~5)
# ---------------------------------------------------------------------------
def cmd_detect_mstep(vault_path: Path, cfg: ConstitutionConfig, fmt: str = "text") -> int:
    """M-Step 1~5: Detect bottom-up cluster promotion candidates and lazy upward sync targets."""
    wiki_dir = vault_path / "400. Wiki"
    if not wiki_dir.exists():
        if fmt == "json":
            print(json.dumps({"clusters": [], "lazy_sync_targets": []}, ensure_ascii=False))
        return 0

    wiki_notes: Dict[str, Dict[str, Any]] = {}
    parent_to_children: Dict[str, List[str]] = {}

    for p in sorted(wiki_dir.glob("*.md")):
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        fm, _, _ = parse_markdown_frontmatter(text)
        if not fm:
            continue
        up_list = normalize_wikilink_list(fm.get("up"))
        up_names = [u[2:-2].split("|")[0].strip() for u in up_list if u.startswith("[[") and u.endswith("]]")]
        updated_str = normalize_date_str(fm.get("updated"), "")
        domain_val = fm.get("domain", [])
        domains = [str(d).strip() for d in domain_val] if isinstance(domain_val, list) else [str(domain_val).strip()]

        wiki_notes[p.stem] = {
            "name": p.stem,
            "filename": p.name,
            "updated": updated_str,
            "up": up_names,
            "domains": domains,
            "type": str(fm.get("type", "")),
        }

        for parent in up_names:
            parent_to_children.setdefault(parent, []).append(p.stem)

    # 1. Cluster detection (parent hubs/axes with >= 3 child wikis)
    cluster_candidates: List[Dict[str, Any]] = []
    for parent_name, children in sorted(parent_to_children.items(), key=lambda x: (-len(x[1]), x[0])):
        count = len(children)
        if count >= 3:
            parent_exists_in_wiki = parent_name in wiki_notes
            status_label = (
                "overcrowded_7plus"
                if count >= 7
                else "cluster_ready_3to6"
            )
            cluster_candidates.append({
                "parent_hub": parent_name,
                "parent_exists_in_400_wiki": parent_exists_in_wiki,
                "child_count": count,
                "status": status_label,
                "children": sorted(children),
            })

    # 2. M-Step 5 Lazy Upward Sync detection (`child.updated > parent.updated`)
    lazy_sync_map: Dict[str, Dict[str, Any]] = {}
    for child_name, c_meta in wiki_notes.items():
        c_updated = c_meta["updated"]
        if not c_updated:
            continue
        for parent_name in c_meta["up"]:
            if parent_name in wiki_notes:
                p_updated = wiki_notes[parent_name]["updated"]
                if p_updated and c_updated > p_updated:
                    entry = lazy_sync_map.setdefault(
                        parent_name,
                        {
                            "parent_wiki": parent_name,
                            "parent_updated": p_updated,
                            "newer_children": [],
                        },
                    )
                    entry["newer_children"].append({
                        "child_wiki": child_name,
                        "child_updated": c_updated,
                    })

    lazy_sync_targets = sorted(
        lazy_sync_map.values(),
        key=lambda x: (-len(x["newer_children"]), x["parent_wiki"]),
    )

    result = {
        "total_wiki_notes": len(wiki_notes),
        "cluster_candidates": cluster_candidates,
        "lazy_sync_targets": lazy_sync_targets,
    }

    if fmt == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("============================================================")
        print(f"  M-Step Meta-Compilation & Sync Diagnostics ({len(wiki_notes)} Wikis)")
        print("============================================================")
        print(f"1. Cluster / Roll-up Candidates (>= 3 children): {len(cluster_candidates)}")
        for c in cluster_candidates:
            exists_tag = "Compiled Wiki" if c["parent_exists_in_400_wiki"] else "Uncompiled Virtual Hub"
            print(f"   - [[{c['parent_hub']}]] ({c['child_count']} children, {c['status']}, {exists_tag})")
        print("------------------------------------------------------------")
        print(f"2. M-Step 5 Lazy Upward Sync Targets (child.updated > parent.updated): {len(lazy_sync_targets)}")
        for t in lazy_sync_targets:
            print(
                f"   - [[{t['parent_wiki']}]] (updated {t['parent_updated']}) <- "
                f"{len(t['newer_children'])} newer child wiki(s)"
            )
        print("============================================================")
    return 0


def main() -> int:
    vault_parent = argparse.ArgumentParser(add_help=False)
    vault_parent.add_argument(
        "--vault",
        type=str,
        default=argparse.SUPPRESS,
        help="Path to Obsidian vault root directory (default: ./My-Wiki)",
    )

    parser = argparse.ArgumentParser(
        description="Inbox & Wiki Compilation Helper CLI for My-PKM (My-Wiki Rules v3.0)"
    )
    parser.add_argument(
        "--vault",
        type=str,
        default="./My-Wiki",
        help="Path to Obsidian vault root directory (default: ./My-Wiki)",
    )

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 1. inbox-status
    p_inbox = subparsers.add_parser("inbox-status", parents=[vault_parent], help="Inspect 000. Inbox uncompiled notes queue")
    p_inbox.add_argument("--format", choices=["text", "json"], default="text")

    # 2. normalize-fm
    p_norm = subparsers.add_parser("normalize-fm", parents=[vault_parent], help="Step 1: Normalize note YAML frontmatter to v3.0")
    p_norm.add_argument("--file", required=True, help="Target markdown file path or filename in 000. Inbox")
    p_norm.add_argument("--origin", choices=["human", "ai", "source", "wiki"], default=None)
    p_norm.add_argument("--type", choices=["hub", "concept", "analysis", "entity", "source", "project", "log"], default=None)
    p_norm.add_argument("--domain", nargs="+", type=str, default=None, help="Comma or space-separated domains (max 2)")
    p_norm.add_argument("--up", nargs="*", type=str, default=None, help="Comma or space-separated parent wikilinks")
    p_norm.add_argument("--status", type=str, default=None, help="Note status (active, completed, archived)")
    p_norm.add_argument("--created", type=str, default=None, help="Created date YYYY-MM-DD")
    p_norm.add_argument("--updated", type=str, default=None, help="Updated date YYYY-MM-DD")
    p_norm.add_argument("--ref-date", type=str, default=None, help="Content reference date YYYY-MM-DD")
    p_norm.add_argument("--period", type=str, default=None, help="Target period (e.g. 2026-Q4)")
    p_norm.add_argument("--summary", type=str, default=None, help="1-line summary")
    p_norm.add_argument("--aliases", type=str, default=None, help="Comma-separated aliases")
    p_norm.add_argument("--stance", type=str, default=None, help="Stance (bullish, bearish, neutral)")
    p_norm.add_argument("--prev", type=str, default=None, help="Previous note wikilinks")
    p_norm.add_argument("--source", type=str, default=None, help="Source note wikilinks")
    p_norm.add_argument("--related", type=str, default=None, help="Related note wikilinks")
    p_norm.add_argument("--author", type=str, default=None, help="Author entity wikilinks")
    p_norm.add_argument("--org", type=str, default=None, help="Organization entity wikilinks")
    p_norm.add_argument("--source-url", type=str, default=None, help="External/Drive viewer URL")
    p_norm.add_argument("--remove-up", nargs="+", default=None, help="Remove one or more wikilinks from note up array")
    p_norm.add_argument("--replace-up", nargs="+", metavar="LINK", default=None, help="Replace OLD with NEW wikilink in note up array (pass 'OLD NEW' or 'OLD->NEW')")
    p_norm.add_argument("--dry-run", action="store_true", help="Preview frontmatter without writing")

    # 3. scan-index
    p_scan = subparsers.add_parser("scan-index", parents=[vault_parent], help="Step 2 & Step 4: Scan 500. Index tables")
    p_scan.add_argument("--scope", choices=["wiki", "origins", "all"], default="all")
    p_scan.add_argument("--query", type=str, default=None, help="Keywords to match in index rows")
    p_scan.add_argument("--domain", type=str, default=None, help="Filter by domain code")
    p_scan.add_argument("--format", choices=["text", "json"], default="text")

    # 4. upsert-index
    p_upsert = subparsers.add_parser("upsert-index", parents=[vault_parent], help="Step 2/3/4: Upsert row in 500. Index markdown table")
    p_upsert.add_argument("--index", "--index-file", dest="index", required=True, help="Index filename inside 500. Index (e.g. _인덱스_100_Concepts.md)")
    p_upsert.add_argument("--note", required=True, help="Target note title (without .md)")
    p_upsert.add_argument("--date", type=str, default=None, help="Date column text")
    p_upsert.add_argument("--meta", type=str, default=None, help="Type/Domain or SourceType/Author column text")
    p_upsert.add_argument("--summary", type=str, default=None, help="Summary & keywords column text")
    p_upsert.add_argument("--up", type=str, default=None, help="Comma-separated `up` wikilinks for new row")
    p_upsert.add_argument("--add-up", type=str, default=None, help="Add `[[Wiki]]` to existing row's `up` column (Step 4)")
    p_upsert.add_argument("--remove-up", nargs="+", default=None, help="Remove wikilink(s) from row up column")
    p_upsert.add_argument("--replace-up", nargs="+", metavar="LINK", default=None, help="Replace OLD with NEW in row up column (pass 'OLD NEW' or 'OLD->NEW')")
    p_upsert.add_argument("--row-cells", type=str, default=None, help="Explicit pipe-separated row cells (use AUTO_NUM for #)")
    p_upsert.add_argument("--section", type=str, default=None, help="Target section heading substring")
    p_upsert.add_argument("--dry-run", action="store_true", help="Preview table row change without writing")

    # 5. move-note
    p_move = subparsers.add_parser("move-note", parents=[vault_parent], help="Step 3: Move compiled note from 000. Inbox to origin folder")
    p_move.add_argument("--file", required=True, help="Source note path or filename in 000. Inbox")
    p_move.add_argument("--origin", choices=["human", "ai", "source", "wiki"], default=None)
    p_move.add_argument("--subfolder", "--target-folder", dest="subfolder", type=str, default=None, help="Optional subfolder (e.g. 220. 산업분석)")
    p_move.add_argument("--dry-run", action="store_true", help="Preview move without modifying disk")

    # 6. detect-mstep
    p_mstep = subparsers.add_parser("detect-mstep", parents=[vault_parent], help="M-Step 1~5: Detect cluster promotion & lazy sync targets")
    p_mstep.add_argument("--format", choices=["text", "json"], default="text")

    args = parser.parse_args()
    vault_path = Path(args.vault).resolve()
    cfg = load_constitution(vault_path)

    if args.subcommand == "inbox-status":
        return cmd_inbox_status(vault_path, cfg, fmt=args.format)
    if args.subcommand == "normalize-fm":
        return cmd_normalize_fm(args, vault_path, cfg)
    if args.subcommand == "scan-index":
        return cmd_scan_index(args, vault_path, cfg)
    if args.subcommand == "upsert-index":
        return cmd_upsert_index(args, vault_path)
    if args.subcommand == "move-note":
        return cmd_move_note(args, vault_path, cfg)
    if args.subcommand == "detect-mstep":
        return cmd_detect_mstep(vault_path, cfg, fmt=args.format)

    return 0


if __name__ == "__main__":
    sys.exit(main())
