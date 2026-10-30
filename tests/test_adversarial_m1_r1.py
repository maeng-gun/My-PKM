"""Adversarial stress test suite for Milestone 1 (R1: Master Constitution Amendment).

Authored by empirical_challenger (challenger_m1_2).
Verifies:
1. Dynamic SSOT loading of live ./My-Wiki via constitution_loader.py:
   - cfg['version'] == 'v3.3'
   - cfg['standard_domains'] has exactly 7 standard domains (no quant, life)
   - cfg['standard_prefixes'] == ['C#_', 'C#-S#_', '산업_', '기업_', '_인덱스_']
   - 10 predefined section keys extraction (overview, schema, links, compile, mstep, astep, index, templates, cases, all)
   - Keyword extractions: "규칙 5", "규칙 2", "5.2", "5.3"
2. My-Wiki Rules.md raw text integrity:
   - YAML frontmatter parsing and clean null conformance
   - Markdown table syntax verification across all tables
   - Verification of the 5 specific R1 requirements
   - Ghost link / index reference / self reference audit
"""

from pathlib import Path
import re
import subprocess
import sys
import unittest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / ".agents" / "skills" / "pkm_manager" / "scripts"
CONSTITUTION_LOADER_PATH = SCRIPTS_DIR / "constitution_loader.py"
LIVE_VAULT_PATH = PROJECT_ROOT / "My-Wiki"
RULES_PATH = LIVE_VAULT_PATH / "My-Wiki Rules.md"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import constitution_loader


class TestConstitutionLoaderRobustness(unittest.TestCase):
    """Stress test constitution_loader against live My-Wiki."""

    def setUp(self):
        self.assertTrue(LIVE_VAULT_PATH.exists(), "Live My-Wiki vault must exist")
        self.assertTrue(RULES_PATH.exists(), "Live My-Wiki Rules.md must exist")
        self.cfg = constitution_loader.load_constitution(LIVE_VAULT_PATH)
        self.rules_text = RULES_PATH.read_text(encoding="utf-8")

    def test_01_version_is_v3_3(self):
        """Verify dynamic parser identifies valid v3.x constitution version."""
        import re
        self.assertTrue(re.match(r"^v3\.[3-9]", self.cfg.version))
        self.assertTrue(re.match(r"^v3\.[3-9]", self.cfg["version"]))

    def test_02_standard_domains_exact_7(self):
        """Verify standard domains contain exactly 7 expected domains without stale items."""
        expected_domains = [
            "theory",
            "macro",
            "equity",
            "portfolio",
            "work",
            "ai-pkm",
            "education",
        ]
        self.assertEqual(self.cfg.standard_domains, expected_domains)
        self.assertEqual(self.cfg["standard_domains"], expected_domains)
        self.assertEqual(self.cfg["allowed_domains"], expected_domains)
        self.assertNotIn("quant", self.cfg.standard_domains)
        self.assertNotIn("life", self.cfg.standard_domains)
        self.assertEqual(len(self.cfg.standard_domains), 7)

    def test_03_standard_prefixes(self):
        """Verify standard filename prefixes extracted correctly."""
        expected_prefixes = ["C#_", "C#-S#_", "산업_", "기업_", "_인덱스_"]
        self.assertEqual(self.cfg.standard_prefixes, expected_prefixes)
        self.assertEqual(self.cfg["standard_prefixes"], expected_prefixes)

    def test_04_all_10_predefined_sections(self):
        """Verify all 10 predefined section keys extract non-empty valid markdown."""
        keys = [
            "overview",
            "schema",
            "links",
            "compile",
            "mstep",
            "astep",
            "index",
            "templates",
            "cases",
            "all",
        ]
        for key in keys:
            res = constitution_loader.extract_section(self.rules_text, key)
            self.assertIsNotNone(res, f"Predefined section '{key}' extraction returned None")
            heading, content = res
            self.assertTrue(len(content.strip()) > 50, f"Section '{key}' returned unexpectedly small content ({len(content)})")
            self.assertTrue(content.startswith(heading) or key == "all", f"Section '{key}' does not start with heading: {heading}")

            # Also verify via CLI subprocess execution
            cmd = [
                sys.executable,
                str(CONSTITUTION_LOADER_PATH),
                "--vault",
                str(LIVE_VAULT_PATH),
                "--section",
                key,
                "--format",
                "text",
            ]
            run_res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(run_res.returncode, 0, f"CLI extraction for '{key}' failed: {run_res.stderr}")
            self.assertIn(heading, run_res.stdout)

    def test_05_keyword_extractions(self):
        """Verify keyword extractions: '규칙 5', '규칙 2', '5.2', '5.3'."""
        keywords = ["규칙 5", "규칙 2", "5.2", "5.3"]
        for kw in keywords:
            res = constitution_loader.extract_section(self.rules_text, kw)
            self.assertIsNotNone(res, f"Keyword extraction for '{kw}' returned None")
            heading, content = res
            self.assertIn(kw.lower(), heading.lower(), f"Matched heading '{heading}' does not contain keyword '{kw}'")
            self.assertTrue(len(content.strip()) > 100, f"Keyword '{kw}' content too short ({len(content)})")

            # Verify CLI
            cmd = [
                sys.executable,
                str(CONSTITUTION_LOADER_PATH),
                "--vault",
                str(LIVE_VAULT_PATH),
                "--section",
                kw,
                "--format",
                "text",
            ]
            run_res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(run_res.returncode, 0, f"CLI keyword extraction for '{kw}' failed: {run_res.stderr}")
            self.assertIn(heading, run_res.stdout)


