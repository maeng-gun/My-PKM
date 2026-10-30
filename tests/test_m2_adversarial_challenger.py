r"""Empirical Adversarial Challenger Test Suite for Milestone 2 (R2: Deterministic Linter & Test Upgrades).

Tests:
1. C3 Boundary Conditions:
   - Lv1 master hub with up: [] (PASS)
   - Case/Event wiki in 400. Wiki with up: [] (PASS)
   - Lv2 stage in 400. Wiki with up: [] (FAIL - C3)
   - Lv3 sub-industry in 400. Wiki with up: [] (FAIL - C3)
   - Lv4 company in 400. Wiki with up: [] (FAIL - C3)
   - 100. Concepts note with up: [] (FAIL - C3)
   - General concept in 400. Wiki with up: [] (FAIL - C3)
   - 200. AI_logs & 300. Sources with up: [] (PASS)

2. C7 Boundary Conditions:
   - Note outside 500. Index containing _인덱스_ wikilink or backtick in frontmatter or body (FAIL - C7)
   - Note inside 500. Index containing _인덱스_ (PASS)
   - Note self-referencing in up, related, or body (FAIL - C7)
   - Note with uncreated ghost wikilink in up, related, or body (FAIL - C7)
   - Note with fake ghost backtick matching all 11 GHOST_HUB_NAMES (FAIL - C7)
   - Note with fake ghost backtick with uncreated standard prefixes (FAIL - C7)
   - Real backtick pointing to existing note in vault (PASS)
   - Regular code backticks and fenced code blocks containing ghost names (PASS)

3. C8 Boundary Conditions:
   - Structural stage, hub, sub-industry, company, or concept with prev (FAIL - C8)
   - Chronological case wiki with prev (PASS)
   - Lv1 hub body linking outside immediate Lv2 children (FAIL - C8)
   - Lv2 stage body linking outside immediate Lv3 children (FAIL - C8)
   - Lv3 sub-industry body linking to Lv1 or source reports (FAIL - C8)
   - Lv4 company body linking to Lv1 or Lv2 (FAIL - C8)
   - Case/event wiki linking to Lv1 or Lv2 in up (FAIL - C8)
   - Case/event wiki linking to Lv3 or Lv4 in up (PASS)
   - Transitive triangle shortcut A ➔ B ➔ C and A ➔ C in up (FAIL - C8)
   - Multi-hop transitive shortcut A ➔ D and A ➔ B ➔ C ➔ D in up (FAIL - C8)
   - Diamond DAG A ➔ B ➔ D and A ➔ C ➔ D without shortcut (PASS)
   - Vertical related where note links to ancestor or descendant (FAIL - C8)
   - Horizontal related between peer siblings (PASS)
   - DAG cycle detection A ➔ B ➔ A and A ➔ B ➔ C ➔ A (FAIL - C8)
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / ".agents" / "skills" / "pkm_manager" / "scripts"
LINTER_PATH = SCRIPTS_DIR / "vault_linter.py"
PYTHON_EXE = sys.executable

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import constitution_loader  # noqa: E402
import vault_linter  # noqa: E402


class BaseLinterTestCase(unittest.TestCase):
    """Base class providing vault fixture generation and linter runners."""

    def run_linter(self, vault_path: Path, extra_args: list[str] | None = None) -> subprocess.CompletedProcess:
        cmd = [PYTHON_EXE, str(LINTER_PATH), "--vault", str(vault_path)]
        if extra_args:
            cmd.extend(extra_args)
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def write_minimal_rules(self, vault_path: Path) -> Path:
        rules = vault_path / "My-Wiki Rules.md"
        rules.write_text(
            """---
