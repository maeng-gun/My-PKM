#!/usr/bin/env python
"""Step 1: Vault Subgraph Explorer CLI for My-PKM Obsidian Canvas (`pkm-canvas`).

High-speed scanner that indexes `./My-Wiki/400. Wiki` and `500. Index` registries,
extracting a focused 2-Hop core wiki subgraph (`Lv4 ➔ Lv3 ➔ Lv2 ➔ Lv1` upward
direct lineage from seeds + strict hub damping) and conditional 1-Hop source leaf
notes (`100. Concepts`, `200. AI_logs`, `300. Sources`) via lazy on-demand disk reads.

Also extracts safe `#subpath` markdown headings (prioritizing clean text headings
free of `[[wikilinks]]` or special characters) and resolves `aliases` / broken links.

Usage:
    python canvas_explorer.py --vault ./My-Wiki --query "AI CAPEX,데이터센터" \
        --output scratch/canvas/subgraph_ai_capex.json
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple
import yaml

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


EXCLUDED_DIRS: Set[str] = {
    ".obsidian",
    ".trash",
    "000. Inbox",
    "500. Index",
    "600. etc",
    "500. etc",
    "700. utilize",
    "900. config",
    "Notion",
}

WIKI_FOLDER = "400. Wiki"
SOURCE_ROOT_FOLDERS = ("100. Concepts", "200. AI_logs", "300. Sources")


@dataclass
class NoteNode:
    title: str
    rel_path: str
    folder_category: str
    origin: str
    note_type: str
    domains: List[str]
    swimlane: str  # "Lv1", "Lv2", "Lv3", "Lv4", "Source"
    up: List[str]
    related: List[str]
    prev: List[str]
    aliases: List[str]
    inline_links: List[str]
    summary: str
    created: str
    updated: str
    ref_date: str
    sort_date: str
    authority_tier: int  # 1: 100. Concepts, 2: 310. 밸리 AI, 3: 300. Sources, 4: 200/210/220
    clean_headings: List[str] = field(default_factory=list)
    all_headings: List[Dict[str, Any]] = field(default_factory=list)
    default_subpath: str = ""


def resolve_vault_root(vault_arg: Optional[str] = None) -> Path:
    """Dynamically locate the My-Wiki vault root by checking for `My-Wiki Rules.md`."""
    candidates: List[Path] = []
    if vault_arg:
        p = Path(vault_arg).resolve()
        candidates.extend([p, p / "My-Wiki"])

    cwd = Path.cwd().resolve()
    candidates.extend([cwd, cwd / "My-Wiki"])
    for parent in cwd.parents:
        candidates.append(parent)
        candidates.append(parent / "My-Wiki")

    script_dir = Path(__file__).resolve().parent
    for parent in script_dir.parents:
        candidates.append(parent)
        candidates.append(parent / "My-Wiki")

    seen: Set[str] = set()
    for cand in candidates:
        key = str(cand)
        if key in seen:
            continue
        seen.add(key)
        if cand.is_dir() and (cand / "My-Wiki Rules.md").is_file():
            return cand

    raise FileNotFoundError(
        "Could not locate 'My-Wiki Rules.md' in any candidate vault directory. "
        "Please pass --vault <path-to-My-Wiki>."
    )


def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter and return (frontmatter_dict, body_text)."""
    if text.startswith("\\---"):
        text = text[1:]
    match = re.match(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)(.*)$", text, re.DOTALL)
    if not match:
        return {}, text
    fm_raw, body = match.group(1), match.group(2)
    try:
        data = yaml.safe_load(fm_raw)
        if isinstance(data, dict):
            return data, body
    except Exception:
        pass
    return {}, body


def extract_wikilink_targets(raw_val: Any, self_title: str = "") -> List[str]:
    """Extract target note titles from frontmatter link arrays (`up`, `related`, `prev`)."""
    if not raw_val:
        return []
    if isinstance(raw_val, list):
        items = [str(x) for x in raw_val if x is not None]
    else:
        s = str(raw_val).strip()
        if s in {"[]", "[[]]", '""', "''", "null", "None"}:
            return []
        items = [p.strip() for p in re.split(r",(?![^\[]*\]\])", s) if p.strip()]

    targets: List[str] = []
    for item in items:
        clean = item.strip().strip("'\"")
        if not clean or clean in {"[]", "[[]]"}:
            continue
        m = re.search(r"\[\[([^\]]+)\]\]", clean)
        inner = m.group(1).strip() if m else clean.strip("[]").strip()
        if not inner:
            continue
        inner = inner.split("|")[0].split("#")[0].strip()
        if not inner or inner.startswith("_인덱스_") or inner == self_title:
            continue
        if inner not in targets:
            targets.append(inner)
    return targets


