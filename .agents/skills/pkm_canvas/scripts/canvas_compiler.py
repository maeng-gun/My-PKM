#!/usr/bin/env python
"""Step 3: Deterministic Geometric Layout & JSON Canvas 1.0 Compiler (`pkm-canvas`).

Reads `canvas_spec.json` (generated in Step 2), validates all note paths against
`My-Wiki` (filtering broken links and resolving `aliases`), computes zero-overlap
planar swimlane coordinates (`Lv1 ➔ Lv2 ➔ Lv3 ➔ Lv4 ➔ Source Dock` + Subgroup
containers) with permutation-optimized adjacency and collision-free edge/label routing,
preserves manual user nodes (`non-auto-` IDs) into a `User Notes` container,
isolates previous versions into root `.trash` (Trash-First-Then-Write), writes
`My-Wiki/700. utilize/Canvas_<Topic>.canvas`, and updates `_인덱스_700_Utilize.md`.

Usage:
    python canvas_compiler.py --vault ./My-Wiki --spec scratch/canvas/canvas_spec.json
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from canvas_explorer import NoteNode, VaultGraph, resolve_vault_root  # noqa: E402


# Default Card Dimensions & Wide Corridor Spacing Constants (Tunable via CLI)
MASTER_W = 1800
MASTER_H = 340

HUB_W = 400
HUB_H = 280

CORE_W = 420
CORE_H = 360

SOURCE_W = 360
SOURCE_H = 230

GROUP_PAD_X = 60
GROUP_PAD_TOP = 70
GROUP_PAD_BOTTOM = 75
GROUP_GAP_X = 240

# Dedicated vertical corridor between main (Lv3/Lv4) groups and bottom Source Dock
# Ensures Source -> Lv4 midpoint edge labels never overlap the Source Dock border or header tab when zoomed out
SOURCE_DOCK_GAP_Y = 560

# Wide gaps (220px) ensure 12~15 char Korean edge labels (~160px wide) never collide with adjacent cards
DEFAULT_X_GAP = 220
DEFAULT_Y_GAP = 220

SWIMLANE_RANK = {"Lv1": 1, "Lv2": 2, "Lv3": 3, "Lv4": 4, "Source": 5}


def make_auto_id(kind: str, key: str) -> str:
    """Generate a deterministic `auto-` prefixed 12-char ID for JSON Canvas elements."""
    digest = hashlib.sha1(f"{kind}:{key}".encode("utf-8")).hexdigest()[:10]
    return f"auto-{kind}-{digest}"


def sanitize_canvas_filename(raw_name: str, topic: str) -> str:
    """Ensure the output filename follows `Canvas_<주제명>.canvas` without illegal chars."""
    base = raw_name.strip() if raw_name else f"Canvas_{topic.strip()}"
    if base.lower().endswith(".canvas"):
        base = base[:-7]
    if not base.startswith("Canvas_"):
        base = f"Canvas_{base}"
    base = re.sub(r'[\\/:*?"<>|\[\]]+', "_", base)
    base = re.sub(r"\s+", "_", base).strip("._")
    return f"{base}.canvas"


def default_node_color(swimlane: str, role: str, origin: str, folder_cat: str) -> str:
    """Assign JSON Canvas 1.0 standard palette color ('1'..'6') by hierarchy & origin."""
    if swimlane == "Lv1":
        return "6"  # Purple
    if swimlane == "Lv2":
        return "5"  # Cyan
    if swimlane == "Lv3":
        return "4"  # Green
    if swimlane == "Lv4":
        return "1" if role == "seed" else "3"  # Red for seed, Yellow for core Lv4
    if origin == "human" or "100" in folder_cat:
        return "2"  # Orange (Human Sovereignty Primary Stance)
    if "310" in folder_cat or origin == "source":
        return "4"  # Green (Ground Truth)
    return "5"  # Cyan (AI logs)


def default_edge_color(rel_type: str) -> str:
    if rel_type == "hierarchy":
        return "5"  # Cyan
    if rel_type == "strategy_pull":
        return "6"  # Purple
    if rel_type == "related":
        return "3"  # Yellow
    if rel_type == "prev":
        return "2"  # Orange
    if rel_type == "source":
        return "4"  # Green
    return "5"


def resolve_safe_subpath(requested_subpath: str, vault_node: NoteNode) -> str:
    """Verify `#subpath` against actual headings in the markdown file and guard against `[[ ]]` or `**`."""
    req = (requested_subpath or "").strip()
    if req and not req.startswith("#"):
        req = f"#{req}"

    has_unsafe = bool(re.search(r"(\[\[|\]\]|\||`|\*\*)", req))
    if req and not has_unsafe:
        if req in vault_node.clean_headings:
            return req
        req_norm = re.sub(r"\s+", " ", req.lstrip("#")).strip().lower()
        for ch in vault_node.clean_headings:
            ch_norm = re.sub(r"\s+", " ", ch.lstrip("#")).strip().lower()
            if req_norm == ch_norm or req_norm in ch_norm or ch_norm in req_norm:
                return ch

    return vault_node.default_subpath


def validate_and_resolve_spec(
    spec: Dict[str, Any], graph: VaultGraph
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    """Filter out broken/trashed links, resolve aliases to actual files, and sanitize subpaths/labels."""
    raw_nodes = spec.get("nodes", [])
    raw_edges = spec.get("edges", [])

    valid_nodes: List[Dict[str, Any]] = []
    valid_node_ids: Set[str] = set()
    seen_titles: Dict[str, str] = {}
    id_remap: Dict[str, str] = {}
    warnings: List[str] = []

    for n in raw_nodes:
        node_id = str(n.get("node_id", "")).strip()
        raw_title = str(n.get("note_title", "")).strip()
        raw_path = str(n.get("file_path", "")).strip()

        if not node_id:
            continue

        resolved_title = graph.resolve_title(raw_title)
        if not resolved_title and raw_path:
            stem = Path(raw_path).stem
            resolved_title = graph.resolve_title(stem)

        if not resolved_title or resolved_title not in graph.nodes:
            warnings.append(
                f"Skipped broken/missing note: '{raw_title or raw_path}' (node_id={node_id})"
            )
            continue

        vault_node = graph.nodes[resolved_title]
        abs_file = graph.vault_root / vault_node.rel_path
        if not abs_file.is_file():
            warnings.append(
                f"Skipped non-existent file on disk: '{vault_node.rel_path}' (node_id={node_id})"
            )
            continue

        if resolved_title in seen_titles:
            canon_id = seen_titles[resolved_title]
            id_remap[node_id] = canon_id
            warnings.append(
                f"Merged duplicate reference '{raw_title}' -> '{resolved_title}' ({node_id} -> {canon_id})"
            )
            continue

        seen_titles[resolved_title] = node_id
        id_remap[node_id] = node_id
        valid_node_ids.add(node_id)

        swimlane = str(n.get("swimlane", "")).strip()
        if swimlane not in SWIMLANE_RANK:
            swimlane = vault_node.swimlane
        if vault_node.swimlane == "Source":
            swimlane = "Source"
        elif swimlane == "Source":
            swimlane = vault_node.swimlane

        role = str(n.get("role", "core_wiki")).strip()
        subpath = resolve_safe_subpath(str(n.get("subpath", "")), vault_node)
        color = str(n.get("color", "")).strip()
        if color not in {"1", "2", "3", "4", "5", "6"}:
            color = default_node_color(
                swimlane, role, vault_node.origin, vault_node.folder_category
            )

        valid_nodes.append(
            {
                "node_id": node_id,
                "note_title": resolved_title,
                "file_path": vault_node.rel_path,
                "swimlane": swimlane,
                "group_id": n.get("group_id"),
                "role": role,
                "subpath": subpath,
                "color": color,
                "order_in_row": int(n.get("order_in_row", 0)),
                "anchor_node_id": n.get("anchor_node_id"),
            }
        )

    valid_edges: List[Dict[str, Any]] = []
    seen_edges: Set[Tuple[str, str, str]] = set()
    for e in raw_edges:
        u_raw = str(e.get("from_node", "")).strip()
        v_raw = str(e.get("to_node", "")).strip()
        u = id_remap.get(u_raw, u_raw)
        v = id_remap.get(v_raw, v_raw)
        if u not in valid_node_ids or v not in valid_node_ids or u == v:
            continue
        rel_type = str(e.get("relation_type", "hierarchy")).strip()
        if rel_type not in {"hierarchy", "related", "prev", "source", "strategy_pull"}:
            rel_type = "hierarchy"

        # Rule: Omit labels on self-evident vertical `hierarchy` edges (Lv1 -> Lv2 -> Lv3 -> Lv4)
        # to eliminate 1:N fan-out label overlapping and corridor clutter.
        # Keep concise labels (<= 15 chars) only on semantic edges (`related`, `prev`, `strategy_pull`, `source`).
        raw_label = str(e.get("label", "")).strip()
        if rel_type == "hierarchy":
            label = ""
        else:
            label = raw_label[:15]

        color = str(e.get("color", "")).strip()
        if color not in {"1", "2", "3", "4", "5", "6"}:
            color = default_edge_color(rel_type)

        key = (u, v, rel_type)
        if key not in seen_edges:
            seen_edges.add(key)
            valid_edges.append(
                {
                    "from_node": u,
                    "to_node": v,
                    "relation_type": rel_type,
                    "label": label,
                    "color": color,
                }
            )

    return valid_nodes, valid_edges, warnings


def resolve_1d_non_overlapping(
    items: List[Tuple[str, float, int]], gap: int
) -> Dict[str, int]:
    """Place items along 1D X-axis near their desired center X without any overlap."""
    if not items:
        return {}
    sorted_items = sorted(items, key=lambda x: (x[1], x[0]))
    placed: List[List[Any]] = []

    for node_id, center_x, w in sorted_items:
        left_x = int(round(center_x - w / 2.0))
        if placed:
            prev_right = placed[-1][1] + placed[-1][2]
            if left_x < prev_right + gap:
                left_x = prev_right + gap
        placed.append([node_id, left_x, w])

    avg_desired = sum(x[1] for x in sorted_items) / len(sorted_items)
    actual_left = placed[0][1]
    actual_right = placed[-1][1] + placed[-1][2]
    actual_center = (actual_left + actual_right) / 2.0
    shift = int(round(avg_desired - actual_center))

    return {str(p[0]): int(p[1] + shift) for p in placed}


def optimize_group_row_ordering(
    row_nodes: List[Dict[str, Any]],
    related_adj: Dict[str, Set[str]],
    node_by_id: Dict[str, Dict[str, Any]],
    prev_gids: Set[str],
    next_gids: Set[str],
    left_neighbor_rightmost_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Find the optimal left-to-right permutation of nodes in a group row so that:
    1) Intra-group `related` pairs are placed immediately adjacent (`|i - j| == 1`),
    2) Cross-group `related` nodes face the adjacent group boundary (leftmost or rightmost),
       specifically matching the left neighbor group's already-selected rightmost node.
    """
    n = len(row_nodes)
    if n <= 1 or n > 7:
        return row_nodes

    best_perm = tuple(row_nodes)
    best_score = -1e9

    for perm in itertools.permutations(row_nodes):
        score = 0.0
        idx_map = {item["node_id"]: i for i, item in enumerate(perm)}

        # 1. Reward intra-group `related` adjacency, heavily penalize intervening nodes
        for i, item in enumerate(perm):
            nid = item["node_id"]
            for nb in related_adj.get(nid, set()):
                if nb in idx_map:
                    dist = abs(i - idx_map[nb])
                    if dist == 1:
                        score += 120.0
                    else:
                        score -= dist * 80.0

                # 2. Reward placing cross-group `related` nodes on the facing boundary
                elif nb in node_by_id:
                    nb_gid = str(node_by_id[nb].get("group_id", ""))
                    if nb_gid in prev_gids:
                        if i == 0:
                            score += 150.0
                            if left_neighbor_rightmost_id and nb == left_neighbor_rightmost_id:
                                score += 200.0
                        else:
                            score -= i * 60.0
                    elif nb_gid in next_gids:
                        if i == n - 1:
                            score += 150.0
                        else:
                            score -= (n - 1 - i) * 60.0

            # 3. Slight tie-breaker for original `order_in_row`
            score -= abs(i - int(item.get("order_in_row", i))) * 2.0

        if score > best_score:
            best_score = score
            best_perm = perm

    return list(best_perm)


