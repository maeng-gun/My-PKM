"""Empirical Adversarial Stress Test Suite for Milestone 1 (parse_sources.py).

Authored by Challenger M1 (challenger_m1_1).
Stress-tests:
1. CLI flag edge cases, combinations, missing file exits, and dry-run safety.
2. Clean Null rule with various ghost link inputs, empty values, and multi-link parsing.
3. Markdown and HTML image link regex rewriting (relative, nested, query, hash, remote, data URIs, bare wikilinks, idempotency).
4. Unicode / Korean filename handling and forward-slash source_url normalization.
5. Vault Constitutional Linter compliance (vault_linter.py --include-inbox).
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
LINTER_PATH = (
    PROJECT_ROOT
    / ".agents"
    / "skills"
    / "pkm_manager"
    / "scripts"
    / "vault_linter.py"
)

# Add pkm_parse scripts directory to sys.path for direct unit-level stress testing
PKM_PARSE_SCRIPTS = SCRIPT_PATH.parent
if str(PKM_PARSE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PKM_PARSE_SCRIPTS))

import parse_sources


class TestM1AdversarialImageRewriting(unittest.TestCase):
    """Stress-test regex image link rewriting in markdown bodies."""

    def setUp(self):
        self.doc_stem = "adversarial_doc_stem"

    def test_adv_img_01_standard_and_nested_markdown_images(self):
        """Stress-test: Standard, nested relative, and Windows-path markdown images."""
        body = (
            "![simple](image_001.png)\n"
            "![nested](assets/figures/chart.jpg)\n"
            "![windows](sub\\folder\\diagram.png)\n"
            "![mixed case](IMAGES/Graphic.PNG)"
        )
        res = parse_sources.rewrite_image_links(body, self.doc_stem)
        self.assertIn("![[adversarial_doc_stem/image_001.png]]", res)
        self.assertIn("![[adversarial_doc_stem/chart.jpg]]", res)
        self.assertIn("![[adversarial_doc_stem/diagram.png]]", res)
        self.assertIn("![[adversarial_doc_stem/Graphic.PNG]]", res)

    def test_adv_img_02_query_params_and_hash_anchors(self):
        """Stress-test: Image URLs with query strings and fragment identifiers."""
        body = (
            "![query](image.png?v=2&size=large)\n"
            "![hash](chart.jpeg#figure1)\n"
            "![both](sub/photo.webp?auth=token#page=2)"
        )
        res = parse_sources.rewrite_image_links(body, self.doc_stem)
        self.assertIn("![[adversarial_doc_stem/image.png]]", res)
        self.assertIn("![[adversarial_doc_stem/chart.jpeg]]", res)
        self.assertIn("![[adversarial_doc_stem/photo.webp]]", res)

    def test_adv_img_03_remote_urls_and_data_uris_strictly_preserved(self):
        """Stress-test: Remote HTTP, HTTPS, FTP, and Base64 Data URIs must never be rewritten."""
        body = (
            "![remote http](http://example.com/logo.png)\n"
            "![remote https](https://cdn.example.org/path/to/img.svg)\n"
            "![ftp](ftp://files.example.com/image.gif)\n"
            "![data uri](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=)"
        )
        res = parse_sources.rewrite_image_links(body, self.doc_stem)
        self.assertEqual(res, body, "Remote URLs and Data URIs must remain completely untouched")

    def test_adv_img_04_html_img_tags_multiline_and_quotes(self):
        """Stress-test: HTML <img> tags with single/double quotes and multiline attributes."""
        body = (
            '<img src="assets/pic1.png" alt="Test 1" width="300">\n'
            '<img src=\'sub/pic2.jpg\' class=\'responsive\'>\n'
            '<img\n  src="images/pic3.png"\n  alt="multiline tag"\n/>'
        )
        res = parse_sources.rewrite_image_links(body, self.doc_stem)
        self.assertIn("![[adversarial_doc_stem/pic1.png]]", res)
        self.assertIn("![[adversarial_doc_stem/pic2.jpg]]", res)
        self.assertIn("![[adversarial_doc_stem/pic3.png]]", res)

    def test_adv_img_05_html_img_remote_and_data_uris_preserved(self):
        """Stress-test: HTML <img> tags with remote URLs or Data URIs must be preserved."""
        body = (
            '<img src="https://example.com/logo.png" width="200">\n'
            '<img src="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD...">\n'
            '<img src="http://insecure.site/pic.png">'
        )
        res = parse_sources.rewrite_image_links(body, self.doc_stem)
        self.assertEqual(res, body)

    def test_adv_img_06_obsidian_bare_wikilinks_and_idempotence(self):
        """Stress-test: Bare image wikilinks rewritten; already prefixed wikilinks preserved without double prefix."""
        body = (
            "![[extracted_001.png]]\n"
            "![[adversarial_doc_stem/already_prefixed.png]]\n"
            "![[OtherNonImageNote]]\n"
            "![[AttachedDocument.pdf]]"
        )
        res = parse_sources.rewrite_image_links(body, self.doc_stem)
        self.assertIn("![[adversarial_doc_stem/extracted_001.png]]", res)
        self.assertIn("![[adversarial_doc_stem/already_prefixed.png]]", res)
        self.assertNotIn("![[adversarial_doc_stem/adversarial_doc_stem/", res, "No double prefix allowed")
        # Non-image wikilinks must not be modified
        self.assertIn("![[OtherNonImageNote]]", res)
        self.assertIn("![[AttachedDocument.pdf]]", res)

    def test_adv_img_07_regular_markdown_links_not_corrupted(self):
        """Stress-test: Regular markdown hyperlink [text](image.png) must NOT be rewritten to image embed."""
        body = (
            "Please click [Download Report Chart](images/chart.png) for full view.\n"
            "Also refer to [Our Architecture Document](docs/architecture.md)."
        )
        res = parse_sources.rewrite_image_links(body, self.doc_stem)
        self.assertEqual(res, body, "Standard markdown links must not be converted into image embeds")


class TestM1AdversarialCleanNullAndGhostLinks(unittest.TestCase):
    """Stress-test Clean Null rule and ghost link variants in YAML frontmatter."""

    def test_adv_ghost_01_all_ghost_link_variants_produce_clean_null(self):
        """Stress-test: Ghost link variants passed to up must strictly sanitize to up: []."""
        ghost_inputs = [
            None,
            "",
            "   ",
            "[[]]",
            " [[]] ",
            '"[[]]"',
            "'[[]]'",
            "[]",
            '""',
            "''",
            '""[[]]""',
            "[[]], [[]]",
            "[[]], [[]], [[]]",
        ]
        for ghost in ghost_inputs:
            fm = parse_sources.generate_frontmatter(up=ghost)
            self.assertIn("up: []", fm, f"Failed to produce up: [] for ghost input: {repr(ghost)}")
            self.assertNotIn('"[[]]"', fm)
            self.assertNotIn("'[[]]'", fm)
            self.assertNotIn(" [[]]", fm)

    def test_adv_ghost_02_mixed_valid_and_ghost_links(self):
        """Stress-test: Mixed valid parent link and ghost link sanitizes to only the valid link."""
        fm = parse_sources.generate_frontmatter(up="[[02_매크로 분석]], [[]]")
        self.assertIn('up: ["[[02_매크로 분석]]"]', fm)
        self.assertNotIn('"[[]]"', fm)

    def test_adv_ghost_03_raw_name_wrapping(self):
        """Stress-test: Raw string without brackets automatically wrapped as wikilink."""
        fm = parse_sources.generate_frontmatter(up="02_매크로 분석")
        self.assertIn('up: ["[[02_매크로 분석]]"]', fm)

    def test_adv_ghost_04_multiple_valid_parents(self):
        """Stress-test: Multiple valid parents correctly serialized."""
        fm = parse_sources.generate_frontmatter(up="[[02_매크로 분석]], [[01_경제 및 금융 이론]]")
        self.assertIn('up: ["[[02_매크로 분석]]", "[[01_경제 및 금융 이론]]"]', fm)

    def test_adv_ghost_05_bracketed_scalar_variant(self):
        """Stress-test: Bracketed empty scalar string '[]' yields clean null."""
        fm = parse_sources.generate_frontmatter(up="[]")
        self.assertEqual("up: []", [line for line in fm.splitlines() if line.startswith("up:")][0])


class TestM1AdversarialCLIFlagsAndSafety(unittest.TestCase):
    """Stress-test CLI invocation edge cases, combinations, dry-run safety, and error exits."""

    def test_adv_cli_01_all_19_flags_combined(self):
        """Stress-test: Invoke CLI passing all 19 flags simultaneously."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            inbox.mkdir(parents=True)
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"

            input_file = inbox / "all_flags_doc.txt"
            input_file.write_text("# Flag Test\nBody content.", encoding="utf-8")

            cmd = [
                sys.executable,
                str(SCRIPT_PATH),
                "--file", str(input_file),
                "--inbox", str(inbox),
                "--vault", str(vault),
                "--archive", str(archive),
                "--subfolder", "310. Reports_Papers",
                "--domain", "macro,equity",
                "--up", "[[02_매크로 분석]]",
                "--source-type", "report",
                "--author", "[[Analyst John]]",
                "--org", "[[Macro Firm]]",
                "--published", "2026-10-25",
                "--ref-date", "2026-10-26",
                "--aliases", "Flag Doc, Test Doc",
                "--summary", "Comprehensive stress test passing all 19 flags.",
                "--table-format", "gfm",
                "--ocr",
                "--dry-run",
                "--force",
                "--verbose",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(res.returncode, 0, f"Combined CLI failed:\nStdout: {res.stdout}\nStderr: {res.stderr}")
            # Dry run must not mutate
            self.assertTrue(input_file.exists())
            self.assertFalse((vault / "000. Inbox").exists())

    def test_adv_cli_02_dry_run_absolute_isolation(self):
        """Stress-test: Dry-run mode guarantees zero disk mutation across all target paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            inbox.mkdir()
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"

            doc = inbox / "sample_binary.pdf"
            doc.write_bytes(b"%PDF-1.4 dummy binary")

            res = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--file", str(doc),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res.returncode, 0)
            self.assertTrue(doc.exists(), "Source binary must NOT be moved during dry-run")
            self.assertFalse(vault.exists(), "Vault directory must NOT be created during dry-run")
            self.assertFalse(archive.exists(), "Archive directory must NOT be created during dry-run")

    def test_adv_cli_03_missing_file_exit_code_1_no_disk_side_effects(self):
        """Stress-test: Missing input file returns exit code 1 with stderr warning and no side effects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            inbox.mkdir()
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"

            res = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--file", str(inbox / "does_not_exist.pdf"),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res.returncode, 1, "Must exit with code 1 on missing file")
            self.assertIn("does not exist", res.stderr)
            self.assertFalse(vault.exists())
            self.assertFalse(archive.exists())

    def test_adv_cli_04_relative_filename_in_inbox_resolution(self):
        """Stress-test: Passing just filename (not full path) resolves inside --inbox directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            inbox.mkdir()
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"

            doc = inbox / "bare_filename_doc.txt"
            doc.write_text("Resolving bare filename.", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--file", "bare_filename_doc.txt",
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"Bare filename resolution failed: {res.stderr}")
            self.assertTrue((vault / "000. Inbox" / "bare_filename_doc.md").exists())
            self.assertFalse(doc.exists())

    def test_adv_cli_05_korean_unicode_filename_and_source_url(self):
        """Stress-test: Korean / Unicode document filenames and forward slash source_url."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            inbox.mkdir()
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"

            korean_name = "2026년 10월 거시경제 동향_금리와 환율.txt"
            doc = inbox / korean_name
            doc.write_text("# 거시경제 동향\n원문 내용입니다.", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--file", str(doc),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--subfolder", "310. Reports_Papers",
                    "--domain", "macro",
                    "--up", "[[02_매크로 분석]]",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"Korean file conversion failed: {res.stderr}")

            out_note = vault / "000. Inbox" / "2026년 10월 거시경제 동향_금리와 환율.md"
            self.assertTrue(out_note.exists())

            content = out_note.read_text(encoding="utf-8")
            parts = content.split("---")
            fm = yaml.safe_load(parts[1])

            expected_source_url = f"Archive_Sources/310. Reports_Papers/{korean_name}"
            self.assertEqual(fm.get("source_url"), expected_source_url)
            self.assertNotIn("\\", str(fm.get("source_url")), "source_url must strictly use forward slashes")

            # Run vault linter against generated note
            lint_res = subprocess.run(
                [sys.executable, str(LINTER_PATH), "--vault", str(vault), "--include-inbox"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(lint_res.returncode, 0, f"Linter flagged generated note:\n{lint_res.stdout}")

    def test_adv_cli_06_subfolder_prefix_normalization(self):
        """Stress-test: --subfolder with 300. Sources/ or Archive_Sources/ prefix normalizes cleanly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            inbox.mkdir()
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"

            doc = inbox / "normalization_test.txt"
            doc.write_text("Prefix normalization test.", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--file", str(doc),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--subfolder", "300. Sources/310. Reports_Papers/",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res.returncode, 0)
            archived = archive / "310. Reports_Papers" / "normalization_test.txt"
            self.assertTrue(archived.exists(), f"Archive must normalize to {archived}")

            out_note = vault / "000. Inbox" / "normalization_test.md"
            content = out_note.read_text(encoding="utf-8")
            fm = yaml.safe_load(content.split("---")[1])
            self.assertEqual(fm.get("source_url"), "Archive_Sources/310. Reports_Papers/normalization_test.txt")

    def test_adv_cli_07_no_images_document_does_not_create_attachment_dir(self):
        """Stress-test: Documents without images must NOT create orphaned 910. Attached/<stem>/ directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            inbox.mkdir()
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"

            doc = inbox / "pure_text_document.txt"
            doc.write_text("This document contains only plain text and no images whatsoever.", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--file", str(doc),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(res.returncode, 0)
            note = vault / "000. Inbox" / "pure_text_document.md"
            self.assertTrue(note.exists())

            # Verify 910. Attached/<doc_stem> is NOT created
            attached_doc_dir = vault / "900. config" / "910. Attached" / "pure_text_document"
            self.assertFalse(
                attached_doc_dir.exists(),
                f"910. Attached/pure_text_document must NOT exist for imageless documents, but found: {attached_doc_dir}",
            )

    def test_adv_cli_08_domain_capping_max_two_rule(self):
        """Stress-test: Domain parameter with >2 domains is capped at max 2 according to 1+1 rule."""
        fm = parse_sources.generate_frontmatter(domain=["macro", "equity", "theory", "work"])
        data = yaml.safe_load(fm.split("---")[1])
        self.assertEqual(len(data["domain"]), 2, "Domain must be strictly capped at max 2")
        self.assertEqual(data["domain"], ["macro", "equity"])

    def test_adv_img_08_table_cell_and_inline_images(self):
        """Stress-test: Markdown images inside table cells and complex formatting."""
        body = (
            "| Column 1 | Column 2 |\n"
            "| --- | --- |\n"
            "| Description | ![fig](table_fig.png) |\n"
            "| Korean Text | ![도표](표_그래프.png) |\n"
        )
        res = parse_sources.rewrite_image_links(body, "table_doc")
        self.assertIn("![[table_doc/table_fig.png]]", res)
        self.assertIn("![[table_doc/표_그래프.png]]", res)


if __name__ == "__main__":
    unittest.main()
