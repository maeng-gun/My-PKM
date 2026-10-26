"""Adversarial Challenge Test Suite for Milestone 3 (F4 AGENTS.md Constitution & F5 PKM Manager Skill).

Authored by Challenger 2 (teamwork_preview_challenger).
Validates human sovereignty, binary isolation, Clean Null rule consistency,
persona preservation, and edge cases.
"""

import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGENTS_MD_PATH = PROJECT_ROOT / "AGENTS.md"
SKILL_MD_PATH = PROJECT_ROOT / ".agents" / "skills" / "pkm_manager" / "SKILL.md"


class TestM3AdversarialSovereigntyAndBinaryIsolation(unittest.TestCase):
    """Adversarial stress-testing of Human Write Sovereignty and Binary Isolation."""

    def setUp(self):
        self.assertTrue(AGENTS_MD_PATH.exists(), f"AGENTS.md missing at {AGENTS_MD_PATH}")
        self.assertTrue(SKILL_MD_PATH.exists(), f"SKILL.md missing at {SKILL_MD_PATH}")
        self.agents_text = AGENTS_MD_PATH.read_text(encoding="utf-8")
        self.skill_text = SKILL_MD_PATH.read_text(encoding="utf-8")

    def test_adv_01_human_sovereignty_protected_folders_in_agents_md(self):
        """Stress-test: Ensure 100. Concepts (including 110, 120) and 500. etc are explicitly protected."""
        self.assertIn("100. Concepts", self.agents_text)
        self.assertIn("500. etc", self.agents_text)
        self.assertIn("110. Notes", self.agents_text)
        self.assertIn("120. Logs", self.agents_text)

        # Unprompted write/overwrite prohibition
        self.assertRegex(
            self.agents_text,
            r"(명시적.*지시|승인).*(임의로.*노트|생성|덮어쓰|Unprompted)",
            "AGENTS.md must strictly forbid unprompted write/overwrite in human sovereignty areas",
        )

    def test_adv_02_human_sovereignty_protected_folders_in_skill_md(self):
        """Stress-test: Ensure SKILL.md marks 100. Concepts and 500. etc with human sovereignty."""
        self.assertIn("100. Concepts", self.skill_text)
        self.assertIn("500. etc", self.skill_text)
        self.assertIn("희명님 전용", self.skill_text)

        # Warning block check
        self.assertIn("인간 주권 침해 금지", self.skill_text)
        self.assertRegex(
            self.skill_text,
            r"(100\.\s*Concepts.*500\.\s*etc|인간 주권).*(임의로.*노트.*생성|덮어쓰|overwrite)",
            "SKILL.md must have warning against overwriting human sovereignty folders",
        )

    def test_adv_03_ai_write_allowed_folders_strictly_bounded(self):
        """Stress-test: Verify that AI autonomous write is strictly partitioned and bounded."""
        ai_allowed_match = re.search(
            r"AI 에이전트 작업 허용 영역.*?:\s*(.*?)(?=\n###|\n##)",
            self.agents_text,
            re.DOTALL,
        )
        self.assertIsNotNone(ai_allowed_match, "AGENTS.md must define AI allowed write section")
        allowed_section = ai_allowed_match.group(1)
        self.assertIn("200. AI_logs", allowed_section)
        self.assertIn("300. Sources", allowed_section)
        self.assertIn("400. Wiki", allowed_section)
        self.assertNotIn("100. Concepts", allowed_section)
        self.assertNotIn("500. etc", allowed_section)

    def test_adv_04_inbox_triage_does_not_auto_write_to_100_concepts(self):
        """Stress-test: Verify that Workflow 3 note triage instructs suggesting movement rather than auto-writing."""
        self.assertIn("000. Inbox", self.skill_text)
        self.assertRegex(
            self.skill_text,
            r"(인간의 사유|100\.\s*Concepts).*(제안|안내|주권)",
            "SKILL.md Workflow 3 triage must guide/suggest moving human notes to 100. Concepts, not auto-write",
        )

    def test_adv_05_vault_binary_isolation_comprehensive_extensions(self):
        """Stress-test: Verify binary isolation covers all specified binary types."""
        binary_types = ["HWP", "HWPX", "PDF", "XLSX", "DOCX", "PPTX"]
        for b_type in binary_types:
            self.assertIn(b_type, self.agents_text, f"AGENTS.md must mention binary type {b_type}")
            self.assertIn(b_type, self.skill_text, f"SKILL.md must mention binary type {b_type}")

        # Check external queue folders
        self.assertIn("Inbox_Raw", self.agents_text)
        self.assertIn("Archive_Sources", self.agents_text)
        self.assertIn("Inbox_Raw", self.skill_text)
        self.assertIn("Archive_Sources", self.skill_text)

    def test_adv_06_vault_linter_c5_allows_only_910_attached_exception(self):
        """Stress-test: Verify C5 linter check explicitly permits only 910. Attached for images/diagrams."""
        self.assertIn("C5", self.skill_text)
        self.assertIn("910. Attached", self.skill_text)
        self.assertRegex(
            self.skill_text,
            r"(900\.\s*config/910\.\s*Attached|허용 이미지/다이어그램)",
            "SKILL.md C5 check must scope binary exceptions strictly to 910. Attached",
        )


