"""Reference Pipeline Harness for Macro Lecture Pipeline Contract Testing.

Implements the contract defined in PROJECT.md § Interface Contracts.
Used directly by tests or as reference verification for run_macro_lecture_pipeline.py.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

from tests.e2e.fixtures.curriculum_fixture import (
    SYNTHETIC_CURRICULUM_DATA,
    create_synthetic_pdf,
)
from tests.e2e.fixtures.validation_gateways import (
    PDF_FILENAME_PATTERN,
    atomic_archive_file,
    format_lecture_filename,
    validate_markdown_note,
    validate_pdf_binary,
    verify_inbox_zero,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PARSE_SCRIPT = PROJECT_ROOT / ".agents" / "skills" / "pkm_parse" / "scripts" / "parse_sources.py"
DOWNLOAD_SCRIPT = PROJECT_ROOT / ".agents" / "skills" / "valley_ai_scrap" / "scripts" / "download_macro_lecture.py"
PIPELINE_SCRIPT = PROJECT_ROOT / ".agents" / "skills" / "valley_ai_scrap" / "scripts" / "run_macro_lecture_pipeline.py"


class MacroLecturePipelineHarness:
    """Orchestrates the 6-step Valley AI Macro Lecture Pipeline:

    1. Download / stage lecture PDFs (2회차 1강 ~ 9회차 3강)
    2. Validate PDF binaries (Gateway 1)
    3. Execute kordoc / parse_sources.py (GFM tables, pure text, 0 images)
    4. Validate generated Markdown notes (Gateway 2)
    5. Atomically archive source PDFs to Archive_Sources/
    6. Verify Inbox Zero in Inbox_temp/ (Gateway 3)
    """

    def __init__(
        self,
        inbox_temp: Path,
        archive_dir: Path,
        vault_dir: Path,
        dry_run: bool = False,
    ):
        self.inbox_temp = Path(inbox_temp)
        self.archive_dir = Path(archive_dir)
        self.vault_dir = Path(vault_dir)
        self.dry_run = dry_run
        self.downloaded_files: List[Path] = []
        self.parsed_notes: List[Path] = []
        self.archived_files: List[Path] = []

    def run_step_download(self, start_round: int = 2, end_round: int = 9) -> List[Path]:
        """Step 1: Download or stage lecture slide PDFs."""
        self.inbox_temp.mkdir(parents=True, exist_ok=True)
        results: List[Path] = []

        for part in SYNTHETIC_CURRICULUM_DATA:
            r = part["round"]
            if not (start_round <= r <= end_round):
                continue
            for lec in part["lectures"]:
                if lec["lecture_type"] != "material" or not lec["attachment_url"]:
                    # Skip attachment-less lectures
                    continue
                filename = format_lecture_filename(r, lec["lecture_num"], lec["title"])
                dest_path = self.inbox_temp / filename
                if not self.dry_run:
                    create_synthetic_pdf(dest_path, title=lec["title"])
                results.append(dest_path)

        self.downloaded_files = results
        return results

    def run_step_validate_pdfs(self) -> Tuple[bool, List[str]]:
        """Step 2: Validate all PDFs in inbox_temp."""
        pdf_files = list(self.inbox_temp.glob("*.pdf"))
        errors: List[str] = []
        for pdf in pdf_files:
            ok, msg = validate_pdf_binary(pdf)
            if not ok:
                errors.append(f"{pdf.name}: {msg}")
        return len(errors) == 0, errors

    def run_step_parse(self) -> List[Path]:
        """Step 3: Execute parse_sources.py for each PDF in inbox_temp."""
        pdf_files = sorted(list(self.inbox_temp.glob("*.pdf")))
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        (self.vault_dir / "000. Inbox").mkdir(parents=True, exist_ok=True)
        notes: List[Path] = []

        if self.dry_run:
            for pdf in pdf_files:
                notes.append(self.inbox_temp / f"{pdf.stem}.md")
            self.parsed_notes = notes
            return notes

        for pdf in pdf_files:
            cmd = [
                sys.executable,
                str(PARSE_SCRIPT),
                "--file", str(pdf),
                "--vault", str(self.vault_dir),
                "--archive", str(self.archive_dir),
                "--subfolder", "320. Lectures",
                "--table-format", "gfm",
                "--no-images",
                "--domain", "macro",
                "--source-type", "report",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            if res.returncode != 0:
                raise RuntimeError(f"parse_sources failed on {pdf.name}: {res.stderr}")

            # Note is generated in vault_dir / '000. Inbox' / '{pdf.stem}.md'
            vault_note = self.vault_dir / "000. Inbox" / f"{pdf.stem}.md"
            # Ensure note is also in inbox_temp per R2 contract
            inbox_note = self.inbox_temp / f"{pdf.stem}.md"
            if vault_note.exists() and not inbox_note.exists():
                inbox_note.write_text(vault_note.read_text(encoding="utf-8"), encoding="utf-8")
            notes.append(inbox_note)

        self.parsed_notes = notes
        return notes

    def run_step_validate_markdown(self) -> Tuple[bool, List[str]]:
        """Step 4: Validate all generated markdown notes."""
        md_files = list(self.inbox_temp.glob("*.md"))
        errors: List[str] = []
        for md in md_files:
            ok, msg = validate_markdown_note(md)
            if not ok:
                errors.append(f"{md.name}: {msg}")
        return len(errors) == 0, errors

    def run_step_archive(self) -> List[Path]:
        """Step 5: Atomically archive all source PDFs to Archive_Sources/320. Lectures/."""
        target_archive = self.archive_dir / "320. Lectures"
        target_archive.mkdir(parents=True, exist_ok=True)

        if self.dry_run:
            return [target_archive / p.name for p in self.downloaded_files]

        for pdf in list(self.inbox_temp.glob("*.pdf")):
            dst = target_archive / pdf.name
            atomic_archive_file(pdf, dst)

        archived = sorted(list(target_archive.glob("*.pdf")))
        self.archived_files = archived
        return archived

    def run_step_verify_inbox_zero(self) -> Tuple[bool, str]:
        """Step 6: Verify Inbox Zero in inbox_temp."""
        if self.dry_run:
            return True, "[DRY-RUN] Inbox Zero verified"
        return verify_inbox_zero(self.inbox_temp, self.archive_dir)

    def run_all(self) -> int:
        """Run full 6-step pipeline sequence. Returns 0 on success, 1 on failure."""
        # 1. Download
        self.run_step_download()

        # 2. Validate PDFs
        ok_pdf, pdf_errs = self.run_step_validate_pdfs()
        if not ok_pdf:
            print(f"[ERROR] PDF validation failed: {pdf_errs}", file=sys.stderr)
            return 1

        # 3. Parse
        self.run_step_parse()

        # 4. Validate MD
        ok_md, md_errs = self.run_step_validate_markdown()
        if not ok_md:
            print(f"[ERROR] Markdown validation failed: {md_errs}", file=sys.stderr)
            return 1

        # 5. Archive
        self.run_step_archive()

        # 6. Verify Inbox Zero
        ok_zero, zero_msg = self.run_step_verify_inbox_zero()
        if not ok_zero:
            print(f"[ERROR] Inbox Zero verification failed: {zero_msg}", file=sys.stderr)
            return 1

        return 0


def execute_pipeline(args_list: List[str]) -> Tuple[int, str, str]:
    """Execute pipeline CLI if script exists, otherwise invoke harness."""
    if PIPELINE_SCRIPT.exists():
        cmd = [sys.executable, str(PIPELINE_SCRIPT)] + args_list
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        return res.returncode, res.stdout, res.stderr

    # Parse args with harness CLI contract
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--parse", action="store_true")
    parser.add_argument("--archive", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--inbox-temp", default="./inbox_temp")
    parser.add_argument("--archive-dir", default="./archive_sources")
    parser.add_argument("--vault", default="./vault")
    parser.add_argument("--dry-run", action="store_true")

    parsed, _ = parser.parse_known_args(args_list)

    harness = MacroLecturePipelineHarness(
        inbox_temp=Path(parsed.inbox_temp),
        archive_dir=Path(parsed.archive_dir),
        vault_dir=Path(parsed.vault),
        dry_run=parsed.dry_run,
    )

    if parsed.dry_run:
        return 0, "[DRY-RUN] Pipeline execution preview complete.", ""

    if parsed.all:
        rc = harness.run_all()
        return rc, "All steps completed successfully.", ""

    if parsed.download:
        harness.run_step_download()
    if parsed.parse:
        harness.run_step_parse()
    if parsed.archive:
        harness.run_step_archive()
        harness.run_step_verify_inbox_zero()

    return 0, "Selected steps completed.", ""