origin: wiki
type: hub
domain: [equity, macro]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# My-Wiki Rules (v3.3)
### Rule 1. 폴더 구조
### Rule 2. 프론트매터 스키마
- `domain`: `macro`, `equity`, `portfolio`, `theory`, `work`, `ai-pkm`, `education`
### Rule 9. 위키 아키텍처
""",
            encoding="utf-8",
        )
        return rules


class TestC3BoundaryConditions(BaseLinterTestCase):
    """Adversarial stress-testing of Check C3 (Orphan Note Partitioning)."""

    def test_lv1_master_hub_with_empty_up_passes(self):
        """Lv1 master hubs (C#_, level: 1, type: hub) in 400. Wiki must pass C3 with up: []."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            (vault / "400. Wiki" / "C1_AI 반도체.md").write_text(
                """---
origin: wiki
type: hub
level: 1
domain: [equity]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# C1 Hub
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault)
            self.assertEqual(res.returncode, 0, f"Lv1 hub with up: [] must pass: {res.stdout}")

    def test_case_and_event_wikis_with_empty_up_pass(self):
        """Case, analysis, and event wikis in 400. Wiki must pass C3 with up: []."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            # type: analysis
            (vault / "400. Wiki" / "2026-10-30_금통위_기준금리_동결.md").write_text(
                """---
origin: wiki
type: analysis
domain: [macro]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Analysis Wiki
""",
                encoding="utf-8",
            )
            # type: event
            (vault / "400. Wiki" / "사건_중동_지정학_충격.md").write_text(
                """---
origin: wiki
type: event
domain: [macro]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Event Wiki
""",
                encoding="utf-8",
            )
            # type: case
            (vault / "400. Wiki" / "케이스_기업_밸류업_프로그램.md").write_text(
                """---
origin: wiki
type: case
domain: [equity]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Case Wiki
""",
                encoding="utf-8",
            )

            res = self.run_linter(vault)
            self.assertEqual(res.returncode, 0, f"Case/Event wikis with up: [] must pass C3: {res.stdout}")

    def test_lv2_stage_with_empty_up_fails(self):
        """Lv2 stages (C#-S#_) with up: [] must fail C3."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            (vault / "400. Wiki" / "C1-S1_AI 가속기 및 서버.md").write_text(
                """---
origin: wiki
type: concept
level: 2
domain: [equity]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Lv2 Stage
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault)
            self.assertEqual(res.returncode, 1)
            self.assertIn("C3", res.stdout)
            self.assertIn("C1-S1_AI 가속기 및 서버.md", res.stdout)

    def test_lv3_sub_industry_with_empty_up_fails(self):
        """Lv3 sub-industries (산업_) with up: [] must fail C3."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            (vault / "400. Wiki" / "산업_HBM.md").write_text(
                """---
origin: wiki
type: concept
level: 3
domain: [equity]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Lv3 Sub-Industry
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault)
            self.assertEqual(res.returncode, 1)
            self.assertIn("C3", res.stdout)
            self.assertIn("산업_HBM.md", res.stdout)

    def test_lv4_company_with_empty_up_fails(self):
        """Lv4 companies (기업_) with up: [] must fail C3."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            (vault / "400. Wiki" / "기업_SK하이닉스.md").write_text(
                """---
origin: wiki
type: entity
level: 4
domain: [equity]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Lv4 Company
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault)
            self.assertEqual(res.returncode, 1)
            self.assertIn("C3", res.stdout)
            self.assertIn("기업_SK하이닉스.md", res.stdout)

    def test_concepts_folder_with_empty_up_fails(self):
        """Notes in 100. Concepts with up: [] must fail C3 (human concepts require anchor)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "100. Concepts").mkdir(parents=True)
            self.write_minimal_rules(vault)

            (vault / "100. Concepts" / "시장_비효율성에_대한_고찰.md").write_text(
                """---
origin: human
type: concept
domain: [equity]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Human Insight
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault)
            self.assertEqual(res.returncode, 1)
            self.assertIn("C3", res.stdout)
            self.assertIn("시장_비효율성에_대한_고찰.md", res.stdout)

    def test_general_concept_in_400_wiki_with_empty_up_fails(self):
        """Structural concept in 400. Wiki that is NOT case/event must fail C3 if up: []."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            (vault / "400. Wiki" / "일반_금융_개념.md").write_text(
                """---