class TestM3AdversarialCleanNullAndGhostLinks(unittest.TestCase):
    """Adversarial stress-testing of Clean Null rule ([] vs '[[]]')."""

    def setUp(self):
        self.agents_text = AGENTS_MD_PATH.read_text(encoding="utf-8")
        self.skill_text = SKILL_MD_PATH.read_text(encoding="utf-8")

    def test_adv_07_clean_null_explicitly_contrasts_empty_brackets_in_agents(self):
        """Stress-test: Verify AGENTS.md explicitly states '[]' and forbids '[[]]'."""
        self.assertIn('"[[]]"', self.agents_text, "AGENTS.md must cite ghost link form '[[]]'")
        self.assertIn("[]", self.agents_text, "AGENTS.md must specify clean null form []")
        self.assertRegex(
            self.agents_text,
            r'절대로\s*`?"\[\[\]\]"`?.*반드시\s*`?\[\]`?',
            "AGENTS.md must explicitly forbid '[[]]' and mandate []",
        )

    def test_adv_08_clean_null_explicitly_contrasts_empty_brackets_in_skill(self):
        """Stress-test: Verify SKILL.md explicitly states '[]' and forbids '[[]]'."""
        self.assertIn('"[[]]"', self.skill_text, "SKILL.md must cite ghost link form '[[]]'")
        self.assertIn("[]", self.skill_text, "SKILL.md must specify clean null form []")
        self.assertRegex(
            self.skill_text,
            r'절대로\s*`?"\[\[\]\]"`?.*반드시\s*`?\[\]`?',
            "SKILL.md must explicitly forbid '[[]]' and mandate []",
        )

    def test_adv_09_clean_null_in_ingestion_and_linter_workflows(self):
        """Stress-test: Verify Workflows 2 and 5 in SKILL.md mandate [] and --fix for '[[]]'."""
        # Workflow 2 Ingestion check
        self.assertRegex(
            self.skill_text,
            r'(빈 링크 배열|up).*(반드시\s*`?\[\]`?|유령 링크\s*`?"\[\[\]\]"`?)',
            "SKILL.md Workflow 2 must mandate [] to prevent ghost links",
        )
        # Workflow 5 C2 check
        self.assertIn("C2", self.skill_text)
        self.assertIn("--fix", self.skill_text)
        self.assertRegex(
            self.skill_text,
            r'C2\.\s*유령 링크[\s\S]*?`?"\[\[\]\]"`?[\s\S]*?--fix[\s\S]*?`?\[\]`?',
            "SKILL.md Workflow 5 C2 must specify replacing '[[]]' with []",
        )

    def test_adv_10_no_unquoted_ghost_link_accidental_usage_in_markdown(self):
        """Stress-test: Verify that neither AGENTS.md nor SKILL.md contains unintentional ghost links."""
        for path, text in [(AGENTS_MD_PATH, self.agents_text), (SKILL_MD_PATH, self.skill_text)]:
            lines = text.splitlines()
            for line_no, line in enumerate(lines, 1):
                if "[[]]" in line:
                    self.assertTrue(
                        ('"[[]]"' in line or "'[[]]'" in line or '`"[[]]"`' in line or "`[[]]`" in line),
                        f"Line {line_no} in {path.name} contains unquoted raw ghost link: {line}",
                    )


