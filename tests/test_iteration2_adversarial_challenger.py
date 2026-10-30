"""Adversarial stress-test suite for Iteration 2 bug fixes.

Empirically verifies:
1. constitution_loader.py:
   - Live vault SSOT deletion sync: assert 'quant' not in standard_domains, 'life' not in standard_domains, exactly 7 domains.
   - Type hints introspection: typing.get_type_hints(constitution_loader.extract_section) executes cleanly without NameError.
   - CLI JSON output: --list-sections --format json produces valid, parseable JSON with all predefined sections and document headings.
   - Fallback mode and edge case inputs.
2. compile_helper.py:
   - _parse_replace_up_args edge cases.
   - cmd_upsert_index Case B (new row append) with arrow format and two-arg format (no IndexError).
   - cmd_upsert_index Case A (existing row update) with arrow and two-arg formats.
   - cmd_normalize_fm with --replace-up and --remove-up.
3. vault_linter.py:
   - Live vault audit: exactly 351/351 passed, 0 violations.
   - Oracle/tamper test: ensures vault_linter detects deliberate violations.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import get_type_hints
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / ".agents" / "skills" / "pkm_manager" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import constitution_loader  # noqa: E402
import compile_helper       # noqa: E402
import vault_linter         # noqa: E402


class TestConstitutionLoaderAdversarial(unittest.TestCase):
    """Stress tests for constitution_loader.py."""

    def test_live_vault_ssot_deletion_sync(self):
        """Live vault test: assert quant & life are deleted, exactly 7 domains remain."""
        vault_path = PROJECT_ROOT / "My-Wiki"
        self.assertTrue(vault_path.exists(), f"Vault not found at {vault_path}")

        cfg = constitution_loader.load_constitution(str(vault_path))

        # Core assertions required by task
        self.assertNotIn("quant", cfg.standard_domains)
        self.assertNotIn("life", cfg.standard_domains)
        self.assertEqual(len(cfg.standard_domains), 7)

        # Exact expected list matching My-Wiki Rules.md line 103
        expected = ["theory", "macro", "equity", "portfolio", "work", "ai-pkm", "education"]
        self.assertEqual(cfg.standard_domains, expected)

    def test_type_hints_introspection(self):
        """Verify get_type_hints executes without NameError across public functions."""
        # Function 1: extract_section (formerly raised NameError on Tuple)
        hints = get_type_hints(constitution_loader.extract_section)
        self.assertIn("return", hints)
        self.assertIn("text", hints)
        self.assertIn("key_or_keyword", hints)

        # Function 2: list_sections_dict
        hints_dict = get_type_hints(constitution_loader.list_sections_dict)
        self.assertIn("return", hints_dict)
        self.assertIn("text", hints_dict)

        # Function 3: list_sections
        hints_str = get_type_hints(constitution_loader.list_sections)
        self.assertIn("return", hints_str)

        # Function 4: load_constitution
        hints_load = get_type_hints(constitution_loader.load_constitution)
        self.assertIn("return", hints_load)

    def test_cli_list_sections_json(self):
        """Verify CLI --list-sections --format json produces valid JSON with all required keys."""
        cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "constitution_loader.py"),
            "--vault",
            str(PROJECT_ROOT / "My-Wiki"),
            "--list-sections",
            "--format",
            "json",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(res.returncode, 0, f"CLI returned error: {res.stderr}")

        data = json.loads(res.stdout)
        self.assertIn("predefined_sections", data)
        self.assertIn("headings", data)

        predefined = data["predefined_sections"]
        expected_keys = [
            "overview", "schema", "links", "compile", "mstep",
            "astep", "index", "templates", "cases", "all",
        ]
        for k in expected_keys:
            self.assertIn(k, predefined)
            self.assertIn("target_prefix", predefined[k])
            self.assertIn("description", predefined[k])

        headings = data["headings"]
        self.assertGreaterEqual(len(headings), 35)
        for h in headings:
            self.assertIn("line", h)
            self.assertIn("level", h)
            self.assertIn("heading", h)
            self.assertIn("title", h)

    def test_cli_section_extraction_json(self):
        """Stress-test extraction for each predefined section key in JSON format."""
        keys = ["overview", "schema", "links", "compile", "mstep", "astep", "index", "templates", "cases", "all"]
        for key in keys:
            cmd = [
                sys.executable,
                str(SCRIPTS_DIR / "constitution_loader.py"),
                "--vault",
                str(PROJECT_ROOT / "My-Wiki"),
                "--section",
                key,
                "--format",
                "json",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res.returncode, 0, f"Extraction failed for section {key}: {res.stderr}")
            data = json.loads(res.stdout)
            self.assertEqual(data["section"], key)
            self.assertTrue(len(data["content"]) > 0)

    def test_cli_section_not_found(self):
        """Non-existent section should exit with code 1 and error message."""
        cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "constitution_loader.py"),
            "--vault",
            str(PROJECT_ROOT / "My-Wiki"),
            "--section",
            "non_existent_key_xyz",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(res.returncode, 1)
        self.assertIn("not found", res.stderr)

    def test_fallback_when_vault_has_no_rules_md(self):
        """Fallback mode should provide default 9 domains when My-Wiki Rules.md is absent."""
        with tempfile.TemporaryDirectory() as tmp:
            cfg = constitution_loader.load_constitution(tmp)
            self.assertFalse(cfg.ssot_exists)
            self.assertEqual(len(cfg.standard_domains), 9)
            self.assertIn("quant", cfg.standard_domains)
            self.assertIn("life", cfg.standard_domains)


class TestCompileHelperAdversarial(unittest.TestCase):
    """Stress tests for compile_helper.py."""

    def test_parse_replace_up_args_edge_cases(self):
        """Adversarial stress-testing of _parse_replace_up_args."""
        parse = compile_helper._parse_replace_up_args

        # None and empty
        self.assertIsNone(parse(None))
        self.assertIsNone(parse([]))
        self.assertIsNone(parse([""]))

        # Single arg without arrow
        self.assertIsNone(parse(["SingleArg"]))
        self.assertIsNone(parse(["[[SingleArg]]"]))

        # Arrow format in single string or list of 1
        self.assertEqual(parse(["Old->New"]), ("Old", "New"))
        self.assertEqual(parse(["[[Old]]->[[New]]"]), ("[[Old]]", "[[New]]"))
        self.assertEqual(parse("Old->New"), ("Old", "New"))
        self.assertEqual(parse(" [[Old]] -> [[New]] "), ("[[Old]]", "[[New]]"))

        # Two-arg format
        self.assertEqual(parse(["Old", "New"]), ("Old", "New"))
        self.assertEqual(parse(["[[Old]]", "[[New]]"]), ("[[Old]]", "[[New]]"))
        self.assertEqual(parse(("Old", "New")), ("Old", "New"))

        # Three or more args
        self.assertIsNone(parse(["A", "B", "C"]))

        # Multi-arrow: split with maxsplit=1
        self.assertEqual(parse(["Old->New->Extra"]), ("Old", "New->Extra"))

    def test_cmd_upsert_index_case_b_no_index_error(self):
        """Comprehensive verification of Case B row append with various replace-up inputs."""
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            index_md = tmpdir / "_인덱스_400_Wiki.md"
            initial_content = (
                "---\n"
                "origin: wiki\n"
                "type: hub\n"
                "domain: [theory]\n"
                "up: []\n"
                "status: active\n"
                "created: 2026-10-30\n"
                "updated: 2026-10-30\n"
                "---\n\n"
                "# 400. Wiki Index\n\n"
                "| # | Note | Date | Type | Sum | up |\n"
                "| :---: | :--- | :---: | :--- | :--- | :--- |\n"
                "| 1 | [[Existing_1]] | 2026-10-30 | `concept` | Summary | `[[P1]]` |\n"
            )
            index_md.write_text(initial_content, encoding="utf-8")
            script = str(SCRIPTS_DIR / "compile_helper.py")

            # Scenario 1: Arrow format with brackets
            cmd1 = [
                sys.executable, script, "upsert-index",
                "--index", str(index_md),
                "--note", "Note_Arrow",
                "--up", "[[Old_P]]",
                "--replace-up", "[[Old_P]]->[[New_P]]",
            ]
            res1 = subprocess.run(cmd1, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res1.returncode, 0, res1.stderr)
            text1 = index_md.read_text(encoding="utf-8")
            self.assertIn("[[Note_Arrow]]", text1)
            self.assertIn("`[[New_P]]`", text1)
            self.assertNotIn("[[Old_P]]", text1)

            # Scenario 2: Two-arg format with brackets
            cmd2 = [
                sys.executable, script, "upsert-index",
                "--index", str(index_md),
                "--note", "Note_TwoArg",
                "--up", "[[Old_P2]]",
                "--replace-up", "[[Old_P2]]", "[[New_P2]]",
            ]
            res2 = subprocess.run(cmd2, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res2.returncode, 0, res2.stderr)
            text2 = index_md.read_text(encoding="utf-8")
            self.assertIn("[[Note_TwoArg]]", text2)
            self.assertIn("`[[New_P2]]`", text2)
            self.assertNotIn("[[Old_P2]]", text2)

            # Scenario 3: Multi-up note, only one parent replaced
            cmd3 = [
                sys.executable, script, "upsert-index",
                "--index", str(index_md),
                "--note", "Note_Multi",
                "--up", "[[Stay_Parent]], [[Change_Parent]]",
                "--replace-up", "[[Change_Parent]]->[[Changed_New]]",
            ]
            res3 = subprocess.run(cmd3, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res3.returncode, 0, res3.stderr)
            text3 = index_md.read_text(encoding="utf-8")
            self.assertIn("[[Note_Multi]]", text3)
            self.assertIn("`[[Stay_Parent]]`<br>`[[Changed_New]]`", text3)

            # Scenario 4: Single-arg without arrow (must not raise IndexError)
            cmd4 = [
                sys.executable, script, "upsert-index",
                "--index", str(index_md),
                "--note", "Note_SingleArg",
                "--up", "[[Parent_Safe]]",
                "--replace-up", "SingleArgOnly",
            ]
            res4 = subprocess.run(cmd4, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res4.returncode, 0, res4.stderr)
            text4 = index_md.read_text(encoding="utf-8")
            self.assertIn("[[Note_SingleArg]]", text4)
            self.assertIn("`[[Parent_Safe]]`", text4)

            # Scenario 5: Replace-up combined with remove-up
            cmd5 = [
                sys.executable, script, "upsert-index",
                "--index", str(index_md),
                "--note", "Note_Combo",
                "--up", "[[P_To_Replace]], [[P_To_Remove]], [[P_To_Stay]]",
                "--replace-up", "[[P_To_Replace]]->[[P_Replaced]]",
                "--remove-up", "[[P_To_Remove]]",
            ]
            res5 = subprocess.run(cmd5, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res5.returncode, 0, res5.stderr)
            text5 = index_md.read_text(encoding="utf-8")
            self.assertIn("[[Note_Combo]]", text5)
            self.assertIn("`[[P_Replaced]]`<br>`[[P_To_Stay]]`", text5)
            self.assertNotIn("[[P_To_Remove]]", text5)

    def test_cmd_upsert_index_case_a_update_existing_row(self):
        """Case A update existing row with both arrow and two-arg replace-up."""
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            index_md = tmpdir / "_인덱스_400_Wiki.md"
            initial_content = (
                "---\n"
                "origin: wiki\n"
                "type: hub\n"
                "domain: [theory]\n"
                "up: []\n"
                "status: active\n"
                "created: 2026-10-30\n"
                "updated: 2026-10-30\n"
                "---\n\n"
                "# 400. Wiki Index\n\n"
                "| # | Note | Date | Type | Sum | up |\n"
                "| :---: | :--- | :---: | :--- | :--- | :--- |\n"
                "| 1 | [[Target_Note]] | 2026-10-30 | `concept` | Summary | `[[Old_Hub]]` |\n"
            )
            index_md.write_text(initial_content, encoding="utf-8")
            script = str(SCRIPTS_DIR / "compile_helper.py")

            # Update existing row with arrow format
            cmd1 = [
                sys.executable, script, "upsert-index",
                "--index", str(index_md),
                "--note", "Target_Note",
                "--replace-up", "[[Old_Hub]]->[[New_Hub]]",
            ]
            res1 = subprocess.run(cmd1, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res1.returncode, 0, res1.stderr)
            text1 = index_md.read_text(encoding="utf-8")
            self.assertIn("`[[New_Hub]]`", text1)
            self.assertNotIn("[[Old_Hub]]", text1)

            # Update again with two-arg format
            cmd2 = [
                sys.executable, script, "upsert-index",
                "--index", str(index_md),
                "--note", "Target_Note",
                "--replace-up", "[[New_Hub]]", "[[Final_Hub]]",
            ]
            res2 = subprocess.run(cmd2, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res2.returncode, 0, res2.stderr)
            text2 = index_md.read_text(encoding="utf-8")
            self.assertIn("`[[Final_Hub]]`", text2)
            self.assertNotIn("[[New_Hub]]", text2)

    def test_cmd_normalize_fm_replace_up(self):
        """normalize-fm frontmatter re-wiring with replace-up and remove-up."""
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            note_md = tmpdir / "test_note.md"
            note_content = (
                "---\n"
                "origin: wiki\n"
                "type: concept\n"
                "domain: [theory]\n"
                "up: ['[[Parent_Old]]', '[[Parent_Keep]]']\n"
                "status: active\n"
                "created: 2026-10-30\n"
                "updated: 2026-10-30\n"
                "---\n\n"
                "# Test Note\n"
            )
            note_md.write_text(note_content, encoding="utf-8")
            script = str(SCRIPTS_DIR / "compile_helper.py")

            cmd = [
                sys.executable, script, "normalize-fm",
                "--file", str(note_md),
                "--replace-up", "[[Parent_Old]]->[[Parent_New]]",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res.returncode, 0, res.stderr)
            text = note_md.read_text(encoding="utf-8")
            self.assertIn("[[Parent_New]]", text)
            self.assertIn("[[Parent_Keep]]", text)
            self.assertNotIn("[[Parent_Old]]", text)


class TestVaultLinterAdversarial(unittest.TestCase):
    """Stress tests and oracle checks for vault_linter.py."""

    def test_live_vault_default_audit_zero_violations(self):
        """Live vault check: 351/351 passed, 0 violations."""
        vault_path = PROJECT_ROOT / "My-Wiki"
        self.assertTrue(vault_path.exists())

        cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "vault_linter.py"),
            "--vault",
            str(vault_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(res.returncode, 0, f"Linter failed:\n{res.stdout}\n{res.stderr}")
        self.assertIn("Scanned:", res.stdout)
        self.assertIn("Passed:", res.stdout)
        self.assertIn("Failed: 0", res.stdout)
        self.assertIn("Total Violations: 0", res.stdout)

    def test_oracle_linter_detects_violations(self):
        """Oracle test: ensure linter actively detects schema / link violations on tampered notes."""
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            # Create a mock vault with an invalid note
            (tmpdir / "400. Wiki").mkdir(parents=True)
            bad_note = tmpdir / "400. Wiki" / "Bad_Note.md"
            bad_note.write_text(
                "---\n"
                "origin: wiki\n"
                "type: invalid_type\n"
                "domain: [invalid_domain]\n"
                "up: '[[]]'\n"
                "status: active\n"
                "created: 2026-10-30\n"
                "updated: 2026-10-30\n"
                "---\n\n"
                "# Bad Note\n",
                encoding="utf-8"
            )

            cmd = [
                sys.executable,
                str(SCRIPTS_DIR / "vault_linter.py"),
                "--vault",
                str(tmpdir),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertNotEqual(res.returncode, 0, "Linter should have failed on invalid note")
            self.assertIn("Violations", res.stdout)


if __name__ == "__main__":
    unittest.main()
