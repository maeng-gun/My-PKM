"""Tier 3: Cross-Feature Combinations E2E Tests for My-PKM.

Tests cross-feature pipelines, multi-module integrations, and junction traversal:
1. Ingestion -> Vault Note Creation -> Vault Linter Verification pipeline.
2. Junction path traversal from local relative paths to GDrive targets.
3. Linter auto-fix repair & re-verification cycle.
4. Binary isolation across ingestion pipeline (Inbox Zero & vault cleanliness).
5. Polyhierarchy and 2D orthogonal ladder frontmatter compliance.

Specification Sources:
- PROJECT.md § Architecture & Interface Contracts
- PKM Constitution v2.1 (Rule 1, 1.2, 2, 5, 6, 7)
- spec_miner_survey_2/handoff.md §5.4 & §5.6
- explorer_survey_3/handoff.md §4.1 & §4.2
"""

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PROJECT_ROOT = Path(r"c:\Users\maeng-gun\Desktop\python\My_PKM")
INGEST_SCRIPT = PROJECT_ROOT / ".agents" / "skills" / "pkm_manager" / "scripts" / "ingest_sources.py"
LINTER_SCRIPT = PROJECT_ROOT / ".agents" / "skills" / "pkm_manager" / "scripts" / "vault_linter.py"


def _safe_unlink(path: Path, max_retries: int = 5, delay: float = 0.1) -> None:
    """Safely unlink a file with retries to absorb transient Windows / GDrive file locks."""
    for attempt in range(max_retries):
        try:
            if path.exists():
                path.unlink()
            return
        except OSError:
            if attempt == max_retries - 1:
                raise
            time.sleep(delay)