class TestConstitutionRawTextIntegrity(unittest.TestCase):
    """Stress test raw content, tables, and R1 requirements in My-Wiki Rules.md."""

    def setUp(self):
        self.rules_text = RULES_PATH.read_text(encoding="utf-8")

    def test_06_yaml_frontmatter_syntax_and_values(self):
        """Verify frontmatter is valid YAML and adheres to constitution schema."""
        match = re.match(r"^---\r?\n(.*?)\r?\n---", self.rules_text, re.DOTALL)
        self.assertIsNotNone(match, "My-Wiki Rules.md must have valid YAML frontmatter delimiters")
        fm = yaml.safe_load(match.group(1))
        self.assertIsInstance(fm, dict)
        self.assertEqual(fm.get("origin"), "wiki")
        self.assertEqual(fm.get("type"), "hub")
        self.assertEqual(fm.get("domain"), ["ai-pkm"])
        self.assertEqual(fm.get("up"), ["[[06_AI 활용 및 PKM 구축]]"])
        self.assertEqual(fm.get("status"), "active")
        self.assertEqual(str(fm.get("updated")), "2026-10-30")

    def test_07_all_markdown_tables_syntax(self):
        """Stress-test: Validate every markdown table has consistent column count across header, separator, and data rows."""
        lines = self.rules_text.splitlines()
        in_table = False
        table_rows = []
        table_count = 0

        def split_table_row(row_str: str):
            inner = row_str.strip()
            if inner.startswith("|"):
                inner = inner[1:]
            if inner.endswith("|"):
                inner = inner[:-1]
            return [t.strip() for t in re.split(r"(?<!\\)\|", inner)]

        for line_no, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                in_table = True
                cells = split_table_row(stripped)
                table_rows.append((line_no, cells))
            else:
                if in_table:
                    # Validate completed table
                    self.assertGreaterEqual(len(table_rows), 2, f"Table ending at line {line_no-1} has less than 2 rows")
                    header_line, header_cells = table_rows[0]
                    col_count = len(header_cells)
                    # Separator row must be line 1
                    sep_line, sep_cells = table_rows[1]
                    self.assertEqual(len(sep_cells), col_count, f"Table separator line {sep_line} column count mismatch: expected {col_count}, got {len(sep_cells)}")
                    for c in sep_cells:
                        self.assertTrue(re.match(r"^:?-+:?$", c), f"Invalid separator cell '{c}' at line {sep_line}")

                    for r_line, r_cells in table_rows[2:]:
                        self.assertEqual(len(r_cells), col_count, f"Table data row at line {r_line} column count mismatch: expected {col_count}, got {len(r_cells)}")

                    table_count += 1
                    in_table = False
                    table_rows = []

        self.assertGreaterEqual(table_count, 6, f"Expected at least 6 markdown tables, found {table_count}")

    def test_08_r1_req1_index_and_self_reference_ban(self):
        """Verify R1.1: Complete ban on referencing index files and self-references."""
        # 1. Check Rule 1.3
        self.assertIn("`500. Index` 역할 분리 및 일반·위키 메모의 인덱스 참조 전면 금지 원칙", self.rules_text)
        # 2. Check Section 5.2 Case 2: old [[_인덱스_210_뉴스큐레이팅]] reference in Case 2 Rule 4 must NOT exist as mandatory monitoring registry link
        sec5_2_res = constitution_loader.extract_section(self.rules_text, "5.2")
        self.assertIsNotNone(sec5_2_res)
        _, sec5_2_content = sec5_2_res
        self.assertNotIn("모니터링 레지스트리는 파이프 별칭 없이 순수 [[_인덱스_210_뉴스큐레이팅]]으로 연결한다", sec5_2_content)
        # 3. Check Rule 10 ban
        self.assertIn("인덱스 파일 참조 금지 원칙", self.rules_text)
        # 4. Check Rule 2.2 self-reference ban
        self.assertIn("자기 자신을 가리키는 자기참조", self.rules_text)

    def test_09_r1_req2_ghost_node_and_fake_backtick_ban_and_clean_null(self):
        """Verify R1.2: Complete ban on ghost node links AND fake note-name backticks, and up: [] clean null allowance."""
        # Check Rule 2.2 clean null allowance
        self.assertIn("`up: []` Clean Null 정식 허용", self.rules_text)
        self.assertIn("상위 총론 위키가 아직 생성되지 않은 각론·사건 위키", self.rules_text)
        # Check Rule 5.3 ghost link and fake backtick ban
        rule5_res = constitution_loader.extract_section(self.rules_text, "규칙 5")
        self.assertIsNotNone(rule5_res)
        _, rule5_content = rule5_res
        self.assertIn("미생성 유령 노드(Ghost Node) 링크 및 가짜 백틱 표기 전면 금지·삭제", rule5_content)
        self.assertIn("가짜 노트명 형태의 백틱 표기", rule5_content)

    def test_10_r1_req3_backtick_strictly_essential_attribution_and_delete_mere_lists(self):
        """Verify R1.3: Backticks strictly limited to essential source attribution; delete mere lists."""
        rule5_res = constitution_loader.extract_section(self.rules_text, "규칙 5")
        _, rule5_content = rule5_res
        self.assertIn("Essential Factual Source Attribution Only", rule5_content)
        self.assertIn("단순히 관련 메모, 원천 리포트, 타 산업, 연계 사건 위키를 나열해 둔 섹션이나 목록은 백틱으로 치환하지 않고 전면 삭제", rule5_content)

    def test_11_r1_req4_flexible_1hop_and_lv4_mediation_rewiring(self):
        """Verify R1.4: Flexible 1-hop and enterprise wiki (Lv4) mediation rewiring."""
        rule5_res = constitution_loader.extract_section(self.rules_text, "규칙 5")
        _, rule5_content = rule5_res
        self.assertIn("기업 위키(Lv4) 매개 리와이어링", rule5_content)
        self.assertIn("`A ➔ C(Lv3)` 직접 연결을 끊고", rule5_content)
        self.assertIn("`각론위키(A) ➔ 개별기업(B, Lv4) ➔ 세부산업(C, Lv3)`으로 매개(Re-wiring)", rule5_content)
        self.assertIn("`A ➔ B ➔ C`의 1-Hop 사슬", self.rules_text)

        sec5_3_res = constitution_loader.extract_section(self.rules_text, "5.3")
        self.assertIsNotNone(sec5_3_res)
        _, sec5_3_content = sec5_3_res
        self.assertIn("모래시계형 `N to 1 to N` 수렴 후 발산 및 Lv4 매개 리와이어링", sec5_3_content)
        self.assertIn("기업 위키를 매개로 연결(`각론위키 ➔ 기업위키(Lv4) ➔ 세부산업(Lv3)`)하며", sec5_3_content)

    def test_12_r1_req5_vertical_related_and_non_chronological_prev_banned(self):
        """Verify R1.5: Prohibition of vertical related and non-chronological prev."""
        self.assertIn("수직 위계 간 `related` 사용 금지", self.rules_text)
        self.assertIn("비시계열 위키의 `prev` 부여 전면 금지", self.rules_text)
        self.assertIn("C1-S1", self.rules_text)


if __name__ == "__main__":
    unittest.main()
