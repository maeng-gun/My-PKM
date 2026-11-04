"""Adversarial stress test suite for Milestone 1: Valley AI News Scraping Production Data Collection.

Authored by empirical_challenger (challenger_scrap_m1_1).
Verifies live files in My-Wiki/000. Inbox/:
1. Scrap files manifest, count, and naming conventions
2. Strict UTF-8 encoding, BOM absence, surrogate absence, null byte absence
3. 100% absence of YAML/TOML frontmatter and strict H1 header compliance
4. Date boundary constraints (2026-10-12 to 2026-11-01) and weekend absence (no dummy files)
5. File size threshold (> 5,000 bytes) and content density
6. Markdown structure, article metadata (date, URL), article counts (19 total articles)
7. Absence of unparsed raw HTML (<script>, <style>, <iframe>, <div>, etc.)
8. Vault isolation and pre-existing file preservation in 000. Inbox/
"""

from datetime import datetime, date
from pathlib import Path
import re
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INBOX_DIR = PROJECT_ROOT / "My-Wiki" / "000. Inbox"


class TestValleyScrapAdversarial(unittest.TestCase):
    """Empirical adversarial test suite for Valley AI scraped inbox files."""

    @classmethod
    def setUpClass(cls):
        cls.inbox_dir = INBOX_DIR
        cls.assertTrue(cls.inbox_dir.exists(), f"Inbox directory {cls.inbox_dir} must exist")
        cls.scrap_files = sorted(list(cls.inbox_dir.glob("밸리AI*.md")))
        cls.all_files = sorted(list(cls.inbox_dir.glob("*.md")))

    def test_01_scrap_files_manifest_and_counts(self):
        """Verify total file counts and naming convention."""
        self.assertEqual(
            len(self.scrap_files),
            21,
            f"Expected exactly 21 scraped files, found {len(self.scrap_files)}"
        )

        wsj_files = [f for f in self.scrap_files if "월가소식" in f.name]
        insight_files = [f for f in self.scrap_files if "오늘의 인사이트" in f.name]

        self.assertEqual(len(wsj_files), 14, f"Expected 14 월가소식 files, got {len(wsj_files)}")
        self.assertEqual(len(insight_files), 7, f"Expected 7 오늘의 인사이트 files, got {len(insight_files)}")

        name_pattern = re.compile(r"^밸리AI (월가소식 리포트|오늘의 인사이트)_\d{4}-\d{2}-\d{2}\.md$")
        for f in self.scrap_files:
            self.assertIsNotNone(
                name_pattern.match(f.name),
                f"File {f.name} does not match strict naming convention"
            )

    def test_02_strict_utf8_encoding_and_no_corruptions(self):
        """Verify strict UTF-8 decoding, BOM absence, surrogate absence, and null byte absence."""
        for f in self.scrap_files:
            raw_bytes = f.read_bytes()
            # Assert no UTF-8 BOM
            self.assertFalse(
                raw_bytes.startswith(b"\xef\xbb\xbf"),
                f"File {f.name} contains UTF-8 BOM"
            )
            # Assert no null bytes
            self.assertNotIn(
                b"\x00",
                raw_bytes,
                f"File {f.name} contains embedded null byte"
            )

            # Strict UTF-8 decoding
            try:
                text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError as exc:
                self.fail(f"File {f.name} failed strict UTF-8 decode: {exc}")

            # Check for surrogate characters
            surrogate_match = re.search(r"[\ud800-\udfff]", text)
            self.assertIsNone(
                surrogate_match,
                f"File {f.name} contains illegal surrogate character at position {surrogate_match.start() if surrogate_match else -1}"
            )

    def test_03_frontmatter_absence_and_h1_header(self):
        """Verify 100% absence of frontmatter and valid H1 header matching filename."""
        frontmatter_pattern = re.compile(r"^---\s*[\r\n]")
        toml_pattern = re.compile(r"^\+\+\+\s*[\r\n]")
        header_pattern = re.compile(r"^# 밸리AI (월가소식 리포트|오늘의 인사이트) \((\d{4}-\d{2}-\d{2})\)")

        for f in self.scrap_files:
            text = f.read_text(encoding="utf-8")
            self.assertIsNone(
                frontmatter_pattern.match(text),
                f"File {f.name} illegally starts with YAML frontmatter delimiter (---)"
            )
            self.assertIsNone(
                toml_pattern.match(text),
                f"File {f.name} illegally starts with TOML frontmatter delimiter (+++)"
            )

            first_line = text.splitlines()[0] if text.splitlines() else ""
            self.assertTrue(
                first_line.startswith("# 밸리AI "),
                f"File {f.name} line 1 must start with '# 밸리AI ', got: {first_line!r}"
            )

            match = header_pattern.match(first_line)
            self.assertIsNotNone(
                match,
                f"File {f.name} header does not match expected pattern: {first_line!r}"
            )

            header_date = match.group(2)
            # Date in filename
            fn_date_match = re.search(r"\d{4}-\d{2}-\d{2}", f.name)
            self.assertIsNotNone(fn_date_match)
            fn_date = fn_date_match.group(0)
            self.assertEqual(
                header_date,
                fn_date,
                f"Date mismatch in {f.name}: header has {header_date}, filename has {fn_date}"
            )

    def test_04_date_boundaries_and_calendar_integrity(self):
        """Verify date boundaries (2026-10-12 to 2026-11-01) and absence of weekend files."""
        min_date = date(2026, 10, 12)
        max_date = date(2026, 11, 1)

        collected_dates = set()
        for f in self.scrap_files:
            m = re.search(r"(\d{4})-(\d{2})-(\d{2})", f.name)
            self.assertIsNotNone(m, f"Could not extract date from {f.name}")
            file_date = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

            self.assertGreaterEqual(
                file_date,
                min_date,
                f"File {f.name} date {file_date} is earlier than start date {min_date}"
            )
            self.assertLessEqual(
                file_date,
                max_date,
                f"File {f.name} date {file_date} is later than end date {max_date}"
            )
            collected_dates.add(file_date)

        # Check weekends in range: 10-17, 10-18, 10-24, 10-25, 10-31, 11-01
        weekend_dates = {
            date(2026, 10, 17),
            date(2026, 10, 18),
            date(2026, 10, 24),
            date(2026, 10, 25),
            date(2026, 10, 31),
            date(2026, 11, 1),
        }
        for wd in weekend_dates:
            self.assertNotIn(
                wd,
                collected_dates,
                f"Weekend date {wd} should have been skipped, but file was collected"
            )

        # Check no dummy/empty files with weekend dates exist anywhere in 000. Inbox
        for f in self.all_files:
            for wd in weekend_dates:
                wd_str = wd.isoformat()
                self.assertNotIn(
                    wd_str,
                    f.name,
                    f"Unexpected file containing weekend date {wd_str} found: {f.name}"
                )

    def test_05_file_size_threshold_and_content_density(self):
        """Verify each file > 5,000 bytes and contains substantive text (not whitespace padded)."""
        for f in self.scrap_files:
            size = f.stat().st_size
            self.assertGreater(
                size,
                5000,
                f"File {f.name} is too small ({size} bytes <= 5000 bytes threshold)"
            )
            # Worker claimed > 15,000 bytes
            self.assertGreater(
                size,
                15000,
                f"File {f.name} size {size} bytes is below worker-reported minimum of 15,000 bytes"
            )

            text = f.read_text(encoding="utf-8")
            non_ws = re.sub(r"\s+", "", text)
            self.assertGreater(
                len(non_ws),
                4000,
                f"File {f.name} non-whitespace character count {len(non_ws)} is too low"
            )

    def test_06_markdown_structure_and_article_metadata(self):
        """Verify markdown structure, article metadata (작성일시, 원문링크), and 21 total articles."""
        total_articles = 0
        date_pattern = re.compile(r"\*\*작성일시:\*\*\s*(\d{4}-\d{2}-\d{2})")
        link_pattern = re.compile(r"\*\*원문링크:\*\*\s*(https://www\.valley\.town/premium/wsaj-column/[a-zA-Z0-9_\-]+/[a-f0-9]+)")

        for f in self.scrap_files:
            text = f.read_text(encoding="utf-8")
            fn_date = re.search(r"\d{4}-\d{2}-\d{2}", f.name).group(0)

            date_matches = date_pattern.findall(text)
            link_matches = link_pattern.findall(text)

            self.assertGreaterEqual(
                len(date_matches),
                1,
                f"File {f.name} missing '**작성일시:**'"
            )
            self.assertEqual(
                len(date_matches),
                len(link_matches),
                f"File {f.name} has mismatched date and link counts: {len(date_matches)} vs {len(link_matches)}"
            )

            # Check dates inside articles match file date
            for article_date in date_matches:
                self.assertEqual(
                    article_date,
                    fn_date,
                    f"File {f.name} contains article date {article_date} mismatched with file date {fn_date}"
                )

            # In Iteration 2, every file contains exactly 1 article
            self.assertEqual(
                len(date_matches),
                1,
                f"Expected 1 article in {f.name}, found {len(date_matches)}"
            )

            total_articles += len(date_matches)

        self.assertEqual(
            total_articles,
            21,
            f"Expected exactly 21 total articles across all files, found {total_articles}"
        )

    def test_07_no_unparsed_html_or_script_residue(self):
        """Verify absence of unparsed raw HTML tags (<script>, <style>)."""
        forbidden_tags = [
            ("script", re.compile(r"<\s*script\b[^>]*>", re.IGNORECASE)),
            ("/script", re.compile(r"<\s*/\s*script\s*>", re.IGNORECASE)),
            ("style", re.compile(r"<\s*style\b[^>]*>", re.IGNORECASE)),
            ("/style", re.compile(r"<\s*/\s*style\s*>", re.IGNORECASE)),
            ("iframe", re.compile(r"<\s*iframe\b[^>]*>", re.IGNORECASE)),
            ("/iframe", re.compile(r"<\s*/\s*iframe\s*>", re.IGNORECASE)),
        ]

        for f in self.scrap_files:
            text = f.read_text(encoding="utf-8")
            for tag_name, tag_regex in forbidden_tags:
                match = tag_regex.search(text)
                if match:
                    self.fail(
                        f"File {f.name} contains raw HTML <{tag_name}> residue at index {match.start()}: {match.group(0)!r}"
                    )

    def test_08_vault_isolation_and_inbox_integrity(self):
        """Verify pre-existing files in Inbox were preserved and no unauthorized files leaked elsewhere."""
        # Pre-existing files check
        untitled_1 = self.inbox_dir / "무제.md"
        untitled_2 = self.inbox_dir / "무제 1.md"
        self.assertTrue(untitled_1.exists(), "Pre-existing '무제.md' must still exist")
        self.assertTrue(untitled_2.exists(), "Pre-existing '무제 1.md' must still exist")
        self.assertEqual(untitled_1.stat().st_size, 31, "'무제.md' size was altered")
        self.assertEqual(untitled_2.stat().st_size, 22, "'무제 1.md' size was altered")

        # Total files in 000. Inbox should be exactly 21 scrap + 2 pre-existing = 23 files
        self.assertEqual(
            len(self.all_files),
            23,
            f"Expected exactly 23 markdown files in 000. Inbox, found {len(self.all_files)}: {[f.name for f in self.all_files]}"
        )

        # Check other vault folders for any leaked scrap files from this milestone
        # Milestone files match '밸리AI (월가소식|오늘의 인사이트)*'
        vault_root = PROJECT_ROOT / "My-Wiki"
        other_folders = [
            vault_root / "100. Concepts",
            vault_root / "200. AI_logs",
            vault_root / "300. Sources",
            vault_root / "400. Wiki",
            vault_root / "500. Index",
        ]
        milestone_pattern = re.compile(r"^밸리AI (월가소식 리포트|오늘의 인사이트)_2026-(10|11)-\d{2}\.md$")
        for folder in other_folders:
            if folder.exists():
                leaked = [f for f in folder.rglob("*.md") if milestone_pattern.match(f.name)]
                self.assertEqual(
                    leaked,
                    [],
                    f"Unauthorized scrap files leaked into {folder}: {[f.name for f in leaked]}"
                )


if __name__ == "__main__":
    unittest.main()