class TestTier3Combinations(unittest.TestCase):
    """Tier 3 Cross-Feature Combination Test Suite."""

    def _require_tools(self):
        if not INGEST_SCRIPT.exists():
            self.fail(f"ingest_sources.py not found at {INGEST_SCRIPT}. Feature M4 pending.")
        if not LINTER_SCRIPT.exists():
            self.fail(f"vault_linter.py not found at {LINTER_SCRIPT}. Feature M4 pending.")

    def test_c01_ingest_to_vault_to_linter_pipeline(self):
        """Pipeline: Ingest raw source -> Note written to 300. Sources -> Linter audits note -> 0 errors."""
        self._require_tools()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"
            inbox.mkdir(parents=True)
            (vault / "400. Wiki").mkdir(parents=True)

            # Pre-populate Level 1 Master Hub in vault so parent link resolves
            (vault / "400. Wiki" / "02_매크로 분석.md").write_text(
                "---\norigin: wiki\ntype: hub\nlevel: 1\ndomain: [macro]\nup: []\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# 02_매크로 분석",
                encoding="utf-8",
            )

            # Drop sample raw document in Inbox_Raw
            raw_doc = inbox / "fed_rate_decision.txt"
            raw_doc.write_text(
                "Title: Federal Reserve Rate Decision Oct 2026\nAuthor: Federal Reserve Board\nDate: 2026-10-20\n\nThe Federal Open Market Committee decided to maintain the federal funds rate target range.",
                encoding="utf-8",
            )

            # 1. Run Ingest
            ingest_cmd = [
                sys.executable,
                str(INGEST_SCRIPT),
                "--file", str(raw_doc),
                "--inbox", str(inbox),
                "--vault", str(vault),
                "--archive", str(archive),
                "--subfolder", "310. Reports_Papers",
                "--domain", "macro",
                "--up", "[[02_매크로 분석]]",
                "--source-type", "report",
            ]
            ingest_res = subprocess.run(ingest_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(ingest_res.returncode, 0, f"Ingestion step failed: {ingest_res.stderr}")

            # Verify note was created in 300. Sources
            notes = list((vault / "300. Sources").rglob("*.md"))
            self.assertEqual(len(notes), 1, "Expected 1 note created in 300. Sources")

            # 2. Run Vault Linter
            linter_cmd = [sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)]
            linter_res = subprocess.run(linter_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(
                linter_res.returncode,
                0,
                f"Vault Linter must pass with 0 errors on newly ingested note:\n{linter_res.stdout}\n{linter_res.stderr}",
            )

    def test_c02_junction_relative_path_traversal_to_gdrive(self):
        """Junction Traversal: Relative file I/O on workspace junctions resolves to GDrive targets."""
        for junction_name in ["scratch", "input_staging", "archive", "secrets", "AGY_Artifacts"]:
            rel_path = PROJECT_ROOT / junction_name
            self.assertTrue(rel_path.exists(), f"Junction {junction_name} must exist")
            self.assertTrue(rel_path.is_dir(), f"Junction {junction_name} must be a directory")

        # Test write and read roundtrip via scratch junction
        scratch_rel = PROJECT_ROOT / "scratch"
        test_file = scratch_rel / ".junction_e2e_probe.tmp"
        probe_data = "My-PKM Junction E2E Probe Content 2026-10-25"

        try:
            test_file.write_text(probe_data, encoding="utf-8")
            self.assertTrue(test_file.exists(), "Probe file must exist via relative junction path")
            read_back = test_file.read_text(encoding="utf-8")
            self.assertEqual(read_back, probe_data, "Probe file content must match exactly")

            # Confirm file also exists directly on the target path
            try:
                target_root = os.readlink(scratch_rel)
                if target_root.startswith("\\\\?\\"):
                    target_root = target_root[4:]
                target_file = Path(target_root) / ".junction_e2e_probe.tmp"
                self.assertTrue(target_file.exists(), "Probe file must be observable directly on GDrive target")
            except OSError:
                pass
        finally:
            _safe_unlink(test_file)

    def test_c03_linter_fix_repair_cycle(self):
        """Auto-Fix Cycle: Multi-note vault with ghost links -> linter fails -> linter --fix -> linter passes."""
        if not LINTER_SCRIPT.exists():
            self.fail(f"vault_linter.py not found at {LINTER_SCRIPT}. Feature M4 pending.")

        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "100. Concepts").mkdir(parents=True)
            (vault / "200. AI_logs").mkdir(parents=True)
            (vault / "300. Sources").mkdir(parents=True)

            # Note 1: Clean
            (vault / "100. Concepts" / "ConceptA.md").write_text(
                "---\norigin: human\ntype: concept\ndomain: [theory]\nup: ['[[01_경제 및 금융 이론]]']\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Concept A",
                encoding="utf-8",
            )
            # Note 2: Ghost link in up
            (vault / "200. AI_logs" / "LogB.md").write_text(
                '---\norigin: ai\ntype: log\ndomain: [macro]\nup:\n  - "[[]]"\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Log B',
                encoding="utf-8",
            )
            # Note 3: Ghost link in source
            (vault / "300. Sources" / "SourceC.md").write_text(
                '---\norigin: source\ntype: source\ndomain: [macro]\nup: ["[[02_매크로 분석]]"]\nsource:\n  - "[[]]"\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Source C',
                encoding="utf-8",
            )

            # First scan: must fail
            res1 = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(res1.returncode, 1, "Vault with ghost links must fail initial linting")

            # Run --fix
            res_fix = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault), "--fix"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)

            # Re-scan: must now pass
            res2 = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(res2.returncode, 0, f"Vault must pass after auto-fix repair: {res2.stdout}")

    def test_c04_binary_isolation_across_ingestion(self):
        """Binary Isolation: Raw binary ingested -> Markdown in vault -> Original binary moved to archive."""
        self._require_tools()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"
            inbox.mkdir(parents=True)

            raw_file = inbox / "quarterly_earnings.txt"
            raw_file.write_text("Quarterly Corporate Earnings Q3 2026\nRevenue grew by 15% YoY.", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable,
                    str(INGEST_SCRIPT),
                    "--file", str(raw_file),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--subfolder", "310. Reports_Papers",
                    "--domain", "equity",
                    "--up", "[[03_산업 및 기업분석]]",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0)

            # 1. Inbox must be empty of this file
            self.assertFalse(raw_file.exists(), "Inbox Zero: source file must not remain in Inbox_Raw")
            # 2. Vault must contain only .md files
            for p in vault.rglob("*"):
                if p.is_file():
                    self.assertEqual(p.suffix.lower(), ".md", f"Vault must contain only .md files, found: {p}")
            # 3. Archive must contain original raw file
            archived = list(archive.rglob("quarterly_earnings.txt"))
            self.assertEqual(len(archived), 1, "Original raw file must be archived in Archive_Sources")

    def test_c05_polyhierarchy_and_ladder_frontmatter_accepted(self):
        """Rule 5 & 6: Polyhierarchy up (orthogonal axes) and prev (horizontal ladder) are accepted by linter."""
        if not LINTER_SCRIPT.exists():
            self.fail(f"vault_linter.py not found at {LINTER_SCRIPT}. Feature M4 pending.")

        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            concept_dir = vault / "100. Concepts"
            concept_dir.mkdir(parents=True)

            # Orthogonal polyhierarchy: Macro Theory axis + Family Portfolio axis
            poly_note = concept_dir / "AllWeatherStrategy.md"
            poly_note.write_text(
                """---
origin: human
type: concept
domain:
  - theory
  - portfolio
up:
  - "[[01_경제 및 금융 이론]]"
  - "[[04_가족 투자 포트폴리오]]"
prev:
  - "[[2026-Q2 올웨더 자산배분 성과]]"
source:
  - "[[달리오의 원칙]]"
status: active
created: 2026-10-25
updated: 2026-10-25
---
# 올웨더 포트폴리오 전략
수직 사다리(up)와 수평 사다리(prev, source)가 결합된 직교 구조 메모.
""",
                encoding="utf-8",
            )

            res = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(res.returncode, 0, f"Polyhierarchy and 2D ladder frontmatter must be accepted: {res.stdout}")


if __name__ == "__main__":
    unittest.main()