origin: wiki
type: concept
domain: [theory]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Concept Note
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault)
            self.assertEqual(res.returncode, 1)
            self.assertIn("C3", res.stdout)
            self.assertIn("일반_금융_개념.md", res.stdout)

    def test_sources_and_logs_with_empty_up_pass(self):
        """300. Sources and 200. AI_logs with up: [] are legitimate unanchored notes and pass C3."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "300. Sources").mkdir(parents=True)
            (vault / "200. AI_logs").mkdir(parents=True)
            self.write_minimal_rules(vault)

            (vault / "300. Sources" / "원천보고서.md").write_text(
                """---
origin: source
type: source
domain: [macro]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Source Report
""",
                encoding="utf-8",
            )
            (vault / "200. AI_logs" / "리서치대화록.md").write_text(
                """---
origin: ai
type: log
domain: [equity]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# AI Log
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault)
            self.assertEqual(res.returncode, 0, f"Sources and Logs with up: [] must pass C3: {res.stdout}")


class TestC7BoundaryConditions(BaseLinterTestCase):
    """Adversarial stress-testing of Check C7 (Index References, Self References, Ghost Links, Fake Backticks)."""

    def test_forbidden_index_reference_in_frontmatter_fails(self):
        """Notes outside 500. Index with _인덱스_ wikilink or backtick in frontmatter must fail C7."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            (vault / "500. Index").mkdir(parents=True)
            self.write_minimal_rules(vault)

            # Wikilink in up
            (vault / "400. Wiki" / "사건_A.md").write_text(
                """---
origin: wiki
type: analysis
domain: [macro]
up: ["[[_인덱스_400_Wiki]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Event A
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("C7", res.stdout)
            self.assertIn("Forbidden index reference detected in frontmatter", res.stdout)

            # Backtick in related
            (vault / "400. Wiki" / "사건_A.md").write_text(
                """---
origin: wiki
type: analysis
domain: [macro]
up: []
related: ["`_인덱스_210_뉴스큐레이팅`"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Event A
""",
                encoding="utf-8",
            )
            res2 = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res2.returncode, 1)
            self.assertIn("C7", res2.stdout)
            self.assertIn("Forbidden index reference detected in frontmatter", res2.stdout)

    def test_forbidden_index_reference_in_body_fails(self):
        """Notes outside 500. Index with _인덱스_ in body (link or backtick) must fail C7."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            # Wikilink in body
            (vault / "400. Wiki" / "사건_B.md").write_text(
                """---
origin: wiki
type: analysis
domain: [macro]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Event B
- **모니터링 레지스트리**: [[_인덱스_210_뉴스큐레이팅]]
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("C7", res.stdout)
            self.assertIn("Forbidden index reference detected in body", res.stdout)

            # Backtick in body
            (vault / "400. Wiki" / "사건_B.md").write_text(
                """---
origin: wiki
type: analysis
domain: [macro]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Event B
참조: `_인덱스_400_Wiki` 확인 요망.
""",
                encoding="utf-8",
            )
            res2 = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res2.returncode, 1)
            self.assertIn("C7", res2.stdout)
            self.assertIn("Forbidden index reference detected in body", res2.stdout)

    def test_index_references_inside_500_index_are_exempt(self):
        """Index files inside 500. Index are legitimate index hubs and can reference other indexes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "500. Index").mkdir(parents=True)
            self.write_minimal_rules(vault)

            (vault / "500. Index" / "_인덱스_400_Wiki.md").write_text(
                """---
