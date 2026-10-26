"""Unit and integration tests for parse_sources.py CLI (pkm_parse skill).

Verifies the 19 CLI flags, Clean Null enforcement, flat note placement in 000. Inbox/,
2-tier YAML frontmatter with extended source attributes, Inbox Zero archival,
source_url relative path format, embedded image extraction, dry-run safety,
missing file error handling, and batch inbox processing.
"""

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
    / "pkm_parse"
    / "scripts"
    / "parse_sources.py"
)
REFERENCE_PDF = (
    PROJECT_ROOT
    / "Archive_Sources"
    / "310. Reports_Papers"
    / "밸리AI 산업 딥다이브_주가에 펀더멘털을 맞추지 말자_2026년 10월.pdf"
)

REQUIRED_19_FLAGS = [
    "--file",
    "--inbox",
    "--vault",
    "--archive",
    "--subfolder",
    "--domain",
    "--up",
    "--source-type",
    "--author",
    "--org",
    "--published",
    "--ref-date",
    "--aliases",
    "--summary",
    "--table-format",
    "--ocr",
    "--dry-run",
    "--force",
    "--verbose",
]


class TestParseSourcesUnit(unittest.TestCase):
    """Unit and integration tests for parse_sources.py CLI."""

    def setUp(self):
        self.assertTrue(
            SCRIPT_PATH.exists(),
            f"parse_sources.py must exist at {SCRIPT_PATH}. Pending Milestone 1.",
        )

    def test_cli_help_lists_all_19_flags(self):
        """1. Verify CLI help exits 0 and lists all 19 required argument flags."""
        res = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        self.assertEqual(res.returncode, 0, f"parse_sources.py --help failed: {res.stderr}")
        out = res.stdout.lower()
        for flag in REQUIRED_19_FLAGS:
            self.assertIn(
                flag,
                out,
                f"parse_sources.py --help must describe flag '{flag}'",
            )

    def test_clean_null_when_up_omitted(self):
        """2. Verify up: [] is produced when --up is omitted (no '[[]]' ghost link)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            inbox.mkdir(parents=True)
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"

            sample = inbox / "sample_unanchored.txt"
            sample.write_text("Document text without parent hierarchy.", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
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
            self.assertEqual(res.returncode, 0, f"Command failed: {res.stderr}\nOutput: {res.stdout}")

            out_note = vault / "000. Inbox" / "sample_unanchored.md"
            self.assertTrue(out_note.exists(), f"Output note must exist at {out_note}")

            content = out_note.read_text(encoding="utf-8")
            self.assertIn("up: []", content, "Frontmatter must format empty up as 'up: []'")
            self.assertNotIn('"[[]]"', content, "Frontmatter must never contain ghost link '\"[[]]\"'")
            self.assertNotIn("'[[]]'", content, "Frontmatter must never contain ghost link '[[]]'")

    def test_clean_null_when_ghost_link_passed(self):
        """3. Verify ghost link variants ('[[]]', '\"[[]]\"', '[]') sanitize to up: []."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            inbox.mkdir(parents=True)
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"

            sample = inbox / "ghost_link_test.txt"
            sample.write_text("Document with explicit ghost link argument.", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
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
            self.assertEqual(res.returncode, 0, f"Command failed: {res.stderr}\nOutput: {res.stdout}")

            out_note = vault / "000. Inbox" / "ghost_link_test.md"
            self.assertTrue(out_note.exists(), f"Output note must exist at {out_note}")

            content = out_note.read_text(encoding="utf-8")
            self.assertIn("up: []", content)
            self.assertNotIn('"[[]]"', content)
            self.assertNotIn("'[[]]'", content)

    def test_flat_note_placement_in_000_inbox(self):
        """4. Verify note is placed flat in 000. Inbox/<stem>.md without subdirectories even when --subfolder is passed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            inbox.mkdir(parents=True)
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"

            sample = inbox / "industry_report.txt"
            sample.write_text("Industry report content.", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--file", str(sample),
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
            self.assertEqual(res.returncode, 0, f"Command failed: {res.stderr}\nOutput: {res.stdout}")

            expected_note = vault / "000. Inbox" / "industry_report.md"
            self.assertTrue(expected_note.exists(), f"Note must reside flat in 000. Inbox/: {expected_note}")

            # Verify no nested subdirectories were created under 000. Inbox
            inbox_subdirs = [p for p in (vault / "000. Inbox").iterdir() if p.is_dir()]
            self.assertEqual(
                len(inbox_subdirs),
                0,
                f"000. Inbox must maintain flat structure without subdirectories, found: {inbox_subdirs}",
            )

    def test_seven_core_and_extended_frontmatter_attributes(self):
        """5. Verify 7 core attributes and conditional extended source attributes in frontmatter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            inbox.mkdir(parents=True)
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"

            sample = inbox / "macro_analysis_2026.txt"
            sample.write_text("# Macro Analysis\nComprehensive macroeconomic study.", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--file", str(sample),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--subfolder", "310. Reports_Papers",
                    "--domain", "macro,equity",
                    "--up", "[[02_매크로 분석]]",
                    "--source-type", "report",
                    "--author", "[[Valley AI]]",
                    "--org", "[[Valley AI Inc]]",
                    "--published", "2026-10",
                    "--ref-date", "2026-10-26",
                    "--aliases", "Deep Dive 2026,Macro Review",
                    "--summary", "An executive summary of macro liquidity and rates.",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"Command failed: {res.stderr}\nOutput: {res.stdout}")

            out_note = vault / "000. Inbox" / "macro_analysis_2026.md"
            self.assertTrue(out_note.exists())

            content = out_note.read_text(encoding="utf-8")
            parts = content.split("---")
            self.assertGreaterEqual(len(parts), 3, "Note must contain valid YAML frontmatter")
            fm = yaml.safe_load(parts[1])

            # 7 Core Attributes
            self.assertEqual(fm.get("origin"), "source", "Core attribute 'origin' must be 'source'")
            self.assertEqual(fm.get("type"), "source", "Core attribute 'type' must be 'source'")
            self.assertEqual(fm.get("domain"), ["macro", "equity"], "Core attribute 'domain' must match")
            self.assertEqual(fm.get("up"), ["[[02_매크로 분석]]"], "Core attribute 'up' must match")
            self.assertEqual(fm.get("status"), "active", "Core attribute 'status' must be 'active'")
            self.assertIn("created", fm, "Core attribute 'created' must be present")
            self.assertIn("updated", fm, "Core attribute 'updated' must be present")

            # Extended Tier 2 Source Attributes
            self.assertEqual(fm.get("source_type"), "report")
            self.assertIn("[[Valley AI]]", str(fm.get("author")))
            self.assertIn("[[Valley AI Inc]]", str(fm.get("org")))
            self.assertEqual(fm.get("published"), "2026-10")
            self.assertEqual(str(fm.get("ref_date")), "2026-10-26")
            self.assertIn("Deep Dive 2026", fm.get("aliases", []))
            self.assertEqual(fm.get("summary"), "An executive summary of macro liquidity and rates.")
            self.assertTrue(
                str(fm.get("source_url")).startswith("Archive_Sources/"),
                f"source_url must point to Archive_Sources path: {fm.get('source_url')}",
            )

    def test_inbox_zero_movement_to_archive(self):
        """6. Verify raw binary document is removed from Inbox_Raw and exists in Archive_Sources (Inbox Zero)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            inbox.mkdir(parents=True)
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"

            sample = inbox / "raw_document.pdf"
            sample.write_bytes(b"%PDF-1.4 dummy binary for inbox zero test")

            res = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--file", str(sample),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--subfolder", "310. Reports_Papers",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"Command failed: {res.stderr}\nOutput: {res.stdout}")

            # Inbox Zero assertion: raw file must no longer exist in Inbox_Raw
            self.assertFalse(sample.exists(), "Source binary must be deleted from Inbox_Raw (Inbox Zero)")

            # Archival assertion: raw file must exist in Archive_Sources/<subfolder>/
            archived = archive / "310. Reports_Papers" / "raw_document.pdf"
            self.assertTrue(archived.exists(), f"Source binary must be archived at {archived}")

    def test_source_url_relative_path_format(self):
        """7. Verify frontmatter source_url matches Archive_Sources/<subfolder>/<filename> with forward slashes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            inbox.mkdir(parents=True)
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"

            sample = inbox / "path_test_doc.txt"
            sample.write_text("Testing source_url formatting.", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--file", str(sample),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--subfolder", "310. Reports_Papers",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0)

            out_note = vault / "000. Inbox" / "path_test_doc.md"
            self.assertTrue(out_note.exists())

            content = out_note.read_text(encoding="utf-8")
            parts = content.split("---")
            fm = yaml.safe_load(parts[1])

            source_url = fm.get("source_url")
            expected_url = "Archive_Sources/310. Reports_Papers/path_test_doc.txt"
            self.assertEqual(source_url, expected_url, "source_url must use forward slashes and match archive path")
            self.assertNotIn("\\", str(source_url), "source_url must not contain Windows backslashes")

    def test_image_extraction_and_wikilink_embed_rewriting(self):
        """8. Verify extraction of document images to 900. config/910. Attached/<doc_stem>/ and body wikilink rewriting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            inbox.mkdir(parents=True)
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"

            sample_stem = "image_extraction_test"
            sample_file = inbox / f"{sample_stem}.pdf"

            if REFERENCE_PDF.exists():
                # Copy real PDF with images for end-to-end extraction verification
                shutil.copy2(str(REFERENCE_PDF), str(sample_file))
            else:
                # Fallback to simulated binary content
                sample_file.write_bytes(b"%PDF-1.4 dummy content")

            res = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--file", str(sample_file),
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
            self.assertEqual(res.returncode, 0, f"Command failed: {res.stderr}\nOutput: {res.stdout}")

            out_note = vault / "000. Inbox" / f"{sample_stem}.md"
            self.assertTrue(out_note.exists(), "Markdown note must be created in 000. Inbox")
            note_content = out_note.read_text(encoding="utf-8")

            # Check image attachments directory
            attached_dir = vault / "900. config" / "910. Attached" / sample_stem
            if REFERENCE_PDF.exists():
                self.assertTrue(attached_dir.exists(), f"Attached images directory must exist at {attached_dir}")
                extracted_images = list(attached_dir.glob("image_*.png"))
                self.assertGreater(len(extracted_images), 0, "At least one image must be extracted")

                # Verify markdown body rewrites references to ![[<doc_stem>/image_XXX.png]]
                first_img_name = extracted_images[0].name
                expected_wikilink = f"![[{sample_stem}/{first_img_name}]]"
                self.assertIn(
                    expected_wikilink,
                    note_content,
                    f"Markdown note body must contain rewritten wikilink embed '{expected_wikilink}'",
                )

            # Assert raw PDF was archived and inbox zero reached
            self.assertFalse(sample_file.exists(), "Source PDF must be removed from Inbox_Raw")
            self.assertTrue((archive / "310. Reports_Papers" / f"{sample_stem}.pdf").exists())

    def test_dry_run_leaves_directories_and_files_untouched(self):
        """9. Verify --dry-run previews conversion without mutating disk or moving inbox files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            inbox.mkdir(parents=True)
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"

            sample = inbox / "dry_run_doc.pdf"
            sample.write_bytes(b"%PDF-1.4 sample content for dry run")

            res = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
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
            self.assertEqual(res.returncode, 0, f"Dry run command failed: {res.stderr}")

            # Verify zero side effects on disk
            self.assertTrue(sample.exists(), "Original file must NOT be moved during --dry-run")
            self.assertFalse((vault / "000. Inbox").exists(), "000. Inbox/ must NOT be created during --dry-run")
            self.assertFalse(archive.exists(), "Archive directory must NOT be created during --dry-run")

    def test_missing_input_file_returns_error_code_1(self):
        """10. Verify missing input file returns non-zero error exit code 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            inbox.mkdir(parents=True)
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"

            non_existent = inbox / "missing_file_never_existed.pdf"

            res = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--file", str(non_existent),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 1, "CLI must exit with code 1 when target file is missing")

    def test_batch_inbox_processing_when_file_omitted(self):
        """11. Verify batch scanning and processing of --inbox folder when --file is omitted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            inbox.mkdir(parents=True)
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"

            doc1 = inbox / "batch_report_01.txt"
            doc1.write_text("Report 1 content.", encoding="utf-8")
            doc2 = inbox / "batch_report_02.txt"
            doc2.write_text("Report 2 content.", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
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
            self.assertEqual(res.returncode, 0, f"Batch parsing failed: {res.stderr}\nOutput: {res.stdout}")

            # Verify both files reached Inbox Zero
            self.assertFalse(doc1.exists(), "batch_report_01.txt must be removed from Inbox_Raw")
            self.assertFalse(doc2.exists(), "batch_report_02.txt must be removed from Inbox_Raw")

            # Verify both notes created flat in 000. Inbox/
            note1 = vault / "000. Inbox" / "batch_report_01.md"
            note2 = vault / "000. Inbox" / "batch_report_02.md"
            self.assertTrue(note1.exists(), f"Note 1 must exist at {note1}")
            self.assertTrue(note2.exists(), f"Note 2 must exist at {note2}")

            # Verify both raw files archived
            archived1 = archive / "310. Reports_Papers" / "batch_report_01.txt"
            archived2 = archive / "310. Reports_Papers" / "batch_report_02.txt"
            self.assertTrue(archived1.exists(), f"Archived file 1 must exist at {archived1}")
            self.assertTrue(archived2.exists(), f"Archived file 2 must exist at {archived2}")

    def test_resolve_gdrive_url_from_mock_drivefs_db(self):
        """12. Verify resolve_gdrive_url resolves Google Drive viewer URL from DriveFS SQLite DB."""
        import importlib.util
        import sqlite3

        spec = importlib.util.spec_from_file_location("parse_sources", str(SCRIPT_PATH))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir).resolve()
            # Simulate DriveFS account folder and SQLite metadata_sqlite_db
            drivefs_base = tmp / "DriveFS"
            acct_dir = drivefs_base / "104213537866668607840"
            acct_dir.mkdir(parents=True)
            db_path = acct_dir / "metadata_sqlite_db"

            # Create simulated path hierarchy under tmp.parts[1:]
            # Note: resolve_gdrive_url walks resolved.parts[1:]
            fake_file = tmp / "Archive_Sources" / "310. Reports_Papers" / "sample_report.pdf"
            fake_file.parent.mkdir(parents=True, exist_ok=True)
            fake_file.write_bytes(b"%PDF-1.4 sample")

            rel_parts = fake_file.resolve().parts[1:]

            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute(
                "CREATE TABLE items (stable_id INTEGER PRIMARY KEY, id TEXT, local_title TEXT, is_folder INTEGER, trashed INTEGER)"
            )
            cur.execute(
                "CREATE TABLE stable_parents (item_stable_id INTEGER, parent_stable_id INTEGER)"
            )
            cur.execute(
                "CREATE TABLE stable_ids (stable_id INTEGER PRIMARY KEY, cloud_id TEXT)"
            )

            # Populate hierarchy matching rel_parts
            parent_sid = None
            for idx, part in enumerate(rel_parts):
                sid = 100 + idx
                is_folder = 1 if idx < len(rel_parts) - 1 else 0
                item_id = f"folder_{sid}" if is_folder else "local-999"
                cur.execute(
                    "INSERT INTO items (stable_id, id, local_title, is_folder, trashed) VALUES (?, ?, ?, ?, 0)",
                    (sid, item_id, part, is_folder),
                )
                if parent_sid is not None:
                    cur.execute(
                        "INSERT INTO stable_parents (item_stable_id, parent_stable_id) VALUES (?, ?)",
                        (sid, parent_sid),
                    )
                parent_sid = sid

            # Map final leaf stable_id to cloud_id in stable_ids
            leaf_sid = 100 + len(rel_parts) - 1
            expected_cloud_id = "1J5kAHs7MlHgJZg6ItDd7neNu3r_4kJZs"
            cur.execute(
                "INSERT INTO stable_ids (stable_id, cloud_id) VALUES (?, ?)",
                (leaf_sid, expected_cloud_id),
            )
            conn.commit()
            conn.close()

            url = mod.resolve_gdrive_url(
                fake_file,
                wait_for_sync=False,
                drivefs_base_dir=drivefs_base,
            )
            self.assertEqual(
                url,
                f"https://drive.google.com/open?id={expected_cloud_id}&usp=drive_fs",
            )

    def test_resolve_gdrive_url_live_junction(self):
        """13. Verify resolve_gdrive_url on live Archive_Sources junction when DriveFS is active."""
        if not REFERENCE_PDF.exists():
            self.skipTest("Reference PDF in Archive_Sources not present")

        import importlib.util

        spec = importlib.util.spec_from_file_location("parse_sources", str(SCRIPT_PATH))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        url = mod.resolve_gdrive_url(REFERENCE_PDF, wait_for_sync=False)
        if url is not None:
            self.assertEqual(
                url,
                "https://drive.google.com/open?id=1J5kAHs7MlHgJZg6ItDd7neNu3r_4kJZs&usp=drive_fs",
            )


if __name__ == "__main__":
    unittest.main()
