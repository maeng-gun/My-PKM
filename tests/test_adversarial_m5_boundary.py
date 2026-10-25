#!/usr/bin/env python
"""Milestone 5 Adversarial & Boundary Stress Harness for My-PKM.

Covers edge case & boundary conditions for:
1. vault_linter.py (non-existent dirs, empty vaults, malformed frontmatter, encoding, C5 isolation)
2. ingest_sources.py (unanchored inputs, clean null up: [], missing files, empty inbox, dry-run safety)
3. Junction isolation and Git leakage prevention
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class TestVaultLinterBoundaryCases(unittest.TestCase):
    """Adversarial stress-testing of vault_linter.py under abnormal/boundary conditions."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent
        cls.python_exe = sys.executable
        cls.linter_script = cls.repo_root / ".agents" / "skills" / "pkm_manager" / "scripts" / "vault_linter.py"
        assert cls.linter_script.exists(), f"Linter script missing: {cls.linter_script}"

    def run_linter(self, *args):
        cmd = [self.python_exe, str(self.linter_script)] + list(args)
        return subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_vault_nonexistent_directory_returns_exit_1(self):
        """Linter should report error on stderr and exit with code 1 when vault path is non-existent."""
        bogus_path = self.repo_root / "NonExistentVault_987654321"
        res = self.run_linter("--vault", str(bogus_path))
        self.assertEqual(res.returncode, 1)
        self.assertIn("does not exist", res.stderr)

    def test_vault_empty_directory_succeeds_with_zero_violations(self):
        """Linter should handle an empty directory cleanly with 0 scanned files and exit code 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            res = self.run_linter("--vault", tmpdir, "--format", "json")
            self.assertEqual(res.returncode, 0)
            data = json.loads(res.stdout)
            self.assertEqual(data["summary"]["total_scanned"], 0)
            self.assertEqual(data["summary"]["total_violations"], 0)

    def test_vault_empty_file_reports_c1_missing_delimiter(self):
        """Empty 0-byte markdown file should be flagged with C1 violation for missing YAML frontmatter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_dir = Path(tmpdir)
            (vault_dir / "100. Concepts").mkdir()
            empty_file = vault_dir / "100. Concepts" / "empty_note.md"
            empty_file.write_text("", encoding="utf-8")

            res = self.run_linter("--vault", tmpdir, "--format", "json")
            self.assertEqual(res.returncode, 1)
            data = json.loads(res.stdout)
            self.assertEqual(data["summary"]["total_violations"], 1)
            violation = data["violations"][0]
            self.assertEqual(violation["check"], "C1")
            self.assertIn("Missing YAML frontmatter delimiter", violation["message"])

    def test_vault_missing_closing_frontmatter_delimiter(self):
        """Note with opening '---' but no closing '---' should be flagged for unclosed frontmatter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_dir = Path(tmpdir)
            (vault_dir / "100. Concepts").mkdir()
            bad_file = vault_dir / "100. Concepts" / "unclosed.md"
            bad_file.write_text("---\norigin: human\ntype: permanent\n# Body without closing dashes\n", encoding="utf-8")

            res = self.run_linter("--vault", tmpdir, "--format", "json")
            self.assertEqual(res.returncode, 1)
            data = json.loads(res.stdout)
            self.assertEqual(data["summary"]["total_violations"], 1)
            violation = data["violations"][0]
            self.assertEqual(violation["check"], "C1")
            self.assertIn("Unclosed YAML frontmatter", violation["message"])

    def test_vault_malformed_yaml_syntax(self):
        """Note with broken YAML syntax should be flagged gracefully without linter crashing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_dir = Path(tmpdir)
            (vault_dir / "100. Concepts").mkdir()
            bad_file = vault_dir / "100. Concepts" / "broken_yaml.md"
            bad_file.write_text(
                "---\n"
                "origin: human\n"
                "type: permanent\n"
                "domain: [macro, equity\n"  # Missing closing bracket
                "---\n"
                "# Content\n",
                encoding="utf-8",
            )

            res = self.run_linter("--vault", tmpdir, "--format", "json")
            self.assertEqual(res.returncode, 1)
            data = json.loads(res.stdout)
            self.assertGreaterEqual(data["summary"]["total_violations"], 1)
            c1_violations = [v for v in data["violations"] if v["check"] == "C1"]
            self.assertTrue(any("Invalid YAML frontmatter syntax" in v["message"] for v in c1_violations))

    def test_vault_yaml_scalar_instead_of_mapping(self):
        """Note where YAML safe_load returns a non-dict scalar should be flagged with C1 mapping error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_dir = Path(tmpdir)
            (vault_dir / "100. Concepts").mkdir()
            bad_file = vault_dir / "100. Concepts" / "scalar.md"
            bad_file.write_text(
                "---\n"
                "just a single string scalar\n"
                "---\n"
                "# Content\n",
                encoding="utf-8",
            )

            res = self.run_linter("--vault", tmpdir, "--format", "json")
            self.assertEqual(res.returncode, 1)
            data = json.loads(res.stdout)
            self.assertGreaterEqual(data["summary"]["total_violations"], 1)
            c1_violations = [v for v in data["violations"] if v["check"] == "C1"]
            self.assertTrue(any("YAML frontmatter must be a key-value mapping" in v["message"] for v in c1_violations))

    def test_vault_cp949_encoding_fallback_works_cleanly(self):
        """Note saved with CP949 Korean encoding should be read without crashing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_dir = Path(tmpdir)
            (vault_dir / "100. Concepts").mkdir()
            cp949_file = vault_dir / "100. Concepts" / "korean_cp949.md"
            content = (
                "---\n"
                "origin: human\n"
                "type: permanent\n"
                "domain:\n"
                "  - macro\n"
                "up: [\"[[02_매크로 분석]]\"]\n"
                "status: active\n"
                "created: 2026-10-25\n"
                "updated: 2026-10-25\n"
                "---\n\n"
                "# 한국어 CP949 테스트 노트\n"
            )
            cp949_file.write_bytes(content.encode("cp949"))

            res = self.run_linter("--vault", tmpdir, "--format", "json")
            self.assertEqual(res.returncode, 0)
            data = json.loads(res.stdout)
            self.assertEqual(data["summary"]["total_violations"], 0)