origin: wiki
type: hub
domain: [macro]
up: ["[[My-Wiki Rules]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Wiki Index
연결 인덱스: [[_인덱스_100_Concepts]]
""",
                encoding="utf-8",
            )
            (vault / "500. Index" / "_인덱스_100_Concepts.md").write_text(
                """---
origin: wiki
type: hub
domain: [macro]
up: ["[[My-Wiki Rules]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Concepts Index
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res.returncode, 0, f"Indexes inside 500. Index must be exempt: {res.stdout}")

    def test_self_referencing_fails(self):
        """Notes referencing themselves in up, related, or body must fail C7."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            # Self-reference in up
            (vault / "400. Wiki" / "사건_자기참조.md").write_text(
                """---
origin: wiki
type: analysis
domain: [macro]
up: ["[[사건_자기참조]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Self in Up
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("Self-reference detected in up", res.stdout)

            # Self-reference in related
            (vault / "400. Wiki" / "사건_자기참조.md").write_text(
                """---
origin: wiki
type: analysis
domain: [macro]
up: []
related: ["[[사건_자기참조]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Self in Related
""",
                encoding="utf-8",
            )
            res2 = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res2.returncode, 1)
            self.assertIn("Self-reference detected in related", res2.stdout)

            # Self-reference in body link
            (vault / "400. Wiki" / "사건_자기참조.md").write_text(
                """---
origin: wiki
type: analysis
domain: [macro]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Self in Body
본 문서는 [[사건_자기참조]]에 대한 분석입니다.
""",
                encoding="utf-8",
            )
            res3 = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res3.returncode, 1)
            self.assertIn("Self-reference detected in body", res3.stdout)

            # Self-reference in body backtick
            (vault / "400. Wiki" / "사건_자기참조.md").write_text(
                """---
origin: wiki
type: analysis
domain: [macro]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Self in Body Backtick
본 문서는 `사건_자기참조`에 대한 기록입니다.
""",
                encoding="utf-8",
            )
            res4 = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res4.returncode, 1)
            self.assertIn("Self-reference detected in body", res4.stdout)

    def test_uncreated_ghost_wikilinks_fail(self):
        """Uncreated ghost wikilinks in up, related, or body must fail C7."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            # Uncreated in up
            (vault / "400. Wiki" / "노트1.md").write_text(
                """---
origin: wiki
type: analysis
domain: [macro]
up: ["[[미생성_상위노트]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Note 1
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("Ghost wikilink detected in up", res.stdout)

            # Uncreated in body
            (vault / "400. Wiki" / "노트1.md").write_text(
                """---
origin: wiki
type: analysis
domain: [macro]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Note 1
본문에서 [[미생성_유령노트]]를 호출합니다.
""",
                encoding="utf-8",
            )
            res2 = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res2.returncode, 1)
            self.assertIn("Ghost wikilink detected: '[[미생성_유령노트]]'", res2.stdout)

    def test_fake_backtick_matching_all_11_ghost_hubs_fails(self):
        """Every single one of the 11 known GHOST_HUB_NAMES must trigger C7 when backticked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            for ghost_name in vault_linter.GHOST_HUB_NAMES:
                note_file = vault / "400. Wiki" / "테스트노트.md"
                note_file.write_text(
                    f"""---
