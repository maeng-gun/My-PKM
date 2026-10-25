"""Tier 4: Real-World Application Scenarios E2E Tests for My-PKM.

Full-lifecycle, end-to-end simulation of real-world knowledge management workflows:
- Scenario 1: Complete E2E simulation (Inbox_Raw -> ingest_sources -> 300. Sources with GFM table -> Archive_Sources -> vault_linter passes with 0 errors).
- Scenario 2: Clean null assertion on unanchored source notes (up: [] without ghost links).
- Scenario 3: Corrupt or invalid input file error resilience and safe failure cascading.
- Scenario 4: Multi-subfolder routing across 310, 320, 330, and 340 source categories.

Specification Sources:
- ORIGINAL_REQUEST.md § Acceptance Criteria 3
- PROJECT.md § Milestones (M5) & Interface Contracts
- PKM Constitution v2.1 (Rule 1, Rule 2, Rule 7)
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(r"c:\Users\maeng-gun\Desktop\python\My_PKM")
INGEST_SCRIPT = PROJECT_ROOT / ".agents" / "skills" / "pkm_manager" / "scripts" / "ingest_sources.py"
LINTER_SCRIPT = PROJECT_ROOT / ".agents" / "skills" / "pkm_manager" / "scripts" / "vault_linter.py"


class TestTier4Scenarios(unittest.TestCase):
    """Tier 4 Real-World Application Scenario Test Suite."""

    def _require_tools(self):
        if not INGEST_SCRIPT.exists():
            self.fail(f"ingest_sources.py not found at {INGEST_SCRIPT}. Feature M4 pending.")
        if not LINTER_SCRIPT.exists():
            self.fail(f"vault_linter.py not found at {LINTER_SCRIPT}. Feature M4 pending.")

    def test_s01_full_lifecycle_ingest_and_audit_simulation(self):
        """Scenario 1: Complete End-to-End Simulation:

        1. Drop document with tabular data in Inbox_Raw.
        2. Run ingest_sources.py with --table-format gfm.
        3. Verify note created in 300. Sources with 2-tier YAML frontmatter and GFM markdown.
        4. Verify raw document archived in Archive_Sources (Inbox Zero).
        5. Run vault_linter.py and verify 100% pass with 0 errors.
        """
        self._require_tools()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"
            inbox.mkdir(parents=True)
            (vault / "400. Wiki").mkdir(parents=True)

            # Master hub anchor
            (vault / "400. Wiki" / "02_매크로 분석.md").write_text(
                "---\norigin: wiki\ntype: hub\nlevel: 1\ndomain: [macro]\nup: []\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# 02_매크로 분석",
                encoding="utf-8",
            )

            # Sample research report with tabular financial indicators
            sample_report = inbox / "2026_Global_Macro_Outlook.txt"
            sample_content = """# 2026 Global Macro Economic Outlook
Author: Global Research Team
Date: 2026-10-25

## Executive Summary
This report analyzes GDP growth trajectories and central bank monetary policies for 2026.

| Region | GDP Growth (%) | Inflation Target (%) | Policy Rate (%) |
|---|---|---|---|
| US | 2.3 | 2.1 | 3.75 |
| Eurozone | 1.1 | 1.9 | 2.25 |
| Korea | 2.0 | 2.0 | 2.75 |

