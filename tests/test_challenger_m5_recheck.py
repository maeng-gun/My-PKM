"""Milestone 5 Gate Re-check: Adversarial Stress Test Suite.

Empirical verification harness by challenger_m5_recheck_2:
Task 1: vault_linter.py --fix does NOT mutate body text prose containing "[[]]".
Task 2: Unquoted up: [[]] is properly converted to up: [] by --fix.
Task 3: Non-wiki notes starting with 01_ are NOT exempt from orphan checks.
Task 4: Live vault ./My-Wiki passes with 0 violations.
Task 5: test_tier3_combinations.py passes reliably.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LINTER_SCRIPT = PROJECT_ROOT / ".agents" / "skills" / "pkm_manager" / "scripts" / "vault_linter.py"
LIVE_VAULT = PROJECT_ROOT / "My-Wiki"
TIER3_TEST = PROJECT_ROOT / "tests" / "e2e" / "test_tier3_combinations.py"

LEVEL_1_HUBS = [
    "01_경제 및 금융 이론.md",
    "02_매크로 분석.md",
    "03_산업 및 기업분석.md",
    "04_가족 투자 포트폴리오.md",
    "05_회사업무 (자산운용).md",
    "06_AI 활용 및 PKM 구축.md",
    "07_자녀교육.md",
]


class TestChallengerTask1BodyPreservation(unittest.TestCase):
    """Task 1: Verify that vault_linter.py --fix NEVER mutates body text prose."""

    def test_fix_does_not_mutate_complex_body_with_ghost_links(self):
        """Test with complex prose containing various ghost link citations."""
        complex_body = (
            "# Main Heading\n\n"
            "This is a paragraph explaining ghost links:\n"
            '1. Never use "[[]]" in frontmatter.\n'
            "2. Also avoid '[[]]' single quotes.\n"
            "3. Bare [[]] is also invalid.\n\n"
            "---\n\n"  # Markdown horizontal rule in body!
            "## Code Examples\n\n"
            "```python\n"
            'ghost = "[[]]"\n'
            "print(ghost)\n"
            "```\n\n"
            "Inline code like `[[]]` and `\"[[]]\"` should also be fine.\n\n"
            "---\n\n"  # Another horizontal rule
            "> Blockquote quoting someone:\n"
            '> "Always replace [[]] with clean null [] array."\n\n'
            "- Bullet item with [[]]\n"
            '- Another item with "[[]]"\n'
            "Ending thoughts.\n"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "100. Concepts").mkdir(parents=True)
            note_path = vault / "100. Concepts" / "ProseTest.md"

            frontmatter = (
                "---\n"
                "origin: human\n"
                "type: concept\n"
                "domain: [theory]\n"
                'up: "[[]]"\n'  # Needs fixing
                'see_also: "[[]]"\n'  # Needs fixing
                "status: active\n"
                "created: 2026-10-25\n"
                "updated: 2026-10-25\n"
                "---\n"
            )

            note_path.write_text(frontmatter + complex_body, encoding="utf-8")

            # Execute --fix
            res_fix = subprocess.run(
                [sys.executable, str(LINTER_SCRIPT), "--vault", str(vault), "--fix"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(res_fix.returncode, 1)  # May still have orphan violation since up became []

            content_after = note_path.read_text(encoding="utf-8")
            parts = content_after.split("---", 2)
            self.assertGreaterEqual(len(parts), 3, "Frontmatter delimiters must be intact")
            fm_after = parts[1]
            body_after = parts[2].lstrip("\r\n")

            # 1. Frontmatter must be fixed
            self.assertIn("up: []", fm_after)
            self.assertIn("see_also: []", fm_after)
            self.assertNotIn('"[[]]"', fm_after)

            # 2. Body must be 100% byte-for-byte identical to complex_body
            self.assertEqual(body_after, complex_body, "Body text was mutated by --fix!")

    def test_fix_with_no_frontmatter_leaves_file_untouched(self):
        """Test that files without frontmatter are untouched by --fix."""
        body_only = "# Standalone File\n\nNo frontmatter here, but mentions \"[[]]\".\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            vault.mkdir(parents=True)
            note_path = vault / "NoFM.md"
            note_path.write_text(body_only, encoding="utf-8")

            subprocess.run(
                [sys.executable, str(LINTER_SCRIPT), "--vault", str(vault), "--fix"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(note_path.read_text(encoding="utf-8"), body_only)


class TestChallengerTask2UnquotedGhostFix(unittest.TestCase):
    """Task 2: Verify that unquoted up: [[]] is properly converted to up: [] by --fix."""

    def test_various_unquoted_ghost_link_syntaxes(self):
        """Test single-line, whitespace-padded, multi-line list, and nested unquoted [[]]."""
        test_cases = [
            ("up: [[]]", "up: []"),
            ("up:  [[]]  ", "up: []"),
            ("up:\t[[]]", "up: []"),
            ("up:\n  - [[]]", "up: []"),
            ("up:\n  -  [[]]  ", "up: []"),
            ("up: [[[]]]", "up: []"),
            ("up: [ [[]] ]", "up: []"),
            ("prev:\n  - '[[02_매크로 분석]]'\n  - [[]]", "prev:\n  - '[[02_매크로 분석]]'\n  - []"),
        ]

        for raw_fm_field, expected_field in test_cases:
            with tempfile.TemporaryDirectory() as tmpdir:
                vault = Path(tmpdir) / "Vault"
                (vault / "400. Wiki").mkdir(parents=True)
                # Master hub so up: [] does not trigger C3 orphan error
                hub_path = vault / "400. Wiki" / "01_경제 및 금융 이론.md"

                if "up:" not in raw_fm_field:
                    up_line = "up: []\n"
                else:
                    up_line = ""

                fm = (
                    "---\n"
                    "origin: wiki\n"
                    "type: hub\n"
                    "level: 1\n"
                    "domain: [theory]\n"
                    f"{up_line}"
                    f"{raw_fm_field}\n"
                    "status: active\n"
                    "created: 2026-10-25\n"
                    "updated: 2026-10-25\n"
                    "---\n"
                    "# 01_경제 및 금융 이론\n"
                )
                hub_path.write_text(fm, encoding="utf-8")

                # Before --fix: must detect C2 violation
                res_before = subprocess.run(
                    [sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self.assertEqual(
                    res_before.returncode,
                    1,
                    f"Must detect ghost link for {raw_fm_field}: {res_before.stdout}",
                )
                self.assertIn("C2", res_before.stdout)

                # Execute --fix
                subprocess.run(
                    [sys.executable, str(LINTER_SCRIPT), "--vault", str(vault), "--fix"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )

                content_after = hub_path.read_text(encoding="utf-8")
                self.assertNotIn("[[]]", content_after.split("---", 2)[1], f"Ghost link not cleared for {raw_fm_field}")

                # After --fix: must pass cleanly with 0 violations
                res_after = subprocess.run(
                    [sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self.assertEqual(
                    res_after.returncode,
                    0,
                    f"Vault must pass with 0 errors after --fix for {raw_fm_field}:\n{res_after.stdout}",
                )


class TestChallengerTask3OrphanExemptions(unittest.TestCase):
    """Task 3: Verify non-wiki notes with names starting with 01_ are NOT exempt from orphan checks."""

    def test_non_wiki_notes_starting_with_01_through_07_are_flagged(self):
        """Notes in 100. Concepts or 500. etc starting with 01_~07_ with up: [] must trigger C3."""
        prefixes = [f"0{i}_" for i in range(1, 8)]

        for prefix in prefixes:
            # Test in 100. Concepts
            with tempfile.TemporaryDirectory() as tmpdir:
                vault = Path(tmpdir) / "Vault"
                (vault / "100. Concepts").mkdir(parents=True)
                note_file = vault / "100. Concepts" / f"{prefix}ConceptNote.md"
                note_file.write_text(
                    f"---\n"
                    f"origin: human\n"
                    f"type: concept\n"
                    f"domain: [theory]\n"
                    f"up: []\n"  # Empty up
                    f"status: active\n"
                    f"created: 2026-10-25\n"
                    f"updated: 2026-10-25\n"
                    f"---\n"
                    f"# {prefix}ConceptNote\n",
                    encoding="utf-8",
                )

                res = subprocess.run(
                    [sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self.assertEqual(
                    res.returncode,
                    1,
                    f"File {note_file.name} in 100. Concepts must NOT be exempt from orphan checks!",
                )
                self.assertIn("C3", res.stdout, f"Expected C3 violation for {note_file.name}")

            # Test in 500. etc
            with tempfile.TemporaryDirectory() as tmpdir:
                vault = Path(tmpdir) / "Vault"
                (vault / "500. etc").mkdir(parents=True)
                note_file = vault / "500. etc" / f"{prefix}PrivateNote.md"
                note_file.write_text(
                    f"---\n"
                    f"origin: human\n"
                    f"type: concept\n"
                    f"domain: [theory]\n"
                    f"up: []\n"  # Empty up
                    f"status: active\n"
                    f"created: 2026-10-25\n"
                    f"updated: 2026-10-25\n"
                    f"---\n"
                    f"# {prefix}PrivateNote\n",
                    encoding="utf-8",
                )

                res = subprocess.run(
                    [sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self.assertEqual(
                    res.returncode,
                    1,
                    f"File {note_file.name} in 500. etc must NOT be exempt from orphan checks!",
                )
                self.assertIn("C3", res.stdout, f"Expected C3 violation for {note_file.name}")

    def test_non_master_hub_in_400_wiki_starting_with_01_is_flagged(self):
        """A note in 400. Wiki starting with 01_ that is not an L1 master hub must be flagged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            note_file = vault / "400. Wiki" / "01_임의의_서브허브.md"
            note_file.write_text(
                "---\n"
                "origin: wiki\n"
                "type: hub\n"
                "level: 2\n"  # Level 2 hub, not Level 1!
                "domain: [theory]\n"
                "up: []\n"  # Level 2 hub cannot be orphan
                "status: active\n"
                "created: 2026-10-25\n"
                "updated: 2026-10-25\n"
                "---\n"
                "# 01_임의의_서브허브\n",
                encoding="utf-8",
            )
            res = subprocess.run(
                [sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(
                res.returncode,
                1,
                "Level 2 hub in 400. Wiki with up: [] must NOT be exempt from orphan checks!",
            )
            self.assertIn("C3", res.stdout)

    def test_all_seven_master_hubs_in_400_wiki_are_exempt(self):
        """All 7 genuine Level 1 Master Hubs in 400. Wiki must pass orphan check with up: []."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "400. Wiki").mkdir(parents=True)
            for hub_name in LEVEL_1_HUBS:
                (vault / "400. Wiki" / hub_name).write_text(
                    f"---\n"
                    f"origin: wiki\n"
                    f"type: hub\n"
                    f"level: 1\n"
                    f"domain: [theory]\n"
                    f"up: []\n"
                    f"status: active\n"
                    f"created: 2026-10-25\n"
                    f"updated: 2026-10-25\n"
                    f"---\n"
                    f"# {hub_name}\n",
                    encoding="utf-8",
                )
            res = subprocess.run(
                [sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(res.returncode, 0, f"All 7 Master Hubs must pass cleanly:\n{res.stdout}")


class TestChallengerTask4LiveVault(unittest.TestCase):
    """Task 4: Check that live vault ./My-Wiki passes with 0 violations."""

    def test_live_vault_zero_violations_all_formats(self):
        """Test live vault with text, markdown, and json output formats."""
        self.assertTrue(LIVE_VAULT.exists(), f"Live vault {LIVE_VAULT} must exist")

        # 1. JSON format verification
        res_json = subprocess.run(
            [sys.executable, str(LINTER_SCRIPT), "--vault", str(LIVE_VAULT), "--format", "json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(res_json.returncode, 0, f"Live vault audit returned non-zero:\n{res_json.stderr}\n{res_json.stdout}")
        data = json.loads(res_json.stdout)
        summary = data["summary"]
        self.assertGreaterEqual(summary["total_scanned"], 30, "Live vault should have at least 30 notes")
        self.assertEqual(summary["total_violations"], 0, f"Live vault has violations: {data.get('violations')}")
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["passed"], summary["total_scanned"])

        for check_key in ["C1", "C2", "C3", "C4", "C5"]:
            self.assertEqual(
                summary["violations_by_check"][check_key],
                0,
                f"Check {check_key} has violations in live vault!",
            )

        # 2. Markdown format verification
        res_md = subprocess.run(
            [sys.executable, str(LINTER_SCRIPT), "--vault", str(LIVE_VAULT), "--format", "markdown"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(res_md.returncode, 0)
        self.assertIn("Result: 100% Compliant (0 errors)", res_md.stdout)

        # 3. Check specific key files in live vault
        karpathy_path = LIVE_VAULT / "300. Sources" / "Karpathy's LLM Wiki.md"
        if karpathy_path.exists():
            content = karpathy_path.read_text(encoding="utf-8")
            self.assertIn("origin: source", content, "Karpathy note must have origin: source")

        rule_path = LIVE_VAULT / "400. Wiki" / "옵시디언 메모간 링크 연결 규칙 설계.md"
        if rule_path.exists():
            sys.path.insert(0, str(LINTER_SCRIPT.parent))
            from vault_linter import audit_markdown_note
            violations = audit_markdown_note(rule_path, LIVE_VAULT)
            self.assertEqual(len(violations), 0, f"Rule doc failed audit: {violations}")


class TestChallengerTask5Tier3Reliability(unittest.TestCase):
    """Task 5: Check that test_tier3_combinations.py passes reliably."""

    def test_tier3_repeated_runs_reliability(self):
        """Run test_tier3_combinations.py 5 consecutive times to prove absence of race conditions."""
        self.assertTrue(TIER3_TEST.exists(), f"Tier 3 test missing at {TIER3_TEST}")

        for iteration in range(1, 6):
            res = subprocess.run(
                [sys.executable, str(TIER3_TEST)],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(
                res.returncode,
                0,
                f"Iteration {iteration}/5 failed:\nStdout:\n{res.stdout}\nStderr:\n{res.stderr}",
            )
            self.assertIn("OK", res.stderr or res.stdout, f"Iteration {iteration}/5 did not report OK")


if __name__ == "__main__":
    unittest.main(verbosity=2)