def extract_inline_wikilinks(body: str, self_title: str = "") -> List[str]:
    """Extract inline `[[Target]]` wikilink targets from markdown body."""
    body_no_code = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    targets: List[str] = []
    for m in re.finditer(r"(?<!!)\[\[([^\]]+)\]\]", body_no_code):
        inner = m.group(1).strip()
        target = inner.split("|")[0].split("#")[0].strip()
        if not target or target.startswith("_인덱스_") or target == self_title:
            continue
        if target not in targets:
            targets.append(target)
    return targets


def extract_safe_headings(body: str) -> Tuple[List[str], List[Dict[str, Any]], str]:
    """Extract headings from markdown body and classify clean headings for `#subpath`.

    Obsidian JSON Canvas `#subpath` works best when the heading does not contain
    nested `[[wikilinks]]`, pipe characters `|`, or markdown link syntax.
    """
    body_no_code = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    all_headings: List[Dict[str, Any]] = []
    clean_h2: List[str] = []
    clean_h3: List[str] = []
    fallback_h2: List[str] = []
    fallback_any: List[str] = []

    for line in body_no_code.splitlines():
        m = re.match(r"^(#{1,3})\s+(.+?)\s*$", line)
        if not m:
            continue
        lvl = len(m.group(1))
        raw_text = m.group(2).strip()
        if not raw_text:
            continue

        has_unsafe_chars = bool(re.search(r"(\[\[|\]\]|\||`|<|>|\*\*)", raw_text))
        is_clean = not has_unsafe_chars
        subpath = f"#{raw_text}"

        if lvl in (2, 3):
            all_headings.append(
                {
                    "level": lvl,
                    "text": raw_text,
                    "subpath": subpath,
                    "is_clean": is_clean,
                }
            )

        if lvl == 2:
            if is_clean:
                clean_h2.append(subpath)
            else:
                fallback_h2.append(subpath)
        elif lvl == 3:
            if is_clean:
                clean_h3.append(subpath)
            else:
                fallback_any.append(subpath)
        elif lvl == 1:
            if is_clean:
                fallback_any.insert(0, subpath)

    clean_headings = clean_h2 + clean_h3
    if clean_h2:
        default_subpath = clean_h2[0]
    elif clean_h3:
        default_subpath = clean_h3[0]
    elif fallback_h2:
        default_subpath = fallback_h2[0]
    elif fallback_any:
        default_subpath = fallback_any[0]
    else:
        default_subpath = ""

    return clean_headings, all_headings, default_subpath


def infer_swimlane_level(title: str, rel_parts: Tuple[str, ...], fm: Dict[str, Any]) -> str:
    """Infer the hierarchical swimlane (`Lv1` ~ `Lv4` or `Source`) of a note."""
    top_folder = rel_parts[0] if rel_parts else ""
    if top_folder != WIKI_FOLDER:
        return "Source"

    if re.match(r"^([TMCP]\d+_|0[1-7]_)", title) or title == "My-Wiki Rules":
        return "Lv1"
    if re.match(r"^[TMCP]\d+-S\d+[A-Z]?_", title):
        return "Lv2"
    if re.match(r"^(산업_|도서_|인물_)", title):
        return "Lv3"
    if re.match(r"^(19\d0년대|20\d0년대).*_", title):
        return "Lv3"
    if re.match(r"^기업_", title):
        return "Lv4"

    raw_level = fm.get("level")
    if raw_level is not None:
        s_lvl = str(raw_level).strip().upper()
        if s_lvl in {"1", "LV1", "LEVEL 1", "LEVEL1"}:
            return "Lv1"
        if s_lvl in {"2", "LV2", "LEVEL 2", "LEVEL2"}:
            return "Lv2"
        if s_lvl in {"3", "LV3", "LEVEL 3", "LEVEL3"}:
            return "Lv3"
        if s_lvl in {"4", "LV4", "LEVEL 4", "LEVEL4"}:
            return "Lv4"

    return "Lv4"