def port_point(box: Dict[str, int], side: str) -> Tuple[float, float]:
    """Return exact (x, y) pixel coordinate of a node's connection port (`top`, `bottom`, `left`, `right`)."""
    if side == "top":
        return (box["x"] + box["w"] / 2.0, float(box["y"]))
    if side == "bottom":
        return (box["x"] + box["w"] / 2.0, float(box["y"] + box["h"]))
    if side == "left":
        return (float(box["x"]), box["y"] + box["h"] / 2.0)
    return (float(box["x"] + box["w"]), box["y"] + box["h"] / 2.0)


def rect_intersects(
    ax: float, ay: float, aw: float, ah: float,
    bx: float, by: float, bw: float, bh: float,
    pad: float = 8.0,
) -> bool:
    """Check if two rectangles intersect (with safety padding `pad`)."""
    return not (
        ax + aw + pad <= bx
        or bx + bw + pad <= ax
        or ay + ah + pad <= by
        or by + bh + pad <= ay
    )


def compute_layout_and_build_canvas(
    spec: Dict[str, Any],
    valid_nodes: List[Dict[str, Any]],
    valid_edges: List[Dict[str, Any]],
    x_gap: int = DEFAULT_X_GAP,
    y_gap: int = DEFAULT_Y_GAP,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Compute top-to-bottom swimlane coordinates and generate collision-free JSON Canvas `nodes` and `edges`."""
    node_by_id: Dict[str, Dict[str, Any]] = {n["node_id"]: n for n in valid_nodes}
    coords: Dict[str, Dict[str, int]] = {}

    lv1_nodes = [n for n in valid_nodes if n["swimlane"] == "Lv1"]
    lv2_nodes = [n for n in valid_nodes if n["swimlane"] == "Lv2"]
    lv3_nodes = [n for n in valid_nodes if n["swimlane"] == "Lv3"]
    lv4_nodes = [n for n in valid_nodes if n["swimlane"] == "Lv4"]
    src_nodes = [n for n in valid_nodes if n["swimlane"] == "Source"]

    lv1_nodes.sort(key=lambda n: (n.get("order_in_row", 0), n["note_title"]))
    lv2_nodes.sort(key=lambda n: (n.get("order_in_row", 0), n["note_title"]))

    # 1. Consolidate Master Briefing + Subgroup Briefings at the very top (Row 0)
    raw_groups = list(spec.get("groups", []))
    raw_groups.sort(key=lambda g: int(g.get("order_x", 0)))
    group_map: Dict[str, Dict[str, Any]] = {
        str(g["group_id"]): dict(g) for g in raw_groups if g.get("group_id")
    }

    default_grp_id = "grp_core_default"
    for n in lv3_nodes + lv4_nodes:
        gid = n.get("group_id")
        if not gid or str(gid) not in group_map:
            if default_grp_id not in group_map:
                group_map[default_grp_id] = {
                    "group_id": default_grp_id,
                    "label": f"📌 {spec.get('topic', '핵심 각론 및 분석 위키')}",
                    "color": "4",
                    "order_x": 999,
                    "briefing": "",
                }
            n["group_id"] = default_grp_id

    ordered_groups = sorted(
        [
            g
            for gid, g in group_map.items()
            if any(n.get("group_id") == gid for n in lv3_nodes + lv4_nodes)
        ],
        key=lambda g: int(g.get("order_x", 0)),
    )

    master_brief = spec.get("master_briefing", {})
    m_title = str(master_brief.get("title", spec.get("topic", "지식 캔버스 마스터 브리핑"))).strip()
    m_lines = [str(line).lstrip("-• ").strip() for line in master_brief.get("summary_lines", []) if str(line).strip()]

    # Standard Obsidian Markdown formatting with # H1 and ### H3 headings.
    # Note: Obsidian Canvas virtualizes (hides) card body text at low zoom levels (.is-zoomed-out),
    # so we also wrap the master briefing in a high-visibility `type: "group"` container whose label
    # remains prominent and crystal-clear at ANY zoom level.
    brief_sections: List[str] = [f"# 🧭 [{m_title}]"]
    for line in m_lines:
        brief_sections.append(f"• {line}")

    grp_brief_lines: List[str] = []
    for g in ordered_groups:
        g_label = str(g.get("label", "")).strip()
        g_brief = str(g.get("briefing", "")).strip()
        if g_brief:
            compact_g_brief = " / ".join(
                s.lstrip("-• ").strip() for s in g_brief.splitlines() if s.strip()
            )
            grp_brief_lines.append(f"• **{g_label}**: {compact_g_brief}")

    if grp_brief_lines:
        brief_sections.append("")
        brief_sections.append("### 📌 [소주제 그룹별 핵심 맥락 요약]")
        brief_sections.extend(grp_brief_lines)

    master_md = "\n".join(brief_sections).strip()
    dynamic_master_h = max(MASTER_H, 120 + len(brief_sections) * 38)
    master_group_h = dynamic_master_h + GROUP_PAD_TOP + 25

    # 2. Compute Vertical Y Coordinates for Swimlanes (Top-to-Bottom)
    curr_y = master_group_h + y_gap

    y_lv1 = curr_y
    if lv1_nodes:
        curr_y += HUB_H + y_gap

    y_lv2 = curr_y
    if lv2_nodes:
        curr_y += HUB_H + y_gap + 60

    has_any_lv3 = len(lv3_nodes) > 0
    has_any_lv4 = len(lv4_nodes) > 0

    y_group_top = curr_y
    y_inner_cursor = y_group_top + GROUP_PAD_TOP

    y_lv3 = y_inner_cursor
    if has_any_lv3:
        y_inner_cursor += CORE_H + (y_gap if has_any_lv4 else 0)

    y_lv4 = y_inner_cursor
    if has_any_lv4:
        y_inner_cursor += CORE_H

    y_group_bottom = (
        y_inner_cursor + GROUP_PAD_BOTTOM
        if ordered_groups
        else y_group_top
    )

    # 3. Optimize horizontal ordering of Lv4 nodes inside each group via permutation scoring
    related_adj: Dict[str, Set[str]] = {}
    for e in valid_edges:
        if e["relation_type"] in {"related", "prev"}:
            u, v = e["from_node"], e["to_node"]
            related_adj.setdefault(u, set()).add(v)
            related_adj.setdefault(v, set()).add(u)

    group_specs: List[Dict[str, Any]] = []
    prev_rightmost_id: Optional[str] = None
    for g_idx, g in enumerate(ordered_groups):
        gid = str(g["group_id"])
        g_lv3 = sorted(
            [n for n in lv3_nodes if n.get("group_id") == gid],
            key=lambda x: (x.get("order_in_row", 0), x["note_title"]),
        )
        g_lv4 = sorted(
            [n for n in lv4_nodes if n.get("group_id") == gid],
            key=lambda x: (x.get("order_in_row", 0), x["note_title"]),
        )

        next_gids = {str(og["group_id"]) for og in ordered_groups[g_idx + 1 :]}
        prev_gids = {str(og["group_id"]) for og in ordered_groups[:g_idx]}
        g_lv4 = optimize_group_row_ordering(
            g_lv4,
            related_adj,
            node_by_id,
            prev_gids,
            next_gids,
            left_neighbor_rightmost_id=prev_rightmost_id,
        )
        if g_lv4:
            prev_rightmost_id = g_lv4[-1]["node_id"]

        w_lv3 = len(g_lv3) * CORE_W + max(0, len(g_lv3) - 1) * x_gap
        w_lv4 = len(g_lv4) * CORE_W + max(0, len(g_lv4) - 1) * x_gap
        inner_w = max(CORE_W, w_lv3, w_lv4)
        outer_w = inner_w + 2 * GROUP_PAD_X
        group_specs.append(
            {
                "meta": g,
                "gid": gid,
                "lv3": g_lv3,
                "lv4": g_lv4,
                "inner_w": inner_w,
                "outer_w": outer_w,
            }
        )

    total_groups_w = (
        sum(gs["outer_w"] for gs in group_specs)
        + max(0, len(group_specs) - 1) * GROUP_GAP_X
    )
    cursor_x = -int(round(total_groups_w / 2.0))

    group_canvas_nodes: List[Dict[str, Any]] = []
    text_canvas_nodes: List[Dict[str, Any]] = []
    file_canvas_nodes: List[Dict[str, Any]] = []

    adj_down: Dict[str, List[str]] = {}
    adj_up: Dict[str, List[str]] = {}
    for e in valid_edges:
        u, v = e["from_node"], e["to_node"]
        u_rank = SWIMLANE_RANK.get(node_by_id[u]["swimlane"], 4)
        v_rank = SWIMLANE_RANK.get(node_by_id[v]["swimlane"], 4)
        if u_rank < v_rank:
            adj_down.setdefault(u, []).append(v)
            adj_up.setdefault(v, []).append(u)
        elif v_rank < u_rank:
            adj_down.setdefault(v, []).append(u)
            adj_up.setdefault(u, []).append(v)

    for gs in group_specs:
        meta = gs["meta"]
        gid = gs["gid"]
        outer_w = gs["outer_w"]
        gx = cursor_x
        gy = y_group_top
        gh = y_group_bottom - y_group_top
        g_center_x = gx + outer_w / 2.0

        g_color = str(meta.get("color", "4")).strip()
        if g_color not in {"1", "2", "3", "4", "5", "6"}:
            g_color = "4"

        group_canvas_nodes.append(
            {
                "id": make_auto_id("group", gid),
                "type": "group",
                "x": int(gx),
                "y": int(gy),
                "width": int(outer_w),
                "height": int(gh),
                "label": str(meta.get("label", gid)),
                "color": g_color,
            }
        )

        g_lv4 = gs["lv4"]
        if g_lv4:
            row_w = len(g_lv4) * CORE_W + max(0, len(g_lv4) - 1) * x_gap
            start_x = int(round(g_center_x - row_w / 2.0))
            for idx, n in enumerate(g_lv4):
                nx = start_x + idx * (CORE_W + x_gap)
                ny = y_lv4
                coords[n["node_id"]] = {
                    "x": nx,
                    "y": ny,
                    "w": CORE_W,
                    "h": CORE_H,
                    "cx": int(nx + CORE_W // 2),
                    "cy": int(ny + CORE_H // 2),
                }

        g_lv3 = gs["lv3"]
        if g_lv3:
            lv2_direct_lv4_cxs: List[int] = []
            for n4 in g_lv4:
                n4_id = n4["node_id"]
                has_lv2_parent = any(
                    node_by_id[p]["swimlane"] == "Lv2" for p in adj_up.get(n4_id, [])
                )
                if has_lv2_parent and n4_id in coords:
                    lv2_direct_lv4_cxs.append(coords[n4_id]["cx"])

            lv3_desired: List[Tuple[str, float, int]] = []
            for idx, n3 in enumerate(g_lv3):
                n3_id = n3["node_id"]
                c_xs = [
                    coords[ch]["cx"]
                    for ch in adj_down.get(n3_id, [])
                    if ch in coords
                ]
                des_cx = sum(c_xs) / len(c_xs) if c_xs else g_center_x
                for corridor_cx in lv2_direct_lv4_cxs:
                    if abs(des_cx - corridor_cx) < CORE_W * 0.45 and len(g_lv4) > 1:
                        if corridor_cx <= g_center_x:
                            des_cx = max(des_cx, corridor_cx + (CORE_W + x_gap) * 0.5)
                        else:
                            des_cx = min(des_cx, corridor_cx - (CORE_W + x_gap) * 0.5)
                lv3_desired.append((n3_id, des_cx, CORE_W))

            lv3_x_map = resolve_1d_non_overlapping(lv3_desired, x_gap)
            for n3 in g_lv3:
                n3_id = n3["node_id"]
                nx = lv3_x_map[n3_id]
                min_gx = gx + GROUP_PAD_X
                max_gx = gx + outer_w - GROUP_PAD_X - CORE_W
                nx = max(min_gx, min(max_gx, nx))
                coords[n3_id] = {
                    "x": nx,
                    "y": y_lv3,
                    "w": CORE_W,
                    "h": CORE_H,
                    "cx": int(nx + CORE_W // 2),
                    "cy": int(y_lv3 + CORE_H // 2),
                }

        cursor_x += outer_w + GROUP_GAP_X

    # 4. Place Lv2 Swimlane aligned to connected Lv3/Lv4 children barycenters
    if lv2_nodes:
        lv2_desired: List[Tuple[str, float, int]] = []
        default_span = max(total_groups_w, len(lv2_nodes) * (HUB_W + x_gap))
        for idx, n in enumerate(lv2_nodes):
            nid = n["node_id"]
            child_xs = [
                coords[ch]["cx"]
                for ch in adj_down.get(nid, [])
                if ch in coords
            ]
            if child_xs:
                des_cx = sum(child_xs) / len(child_xs)
            else:
                des_cx = (
                    -default_span / 2.0
                    + (idx + 0.5) * (default_span / max(1, len(lv2_nodes)))
                )
            lv2_desired.append((nid, des_cx, HUB_W))

        lv2_x_map = resolve_1d_non_overlapping(lv2_desired, x_gap)
        for n in lv2_nodes:
            nid = n["node_id"]
            nx = lv2_x_map[nid]
            coords[nid] = {
                "x": nx,
                "y": y_lv2,
                "w": HUB_W,
                "h": HUB_H,
                "cx": int(nx + HUB_W // 2),
                "cy": int(y_lv2 + HUB_H // 2),
            }

    # 5. Place Lv1 Swimlane aligned to connected Lv2/Lv3/Lv4 children barycenters
    if lv1_nodes:
        lv1_desired: List[Tuple[str, float, int]] = []
        default_span = max(total_groups_w, len(lv1_nodes) * (HUB_W + x_gap))
        for idx, n in enumerate(lv1_nodes):
            nid = n["node_id"]
            child_xs = [
                coords[ch]["cx"]
                for ch in adj_down.get(nid, [])
                if ch in coords
            ]
            if child_xs:
                des_cx = sum(child_xs) / len(child_xs)
            else:
                des_cx = (
                    -default_span / 2.0
                    + (idx + 0.5) * (default_span / max(1, len(lv1_nodes)))
                )
            lv1_desired.append((nid, des_cx, HUB_W))

        lv1_x_map = resolve_1d_non_overlapping(lv1_desired, x_gap)
        for n in lv1_nodes:
            nid = n["node_id"]
            nx = lv1_x_map[nid]
            coords[nid] = {
                "x": nx,
                "y": y_lv1,
                "w": HUB_W,
                "h": HUB_H,
                "cx": int(nx + HUB_W // 2),
                "cy": int(y_lv1 + HUB_H // 2),
            }

    # 6. Place Bottom Source Dock (`100·200·300` Leaf Notes)
    if src_nodes:
        src_dock_gap = max(SOURCE_DOCK_GAP_Y, int(y_gap * 2.5))
        y_src_group_top = (
            (y_group_bottom if ordered_groups else curr_y) + src_dock_gap
        )
        y_src_cards = y_src_group_top + GROUP_PAD_TOP

        src_desired: List[Tuple[str, float, int]] = []
        for idx, n in enumerate(src_nodes):
            nid = n["node_id"]
            anchor_id = n.get("anchor_node_id")
            parent_xs: List[int] = []
            if anchor_id and anchor_id in coords:
                parent_xs.append(coords[anchor_id]["cx"])
            else:
                for p in adj_up.get(nid, []):
                    if p in coords:
                        parent_xs.append(coords[p]["cx"])

            if parent_xs:
                des_cx = sum(parent_xs) / len(parent_xs)
            else:
                des_cx = (idx - (len(src_nodes) - 1) / 2.0) * (SOURCE_W + x_gap)
            src_desired.append((nid, des_cx, SOURCE_W))

        src_x_map = resolve_1d_non_overlapping(src_desired, x_gap)
        for n in src_nodes:
            nid = n["node_id"]
            nx = src_x_map[nid]
            coords[nid] = {
                "x": nx,
                "y": y_src_cards,
                "w": SOURCE_W,
                "h": SOURCE_H,
                "cx": int(nx + SOURCE_W // 2),
                "cy": int(y_src_cards + SOURCE_H // 2),
            }

        src_min_x = min(coords[n["node_id"]]["x"] for n in src_nodes) - GROUP_PAD_X
        src_max_x = (
            max(coords[n["node_id"]]["x"] + SOURCE_W for n in src_nodes)
            + GROUP_PAD_X
        )
        src_group_h = SOURCE_H + GROUP_PAD_TOP + GROUP_PAD_BOTTOM

        group_canvas_nodes.append(
            {
                "id": make_auto_id("group", "source_dock"),
                "type": "group",
                "x": int(src_min_x),
                "y": int(y_src_group_top),
                "width": int(src_max_x - src_min_x),
                "height": int(src_group_h),
                "label": "📚 Source Dock (100·200·300 원천 근거 메모)",
                "color": "2",
            }
        )

    if coords or group_canvas_nodes:
        min_canvas_x = min(
            [c["x"] for c in coords.values()] + [g["x"] for g in group_canvas_nodes]
        )
        max_canvas_x = max(
            [c["x"] + c["w"] for c in coords.values()]
            + [g["x"] + g["width"] for g in group_canvas_nodes]
        )
        all_cx = (min_canvas_x + max_canvas_x) / 2.0
        total_canvas_span = max_canvas_x - min_canvas_x
        # Width set to ~48-50% of total canvas span per user guidance
        dynamic_master_w = max(
            1600, min(2000, int(round(total_canvas_span * 0.48)))
        )
    else:
        all_cx = 0.0
        dynamic_master_w = MASTER_W

    master_group_w = int(dynamic_master_w + 2 * GROUP_PAD_X)
    master_group_x = int(round(all_cx - master_group_w / 2.0))
    master_group_box = {
        "x": master_group_x,
        "y": 0,
        "w": master_group_w,
        "h": int(master_group_h),
    }

    # Wrap the master briefing in a high-visibility `type: "group"` container.
    # Obsidian Canvas native LOD virtualizes (collapses to `≡`) text node bodies at low zoom,
    # but group labels are ALWAYS rendered at large scale regardless of zoom level.
    group_canvas_nodes.insert(
        0,
        {
            "id": make_auto_id("group", "master_briefing"),
            "type": "group",
            "x": master_group_box["x"],
            "y": master_group_box["y"],
            "width": master_group_box["w"],
            "height": master_group_box["h"],
            "label": f"🧭 마스터 브리핑: {m_title}",
            "color": "6",
        },
    )

    master_box = {
        "x": master_group_x + GROUP_PAD_X,
        "y": GROUP_PAD_TOP,
        "w": dynamic_master_w,
        "h": dynamic_master_h,
    }
    text_canvas_nodes.insert(
        0,
        {
            "id": "auto-text-master-briefing",
            "type": "text",
            "x": master_box["x"],
            "y": master_box["y"],
            "width": master_box["w"],
            "height": master_box["h"],
            "text": master_md,
            "color": "6",
        },
    )

    # 7. Build JSON Canvas `file` node objects
    for n in valid_nodes:
        nid = n["node_id"]
        if nid not in coords:
            continue
        box = coords[nid]
        c_node: Dict[str, Any] = {
            "id": make_auto_id("node", n["note_title"]),
            "type": "file",
            "file": n["file_path"],
            "x": box["x"],
            "y": box["y"],
            "width": box["w"],
            "height": box["h"],
            "color": n["color"],
        }
        if n.get("subpath"):
            c_node["subpath"] = n["subpath"]
        file_canvas_nodes.append(c_node)

    canvas_id_map: Dict[str, str] = {
        n["node_id"]: make_auto_id("node", n["note_title"]) for n in valid_nodes
    }

    all_card_boxes: List[Dict[str, int]] = [master_box, master_group_box] + list(coords.values())

    def has_intervening_card_on_row(u_id: str, v_id: str) -> bool:
        ub, vb = coords[u_id], coords[v_id]
        if abs(ub["y"] - vb["y"]) > 80:
            return False
        left_x = min(ub["x"] + ub["w"], vb["x"] + vb["w"])
        right_x = max(ub["x"], vb["x"])
        row_y = ub["y"]
        for other_id, ob in coords.items():
            if other_id in (u_id, v_id):
                continue
            if abs(ob["y"] - row_y) < 80:
                if ob["x"] + ob["w"] > left_x + 10 and ob["x"] < right_x - 10:
                    return True
        return False

    # 8. Build JSON Canvas `edges` and enforce planar non-overlapping label placement
    placed_label_boxes: List[Tuple[float, float, float, float]] = []
    canvas_edges: List[Dict[str, Any]] = []

    for e in valid_edges:
        u_spec = e["from_node"]
        v_spec = e["to_node"]
        if u_spec not in coords or v_spec not in coords:
            continue

        rel_type = e["relation_type"]
        u_node = node_by_id[u_spec]
        v_node = node_by_id[v_spec]
        u_box = coords[u_spec]
        v_box = coords[v_spec]
        label = e.get("label", "").strip()

        if rel_type in {"hierarchy", "strategy_pull"}:
            if u_box["y"] <= v_box["y"]:
                from_spec, to_spec = u_spec, v_spec
            else:
                from_spec, to_spec = v_spec, u_spec

            if coords[from_spec]["y"] == coords[to_spec]["y"]:
                if coords[from_spec]["x"] <= coords[to_spec]["x"]:
                    from_side, to_side = "right", "left"
                else:
                    from_side, to_side = "left", "right"
            else:
                from_side, to_side = "bottom", "top"
            from_end, to_end = "none", "arrow"

        elif rel_type == "source":
            if u_node["swimlane"] == "Source" and v_node["swimlane"] != "Source":
                from_spec, to_spec = u_spec, v_spec
            elif v_node["swimlane"] == "Source" and u_node["swimlane"] != "Source":
                from_spec, to_spec = v_spec, u_spec
            else:
                from_spec, to_spec = (
                    (u_spec, v_spec) if u_box["y"] >= v_box["y"] else (v_spec, u_spec)
                )
            from_side, to_side = "top", "bottom"
            from_end, to_end = "none", "arrow"

        elif rel_type == "related":
            if abs(u_box["y"] - v_box["y"]) < 100:
                if u_box["x"] <= v_box["x"]:
                    from_spec, to_spec = u_spec, v_spec
                else:
                    from_spec, to_spec = v_spec, u_spec

                # Planar Horizontal Rule: If another card sits directly between `from_spec` and `to_spec`
                # on the same horizontal row, skip this non-adjacent cross-row `related` edge so it never
                # cuts across intermediate cards or collides with bottom Source Dock vertical arrows!
                if has_intervening_card_on_row(from_spec, to_spec):
                    continue
                from_side, to_side = "right", "left"
            else:
                if u_box["y"] <= v_box["y"]:
                    from_spec, to_spec = u_spec, v_spec
                else:
                    from_spec, to_spec = v_spec, u_spec
                from_side, to_side = "bottom", "top"
            from_end, to_end = "arrow", "arrow"

        else:  # "prev"
            from_spec, to_spec = u_spec, v_spec
            if has_intervening_card_on_row(from_spec, to_spec):
                continue
            if coords[from_spec]["x"] <= coords[to_spec]["x"]:
                from_side, to_side = "right", "left"
            else:
                from_side, to_side = "left", "right"
            from_end, to_end = "none", "arrow"

        # Verify label midpoint does not intersect any card or already placed label
        if label:
            p1 = port_point(coords[from_spec], from_side)
            p2 = port_point(coords[to_spec], to_side)
            mx = (p1[0] + p2[0]) / 2.0
            my = (p1[1] + p2[1]) / 2.0
            lw = max(90.0, len(label) * 14.0 + 24.0)
            lh = 36.0
            lx = mx - lw / 2.0
            ly = my - lh / 2.0

            card_hit = any(
                rect_intersects(lx, ly, lw, lh, cb["x"], cb["y"], cb["w"], cb["h"], pad=4.0)
                for cb in all_card_boxes
            )
            label_hit = any(
                rect_intersects(lx, ly, lw, lh, pl[0], pl[1], pl[2], pl[3], pad=6.0)
                for pl in placed_label_boxes
            )
            if not card_hit and not label_hit:
                placed_label_boxes.append((lx, ly, lw, lh))
            else:
                label = ""

        from_cid = canvas_id_map[from_spec]
        to_cid = canvas_id_map[to_spec]
        edge_id = make_auto_id("edge", f"{from_cid}->{to_cid}:{rel_type}")

        edge_obj: Dict[str, Any] = {
            "id": edge_id,
            "fromNode": from_cid,
            "fromSide": from_side,
            "toNode": to_cid,
            "toSide": to_side,
            "toEnd": to_end,
            "color": e["color"],
        }
        if from_end != "none":
            edge_obj["fromEnd"] = from_end
        if label:
            edge_obj["label"] = label

        canvas_edges.append(edge_obj)

    canvas_nodes = group_canvas_nodes + text_canvas_nodes + file_canvas_nodes
    return canvas_nodes, canvas_edges


def extract_and_relocate_user_nodes(
    existing_canvas_path: Path,
    new_nodes: List[Dict[str, Any]],
    new_edges: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
    """Preserve manual user-created nodes (`id` not starting with `auto-`) into a right-side `User Notes` group."""
    if not existing_canvas_path.is_file():
        return new_nodes, new_edges, 0

    try:
        old_data = json.loads(existing_canvas_path.read_text(encoding="utf-8"))
    except Exception:
        return new_nodes, new_edges, 0

    old_nodes = old_data.get("nodes", [])
    old_edges = old_data.get("edges", [])

    user_nodes: List[Dict[str, Any]] = []
    user_node_ids: Set[str] = set()
    for onode in old_nodes:
        oid = str(onode.get("id", ""))
        if not oid or oid.startswith("auto-"):
            continue
        user_nodes.append(dict(onode))
        user_node_ids.add(oid)

    if not user_nodes:
        return new_nodes, new_edges, 0

    if new_nodes:
        max_new_right = max(int(n.get("x", 0)) + int(n.get("width", 400)) for n in new_nodes)
        min_new_top = min(int(n.get("y", 0)) for n in new_nodes)
    else:
        max_new_right = 0
        min_new_top = 0

    min_user_x = min(int(n.get("x", 0)) for n in user_nodes)
    min_user_y = min(int(n.get("y", 0)) for n in user_nodes)

    target_left_x = max_new_right + 200 + GROUP_PAD_X
    target_top_y = min_new_top + GROUP_PAD_TOP

    dx = target_left_x - min_user_x
    dy = target_top_y - min_user_y

    for unode in user_nodes:
        unode["x"] = int(unode.get("x", 0)) + dx
        unode["y"] = int(unode.get("y", 0)) + dy

    max_user_right = max(int(n["x"]) + int(n.get("width", 300)) for n in user_nodes)
    max_user_bottom = max(int(n["y"]) + int(n.get("height", 200)) for n in user_nodes)

    user_group = {
        "id": "auto-group-user-notes",
        "type": "group",
        "x": int(target_left_x - GROUP_PAD_X),
        "y": int(target_top_y - GROUP_PAD_TOP),
        "width": int((max_user_right - target_left_x) + 2 * GROUP_PAD_X),
        "height": int((max_user_bottom - target_top_y) + GROUP_PAD_TOP + GROUP_PAD_BOTTOM),
        "label": "✍️ User Notes (사용자 수동 편집 보존 영역)",
        "color": "2",
    }

    all_valid_ids = {str(n["id"]) for n in new_nodes} | user_node_ids
    preserved_edges: List[Dict[str, Any]] = []
    existing_edge_ids = {str(e["id"]) for e in new_edges}

    for oedge in old_edges:
        eid = str(oedge.get("id", ""))
        u = str(oedge.get("fromNode", ""))
        v = str(oedge.get("toNode", ""))
        if not eid.startswith("auto-") or u in user_node_ids or v in user_node_ids:
            if u in all_valid_ids and v in all_valid_ids and eid not in existing_edge_ids:
                preserved_edges.append(dict(oedge))

    merged_nodes = [user_group] + new_nodes + user_nodes
    merged_edges = new_edges + preserved_edges
    return merged_nodes, merged_edges, len(user_nodes)


def resolve_root_trash_dir(vault_root: Path) -> Path:
    """Resolve Google Drive root `.trash` (`parentId = 'root'`) or fallback to `vault_root / .trash`."""
    try:
        real_vault = vault_root.resolve()
        drive_root_trash = real_vault.parent / ".trash"
        if drive_root_trash.is_dir():
            return drive_root_trash
    except Exception:
        pass
    fallback_trash = vault_root / ".trash"
    fallback_trash.mkdir(parents=True, exist_ok=True)
    return fallback_trash


def save_canvas_with_trash_isolation(
    vault_root: Path,
    canvas_filename: str,
    canvas_payload: Dict[str, Any],
) -> Tuple[Path, Optional[Path]]:
    """Execute `Trash-First-Then-Write` transaction to `My-Wiki/700. utilize/`."""
    utilize_dir = vault_root / "700. utilize"
    utilize_dir.mkdir(parents=True, exist_ok=True)
    target_path = utilize_dir / canvas_filename

    trashed_path: Optional[Path] = None
    if target_path.is_file():
        trash_dir = resolve_root_trash_dir(vault_root)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = target_path.stem
        backup_name = f"{stem}_backup_{ts}.canvas"
        trashed_path = trash_dir / backup_name
        shutil.move(str(target_path), str(trashed_path))

    target_path.write_text(
        json.dumps(canvas_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target_path, trashed_path


def upsert_utilize_canvas_index(
    vault_root: Path,
    canvas_filename: str,
    topic: str,
    seed_titles: List[str],
    node_count: int,
    edge_count: int,
) -> bool:
    """Upsert Section 4 (`인터랙티브 지식 캔버스 레지스트리`) in `500. Index/_인덱스_700_Utilize.md`."""
    index_path = vault_root / "500. Index" / "_인덱스_700_Utilize.md"
    if not index_path.is_file():
        return False

    text = index_path.read_text(encoding="utf-8")
    today_str = datetime.now().strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    text = re.sub(
        r"(?m)^(updated:\s*)\d{4}-\d{2}-\d{2}\s*$",
        f"\\g<1>{today_str}",
        text,
        count=1,
    )

    canvas_link = f"`[[{canvas_filename}]]`"
    seeds_str = ", ".join(f"`[[{s}]]`" for s in seed_titles[:3]) if seed_titles else "-"
    new_row = (
        f"| {now_str} | {canvas_link} | **{topic}** (시드: {seeds_str}) "
        f"| 노드 {node_count}개 · 엣지 {edge_count}개 | `Permanent` (Rolling Window 제외) |"
    )

    sec4_header = "## 4. 인터랙티브 지식 캔버스 레지스트리 (`700. utilize` — 영구 보존)"
    table_header = (
        "| 생성/갱신 일시 (`updated`) | 캔버스 파일명 (`700. utilize`) | 핵심 주제 및 출발 시드 위키 | 규모 (노드·엣지) | 보존 정책 (`Lifecycle`) |\n"
        "| :---: | :--- | :--- | :---: | :---: |"
    )

    if "## 4. 인터랙티브 지식 캔버스 레지스트리" not in text:
        block = f"\n\n---\n\n{sec4_header}\n\n{table_header}\n{new_row}\n"
        text = text.rstrip() + block
    else:
        row_pattern = re.compile(
            rf"^\|[^\n]*\[\[{re.escape(canvas_filename)}\]\][^\n]*\|$",
            re.MULTILINE,
        )
        if row_pattern.search(text):
            text = row_pattern.sub(new_row, text)
        else:
            sec_pos = text.find("## 4. 인터랙티브 지식 캔버스 레지스트리")
            sep_match = re.search(r"\|[\s:-]+\|[\s:-]+\|\r?\n", text[sec_pos:])
            if sep_match:
                insert_at = sec_pos + sep_match.end()
                text = text[:insert_at] + new_row + "\n" + text[insert_at:]
            else:
                text = text.rstrip() + "\n" + new_row + "\n"

    index_path.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Step 3: Compile canvas_spec.json into an Obsidian .canvas file in My-Wiki/700. utilize/."
    )
    parser.add_argument(
        "--vault",
        type=str,
        default=None,
        help="Path to My-Wiki vault (auto-detected via My-Wiki Rules.md if omitted).",
    )
    parser.add_argument(
        "--spec",
        "-s",
        type=str,
        required=True,
        help="Path to input canvas_spec.json generated in Step 2.",
    )
    parser.add_argument(
        "--x-gap",
        type=int,
        default=DEFAULT_X_GAP,
        help=f"Horizontal pixel gap between cards (default: {DEFAULT_X_GAP}).",
    )
    parser.add_argument(
        "--y-gap",
        type=int,
        default=DEFAULT_Y_GAP,
        help=f"Vertical pixel gap between swimlanes (default: {DEFAULT_Y_GAP}).",
    )

    args = parser.parse_args()
    vault_root = resolve_vault_root(args.vault)
    spec_path = Path(args.spec).resolve()

    if not spec_path.is_file():
        print(f"Error: Specification file not found: {spec_path}", file=sys.stderr)
        return 1

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    topic = str(spec.get("topic", "지식_캔버스")).strip()
    canvas_filename = sanitize_canvas_filename(
        str(spec.get("canvas_filename", "")), topic
    )

    graph = VaultGraph(vault_root)
    graph.load()

    valid_nodes, valid_edges, warnings = validate_and_resolve_spec(spec, graph)
    if not valid_nodes:
        print("Error: No valid existing vault notes found in canvas_spec.json.", file=sys.stderr)
        return 1

    canvas_nodes, canvas_edges = compute_layout_and_build_canvas(
        spec=spec,
        valid_nodes=valid_nodes,
        valid_edges=valid_edges,
        x_gap=args.x_gap,
        y_gap=args.y_gap,
    )

    target_canvas_path = vault_root / "700. utilize" / canvas_filename
    canvas_nodes, canvas_edges, preserved_user_count = extract_and_relocate_user_nodes(
        existing_canvas_path=target_canvas_path,
        new_nodes=canvas_nodes,
        new_edges=canvas_edges,
    )

    payload = {
        "nodes": canvas_nodes,
        "edges": canvas_edges,
    }

    saved_path, trashed_path = save_canvas_with_trash_isolation(
        vault_root=vault_root,
        canvas_filename=canvas_filename,
        canvas_payload=payload,
    )

    seed_titles = [
        n["note_title"] for n in valid_nodes if n.get("role") == "seed"
    ] or [valid_nodes[0]["note_title"]]

    index_updated = upsert_utilize_canvas_index(
        vault_root=vault_root,
        canvas_filename=canvas_filename,
        topic=topic,
        seed_titles=seed_titles,
        node_count=len(valid_nodes),
        edge_count=len(canvas_edges),
    )

    labeled_edges = sum(1 for e in canvas_edges if e.get("label"))
    print(f"[Step 3: canvas_compiler] Canvas compiled successfully.")
    print(f"  - Topic              : {topic}")
    print(f"  - Saved Canvas Path  : {saved_path}")
    if trashed_path:
        print(f"  - Previous Isolated  : {trashed_path}")
    print(
        f"  - File Nodes Rendered: {len(valid_nodes)} "
        f"(Total Canvas Elements incl. Groups/Text: {len(canvas_nodes)})"
    )
    print(
        f"  - Semantic Edges     : {len(canvas_edges)} "
        f"(Labeled key edges: {labeled_edges}, Unlabeled clean hierarchy edges: {len(canvas_edges) - labeled_edges})"
    )
    print(f"  - User Nodes Kept    : {preserved_user_count}")
    print(f"  - 700 Index Updated  : {index_updated}")
    if warnings:
        print(f"  - Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"      * {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