class TestM3AdversarialPersonaAndWorkflowIntegrity(unittest.TestCase):
    """Adversarial stress-testing of Persona Preservation and 5 Workflows."""

    def setUp(self):
        self.agents_text = AGENTS_MD_PATH.read_text(encoding="utf-8")
        self.skill_text = SKILL_MD_PATH.read_text(encoding="utf-8")

    def test_adv_11_all_8_macro_asset_classes_strictly_preserved(self):
        """Stress-test: Verify that all 8 macro asset classes are preserved in AGENTS.md."""
        expected_classes = [
            "귀금속",
            "원자재",
            "인컴자산",
            "국내주식",
            "해외주식",
            "국내채권",
            "해외채권",
            "만기보유채권 및 현금성",
        ]
        for asset in expected_classes:
            self.assertIn(asset, self.agents_text, f"AGENTS.md missing asset class: {asset}")

    def test_adv_12_all_4_orthogonal_parameters_strictly_preserved(self):
        """Stress-test: Verify that Direction, Horizon, Signal, Impact guidelines are intact."""
        self.assertIn("Direction (방향성)", self.agents_text)
        self.assertIn("Horizon (시계)", self.agents_text)
        self.assertIn("Signal (신뢰도)", self.agents_text)
        self.assertIn("Impact (영향 강도 및 민감도)", self.agents_text)
        self.assertIn("calculate_metrics.py", self.agents_text)
        self.assertIn("LLM의 부동소수점 수학 연산 엄격 금지", self.agents_text)

    def test_adv_13_supabase_security_and_atomic_migration_preserved(self):
        """Stress-test: Verify Supabase RLS and atomic unit migration rules in AGENTS.md."""
        self.assertIn("SUPABASE_SERVICE_ROLE_KEY", self.agents_text)
        self.assertIn("Row Level Security", self.agents_text)
        self.assertIn("원자적 단위", self.agents_text)
        self.assertIn("CREATE POLICY", self.agents_text)

    def test_adv_14_all_7_core_yaml_attributes_defined(self):
        """Stress-test: Verify 7 mandatory frontmatter keys in SKILL.md and AGENTS.md."""
        core_keys = ["origin", "type", "domain", "up", "status", "created", "updated"]
        for key in core_keys:
            self.assertRegex(self.skill_text, rf"{key}:", f"SKILL.md must define core key '{key}'")
            self.assertIn(f"`{key}`", self.agents_text, f"AGENTS.md must define core key '{key}'")

    def test_adv_15_all_7_standard_domain_codes_defined(self):
        """Stress-test: Verify 7 standard domain codes in SKILL.md."""
        domain_codes = ["theory", "macro", "equity", "portfolio", "work", "ai-pkm", "education"]
        for code in domain_codes:
            self.assertIn(f"`{code}`", self.skill_text, f"SKILL.md must define domain code '{code}'")

    def test_adv_16_all_5_workflows_explicitly_numbered_and_detailed(self):
        """Stress-test: Verify Workflows 1 through 5 in SKILL.md."""
        self.assertIn("Workflow 1:", self.skill_text)
        self.assertIn("Workflow 2:", self.skill_text)
        self.assertIn("Workflow 3:", self.skill_text)
        self.assertIn("Workflow 4:", self.skill_text)
        self.assertIn("Workflow 5:", self.skill_text)
        self.assertIn("ingest_sources.py", self.skill_text)
        self.assertIn("vault_linter.py", self.skill_text)
        self.assertIn("vault_patch", self.skill_text)
        self.assertIn("400. Wiki", self.skill_text)


if __name__ == "__main__":
    unittest.main()