def normalize_date(val: Any, fallback: str = "1970-01-01") -> str:
    if not val:
        return fallback
    s = str(val).strip()
    m = re.match(r"^(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})", s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return fallback


def extract_summary_or_excerpt(fm: Dict[str, Any], body: str) -> str:
    """Extract frontmatter `summary` or a clean 2-3 sentence excerpt from the body."""
    raw_sum = fm.get("summary")
    if raw_sum and str(raw_sum).strip():
        return str(raw_sum).strip()[:350]

    body_no_code = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    lines: List[str] = []
    for line in body_no_code.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("---") or s.startswith("|"):
            continue
        s = re.sub(r"^[-*>+\s]+", "", s).strip()
        if len(s) >= 10:
            lines.append(s)
        if len(" ".join(lines)) >= 260 or len(lines) >= 3:
            break
    return " / ".join(lines)[:320]


def determine_authority_tier(rel_parts: Tuple[str, ...]) -> int:
    """Return Constitutional Authority Hierarchy tier (1 is highest)."""
    if not rel_parts:
        return 4
    top = rel_parts[0]
    sub = rel_parts[1] if len(rel_parts) > 1 else ""
    if top == "100. Concepts":
        return 1  # Primary Stance (Human Sovereignty)
    if top == "300. Sources" and "310" in sub:
        return 2  # Tier-1 Anchor Ground Truth (Valley AI)
    if top == "300. Sources":
        return 3  # Standard Ground Truth
    return 4  # 200. AI_logs / 210 / 220


class VaultGraph:
    """High-speed in-memory index of `My-Wiki` with lazy loading for `100/200/300` source files."""

    def __init__(self, vault_root: Path):
        self.vault_root = vault_root
        self.nodes: Dict[str, NoteNode] = {}
        self.alias_map: Dict[str, str] = {}  # lower(alias_or_title) -> canonical title
        self.children_map: Dict[str, List[str]] = {}  # parent_title -> [child_titles]
        self.inbound_links: Dict[str, List[str]] = {}  # target_title -> [source_titles]
        self.source_path_map: Dict[str, Path] = {}  # stem -> Path (for 100/200/300 files)
        self.source_up_index: Dict[str, List[str]] = {}  # wiki_title -> [source_stems from 500. Index]

    def load(self) -> None:
        # 1. Eagerly parse all `400. Wiki` markdown files (Core knowledge graph)
        wiki_dir = self.vault_root / WIKI_FOLDER
        if wiki_dir.is_dir():
            for entry in os.scandir(wiki_dir):
                if entry.is_file() and entry.name.endswith(".md"):
                    self._index_file(Path(entry.path))

        # 2. Fast-scan filenames in `100. Concepts`, `200. AI_logs`, `300. Sources` without reading file contents yet
        for src_folder in SOURCE_ROOT_FOLDERS:
            base_dir = self.vault_root / src_folder
            if not base_dir.is_dir():
                continue
            for root, dirs, files in os.walk(base_dir):
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
                root_p = Path(root)
                for fname in files:
                    if fname.endswith(".md"):
                        stem = fname[:-3]
                        self.source_path_map[stem] = root_p / fname
                        self.alias_map.setdefault(stem.lower(), stem)

        # 3. Fast-scan `500. Index/_인덱스_100/200/300/210/220/310.md` to map source -> wiki `up` relationships
        self._scan_partitioned_source_indexes()
        self._build_reverse_edges()

    def _scan_partitioned_source_indexes(self) -> None:
        index_dir = self.vault_root / "500. Index"
        if not index_dir.is_dir():
            return
        index_files = [
            "_인덱스_100_Concepts.md",
            "_인덱스_200_AI_logs.md",
            "_인덱스_300_Sources.md",
            "_인덱스_310_밸리AI리포트.md",
            "_인덱스_210_뉴스큐레이팅.md",
            "_인덱스_220_산업분석.md",
        ]
        for idx_name in index_files:
            idx_path = index_dir / idx_name
            if not idx_path.is_file():
                continue
            try:
                content = idx_path.read_text(encoding="utf-8")
            except Exception:
                continue
            for line in content.splitlines():
                if not line.startswith("|"):
                    continue
                links = [
                    m.group(1).split("|")[0].split("#")[0].strip()
                    for m in re.finditer(r"\[\[([^\]]+)\]\]", line)
                ]
                if len(links) < 2:
                    continue
                # First link in a table row is typically the source note title; subsequent links are `up` wikis
                src_candidates = [lk for lk in links if lk in self.source_path_map]
                wiki_candidates = [lk for lk in links if lk in self.nodes]
                for sc in src_candidates:
                    for wc in wiki_candidates:
                        lst = self.source_up_index.setdefault(wc, [])
                        if sc not in lst:
                            lst.append(sc)

    def ensure_source_loaded(self, title_or_alias: str) -> Optional[NoteNode]:
        """Lazily load and parse a `100/200/300` source markdown file on demand."""
        clean = title_or_alias.strip().strip("[]").split("|")[0].split("#")[0].strip()
        if clean in self.nodes:
            return self.nodes[clean]
        resolved = self.alias_map.get(clean.lower(), clean)
        if resolved in self.nodes:
            return self.nodes[resolved]
        if resolved in self.source_path_map:
            self._index_file(self.source_path_map[resolved])
            return self.nodes.get(resolved)
        return None

    def _index_file(self, fpath: Path) -> None:
        try:
            text = fpath.read_text(encoding="utf-8")
        except Exception:
            return

        title = fpath.stem
        rel_path = fpath.relative_to(self.vault_root).as_posix()
        rel_parts = fpath.relative_to(self.vault_root).parts
        folder_category = rel_parts[1] if len(rel_parts) > 2 else rel_parts[0]

        fm, body = parse_frontmatter(text)
        origin = str(fm.get("origin", "")).strip() or (
            "wiki" if rel_parts[0] == WIKI_FOLDER else "source"
        )
        note_type = str(fm.get("type", "concept")).strip()

        raw_domain = fm.get("domain", [])
        if isinstance(raw_domain, list):
            domains = [str(d).strip() for d in raw_domain if d]
        elif raw_domain:
            domains = [str(raw_domain).strip()]
        else:
            domains = []

        swimlane = infer_swimlane_level(title, rel_parts, fm)
        up = extract_wikilink_targets(fm.get("up"), self_title=title)
        related = extract_wikilink_targets(fm.get("related"), self_title=title)
        prev = extract_wikilink_targets(fm.get("prev"), self_title=title)

        raw_aliases = fm.get("aliases", [])
        aliases: List[str] = []
        if isinstance(raw_aliases, list):
            aliases = [str(a).strip() for a in raw_aliases if a and str(a).strip()]
        elif isinstance(raw_aliases, str) and raw_aliases.strip():
            aliases = [raw_aliases.strip()]

        inline_links = extract_inline_wikilinks(body, self_title=title)
        clean_headings, all_headings, default_subpath = extract_safe_headings(body)
        summary = extract_summary_or_excerpt(fm, body)

        created = normalize_date(fm.get("created"))
        updated = normalize_date(fm.get("updated"), fallback=created)
        ref_date = normalize_date(fm.get("ref_date"), fallback="")
        sort_date = ref_date if ref_date and ref_date != "1970-01-01" else updated

        node = NoteNode(
            title=title,
            rel_path=rel_path,
            folder_category=folder_category,
            origin=origin,
            note_type=note_type,
            domains=domains,
            swimlane=swimlane,
            up=up,
            related=related,
            prev=prev,
            aliases=aliases,
            inline_links=inline_links,
            summary=summary,
            created=created,
            updated=updated,
            ref_date=ref_date,
            sort_date=sort_date,
            authority_tier=determine_authority_tier(rel_parts),
            clean_headings=clean_headings,
            all_headings=all_headings,
            default_subpath=default_subpath,
        )
        self.nodes[title] = node
        self.alias_map[title.lower()] = title
        for alias in aliases:
            a_low = alias.lower()
            if a_low not in self.alias_map:
                self.alias_map[a_low] = title

    def resolve_title(self, name: str) -> Optional[str]:
        """Resolve a note name or alias to its canonical existing `title` (loading source on demand)."""
        if not name:
            return None
        clean = name.strip().strip("[]").split("|")[0].split("#")[0].strip()
        if clean in self.nodes:
            return clean
        low = clean.lower()
        if low in self.alias_map:
            target = self.alias_map[low]
            if target not in self.nodes and target in self.source_path_map:
                self.ensure_source_loaded(target)
            if target in self.nodes:
                return target
        if clean in self.source_path_map:
            self.ensure_source_loaded(clean)
            if clean in self.nodes:
                return clean
        # Fallback: match standard taxonomy prefix code (e.g., 'C1-S3_...' -> 'C1-S3')
        m_code = re.match(r"^([TMCP]\d+(?:-S\d+[A-Z]?)?)_", clean, re.IGNORECASE)
        if m_code:
            code_low = m_code.group(1).lower()
            if code_low in self.alias_map:
                target = self.alias_map[code_low]
                if target in self.nodes:
                    return target
            for existing_title in self.nodes:
                if existing_title.lower().startswith(code_low + "_"):
                    return existing_title
        return None

    def _build_reverse_edges(self) -> None:
        for title, node in list(self.nodes.items()):
            resolved_up: List[str] = []
            for u in node.up:
                rt = self.alias_map.get(u.lower(), u)
                if rt in self.nodes and rt != title and rt not in resolved_up:
                    resolved_up.append(rt)
                    self.children_map.setdefault(rt, []).append(title)
            node.up = resolved_up

            resolved_rel: List[str] = []
            for r in node.related:
                rt = self.alias_map.get(r.lower(), r)
                if rt in self.nodes and rt != title and rt not in resolved_rel:
                    resolved_rel.append(rt)
            node.related = resolved_rel

            resolved_prev: List[str] = []
            for p in node.prev:
                rt = self.alias_map.get(p.lower(), p)
                if rt in self.nodes and rt != title and rt not in resolved_prev:
                    resolved_prev.append(rt)
            node.prev = resolved_prev


def score_wiki_for_query(node: NoteNode, keywords: List[str]) -> float:
    """Compute relevance score of a `400. Wiki` node against query keywords."""
    if not keywords:
        return 0.0
    score = 0.0
    matched_kw_count = 0
    title_low = node.title.lower()
    aliases_low = " ".join(node.aliases).lower()
    summary_low = node.summary.lower()
    headings_low = " ".join(node.clean_headings).lower()

    for kw in keywords:
        kw_low = kw.lower().strip()
        if not kw_low:
            continue
        kw_matched = False
        if title_low == kw_low:
            score += 120.0
            kw_matched = True
        elif kw_low in title_low:
            score += 55.0
            kw_matched = True

        if any(a.lower() == kw_low for a in node.aliases):
            score += 60.0
            kw_matched = True
        elif kw_low in aliases_low:
            score += 35.0
            kw_matched = True

        if kw_low in summary_low:
            score += 18.0
            kw_matched = True

        if kw_low in headings_low:
            score += 10.0
            kw_matched = True

        if kw_matched:
            matched_kw_count += 1

    if matched_kw_count > 1:
        score += matched_kw_count * 30.0

    # Prefer concrete Lv4 / Lv3 wikis as primary seeds so Lv1/Lv2 hubs act purely as damped lineage ancestors
    if score > 0:
        if node.swimlane == "Lv4":
            score += 20.0
        elif node.swimlane == "Lv3":
            score += 15.0
        elif node.swimlane == "Lv2":
            score += 2.0

    return score


def explore_subgraph(
    graph: VaultGraph,
    keywords: List[str],
    explicit_seeds: List[str],
    max_seeds: int = 5,
    max_children_per_seed: int = 5,
    include_sources: bool = False,
    max_sources: int = 5,
) -> Dict[str, Any]:
    """Execute 2-Hop hierarchy-controlled subgraph exploration with strict hub damping."""
    seed_titles: List[str] = []

    # 1. Resolve explicit seeds first
    for s in explicit_seeds:
        rt = graph.resolve_title(s)
        if rt and rt not in seed_titles:
            seed_titles.append(rt)

    # 2. Score `400. Wiki` nodes by query keywords
    scored_wikis: List[Tuple[float, str]] = []
    for title, node in graph.nodes.items():
        if node.swimlane == "Source":
            continue
        sc = score_wiki_for_query(node, keywords)
        if sc > 0:
            scored_wikis.append((sc, title))

    scored_wikis.sort(key=lambda x: (-x[0], graph.nodes[x[1]].sort_date), reverse=False)

    # If we already have strong Lv3/Lv4 seeds, avoid picking broad Lv1/Lv2 pillars as seeds
    # unless explicitly matched in title or no Lv3/Lv4 seeds exist.
    concrete_candidates = [
        (sc, t)
        for sc, t in scored_wikis
        if graph.nodes[t].swimlane in {"Lv3", "Lv4"}
        or any(kw.lower() in t.lower() for kw in keywords if len(kw) >= 2)
    ]
    pool = concrete_candidates if concrete_candidates else scored_wikis

    for sc, title in pool:
        if len(seed_titles) >= max_seeds:
            break
        if title not in seed_titles:
            seed_titles.append(title)

    # Fallback token split if still empty
    if not seed_titles and keywords:
        tokens = [
            t
            for kw in keywords
            for t in re.split(r"[\s·/()_-]+", kw)
            if len(t) >= 2
        ]
        if tokens:
            for title, node in graph.nodes.items():
                if node.swimlane == "Source":
                    continue
                sc = score_wiki_for_query(node, tokens)
                if sc > 0:
                    scored_wikis.append((sc, title))
            scored_wikis.sort(key=lambda x: -x[0])
            for _, title in scored_wikis[:max_seeds]:
                if title not in seed_titles:
                    seed_titles.append(title)

    selected_wiki_roles: Dict[str, str] = {}  # title -> "seed" | "lineage_ancestor" | "core_wiki"
    candidate_edges: List[Dict[str, str]] = []
    edge_keys: Set[Tuple[str, str, str]] = set()

    def add_edge(from_t: str, to_t: str, rel_type: str) -> None:
        if from_t == to_t:
            return
        key = (from_t, to_t, rel_type)
        if key not in edge_keys:
            edge_keys.add(key)
            candidate_edges.append(
                {"from_title": from_t, "to_title": to_t, "relation_type": rel_type}
            )

    for st in seed_titles:
        selected_wiki_roles[st] = "seed"

    # 3. Direct 1-Hop Downward & Horizontal expansion from Seeds ONLY (Strict Hub Damping)
    for st in seed_titles:
        seed_node = graph.nodes[st]

        # 3a. 1-Hop Wiki Children (only if seed is not a broad Lv1 hub, or if Lv1 is the sole seed)
        if seed_node.swimlane != "Lv1" or len(seed_titles) == 1:
            wiki_children = [
                ch
                for ch in graph.children_map.get(st, [])
                if graph.nodes[ch].swimlane != "Source"
            ]
            wiki_children.sort(
                key=lambda c: (
                    score_wiki_for_query(graph.nodes[c], keywords),
                    graph.nodes[c].sort_date,
                ),
                reverse=True,
            )
            for ch in wiki_children[:max_children_per_seed]:
                if ch not in selected_wiki_roles:
                    selected_wiki_roles[ch] = "core_wiki"
                add_edge(st, ch, "hierarchy")

        # 3b. Portfolio (`P#-S#`) Strategy Pull: inline wikilinks from portfolio playbook to T/M/C wikis
        if "portfolio" in seed_node.domains or re.match(r"^P\d+", st):
            pulled = [
                graph.alias_map.get(il.lower(), il)
                for il in seed_node.inline_links
            ]
            pulled = [
                p
                for p in pulled
                if p in graph.nodes and graph.nodes[p].swimlane in {"Lv3", "Lv4", "Lv2"}
            ]
            pulled.sort(
                key=lambda c: (
                    score_wiki_for_query(graph.nodes[c], keywords),
                    graph.nodes[c].sort_date,
                ),
                reverse=True,
            )
            for p_title in pulled[:max_children_per_seed]:
                if p_title not in selected_wiki_roles:
                    selected_wiki_roles[p_title] = "core_wiki"
                add_edge(st, p_title, "strategy_pull")

        # 3c. Horizontal `related` and `prev` on seeds
        for rel_t in seed_node.related:
            if rel_t in graph.nodes and graph.nodes[rel_t].swimlane != "Source":
                if rel_t not in selected_wiki_roles:
                    selected_wiki_roles[rel_t] = "core_wiki"
                add_edge(st, rel_t, "related")

        for prev_t in seed_node.prev:
            if prev_t in graph.nodes and graph.nodes[prev_t].swimlane != "Source":
                if prev_t not in selected_wiki_roles:
                    selected_wiki_roles[prev_t] = "core_wiki"
                add_edge(prev_t, st, "prev")

    # 4. Upward Direct Lineage Trace (`Lv4 ➔ Lv3 ➔ Lv2 ➔ Lv1`) strictly from Seeds
    #    (Prevents 1-Hop peripheral `core_wiki` nodes from dragging in unrelated domain trees)
    trace_queue = list(seed_titles)
    visited_up: Set[str] = set()
    while trace_queue:
        curr = trace_queue.pop(0)
        if curr in visited_up or curr not in graph.nodes:
            continue
        visited_up.add(curr)
        curr_node = graph.nodes[curr]
        for parent_t in curr_node.up:
            if parent_t not in graph.nodes:
                continue
            parent_node = graph.nodes[parent_t]
            if parent_node.swimlane == "Source":
                continue
            if parent_t not in selected_wiki_roles:
                selected_wiki_roles[parent_t] = "lineage_ancestor"
            add_edge(parent_t, curr, "hierarchy")
            if parent_t not in visited_up:
                trace_queue.append(parent_t)

    # Connect any `core_wiki` nodes to already-selected ancestors or peers
    selected_wiki_set = set(selected_wiki_roles.keys())
    for wt in list(selected_wiki_set):
        wnode = graph.nodes[wt]
        for u in wnode.up:
            if u in selected_wiki_set:
                add_edge(u, wt, "hierarchy")
        for r in wnode.related:
            if r in selected_wiki_set:
                if (r, wt, "related") not in edge_keys:
                    add_edge(wt, r, "related")

    # 5. Conditional 1-Hop Source Dock (`100. Concepts`, `200. AI_logs`, `300. Sources`)
    #    Triggered when `include_sources` is True OR total core wikis < 3
    core_wiki_count = len(selected_wiki_set)
    auto_trigger_sources = include_sources or (core_wiki_count < 3)

    anchor_candidates = [
        wt
        for wt, role in selected_wiki_roles.items()
        if role in {"seed", "core_wiki"}
        and graph.nodes[wt].swimlane in {"Lv4", "Lv3", "Lv2"}
    ]
    if not anchor_candidates:
        anchor_candidates = list(seed_titles)

    source_candidates_map: Dict[str, Tuple[str, str]] = {}  # source_title -> (anchor_wiki, link_reason)
    for wt in anchor_candidates:
        wnode = graph.nodes[wt]
        # 5a. Source notes registered in `500. Index` pointing `up` to `wt`
        for src_stem in graph.source_up_index.get(wt, []):
            if src_stem not in source_candidates_map:
                source_candidates_map[src_stem] = (wt, "up_index")
        # 5b. Source notes cited inline inside `wt`
        for il in wnode.inline_links:
            resolved_src = graph.alias_map.get(il.lower(), il)
            if (
                resolved_src in graph.source_path_map
                and resolved_src not in source_candidates_map
            ):
                source_candidates_map[resolved_src] = (wt, "cited_inline")

    # Lazily load only the candidate source files (cap at 25 to keep I/O instantaneous)
    loaded_source_items: List[Tuple[str, Tuple[str, str]]] = []
    for src_stem, (anchor_wt, reason) in list(source_candidates_map.items())[:25]:
        snode = graph.ensure_source_loaded(src_stem)
        if snode and snode.swimlane == "Source":
            loaded_source_items.append((snode.title, (anchor_wt, reason)))

    # Sort by sort_date DESC, then by (seed anchor priority, Constitutional authority_tier 100 > 310 > 300 > 200)
    loaded_source_items.sort(
        key=lambda x: graph.nodes[x[0]].sort_date,
        reverse=True,
    )
    loaded_source_items.sort(
        key=lambda x: (
            0 if selected_wiki_roles.get(x[1][0]) == "seed" else 1,
            graph.nodes[x[0]].authority_tier,
        )
    )

    selected_sources: List[Dict[str, Any]] = []
    available_sources: List[Dict[str, Any]] = []

    for src_title, (anchor_wt, reason) in loaded_source_items:
        snode = graph.nodes[src_title]
        entry = {
            "title": snode.title,
            "rel_path": snode.rel_path,
            "folder_category": snode.folder_category,
            "origin": snode.origin,
            "authority_tier": snode.authority_tier,
            "swimlane": "Source",
            "role": "source_leaf",
            "anchor_wiki": anchor_wt,
            "link_reason": reason,
            "sort_date": snode.sort_date,
            "summary": snode.summary,
            "clean_headings": snode.clean_headings[:6],
            "default_subpath": snode.default_subpath,
        }
        available_sources.append(entry)
        if auto_trigger_sources and len(selected_sources) < max_sources:
            selected_sources.append(entry)
            add_edge(src_title, anchor_wt, "source")

    swimlane_order = {"Lv1": 1, "Lv2": 2, "Lv3": 3, "Lv4": 4}
    wiki_nodes_out: List[Dict[str, Any]] = []
    for wt, role in sorted(
        selected_wiki_roles.items(),
        key=lambda x: (swimlane_order.get(graph.nodes[x[0]].swimlane, 9), x[0]),
    ):
        wnode = graph.nodes[wt]
        wiki_nodes_out.append(
            {
                "title": wnode.title,
                "rel_path": wnode.rel_path,
                "swimlane": wnode.swimlane,
                "role": role,
                "note_type": wnode.note_type,
                "domains": wnode.domains,
                "aliases": wnode.aliases,
                "up": wnode.up,
                "related": wnode.related,
                "prev": wnode.prev,
                "updated": wnode.updated,
                "summary": wnode.summary,
                "clean_headings": wnode.clean_headings,
                "default_subpath": wnode.default_subpath,
            }
        )

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "vault_root": str(graph.vault_root),
        "query_keywords": keywords,
        "explicit_seeds": explicit_seeds,
        "resolved_seeds": seed_titles,
        "source_inclusion_triggered": auto_trigger_sources,
        "stats": {
            "total_wiki_notes_indexed": len(
                [n for n in graph.nodes.values() if n.swimlane != "Source"]
            ),
            "total_source_files_mapped": len(graph.source_path_map),
            "selected_wiki_count": len(wiki_nodes_out),
            "selected_source_count": len(selected_sources),
            "available_source_count": len(available_sources),
            "candidate_edge_count": len(candidate_edges),
            "by_swimlane": {
                sl: sum(1 for n in wiki_nodes_out if n["swimlane"] == sl)
                for sl in ["Lv1", "Lv2", "Lv3", "Lv4"]
            },
        },
        "wiki_nodes": wiki_nodes_out,
        "selected_source_nodes": selected_sources,
        "available_source_nodes": available_sources[:12],
        "candidate_edges": candidate_edges,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Step 1: Explore My-Wiki subgraph for Obsidian JSON Canvas compilation."
    )
    parser.add_argument(
        "--vault",
        type=str,
        default=None,
        help="Path to My-Wiki vault (auto-detected via My-Wiki Rules.md if omitted).",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="",
        help="Comma-separated search keywords (e.g., 'AI CAPEX,데이터센터 부채').",
    )
    parser.add_argument(
        "--seeds",
        type=str,
        default="",
        help="Comma-separated exact seed note titles or aliases.",
    )
    parser.add_argument(
        "--max-seeds",
        type=int,
        default=5,
        help="Maximum number of seed wikis to select (default: 5).",
    )
    parser.add_argument(
        "--max-children",
        type=int,
        default=5,
        help="Maximum 1-Hop downward children per seed (default: 5).",
    )
    parser.add_argument(
        "--include-sources",
        action="store_true",
        help="Explicitly include top 3~5 source notes (100/200/300) in the Source Dock.",
    )
    parser.add_argument(
        "--max-sources",
        type=int,
        default=5,
        help="Maximum number of source leaf notes to attach (default: 5).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="scratch/canvas/subgraph.json",
        help="Output JSON path (outside vault, default: scratch/canvas/subgraph.json).",
    )

    args = parser.parse_args()
    vault_root = resolve_vault_root(args.vault)

    keywords = [k.strip() for k in args.query.split(",") if k.strip()]
    explicit_seeds = [s.strip() for s in args.seeds.split(",") if s.strip()]

    if not keywords and not explicit_seeds:
        print("Error: Provide at least one of --query or --seeds.", file=sys.stderr)
        return 1

    graph = VaultGraph(vault_root)
    graph.load()

    result = explore_subgraph(
        graph=graph,
        keywords=keywords,
        explicit_seeds=explicit_seeds,
        max_seeds=args.max_seeds,
        max_children_per_seed=args.max_children,
        include_sources=args.include_sources,
        max_sources=args.max_sources,
    )

    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    stats = result["stats"]
    print(f"[Step 1: canvas_explorer] Subgraph extracted successfully.")
    print(f"  - Vault Root       : {vault_root}")
    print(f"  - Resolved Seeds   : {result['resolved_seeds']}")
    print(
        f"  - Core Wiki Nodes  : {stats['selected_wiki_count']} "
        f"(Lv1:{stats['by_swimlane']['Lv1']}, Lv2:{stats['by_swimlane']['Lv2']}, "
        f"Lv3:{stats['by_swimlane']['Lv3']}, Lv4:{stats['by_swimlane']['Lv4']})"
    )
    print(
        f"  - Source Leaf Nodes: {stats['selected_source_count']} selected "
        f"({stats['available_source_count']} available)"
    )
    print(f"  - Candidate Edges  : {stats['candidate_edge_count']}")
    print(f"  - Output File      : {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