class TestIngestSourcesBoundaryCases(unittest.TestCase):
    """Adversarial stress-testing of ingest_sources.py under abnormal/boundary conditions."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent
        cls.python_exe = sys.executable
        cls.ingest_script = cls.repo_root / ".agents" / "skills" / "pkm_manager" / "scripts" / "ingest_sources.py"
        assert cls.ingest_script.exists(), f"Ingest script missing: {cls.ingest_script}"

    def run_ingest(self, *args):
        cmd = [self.python_exe, str(self.ingest_script)] + list(args)
        return subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_ingest_missing_file_fails_with_exit_code_1(self):
        """Ingest CLI with non-existent target file must exit with code 1."""
        res = self.run_ingest("--file", "completely_non_existent_document_12345.pdf")
        self.assertEqual(res.returncode, 1)
        self.assertIn("does not exist", res.stderr)

    def test_ingest_empty_inbox_directory_exits_0(self):
        """Ingest CLI targeting an empty inbox directory must exit cleanly with code 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            res = self.run_ingest("--inbox", tmpdir)
            self.assertEqual(res.returncode, 0)

    def test_ingest_unanchored_all_variations_generate_clean_null(self):
        """Stress-test: every empty/ghost link form of --up must output 'up: []'."""
        variations = [
            None,           # Omitted
            "",             # Empty string
            "   ",          # Spaces
            "[[]]",         # Ghost link brackets
            '"[[]]"',       # Quoted ghost link
            "'[[]]'",       # Single-quoted ghost link
            "[]",           # Empty list literal
            '""',           # Empty quotes
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            inbox_dir = base_dir / "Inbox"
            vault_dir = base_dir / "Vault"
            archive_dir = base_dir / "Archive"
            inbox_dir.mkdir()
            vault_dir.mkdir()
            archive_dir.mkdir()

            for idx, up_val in enumerate(variations):
                src_file = inbox_dir / f"test_doc_{idx}.md"
                src_file.write_text(f"# Test Document {idx}\n\nBody content for variant {idx}.\n", encoding="utf-8")

                args = [
                    "--file", str(src_file),
                    "--inbox", str(inbox_dir),
                    "--vault", str(vault_dir),
                    "--archive", str(archive_dir),
                    "--subfolder", "310. Reports_Papers",
                    "--domain", "macro",
                ]
                if up_val is not None:
                    args.extend(["--up", up_val])

                res = self.run_ingest(*args)
                self.assertEqual(res.returncode, 0, f"Failed for variant up={repr(up_val)}: {res.stderr}")

                dest_note = vault_dir / "300. Sources" / "310. Reports_Papers" / f"test_doc_{idx}.md"
                self.assertTrue(dest_note.exists(), f"Destination note not created: {dest_note}")
                content = dest_note.read_text(encoding="utf-8")

                self.assertIn("up: []", content, f"Clean null 'up: []' missing for variant {repr(up_val)}")
                self.assertNotIn('"[[]]"', content)
                self.assertNotIn("'[[]]'", content)
                self.assertNotIn("-[[ ]]", content)

    def test_ingest_dry_run_preserves_inbox_and_leaves_vault_untouched(self):
        """Stress-test: --dry-run must not create vault notes or delete/move inbox files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            inbox_dir = base_dir / "Inbox"
            vault_dir = base_dir / "Vault"
            archive_dir = base_dir / "Archive"
            inbox_dir.mkdir()
            vault_dir.mkdir()
            archive_dir.mkdir()

            test_file = inbox_dir / "dry_run_test.txt"
            test_file.write_text("Dry run sample content.", encoding="utf-8")

            res = self.run_ingest(
                "--file", str(test_file),
                "--inbox", str(inbox_dir),
                "--vault", str(vault_dir),
                "--archive", str(archive_dir),
                "--dry-run",
            )
            self.assertEqual(res.returncode, 0)
            self.assertIn("[DRY-RUN]", res.stdout)

            # In inbox still?
            self.assertTrue(test_file.exists(), "Source file in inbox was mutated by dry-run!")
            # Note written to vault?
            expected_note = vault_dir / "300. Sources" / "310. Reports_Papers" / "dry_run_test.md"
            self.assertFalse(expected_note.exists(), "Vault note was unexpectedly written during dry-run!")


class TestJunctionIsolationAndGitStatus(unittest.TestCase):
    """Adversarial stress-testing of Git untracked status & binary isolation."""

    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent

    def test_gitignore_contains_critical_pkm_junctions(self):
        """Verify .gitignore contains all 3 core PKM junction paths."""
        gitignore_path = self.repo_root / ".gitignore"
        self.assertTrue(gitignore_path.exists())
        content = gitignore_path.read_text(encoding="utf-8")

        self.assertIn("/My-Wiki/", content)
        self.assertIn("/Inbox_Raw/", content)
        self.assertIn("/Archive_Sources/", content)

    def test_git_status_does_not_track_binaries_or_vault_notes(self):
        """Verify that git status ignores files inside My-Wiki, Inbox_Raw, and Archive_Sources."""
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(proc.returncode, 0)
        lines = proc.stdout.splitlines()

        for line in lines:
            clean_line = line.strip()
            # Ensure no live vault note is tracked
            self.assertFalse(
                "My-Wiki/" in clean_line or "Inbox_Raw/" in clean_line or "Archive_Sources/" in clean_line,
                f"Leaked path in git status: {clean_line}",
            )
            # Ensure no heavy binary files are tracked
            for ext in [".pdf", ".hwpx", ".hwp", ".xlsx", ".docx", ".pptx"]:
                self.assertFalse(
                    clean_line.endswith(ext),
                    f"Binary file leaked into git status: {clean_line}",
                )


if __name__ == "__main__":
    unittest.main()
