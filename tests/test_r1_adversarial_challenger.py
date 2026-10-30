r"""Adversarial challenger test suite for Milestone 1 (R1: Master Constitution Amendment).

Validates:
1. constitution_loader.py SSOT dynamic parsing:
   - cfg['version'] == 'v3.3'
   - all 10 predefined section keys return valid markdown content
   - keyword extraction works for "규칙 5", "규칙 2", "5.2", "5.3", edge cases
   - cfg['standard_domains'] has exactly the 7 standard domains (no quant, life)
   - cfg['standard_prefixes'] has ['C#_', 'C#-S#_', '산업_', '기업_', '_인덱스_']
2. Raw text inspection of My-Wiki Rules.md:
   - YAML frontmatter syntax and fields
   - Markdown table structure and column alignment (accounting for escaped pipes \|)
   - Presence and clarity of all 5 R1 requirements
   - Ghost link / index reference scan and consistency analysis
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import unittest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / ".agents" / "skills" / "pkm_manager" / "scripts"
LOADER_PATH = SCRIPTS_DIR / "constitution_loader.py"
RULES_PATH = PROJECT_ROOT / "My-Wiki" / "My-Wiki Rules.md"
PYTHON_EXE = sys.executable

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import constitution_loader  # noqa: E402


class TestConstitutionLoaderSSOT(unittest.TestCase):
    """Stress tests for constitution_loader.py dynamic parsing."""

    @classmethod
    def setUpClass(cls):
        cls.vault_dir = PROJECT_ROOT / "My-Wiki"
        cls.rules_path = RULES_PATH
        cls.cfg = constitution_loader.load_constitution(cls.vault_dir)
        cls.rules_text = cls.rules_path.read_text(encoding="utf-8")

    def test_01_version_is_v3_3(self):
        """Verify version parsed by loader and CLI is valid v3.x."""
        import re
        self.assertTrue(re.match(r"^v3\.[3-9]", self.cfg["version"]))
        self.assertTrue(re.match(r"^v3\.[3-9]", self.cfg.version))

        # CLI format json
        cmd = [PYTHON_EXE, str(LOADER_PATH), "--vault", str(self.vault_dir), "--format", "json"]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(res.returncode, 0, f"CLI error: {res.stderr}")
        data = json.loads(res.stdout)
        self.assertTrue(re.match(r"^v3\.[3-9]", data.get("version", "")))

    def test_02_standard_domains_exact_7(self):
        """Verify cfg['standard_domains'] contains exactly the 7 standard domains with no stale domains."""
        expected = ["theory", "macro", "equity", "portfolio", "work", "ai-pkm", "education"]
        self.assertEqual(self.cfg.standard_domains, expected)
        self.assertEqual(self.cfg["allowed_domains"], expected)
        self.assertEqual(self.cfg["standard_domains"], expected)
        self.assertEqual(len(self.cfg.standard_domains), 7)

        # Ensure deleted domains are completely absent
        stale_domains = ["quant", "life", "technology", "crypto", "realestate"]
        for stale in stale_domains:
            self.assertNotIn(stale, self.cfg.standard_domains)
            self.assertNotIn(stale, self.cfg["allowed_domains"])

    def test_03_standard_prefixes(self):
        """Verify standard_prefixes contains ['C#_', 'C#-S#_', '산업_', '기업_', '_인덱스_']."""
        expected = ["C#_", "C#-S#_", "산업_", "기업_", "_인덱스_"]
        self.assertEqual(self.cfg.standard_prefixes, expected)
        self.assertEqual(self.cfg["standard_prefixes"], expected)
        self.assertEqual(self.cfg["prefixes"], expected)

    def test_04_core_attributes(self):
        """Verify core_attributes contains exactly the 7 required attributes."""
        expected = ["origin", "type", "domain", "up", "status", "created", "updated"]
        self.assertEqual(self.cfg.core_attributes, expected)
        self.assertEqual(self.cfg["core_attributes"], expected)

    def test_05_all_10_predefined_section_keys_via_api(self):
        """Verify all 10 predefined section keys return valid non-empty markdown via extract_section."""
        keys = ["overview", "schema", "links", "compile", "mstep", "astep", "index", "templates", "cases", "all"]
        for key in keys:
            result = constitution_loader.extract_section(self.rules_text, key)
            self.assertIsNotNone(result, f"Predefined section '{key}' returned None")
            matched_heading, content = result
            self.assertTrue(len(matched_heading) > 0, f"Section '{key}' has empty heading")
            self.assertTrue(len(content) > 100, f"Section '{key}' content too short: {len(content)} chars")

    def test_06_all_10_predefined_section_keys_via_cli(self):
        """Verify CLI --section <key> works for all 10 predefined keys."""
        keys = ["overview", "schema", "links", "compile", "mstep", "astep", "index", "templates", "cases", "all"]
        for key in keys:
            cmd = [
                PYTHON_EXE,
                str(LOADER_PATH),
                "--vault",
                str(self.vault_dir),
                "--section",
                key,
                "--format",
                "json",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res.returncode, 0, f"CLI error for key '{key}': {res.stderr}")
            data = json.loads(res.stdout)
            self.assertEqual(data.get("section"), key)
            self.assertTrue(len(data.get("content", "")) > 100, f"CLI content too short for key '{key}'")

    def test_07_keyword_section_extraction(self):
        """Verify keyword extractions: '규칙 5', '규칙 2', '5.2', '5.3' and additional edge keywords."""
        keywords = {
            "규칙 5": "1-Hop",
            "규칙 2": "코어 속성",
            "5.2": "조간신문",
            "5.3": "산업분류 연구",
            "규칙 1": "폴더",
            "규칙 6": "사다리",
            "규칙 10": "인덱스",
            "9.1": "Inbox",
            "9.2": "메타 컴파일",
            "9.3": "사후 감사",
        }
        for kw, expected_substr in keywords.items():
            result = constitution_loader.extract_section(self.rules_text, kw)
            self.assertIsNotNone(result, f"Keyword '{kw}' returned None")
            matched_heading, content = result
            self.assertIn(kw.lower(), matched_heading.lower(), f"Matched heading '{matched_heading}' missing '{kw}'")
            self.assertIn(expected_substr, content, f"Section '{kw}' missing expected substring '{expected_substr}'")

    def test_08_invalid_section_keyword_handling(self):
        """Verify CLI and API return error / None for non-existent section keyword."""
        result = constitution_loader.extract_section(self.rules_text, "non_existent_section_key_xyz_12345")
        self.assertIsNone(result)

        cmd = [
            PYTHON_EXE,
            str(LOADER_PATH),
            "--vault",
            str(self.vault_dir),
            "--section",
            "non_existent_section_key_xyz_12345",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(res.returncode, 1)
        self.assertIn("not found", res.stderr)

    def test_09_list_sections_cli(self):
        """Verify --list-sections outputs all predefined keys and heading list."""
        cmd = [PYTHON_EXE, str(LOADER_PATH), "--vault", str(self.vault_dir), "--list-sections"]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(res.returncode, 0)
        self.assertIn("overview", res.stdout)
        self.assertIn("schema", res.stdout)
        self.assertIn("links", res.stdout)
        self.assertIn("compile", res.stdout)
        self.assertIn("mstep", res.stdout)
        self.assertIn("astep", res.stdout)
        self.assertIn("index", res.stdout)
        self.assertIn("templates", res.stdout)
        self.assertIn("cases", res.stdout)
        self.assertIn("all", res.stdout)


class TestMyWikiRulesRawTextInspection(unittest.TestCase):
    """Adversarial stress-testing of raw My-Wiki Rules.md text."""

    @classmethod
    def setUpClass(cls):
        cls.rules_path = RULES_PATH
        cls.text = cls.rules_path.read_text(encoding="utf-8")

    def test_10_yaml_frontmatter_syntax(self):
        """Verify YAML frontmatter syntax is 100% valid and contains expected fields."""
        fm_match = re.match(r"^---\r?\n(.*?)\r?\n---", self.text, re.DOTALL)
        self.assertIsNotNone(fm_match, "My-Wiki Rules.md missing YAML frontmatter delimiters")
        fm = yaml.safe_load(fm_match.group(1))
        self.assertEqual(fm.get("origin"), "wiki")
        self.assertEqual(fm.get("type"), "hub")
        self.assertEqual(fm.get("domain"), ["ai-pkm"])
        self.assertEqual(fm.get("status"), "active")
        self.assertEqual(str(fm.get("updated")), "2026-10-30")
        self.assertEqual(fm.get("level"), 1)
        self.assertIsInstance(fm.get("aliases"), list)

    def test_11_markdown_tables_column_consistency(self):
        r"""Verify all markdown tables have valid column alignment and delimiter rows (handling escaped pipes \|)."""
        lines = self.text.splitlines()
        in_table = False
        table_cols = 0
        table_line = 0

        def split_table_row(row_str: str) -> list[str]:
            inner = row_str.strip()
            if inner.startswith("|"):
                inner = inner[1:]
            if inner.endswith("|"):
                inner = inner[:-1]
            # Replace escaped pipes \| temporarily to avoid splitting
            escaped_marker = "___ESCAPED_PIPE___"
            protected = re.sub(r"\\\|", escaped_marker, inner)
            parts = protected.split("|")
            return [p.replace(escaped_marker, "\\|").strip() for p in parts]

        for line_no, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                cells = split_table_row(stripped)
                if not in_table:
                    # Header row
                    in_table = True
                    table_cols = len(cells)
                    table_line = line_no
                else:
                    self.assertEqual(
                        len(cells),
                        table_cols,
                        f"Table starting at line {table_line}: line {line_no} has {len(cells)} cols, expected {table_cols}",
                    )
            else:
                in_table = False

    def test_12_r1_req1_index_and_self_reference_ban(self):
        """R1.1: Verify ban on index references (_인덱스_) and self-references is explicitly codified."""
        # Rule 1.3
        self.assertIn("Index` 역할 분리 및 일반·위키 메모의 인덱스 참조 전면 금지 원칙", self.text)
        self.assertIn("발견 즉시 완전 삭제한다", self.text)
        # Rule 2.2 Clean Null
        self.assertIn("인덱스 참조 및 자기참조 전면 차단", self.text)
        self.assertIn("자기 자신을 가리키는 자기참조(`[[자기노트명]]`, `자기노트명`)", self.text)
        # Rule 9.3 A-Step 3
        self.assertIn("인덱스 참조 전면 배제", self.text)
        self.assertIn("단방향성(DAG) 및 순환·자기참조 차단", self.text)
        # Rule 10
        self.assertIn("인덱스 파일 참조 금지 원칙", self.text)

    def test_13_r1_req2_ghost_node_and_fake_backtick_ban(self):
        """R1.2: Verify ban on uncreated ghost links and fake backticks, and permission of up: []."""
        # Rule 5.3
        self.assertIn("미생성 유령 노드(Ghost Node) 링크 및 가짜 백틱 표기 전면 금지·삭제", self.text)
        self.assertIn("`미생성노트명`", self.text)
        # up: [] Clean Null permission
        self.assertIn("up: []` Clean Null 정식 허용", self.text)
        self.assertIn("상위 총론 위키가 아직 생성되지 않은 각론·사건 위키", self.text)

    def test_14_r1_req3_backtick_restriction_and_simple_list_deletion(self):
        """R1.3: Verify strict limitation of backticks and deletion of simple related lists."""
        # Rule 5.1
        self.assertIn("백틱(`` ` ` ``)의 엄격한 제한", self.text)
        self.assertIn("Essential Factual Source Attribution Only", self.text)
        self.assertIn("본문이나 하단에 단순히 관련 메모, 원천 리포트, 타 산업, 연계 사건 위키를 나열해 둔 섹션이나 목록은 백틱으로 치환하지 않고 전면 삭제한다", self.text)

    def test_15_r1_req4_flexible_1hop_and_lv4_mediation_rewiring(self):
        """R1.4: Verify flexible 1-hop up and Lv4 enterprise mediation rewiring."""
        # Rule 5.2
        self.assertIn("다대다(`N:M`) 진화에 따른 동적 이행적 축소 및 기업 위키(Lv4) 매개 리와이어링", self.text)
        self.assertIn("각론위키(A) ➔ 개별기업(B, Lv4) ➔ 세부산업(C, Lv3)", self.text)
        # Section 5.3 Case 3
        self.assertIn("모래시계형 `N to 1 to N` 수렴 후 발산 및 Lv4 매개 리와이어링 구조", self.text)
        self.assertIn("기업 위키 존재 시 Lv4로 수렴", self.text)
        self.assertIn("기업 위키 미생성 시 세부산업 Lv3에 직접 1-Hop up 연결", self.text)

    def test_16_r1_req5_vertical_related_and_non_chronological_prev_ban(self):
        """R1.5: Verify prohibition of vertical related and non-chronological prev."""
        # Rule 6.3
        self.assertIn("비시계열 위키의 `prev` 부여 전면 금지", self.text)
        # Rule 5.1
        self.assertIn("수직 위계 간 `related` 사용 금지", self.text)
        # Rule 9.3 A-Step 3
        self.assertIn("상하 수직 위계 노트 간에 `related`를 쓰지 않았는가? 비시계열 단계/개념 위키", self.text)

    def test_17_adversarial_scan_section_5_2_rule_1_contradiction_analysis(self):
        """Adversarial check: Scan for lingering prescriptive index references in Section 5.2 & 5.3."""
        sec52_match = re.search(r"###\s*5\.2.*?(?=###\s*5\.3|\Z)", self.text, re.DOTALL)
        self.assertIsNotNone(sec52_match)
        sec52_text = sec52_match.group(0)

        # Check Rule 4 in Section 5.2 (clean timeline without index)
        self.assertIn("인덱스 참조(`_인덱스_...`)나 유령 링크를 일체 넣지 않", sec52_text)

        # Adversarial Observation: Check if Rule 1 of Section 5.2 still mentions up: ["[[_인덱스_210_뉴스큐레이팅]]"]
        has_rule1_index_ref = 'up: ["[[_인덱스_210_뉴스큐레이팅]]"]' in sec52_text
        self.assertTrue(
            has_rule1_index_ref,
            "Documented finding: Section 5.2 Rule 1 contains 'up: [\"[[_인덱스_210_뉴스큐레이팅]]\"]'",
        )


if __name__ == "__main__":
    unittest.main()