origin: wiki
type: analysis
domain: [macro]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Test Ghost
상위 개념: `{ghost_name}`
""",
                    encoding="utf-8",
                )
                res = self.run_linter(vault, ["--check-astep"])
                self.assertEqual(res.returncode, 1, f"Ghost hub backtick '{ghost_name}' must fail C7")
                self.assertIn(f"Fake ghost note backtick detected: '`{ghost_name}`'", res.stdout)

    def test_fake_backtick_with_standard_prefixes_fails(self):
        """Uncreated standard prefix backticks (산업_, 기업_, C#_, C#-S#_) must fail C7."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            prefixes = ["산업_가짜산업", "기업_가짜기업", "C1_가짜허브", "C1-S1_가짜단계"]
            for fake_item in prefixes:
                note_file = vault / "400. Wiki" / "테스트노트.md"
                note_file.write_text(
                    f"""---
origin: wiki
type: analysis
domain: [equity]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Test Fake Prefix
참조: `{fake_item}`
""",
                    encoding="utf-8",
                )
                res = self.run_linter(vault, ["--check-astep"])
                self.assertEqual(res.returncode, 1, f"Fake uncreated prefix '{fake_item}' must fail C7")
                self.assertIn(f"Fake uncreated note backtick detected: '`{fake_item}`'", res.stdout)

    def test_real_backtick_pointing_to_existing_note_passes(self):
        """Backtick pointing to an existing file in the vault is legitimate source citation and passes C7."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            (vault / "400. Wiki" / "산업_HBM.md").write_text(
                """---
origin: wiki
type: concept
level: 3
domain: [equity]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# HBM
""",
                encoding="utf-8",
            )
            # Case wiki citing `산업_HBM` in backticks
            (vault / "400. Wiki" / "사건_HBM_공급계약.md").write_text(
                """---
origin: wiki
type: analysis
domain: [equity]
up: ["[[산업_HBM]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Case
본 연구는 `산업_HBM` 분석을 인용합니다.
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault, ["--check-astep"])
            self.assertNotIn("Fake uncreated note backtick", res.stdout)

    def test_fenced_code_blocks_and_regular_backticks_pass(self):
        """Regular code backticks (`SELECT *`, `var_x`) and fenced blocks with ghost strings pass C7."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            (vault / "400. Wiki" / "사건_코드분석.md").write_text(
                """---
origin: wiki
type: analysis
domain: [equity]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Code Test
Here is some inline code: `const x = 42;` and `query_logs()`.

```python
# In fenced code block, mentioning ghost hub is allowed:
ghost_name = "국내 거시경제 및 정책"
print("산업_가짜산업")
```
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res.returncode, 0, f"Regular code and fenced blocks must pass C7: {res.stdout}")


class TestC8BoundaryConditions(BaseLinterTestCase):
    """Adversarial stress-testing of Check C8 (Topology, 1-Hop Scope, DAG Cycles, Transitive Triangles)."""

    def test_structural_nodes_with_prev_fail(self):
        """Structural nodes (Lv1~Lv4, hubs, concepts) must fail C8 if prev is populated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            # Stage with prev
            (vault / "400. Wiki" / "C1-S1_AI 가속기.md").write_text(
                """---
