"""Tier 5 Adversarial Coverage Hardening Test Suite for My-PKM pkm_parse.

Authored by empirical challenger (challenger_m3_tier5).
Covers:
1. Ghost Link & Clean Null Permutations & Frontmatter Immunization
2. Special Characters in Filenames, Paths with Spaces & Deeply Nested Subfolders
3. Image Embed Link Rewriting, Query Strings, and Remote/Data URI Preservation
4. YAML Frontmatter Escaping for Colons, Quotes, and Complex Strings
5. Corrupted, Empty (0-byte), and Non-UTF8 Input Documents
6. Vault Safety Invariants: Binary Isolation, Human Write Sovereignty, and Live Vault Linter with --include-inbox
"""

from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARSE_SCRIPT = (
    PROJECT_ROOT
    / ".agents"
    / "skills"
    / "pkm_parse"
    / "scripts"
    / "parse_sources.py"
)
LINTER_SCRIPT = (
    PROJECT_ROOT
    / ".agents"
    / "skills"
    / "pkm_manager"
    / "scripts"
    / "vault_linter.py"
)
PYTHON_EXE = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"


class TestTier5AdversarialGhostLinkCleanNull(unittest.TestCase):
    """Tier 5 Adversarial probes for ghost link permutations and clean null enforcement."""

    def setUp(self):
        self.assertTrue(PARSE_SCRIPT.exists(), f"Missing parse script: {PARSE_SCRIPT}")
        self.assertTrue(PYTHON_EXE.exists(), f"Missing python: {PYTHON_EXE}")

    def test_adv_t5_01_ghost_link_permutations_normalize_to_clean_null(self):
        """Stress-test: Verify all ghost link permutations in --up normalize cleanly to 'up: []'."""
        permutations = [
            ("[[]], [[]]", "comma-separated double ghost"),
            ("[], []", "comma-separated empty lists"),
            ("[[]]", "literal ghost link"),
            ('"[[]]"', "quoted ghost link"),
            ("'[[]]'", "single-quoted ghost link"),
            ("[ [ ] ]", "spaced double brackets"),
            ("   ", "whitespace only"),
            ("", "empty string"),
            ("[]", "bare empty list"),
            ('""', "empty double quotes"),
            ("''", "empty single quotes"),
        ]

        for up_input, case_name in permutations:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)
                inbox = tmp / "Inbox_Raw"
                vault = tmp / "My-Wiki"
                archive = tmp / "Archive_Sources"
                inbox.mkdir(parents=True)

                doc = inbox / "ghost_probe.txt"
                doc.write_text(f"Document content for {case_name}.", encoding="utf-8")

                res = subprocess.run(
                    [
                        str(PYTHON_EXE),
                        str(PARSE_SCRIPT),
                        "--file", str(doc),
                        "--inbox", str(inbox),
                        "--vault", str(vault),
                        "--archive", str(archive),
                        "--up", up_input,
                        "--domain", "macro",
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                self.assertEqual(
                    res.returncode,
                    0,
                    f"CLI failed on case '{case_name}' with input '{up_input}': {res.stderr}",
                )

                note = vault / "000. Inbox" / "ghost_probe.md"
                self.assertTrue(note.exists())
                content = note.read_text(encoding="utf-8")

                self.assertIn(
                    "up: []",
                    content,
                    f"Case '{case_name}' failed to produce 'up: []'. Frontmatter:\n{content[:200]}",
                )
                self.assertNotIn('"[[]]"', content)
                self.assertNotIn("'[[]]'", content)
                self.assertNotIn("[[]]", content)

    def test_adv_t5_02_ghost_link_mixed_with_valid_parent(self):
        """Stress-test: Frontmatter with a valid parent link AND a ghost link must filter out the ghost."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"
            inbox.mkdir(parents=True)

            doc = inbox / "mixed_ghost.txt"
            doc.write_text("Document with mixed parent links.", encoding="utf-8")

            res = subprocess.run(
                [
                    str(PYTHON_EXE),
                    str(PARSE_SCRIPT),
                    "--file", str(doc),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--up", "[[]], [[02_매크로 분석]]",
                    "--domain", "macro",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"Mixed ghost up failed: {res.stderr}")

            note = vault / "000. Inbox" / "mixed_ghost.md"
            self.assertTrue(note.exists())
            content = note.read_text(encoding="utf-8")

            parts = content.split("---")
            fm = yaml.safe_load(parts[1])
            self.assertEqual(fm["up"], ["[[02_매크로 분석]]"])
            self.assertNotIn("[[]]", str(fm["up"]))

    def test_adv_t5_03_author_and_org_ghost_link_immunity(self):
        """Stress-test: Author and org parameters passing '[[]]' or '[]' must not produce ghost links."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"
            inbox.mkdir(parents=True)

            doc = inbox / "author_org_ghost.txt"
            doc.write_text("Testing author and org ghost inputs.", encoding="utf-8")

            res = subprocess.run(
                [
                    str(PYTHON_EXE),
                    str(PARSE_SCRIPT),
                    "--file", str(doc),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--author", "[[]]",
                    "--org", "[]",
                    "--domain", "macro",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"Command failed: {res.stderr}")

            note = vault / "000. Inbox" / "author_org_ghost.md"
            content = note.read_text(encoding="utf-8")
            self.assertNotIn('"[[]]"', content)
            self.assertNotIn("'[[]]'", content)

            parts = content.split("---")
            fm = yaml.safe_load(parts[1])
            self.assertNotIn("author", fm, "Ghost author should be excluded or sanitized")
            self.assertNotIn("org", fm, "Ghost org should be excluded or sanitized")

    def test_adv_t5_04_domain_truncation_max_2_rule(self):
        """Stress-test: Domain parameter with 3+ standard domains is strictly capped at 2 ('1+1' rule)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"
            inbox.mkdir(parents=True)

            doc = inbox / "multi_domain.txt"
            doc.write_text("Document spanning 4 domains.", encoding="utf-8")

            res = subprocess.run(
                [
                    str(PYTHON_EXE),
                    str(PARSE_SCRIPT),
                    "--file", str(doc),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--domain", "macro,equity,portfolio,theory",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"Command failed: {res.stderr}")

            note = vault / "000. Inbox" / "multi_domain.md"
            content = note.read_text(encoding="utf-8")
            parts = content.split("---")
            fm = yaml.safe_load(parts[1])

            self.assertEqual(len(fm["domain"]), 2, f"Domain list must be capped at 2: {fm['domain']}")
            self.assertEqual(fm["domain"], ["macro", "equity"])


class TestTier5AdversarialFilenamesAndPaths(unittest.TestCase):
    """Tier 5 Adversarial probes for special filenames, spaces, and nested path handling."""

    def test_adv_t5_05_filename_with_spaces_brackets_and_korean(self):
        """Stress-test: Source file containing spaces, brackets, hyphens, and Korean characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"
            inbox.mkdir(parents=True)

            complex_filename = "2026 [특집] 한국은행 금융통화위원회 & 거시경제 분석 - Final.txt"
            doc = inbox / complex_filename
            doc.write_text(
                "# 2026 한국은행 금통위 분석\n\n금리 결정 배경 및 전망 내용입니다.\n",
                encoding="utf-8",
            )

            res = subprocess.run(
                [
                    str(PYTHON_EXE),
                    str(PARSE_SCRIPT),
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
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"Command failed: {res.stderr}")

            # Note must be placed flat in 000. Inbox/
            expected_stem = Path(complex_filename).stem
            out_note = vault / "000. Inbox" / f"{expected_stem}.md"
            self.assertTrue(out_note.exists(), f"Note must exist at {out_note}")

            # Binary archived to Archive_Sources/310. Reports_Papers/
            archived = archive / "310. Reports_Papers" / complex_filename
            self.assertTrue(archived.exists(), f"Archived file must exist at {archived}")
            self.assertFalse(doc.exists(), "Source file must be moved (Inbox Zero)")

            # Check source_url in frontmatter
            content = out_note.read_text(encoding="utf-8")
            parts = content.split("---")
            fm = yaml.safe_load(parts[1])
            expected_url = f"Archive_Sources/310. Reports_Papers/{complex_filename}"
            self.assertEqual(fm["source_url"], expected_url)
            self.assertNotIn("\\", fm["source_url"])

    def test_adv_t5_06_deeply_nested_archive_subfolder(self):
        """Stress-test: Deeply nested subfolder path preserved in archive while note remains flat in 000. Inbox."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"
            inbox.mkdir(parents=True)

            doc = inbox / "nested_test.txt"
            doc.write_text("Nested subfolder test content.", encoding="utf-8")

            res = subprocess.run(
                [
                    str(PYTHON_EXE),
                    str(PARSE_SCRIPT),
                    "--file", str(doc),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--subfolder", "310. Reports_Papers/Macro/Global/Deep/2026",
                    "--domain", "macro",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"Deep subfolder failed: {res.stderr}")

            # Note must still be flat in 000. Inbox/
            out_note = vault / "000. Inbox" / "nested_test.md"
            self.assertTrue(out_note.exists())
            self.assertEqual(len(list((vault / "000. Inbox").glob("*/"))), 0, "000. Inbox must have no subfolders")

            # Archive must have deep directory structure
            archived = archive / "310. Reports_Papers" / "Macro" / "Global" / "Deep" / "2026" / "nested_test.txt"
            self.assertTrue(archived.exists(), f"Archive must exist at {archived}")

            # source_url must use forward slashes
            content = out_note.read_text(encoding="utf-8")
            parts = content.split("---")
            fm = yaml.safe_load(parts[1])
            self.assertEqual(
                fm["source_url"],
                "Archive_Sources/310. Reports_Papers/Macro/Global/Deep/2026/nested_test.txt",
            )

    def test_adv_t5_07_windows_backslash_subfolder_normalized(self):
        """Stress-test: Passing Windows backslashes in --subfolder normalizes to forward slashes in source_url."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"
            inbox.mkdir(parents=True)

            doc = inbox / "backslash_test.txt"
            doc.write_text("Backslash subfolder test.", encoding="utf-8")

            res = subprocess.run(
                [
                    str(PYTHON_EXE),
                    str(PARSE_SCRIPT),
                    "--file", str(doc),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--subfolder", "310. Reports_Papers\\Macro\\Korea",
                    "--domain", "macro",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0)

            out_note = vault / "000. Inbox" / "backslash_test.md"
            content = out_note.read_text(encoding="utf-8")
            parts = content.split("---")
            fm = yaml.safe_load(parts[1])

            self.assertEqual(
                fm["source_url"],
                "Archive_Sources/310. Reports_Papers/Macro/Korea/backslash_test.txt",
            )
            self.assertNotIn("\\", fm["source_url"])


class TestTier5AdversarialImageRewriting(unittest.TestCase):
    """Tier 5 Adversarial probes for image links, HTML tags, and remote URL preservation."""

    def test_adv_t5_08_image_rewriting_edge_cases(self):
        """Stress-test: Verify rewriting rewrites local images while preserving remote URLs and data URIs."""
        sys.path.insert(0, str(PARSE_SCRIPT.parent))
        from parse_sources import rewrite_image_links

        doc_stem = "2026_Macro_DeepDive"
        body = (
            "# Document with Various Image Types\n\n"
            "## Local Markdown Images\n"
            "![Chart 1](image_001.png)\n"
            "![Chart with path](assets/images/fig2.jpg)\n"
            "![Image with query](chart.png?version=1.2#figure1)\n\n"
            "## HTML Img Tags\n"
            '<img src="photo_001.jpeg" alt="Photo" width="400" />\n'
            '<img class="chart" src="subfolder/diagram.svg">\n\n'
            "## Remote Images (MUST NOT be rewritten)\n"
            "![Remote Logo](https://valley.ai/assets/logo.png)\n"
            "![HTTP Image](http://example.com/images/banner.jpg)\n"
            '<img src="https://example.com/cdn/chart.png" alt="Remote">\n\n'
            "## Data URIs (MUST NOT be rewritten)\n"
            "![Base64](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=)\n\n"
            "## Bare Wikilink Embeds\n"
            "![[extracted_01.png]]\n"
            "![[2026_Macro_DeepDive/already_rewritten.png]]\n"
        )

        rewritten = rewrite_image_links(body, doc_stem)

        # 1. Local markdown images rewritten to ![[<doc_stem>/<filename>]]
        self.assertIn(f"![[{doc_stem}/image_001.png]]", rewritten)
        self.assertIn(f"![[{doc_stem}/fig2.jpg]]", rewritten)
        self.assertIn(f"![[{doc_stem}/chart.png]]", rewritten)

        # 2. HTML img tags rewritten to ![[<doc_stem>/<filename>]]
        self.assertIn(f"![[{doc_stem}/photo_001.jpeg]]", rewritten)
        self.assertIn(f"![[{doc_stem}/diagram.svg]]", rewritten)

        # 3. Remote images strictly preserved
        self.assertIn("![Remote Logo](https://valley.ai/assets/logo.png)", rewritten)
        self.assertIn("![HTTP Image](http://example.com/images/banner.jpg)", rewritten)
        self.assertIn('<img src="https://example.com/cdn/chart.png" alt="Remote">', rewritten)

        # 4. Data URI strictly preserved
        self.assertIn("data:image/png;base64,", rewritten)

        # 5. Bare wikilink embed rewritten, already rewritten untouched
        self.assertIn(f"![[{doc_stem}/extracted_01.png]]", rewritten)
        self.assertIn(f"![[{doc_stem}/already_rewritten.png]]", rewritten)
        self.assertNotIn(f"![[{doc_stem}/{doc_stem}/already_rewritten.png]]", rewritten)


class TestTier5AdversarialYAMLEscaping(unittest.TestCase):
    """Tier 5 Adversarial probes for frontmatter special characters, colons, and YAML safety."""

    def test_adv_t5_09_special_characters_in_summary_and_aliases(self):
        """Stress-test: Summary and aliases with colons, quotes, braces, and brackets parse as valid YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"
            inbox.mkdir(parents=True)

            doc = inbox / "yaml_escape_test.txt"
            doc.write_text("Content testing YAML quoting.", encoding="utf-8")

            res = subprocess.run(
                [
                    str(PYTHON_EXE),
                    str(PARSE_SCRIPT),
                    "--file", str(doc),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--aliases", "FOMC: 2026 Preview, Rate Cut [Scenario A], {Special} Topic",
                    "--summary", 'Key finding: Core inflation is 2.1% (MoM: +0.2%); "Neutral" stance expected.',
                    "--domain", "macro",
                    "--up", "[[02_매크로 분석]]",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"Command failed: {res.stderr}\nOutput: {res.stdout}")

            out_note = vault / "000. Inbox" / "yaml_escape_test.md"
            content = out_note.read_text(encoding="utf-8")

            # Must safely parse with yaml.safe_load
            parts = content.split("---")
            self.assertGreaterEqual(len(parts), 3)
            try:
                fm = yaml.safe_load(parts[1])
            except Exception as exc:
                self.fail(f"YAML parsing failed on escaped frontmatter: {exc}\nFrontmatter:\n{parts[1]}")

            self.assertIn("FOMC: 2026 Preview", fm["aliases"])
            self.assertIn("Rate Cut [Scenario A]", fm["aliases"])
            self.assertIn("{Special} Topic", fm["aliases"])
            self.assertIn("Key finding: Core inflation is 2.1%", fm["summary"])


class TestTier5AdversarialCorruptedAndAbnormalFiles(unittest.TestCase):
    """Tier 5 Adversarial probes for corrupted, empty, and non-UTF8 input documents."""

    def test_adv_t5_10_empty_zero_byte_document_handling(self):
        """Stress-test: An empty 0-byte input document should either parse gracefully or report clean error without unhandled trace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"
            inbox.mkdir(parents=True)

            empty_file = inbox / "empty_doc.txt"
            empty_file.write_bytes(b"")

            res = subprocess.run(
                [
                    str(PYTHON_EXE),
                    str(PARSE_SCRIPT),
                    "--file", str(empty_file),
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

            # Text files with 0 bytes succeed by creating a note with title header
            self.assertEqual(res.returncode, 0, f"Empty txt should create note: {res.stderr}")
            out_note = vault / "000. Inbox" / "empty_doc.md"
            self.assertTrue(out_note.exists())
            self.assertTrue((archive / "empty_doc.txt").exists())

    def test_adv_t5_11_corrupted_binary_fails_gracefully(self):
        """Stress-test: Corrupted binary (e.g. random garbage with .pdf extension) exits 1 and leaves inbox/vault unpolluted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"
            inbox.mkdir(parents=True)

            corrupt_file = inbox / "corrupt_data.bin"
            # Unparseable binary bytes that cannot be decoded as utf-8 or parsed by kordoc
            corrupt_file.write_bytes(bytes([0x80, 0xFF, 0xFE, 0x00, 0x12, 0x34, 0x56, 0x78] * 100))

            res = subprocess.run(
                [
                    str(PYTHON_EXE),
                    str(PARSE_SCRIPT),
                    "--file", str(corrupt_file),
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

            # Must exit with non-zero code
            self.assertEqual(res.returncode, 1, "CLI must exit 1 on unextractable binary file")
            self.assertIn("Error", res.stderr)

            # Invariant: source file must NOT be deleted from inbox if extraction failed!
            self.assertTrue(corrupt_file.exists(), "Corrupt source file must NOT be deleted if parsing failed")
            # Invariant: no partial note in 000. Inbox
            self.assertFalse((vault / "000. Inbox" / "corrupt_data.md").exists())

    def test_adv_t5_12_cp949_korean_text_fallback(self):
        """Stress-test: Korean plain text encoded in CP949 decodes seamlessly and generates valid UTF-8 note."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"
            inbox.mkdir(parents=True)

            cp949_file = inbox / "korean_legacy_cp949.txt"
            korean_text = "# 한국은행 통화신용정책 보고서\n\n기준금리 동결 배경 및 거시경제 전망입니다.\n"
            cp949_file.write_bytes(korean_text.encode("cp949"))

            res = subprocess.run(
                [
                    str(PYTHON_EXE),
                    str(PARSE_SCRIPT),
                    "--file", str(cp949_file),
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
            self.assertEqual(res.returncode, 0, f"CP949 parsing failed: {res.stderr}")

            out_note = vault / "000. Inbox" / "korean_legacy_cp949.md"
            self.assertTrue(out_note.exists())
            content = out_note.read_text(encoding="utf-8")
            self.assertIn("한국은행 통화신용정책 보고서", content)
            self.assertIn("기준금리 동결 배경", content)


class TestTier5AdversarialVaultSafetyAndLinter(unittest.TestCase):
    """Tier 5 Adversarial probes for vault binary isolation, sovereignty, and constitutional linter."""

    def test_adv_t5_13_vault_binary_isolation_and_sovereignty(self):
        """Stress-test: Zero binaries enter My-Wiki; zero writes to 100. Concepts or 500. etc."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"
            inbox.mkdir(parents=True)

            # Pre-populate human sovereignty folders
            (vault / "100. Concepts").mkdir(parents=True)
            (vault / "500. etc").mkdir(parents=True)
            human_concept = vault / "100. Concepts" / "MyThought.md"
            human_concept.write_text("Human thoughts never to be touched.", encoding="utf-8")

            # Create mock binary document
            doc = inbox / "macro_doc.pdf"
            doc.write_bytes(b"%PDF-1.4 mock pdf content for isolation test")

            res = subprocess.run(
                [
                    str(PYTHON_EXE),
                    str(PARSE_SCRIPT),
                    "--file", str(doc),
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
            self.assertEqual(res.returncode, 0)

            # 1. Verify no binary file (.pdf) exists anywhere in vault
            vault_binaries = list(vault.rglob("*.pdf"))
            self.assertEqual(len(vault_binaries), 0, f"Binary files leaked into vault: {vault_binaries}")

            # 2. Verify Human Sovereignty: 100. Concepts/MyThought.md untouched
            self.assertEqual(human_concept.read_text(encoding="utf-8"), "Human thoughts never to be touched.")
            self.assertEqual(len(list((vault / "100. Concepts").iterdir())), 1)
            self.assertEqual(len(list((vault / "500. etc").iterdir())), 0)

            # 3. Verify output note is solely in 000. Inbox
            inbox_notes = list((vault / "000. Inbox").glob("*.md"))
            self.assertEqual(len(inbox_notes), 1)
            self.assertEqual(inbox_notes[0].name, "macro_doc.md")

    def test_adv_t5_14_live_vault_linter_include_inbox_clean_pass(self):
        """Stress-test: End-to-end integration: parse_sources -> 000. Inbox -> vault_linter --include-inbox passes with 0 violations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"
            inbox.mkdir(parents=True)

            # Set up minimal compliant vault skeleton
            wiki_dir = vault / "400. Wiki"
            wiki_dir.mkdir(parents=True)
            (wiki_dir / "02_매크로 분석.md").write_text(
                "---\norigin: wiki\ntype: hub\nlevel: 1\ndomain: [macro]\nup: []\nstatus: active\ncreated: 2026-10-26\nupdated: 2026-10-26\n---\n# 02_매크로 분석\n",
                encoding="utf-8",
            )

            # Process document through parse_sources.py
            doc = inbox / "fomc_preview.txt"
            doc.write_text("# FOMC Preview\n\nRate policy outlook discussion.\n", encoding="utf-8")

            res_parse = subprocess.run(
                [
                    str(PYTHON_EXE),
                    str(PARSE_SCRIPT),
                    "--file", str(doc),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--subfolder", "310. Reports_Papers",
                    "--domain", "macro",
                    "--up", "[[02_매크로 분석]]",
                    "--source-type", "report",
                    "--author", "[[Valley AI]]",
                    "--org", "[[Valley AI Inc]]",
                    "--published", "2026-10-26",
                    "--aliases", "FOMC Preview 2026",
                    "--summary", "Analysis of FOMC interest rate decision.",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res_parse.returncode, 0, f"Parse failed: {res_parse.stderr}")

            # Run vault_linter.py with --include-inbox
            res_linter = subprocess.run(
                [
                    str(PYTHON_EXE),
                    str(LINTER_SCRIPT),
                    "--vault", str(vault),
                    "--include-inbox",
                    "--format", "json",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(
                res_linter.returncode,
                0,
                f"Linter failed on parsed note in 000. Inbox: {res_linter.stdout}\nErrors: {res_linter.stderr}",
            )

            report = json.loads(res_linter.stdout)
            self.assertEqual(report["summary"]["total_violations"], 0)
            self.assertEqual(report["summary"]["failed"], 0)
            self.assertGreaterEqual(report["summary"]["total_scanned"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
