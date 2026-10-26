"""Unit and integration tests for ingest_sources.py CLI."""

from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    PROJECT_ROOT
    / ".agents"
    / "skills"
    / "pkm_manager"
    / "scripts"
    / "ingest_sources.py"
)


class TestIngestSourcesUnit(unittest.TestCase):
    """Unit tests for ingest_sources CLI helper functions and end-to-end execution."""

    def setUp(self):
        self.assertTrue(SCRIPT_PATH.exists(), f"ingest_sources.py must exist at {SCRIPT_PATH}")

    def test_cli_help(self):
        """Verify CLI help lists all required arguments."""
        res = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        self.assertEqual(res.returncode, 0)
        out = res.stdout.lower()
        for opt in ["--file", "--inbox", "--vault", "--archive", "--subfolder", "--domain", "--up", "--source-type", "--table-format", "--ocr", "--dry-run", "--force", "--verbose"]:
            self.assertIn(opt, out)

    def test_clean_null_when_up_omitted(self):
        """Verify up: [] is produced when --up is omitted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox"
            inbox.mkdir()
            vault = tmp / "Vault"
            archive = tmp / "Archive"
            sample = inbox / "no_up_doc.txt"
            sample.write_text("Test body without parent anchor.", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable, str(SCRIPT_PATH),
                    "--file", str(sample),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--domain", "macro",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"Command failed: {res.stderr}")
            out_files = list(vault.rglob("*.md"))
            self.assertEqual(len(out_files), 1)
            content = out_files[0].read_text(encoding="utf-8")
            self.assertIn("up: []", content)
            self.assertNotIn('"[[]]"', content)

    def test_clean_null_when_ghost_link_passed_as_up(self):
        """Verify ghost link strings like '[[]]' or '\"[[]]\"' are sanitized to up: []."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox"
            inbox.mkdir()
            vault = tmp / "Vault"
            archive = tmp / "Archive"
            sample = inbox / "ghost_up_doc.txt"
            sample.write_text("Test body with ghost link passed.", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable, str(SCRIPT_PATH),
                    "--file", str(sample),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--up", "[[]]",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"Command failed: {res.stderr}")
            out_files = list(vault.rglob("*.md"))
            self.assertEqual(len(out_files), 1)
            content = out_files[0].read_text(encoding="utf-8")
            self.assertIn("up: []", content)
            self.assertNotIn('"[[]]"', content)

    def test_valid_parent_up_link_formatting(self):
        """Verify valid wikilinks in --up are correctly formatted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox"
            inbox.mkdir()
            vault = tmp / "Vault"
            archive = tmp / "Archive"
            sample = inbox / "macro_doc.txt"
            sample.write_text("Macro overview.", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable, str(SCRIPT_PATH),
                    "--file", str(sample),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--up", "[[02_매크로 분석]]",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0)
            out_files = list(vault.rglob("*.md"))
            self.assertEqual(len(out_files), 1)
            content = out_files[0].read_text(encoding="utf-8")
            self.assertIn('up: ["[[02_매크로 분석]]"]', content)

    def test_seven_core_attributes_and_valid_yaml(self):
        """Verify all 7 core attributes are present and frontmatter is valid YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox"
            inbox.mkdir()
            vault = tmp / "Vault"
            archive = tmp / "Archive"
            sample = inbox / "core_doc.txt"
            sample.write_text("# Core Document Title\nDocument text content.", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable, str(SCRIPT_PATH),
                    "--file", str(sample),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--domain", "macro,equity",
                    "--up", "[[02_매크로 분석]]",
                    "--source-type", "report",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0)
            out_files = list(vault.rglob("*.md"))
            self.assertEqual(len(out_files), 1)
            content = out_files[0].read_text(encoding="utf-8")

            # Parse YAML frontmatter
            parts = content.split("---")
            self.assertGreaterEqual(len(parts), 3, "Document must have frontmatter delimited by ---")
            fm_data = yaml.safe_load(parts[1])

            self.assertEqual(fm_data["origin"], "source")
            self.assertEqual(fm_data["type"], "source")
            self.assertEqual(fm_data["domain"], ["macro", "equity"])
            self.assertEqual(fm_data["up"], ["[[02_매크로 분석]]"])
            self.assertEqual(fm_data["status"], "active")
            self.assertIn("created", fm_data)
            self.assertIn("updated", fm_data)
            self.assertEqual(fm_data["source_type"], "report")

    def test_dry_run_leaves_directories_and_files_untouched(self):
        """Verify --dry-run previews conversion without writing files or moving inputs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox"
            inbox.mkdir()
            vault = tmp / "Vault"
            archive = tmp / "Archive"
            sample = inbox / "dry_run_sample.txt"
            sample.write_text("Dry run sample content.", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable, str(SCRIPT_PATH),
                    "--file", str(sample),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0)
            self.assertTrue(sample.exists(), "Original file must not be moved during --dry-run")
            self.assertFalse(vault.exists(), "Vault directory must not be created during --dry-run")
            self.assertFalse(archive.exists(), "Archive directory must not be created during --dry-run")

    def test_missing_input_file_returns_error_code(self):
        """Verify non-existent input file returns non-zero exit code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            non_existent = tmp / "does_not_exist.pdf"
            res = subprocess.run(
                [
                    sys.executable, str(SCRIPT_PATH),
                    "--file", str(non_existent),
                    "--inbox", str(tmp / "Inbox"),
                    "--vault", str(tmp / "Vault"),
                    "--archive", str(tmp / "Archive"),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertNotEqual(res.returncode, 0)

    def test_inbox_zero_movement_to_archive(self):
        """Verify original file is deleted from inbox and moved to archive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox"
            inbox.mkdir()
            vault = tmp / "Vault"
            archive = tmp / "Archive"
            sample = inbox / "raw_inbox_file.txt"
            sample.write_text("Data to be archived.", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable, str(SCRIPT_PATH),
                    "--file", str(sample),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--subfolder", "340. Work_Docs",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0)
            self.assertFalse(sample.exists(), "Source must be moved from inbox (Inbox Zero)")
            archived = list(archive.rglob("raw_inbox_file.txt"))
            self.assertEqual(len(archived), 1, "Source file must exist in archive")
            self.assertTrue((archive / "340. Work_Docs" / "raw_inbox_file.txt").exists())

    def test_batch_inbox_processing_when_file_omitted(self):
        """Verify batch scanning of inbox folder when --file is not specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox"
            inbox.mkdir()
            vault = tmp / "Vault"
            archive = tmp / "Archive"

            doc1 = inbox / "doc1.txt"
            doc1.write_text("Document 1 content", encoding="utf-8")
            doc2 = inbox / "doc2.txt"
            doc2.write_text("Document 2 content", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable, str(SCRIPT_PATH),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--subfolder", "310. Reports_Papers",
                    "--domain", "macro",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0)
            self.assertFalse(doc1.exists())
            self.assertFalse(doc2.exists())
            out_files = list(vault.rglob("*.md"))
            self.assertEqual(len(out_files), 2)
            archived = list(archive.rglob("*.txt"))
            self.assertEqual(len(archived), 2)


if __name__ == "__main__":
    unittest.main()