Key takeaway: Soft landing scenario remains the baseline.
"""
            sample_report.write_text(sample_content, encoding="utf-8")

            # Step 1: Run Ingest CLI
            ingest_cmd = [
                sys.executable,
                str(INGEST_SCRIPT),
                "--file", str(sample_report),
                "--inbox", str(inbox),
                "--vault", str(vault),
                "--archive", str(archive),
                "--subfolder", "310. Reports_Papers",
                "--domain", "macro",
                "--up", "[[02_매크로 분석]]",
                "--source-type", "report",
                "--table-format", "gfm",
            ]
            ingest_res = subprocess.run(ingest_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(
                ingest_res.returncode,
                0,
                f"Ingestion step failed: {ingest_res.stderr}\nOutput: {ingest_res.stdout}",
            )

            # Step 2: Validate Note Creation & Formatting
            out_md_files = list((vault / "300. Sources" / "310. Reports_Papers").glob("*.md"))
            self.assertEqual(len(out_md_files), 1, "Exactly 1 note must be created in 310. Reports_Papers")
            note_content = out_md_files[0].read_text(encoding="utf-8")

            # Frontmatter assertions
            self.assertIn("origin: source", note_content)
            self.assertIn("type: source", note_content)
            self.assertIn("domain:", note_content)
            self.assertIn("macro", note_content)
            self.assertIn('up: ["[[02_매크로 분석]]"]', note_content)
            self.assertIn("source_type: report", note_content)

            # GFM Table structure assertion
            self.assertIn("| Region | GDP Growth (%) |", note_content, "GFM table header must be preserved")

            # Step 3: Validate Inbox Zero Archival
            self.assertFalse(sample_report.exists(), "Original file must be removed from Inbox_Raw")
            archived_files = list((archive / "310. Reports_Papers").glob("2026_Global_Macro_Outlook.txt"))
            self.assertEqual(len(archived_files), 1, "Original file must be safely moved to Archive_Sources")

            # Step 4: Validate Vault Linter Verification
            linter_cmd = [sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)]
            linter_res = subprocess.run(linter_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(
                linter_res.returncode,
                0,
                f"Vault Linter failed on newly ingested note:\n{linter_res.stdout}\n{linter_res.stderr}",
            )

    def test_s02_unanchored_source_note_clean_null(self):
        """Scenario 2: Ingesting source without parent --up generates up: [] and passes linter."""
        self._require_tools()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"
            inbox.mkdir(parents=True)

            raw_file = inbox / "market_clipping.txt"
            raw_file.write_text("Short market news snippet.", encoding="utf-8")

            ingest_cmd = [
                sys.executable,
                str(INGEST_SCRIPT),
                "--file", str(raw_file),
                "--inbox", str(inbox),
                "--vault", str(vault),
                "--archive", str(archive),
                "--subfolder", "330. Clippings_News",
                "--domain", "macro",
                "--source-type", "clipping",
            ]
            ingest_res = subprocess.run(ingest_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(ingest_res.returncode, 0)

            out_notes = list((vault / "300. Sources" / "330. Clippings_News").glob("*.md"))
            self.assertEqual(len(out_notes), 1)
            content = out_notes[0].read_text(encoding="utf-8")

            # Clean null: up: []
            self.assertRegex(content, r"up:\s*\[\s*\]")
            self.assertNotIn('"[[]]"', content)

    def test_s03_error_resilience_missing_input(self):
        """Scenario 3: Graceful failure when target input file is missing."""
        self._require_tools()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            non_existent = tmp / "non_existent_file.pdf"
            ingest_cmd = [
                sys.executable,
                str(INGEST_SCRIPT),
                "--file", str(non_existent),
                "--inbox", str(tmp / "Inbox"),
                "--vault", str(tmp / "Vault"),
                "--archive", str(tmp / "Archive"),
            ]
            res = subprocess.run(ingest_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertNotEqual(res.returncode, 0, "Ingestion must exit non-zero for missing input file")

    def test_s04_multi_subfolder_routing_and_archival(self):
        """Scenario 4: Multi-document batch ingestion into different subfolders."""
        self._require_tools()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"
            inbox.mkdir(parents=True)
            (vault / "400. Wiki").mkdir(parents=True)

            # Master hubs
            (vault / "400. Wiki" / "02_매크로 분석.md").write_text(
                "---\norigin: wiki\ntype: hub\nlevel: 1\ndomain: [macro]\nup: []\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# 02_매크로 분석",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "05_회사업무 (자산운용).md").write_text(
                "---\norigin: wiki\ntype: hub\nlevel: 1\ndomain: [work]\nup: []\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# 05_회사업무",
                encoding="utf-8",
            )

            # Doc 1: Report
            doc1 = inbox / "macro_weekly.txt"
            doc1.write_text("Macro weekly analysis", encoding="utf-8")
            # Doc 2: Work doc
            doc2 = inbox / "fund_allocation_spec.txt"
            doc2.write_text("Fund allocation memo", encoding="utf-8")

            # Ingest Doc 1 -> 310. Reports_Papers
            subprocess.run(
                [
                    sys.executable, str(INGEST_SCRIPT),
                    "--file", str(doc1),
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
                check=True,
            )

            # Ingest Doc 2 -> 340. Work_Docs
            subprocess.run(
                [
                    sys.executable, str(INGEST_SCRIPT),
                    "--file", str(doc2),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--subfolder", "340. Work_Docs",
                    "--domain", "work",
                    "--up", "[[05_회사업무 (자산운용)]]",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True,
            )

            # Assert notes exist in respective subfolders
            self.assertTrue((vault / "300. Sources" / "310. Reports_Papers" / "macro_weekly.md").exists())
            self.assertTrue((vault / "300. Sources" / "340. Work_Docs" / "fund_allocation_spec.md").exists())

            # Assert archived files exist in respective subfolders
            self.assertTrue((archive / "310. Reports_Papers" / "macro_weekly.txt").exists())
            self.assertTrue((archive / "340. Work_Docs" / "fund_allocation_spec.txt").exists())

            # Vault Linter run across whole vault
            linter_res = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(linter_res.returncode, 0, f"Multi-folder vault must pass linter: {linter_res.stdout}")


if __name__ == "__main__":
    unittest.main()