origin: wiki
type: concept
level: 2
domain: [equity]
up: []
prev: ["[[C1-S2_구동 부품]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Stage
""",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "C1-S2_구동 부품.md").write_text(
                """---
origin: wiki
type: concept
level: 2
domain: [equity]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Stage 2
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("C8", res.stdout)
            self.assertIn("Non-chronological prev detected", res.stdout)

    def test_chronological_case_wiki_with_prev_passes(self):
        """Chronological case/event wikis (non-structural) can legitimately use prev."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            (vault / "400. Wiki" / "2026-09-12_금통위.md").write_text(
                """---
origin: wiki
type: analysis
domain: [macro]
up: []
status: active
created: 2026-09-12
updated: 2026-09-12
---
# Sep Meeting
""",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "2026-10-30_금통위.md").write_text(
                """---
origin: wiki
type: analysis
domain: [macro]
up: []
prev: ["[[2026-09-12_금통위]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Oct Meeting
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res.returncode, 0, f"Chronological case wikis with prev must pass C8: {res.stdout}")

    def test_lv1_body_linking_outside_immediate_lv2_children_fails(self):
        """Lv1 body linking to Lv3, Lv4, or another cluster's Lv2 must fail C8."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            (vault / "400. Wiki" / "C1_AI 반도체.md").write_text(
                """---
origin: wiki
type: hub
level: 1
domain: [equity]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# C1
- Direct link to Lv3: [[산업_반도체]]
- Direct link to other cluster Lv2: [[C2-S1_다른클러스터]]
""",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "산업_반도체.md").write_text(
                "---\norigin: wiki\ntype: concept\nlevel: 3\ndomain: [equity]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# Sub",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "C2-S1_다른클러스터.md").write_text(
                "---\norigin: wiki\ntype: concept\nlevel: 2\ndomain: [equity]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# Stage C2",
                encoding="utf-8",
            )
            res = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("1-Hop scope violation in Level 1 wiki", res.stdout)

    def test_lv2_body_linking_outside_immediate_lv3_children_fails(self):
        """Lv2 body linking to Lv4 or Lv1 must fail C8."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            (vault / "400. Wiki" / "C1_AI 반도체.md").write_text(
                "---\norigin: wiki\ntype: hub\nlevel: 1\ndomain: [equity]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# C1",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "기업_삼성전자.md").write_text(
                "---\norigin: wiki\ntype: entity\nlevel: 4\ndomain: [equity]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# Company",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "C1-S1_AI 가속기.md").write_text(
                """---
origin: wiki
type: concept
level: 2
domain: [equity]
up: ["[[C1_AI 반도체]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# C1-S1
Invalid link to Lv4: [[기업_삼성전자]]
Invalid link to Lv1: [[C1_AI 반도체]]
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("1-Hop scope violation in Level 2 wiki", res.stdout)

    def test_lv3_body_linking_to_lv1_or_source_reports_fails(self):
        """Lv3 body linking to Lv1 ancestor or source report (산업분석_) must fail C8."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            (vault / "300. Sources").mkdir(parents=True)
            self.write_minimal_rules(vault)

            (vault / "400. Wiki" / "C1_AI 반도체.md").write_text(
                "---\norigin: wiki\ntype: hub\nlevel: 1\ndomain: [equity]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# C1",
                encoding="utf-8",
            )
            (vault / "300. Sources" / "산업분석_HBM_동향.md").write_text(
                "---\norigin: source\ntype: source\ndomain: [equity]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# Source",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "산업_HBM.md").write_text(
                """---
origin: wiki
type: concept
level: 3
domain: [equity]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Sub-industry
Invalid link to Lv1: [[C1_AI 반도체]]
Invalid link to Source: [[산업분석_HBM_동향]]
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("1-Hop scope violation in Level 3 wiki", res.stdout)

    def test_lv4_company_body_linking_to_lv1_or_lv2_fails(self):
        """Lv4 company body linking to Lv1 or Lv2 remote ancestors must fail C8."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            (vault / "400. Wiki" / "C1_AI 반도체.md").write_text(
                "---\norigin: wiki\ntype: hub\nlevel: 1\ndomain: [equity]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# C1",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "C1-S1_AI 가속기.md").write_text(
                "---\norigin: wiki\ntype: concept\nlevel: 2\ndomain: [equity]\nup: [\"[[C1_AI 반도체]]\"]\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# C1-S1",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "기업_SK하이닉스.md").write_text(
                """---
origin: wiki
type: entity
level: 4
domain: [equity]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Company
Invalid remote link to Lv1: [[C1_AI 반도체]]
Invalid remote link to Lv2: [[C1-S1_AI 가속기]]
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("1-Hop scope violation in Level 4 wiki", res.stdout)

    def test_case_wiki_linking_to_lv1_or_lv2_in_up_fails(self):
        """Case/event wiki linking to Lv1 (C#_) or Lv2 (C#-S#_) in up must fail C8."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            (vault / "400. Wiki" / "C1_AI 반도체.md").write_text(
                "---\norigin: wiki\ntype: hub\nlevel: 1\ndomain: [equity]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# C1",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "사건_반도체_규제.md").write_text(
                """---
origin: wiki
type: analysis
domain: [equity]
up: ["[[C1_AI 반도체]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Event
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("1-Hop scope violation in case/event wiki", res.stdout)

    def test_transitive_triangle_shortcut_fails(self):
        """A ➔ B ➔ C and direct A ➔ C in up must fail C8 (transitive triangle)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            # Node C (Grandparent)
            (vault / "400. Wiki" / "C1-S1_가속기.md").write_text(
                "---\norigin: wiki\ntype: concept\nlevel: 2\ndomain: [equity]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# C",
                encoding="utf-8",
            )
            # Node B (Parent): B ➔ C
            (vault / "400. Wiki" / "산업_반도체.md").write_text(
                "---\norigin: wiki\ntype: concept\nlevel: 3\ndomain: [equity]\nup: [\"[[C1-S1_가속기]]\"]\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# B",
                encoding="utf-8",
            )
            # Node A (Child): A ➔ B and A ➔ C (Transitive triangle!)
            (vault / "400. Wiki" / "기업_엔비디아.md").write_text(
                """---
origin: wiki
type: entity
level: 4
domain: [equity]
up: ["[[산업_반도체]]", "[[C1-S1_가속기]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# A
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("Transitive triangle shortcut detected in '기업_엔비디아'", res.stdout)

    def test_diamond_dag_passes(self):
        """Diamond DAG (A ➔ B ➔ D and A ➔ C ➔ D) without direct A ➔ D must pass C8."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            # Node D (Root)
            (vault / "400. Wiki" / "루트.md").write_text(
                "---\norigin: wiki\ntype: analysis\ndomain: [macro]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# D",
                encoding="utf-8",
            )
            # Node B: B ➔ D
            (vault / "400. Wiki" / "중간_B.md").write_text(
                "---\norigin: wiki\ntype: analysis\ndomain: [macro]\nup: [\"[[루트]]\"]\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# B",
                encoding="utf-8",
            )
            # Node C: C ➔ D
            (vault / "400. Wiki" / "중간_C.md").write_text(
                "---\norigin: wiki\ntype: analysis\ndomain: [macro]\nup: [\"[[루트]]\"]\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# C",
                encoding="utf-8",
            )
            # Node A: A ➔ B and A ➔ C
            (vault / "400. Wiki" / "자식_A.md").write_text(
                """---
origin: wiki
type: analysis
domain: [macro]
up: ["[[중간_B]]", "[[중간_C]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# A
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res.returncode, 0, f"Diamond DAG must pass C8: {res.stdout}")

    def test_vertical_related_fails(self):
        """Note containing its ancestor or descendant in related must fail C8."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            # Parent
            (vault / "400. Wiki" / "산업_반도체.md").write_text(
                "---\norigin: wiki\ntype: concept\nlevel: 3\ndomain: [equity]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# Parent",
                encoding="utf-8",
            )
            # Child with parent in up AND related
            (vault / "400. Wiki" / "기업_삼성전자.md").write_text(
                """---
origin: wiki
type: entity
level: 4
domain: [equity]
up: ["[[산업_반도체]]"]
related: ["[[산업_반도체]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Child
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("Vertical hierarchy in related detected", res.stdout)

    def test_horizontal_related_between_peers_passes(self):
        """Peer notes that are siblings under the same parent can link via related."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            # Lv1 Hub as root parent (exempt from C3)
            (vault / "400. Wiki" / "C1_AI 반도체.md").write_text(
                "---\norigin: wiki\ntype: hub\nlevel: 1\ndomain: [equity]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# Parent Hub",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "기업_삼성전자.md").write_text(
                """---
origin: wiki
type: entity
level: 4
domain: [equity]
up: ["[[C1_AI 반도체]]"]
related: ["[[기업_SK하이닉스]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Sibling 1
""",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "기업_SK하이닉스.md").write_text(
                """---
origin: wiki
type: entity
level: 4
domain: [equity]
up: ["[[C1_AI 반도체]]"]
related: ["[[기업_삼성전자]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Sibling 2
""",
                encoding="utf-8",
            )
            res = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res.returncode, 0, f"Horizontal related between peer siblings must pass C8: {res.stdout}")

    def test_dag_cycle_detection_fails(self):
        """Circular references in up (A ➔ B ➔ A or A ➔ B ➔ C ➔ A) must fail C8."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            self.write_minimal_rules(vault)

            # Cycle A ➔ B ➔ A
            (vault / "400. Wiki" / "노트_A.md").write_text(
                "---\norigin: wiki\ntype: analysis\ndomain: [macro]\nup: [\"[[노트_B]]\"]\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# A",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "노트_B.md").write_text(
                "---\norigin: wiki\ntype: analysis\ndomain: [macro]\nup: [\"[[노트_A]]\"]\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# B",
                encoding="utf-8",
            )
            res = self.run_linter(vault, ["--check-astep"])
            self.assertEqual(res.returncode, 1)
            self.assertIn("DAG cycle detected in 'up' graph", res.stdout)


if __name__ == "__main__":
    unittest.main()
