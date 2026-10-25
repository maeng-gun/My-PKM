"""Tier 2: Boundary & Corner Cases E2E Tests for My-PKM.

Tests constitutional boundaries, edge cases, exemptions, and constraints:
1. Empty link clean null (`[]` vs `"[[]]"` and `--fix` transformation).
2. Level 1 Master Hub orphan exemption (`01_경제 및 금융 이론.md` ~ `07_자녀교육.md`).
3. Excluded folder handling (`000. Inbox`, `900. config`, `Notion`, `.obsidian`, `.trash`).
4. Domain code validation (standard 7 codes, max 2 "1+1" rule, unknown codes).
5. Heavy binary isolation & allowed attachment locations.

Specification Sources:
- PKM Constitution v2.1 (Rule 1, 1.2, 2.1, 2.2, 2.4, 5)
- spec_miner_survey_2/handoff.md §4 & §5.6
- explorer_survey_3/handoff.md §4.2
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(r"c:\Users\maeng-gun\Desktop\python\My_PKM")
LINTER_SCRIPT = PROJECT_ROOT / ".agents" / "skills" / "pkm_manager" / "scripts" / "vault_linter.py"

LEVEL_1_HUBS = [
    "01_경제 및 금융 이론.md",
    "02_매크로 분석.md",
    "03_산업 및 기업분석.md",
    "04_가족 투자 포트폴리오.md",
    "05_회사업무 (자산운용).md",
    "06_AI 활용 및 PKM 구축.md",
    "07_자녀교육.md",
]

STANDARD_DOMAINS = [
    "theory",
    "macro",
    "equity",
    "portfolio",
    "work",
    "ai-pkm",
    "education",
]


class TestTier2Boundaries(unittest.TestCase):
    """Tier 2 Boundary, Exemption & Edge Case Test Suite."""

    def _require_linter(self):
        if not LINTER_SCRIPT.exists():
            self.fail(f"vault_linter.py not found at {LINTER_SCRIPT}. Feature M4 pending.")

    def test_b01_clean_null_empty_brackets_vs_ghost_links(self):
        """Rule 2.2: Verify empty link lists MUST be [] and '[[]]' is flagged as C2 error."""
        self._require_linter()
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            concept_dir = vault / "100. Concepts"
            concept_dir.mkdir(parents=True)

            # Note with clean null
            clean_note = concept_dir / "CleanNote.md"
            clean_note.write_text(
                "---\norigin: human\ntype: concept\ndomain: [theory]\nup: ['[[01_경제 및 금융 이론]]']\nprev: []\nsource: []\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Clean Note",
                encoding="utf-8",
            )

            # Note with ghost link
            ghost_note = concept_dir / "GhostNote.md"
            ghost_note.write_text(
                '---\norigin: human\ntype: concept\ndomain: [theory]\nup: ["[[01_경제 및 금융 이론]]"]\nprev:\n  - "[[]]"\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Ghost Note',
                encoding="utf-8",
            )

            res = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(res.returncode, 1, "Linter must fail when ghost link is present")
            self.assertIn("GhostNote.md", res.stdout)
            self.assertNotIn("CleanNote.md", res.stdout, "Clean note must not be flagged")

    def test_b02_linter_fix_mode_transforms_ghost_links(self):
        """Rule 2.2 Auto-fix: vault_linter.py --fix converts '[[]]' into [] in frontmatter."""
        self._require_linter()
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            concept_dir = vault / "100. Concepts"
            concept_dir.mkdir(parents=True)

            target_note = concept_dir / "LegacyTemplateNote.md"
            target_note.write_text(
                '---\norigin: human\ntype: concept\ndomain: [theory]\nup:\n  - "[[01_경제 및 금융 이론]]"\nprev:\n  - "[[]]"\nsource:\n  - "[[]]"\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Legacy Note',
                encoding="utf-8",
            )

            # Run with --fix
            res_fix = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault), "--fix"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            fixed_content = target_note.read_text(encoding="utf-8")
            self.assertNotIn('"[[]]"', fixed_content, "Auto-fix must eliminate all '[[]]' occurrences")

            # Re-running linter must now pass
            res_after = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(res_after.returncode, 0, f"Vault must pass after auto-fix: {res_after.stdout}")

    def test_b03_level_1_master_hubs_orphan_exemption(self):
        """Rule 5 & Rule 2.5: The 7 Level 1 Master Hubs are exempt from orphan check (up: [] is valid)."""
        self._require_linter()
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            wiki_dir = vault / "400. Wiki"
            wiki_dir.mkdir(parents=True)

            # Create all 7 Level 1 Master Hubs with up: []
            for hub_name in LEVEL_1_HUBS:
                hub_file = wiki_dir / hub_name
                hub_file.write_text(
                    f"---\norigin: wiki\ntype: hub\nlevel: 1\ndomain: [theory]\nup: []\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# {hub_name[:-3]}",
                    encoding="utf-8",
                )

            res = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(res.returncode, 0, f"All Level 1 Master Hubs must be exempt from orphan check: {res.stdout}")

    def test_b04_non_master_hub_orphan_flagged(self):
        """Rule 5: Non-master notes with up: [] MUST be flagged as orphan notes (C3)."""
        self._require_linter()
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            wiki_dir = vault / "400. Wiki"
            wiki_dir.mkdir(parents=True)

            # Level 2 Hub or regular note with up: []
            orphan_hub = wiki_dir / "10_임의의 허브.md"
            orphan_hub.write_text(
                "---\norigin: wiki\ntype: hub\nlevel: 2\ndomain: [macro]\nup: []\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# 임의의 허브",
                encoding="utf-8",
            )

            res = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(res.returncode, 1, "Non-master hub with up: [] must trigger C3 violation")
            self.assertIn("10_임의의 허브.md", res.stdout)

    def test_b05_excluded_folders_ignored_by_default(self):
        """Rule 1: 000. Inbox, 900. config, Notion, .obsidian, .trash are ignored by default."""
        self._require_linter()
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "000. Inbox").mkdir(parents=True)
            (vault / "900. config" / "930. Template").mkdir(parents=True)
            (vault / "Notion" / "Master DB").mkdir(parents=True)
            (vault / ".obsidian").mkdir(parents=True)
            (vault / ".trash").mkdir(parents=True)

            # Put non-compliant notes in excluded folders
            (vault / "000. Inbox" / "RawIdea.md").write_text("No frontmatter idea", encoding="utf-8")
            (vault / "900. config" / "930. Template" / "Template.md").write_text('up: - "[[]]"', encoding="utf-8")
            (vault / "Notion" / "Master DB" / "Export.md").write_text("# Raw Export", encoding="utf-8")
            (vault / ".obsidian" / "workspace.json").write_text("{}", encoding="utf-8")

            # Also add 1 valid note in 100. Concepts so vault is not empty
            concept_dir = vault / "100. Concepts"
            concept_dir.mkdir(parents=True)
            (concept_dir / "ValidConcept.md").write_text(
                "---\norigin: human\ntype: concept\ndomain: [theory]\nup: ['[[01_경제 및 금융 이론]]']\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Valid",
                encoding="utf-8",
            )

            res = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(res.returncode, 0, f"Excluded folders must not cause linter failures: {res.stdout}")

    def test_b06_inbox_audited_when_flag_present(self):
        """Rule 1: When --include-inbox is passed, 000. Inbox notes ARE evaluated."""
        self._require_linter()
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            inbox_dir = vault / "000. Inbox"
            inbox_dir.mkdir(parents=True)
            (inbox_dir / "UnclassifiedNote.md").write_text("No frontmatter", encoding="utf-8")

            res = subprocess.run(
                [sys.executable, str(LINTER_SCRIPT), "--vault", str(vault), "--include-inbox"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 1, "--include-inbox must flag non-compliant inbox notes")
            self.assertIn("UnclassifiedNote.md", res.stdout)

    def test_b07_domain_code_validation_valid_single_and_dual(self):
        """Rule 2.4: Domain list with 1 or 2 standard codes is valid."""
        self._require_linter()
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            concept_dir = vault / "100. Concepts"
            concept_dir.mkdir(parents=True)

            # 1 code: [macro]
            (concept_dir / "SingleDomain.md").write_text(
                "---\norigin: human\ntype: concept\ndomain:\n  - macro\nup: ['[[02_매크로 분석]]']\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Single",
                encoding="utf-8",
            )
            # 2 codes: [macro, equity]
            (concept_dir / "DualDomain.md").write_text(
                "---\norigin: human\ntype: concept\ndomain:\n  - macro\n  - equity\nup: ['[[02_매크로 분석]]']\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Dual",
                encoding="utf-8",
            )

            res = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(res.returncode, 0, f"Valid single/dual domain notes must pass: {res.stdout}")

    def test_b08_domain_code_validation_exceeding_max_2_rejected(self):
        """Rule 2.4: Domain list with > 2 items violates max 2 (1+1) rule."""
        self._require_linter()
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            concept_dir = vault / "100. Concepts"
            concept_dir.mkdir(parents=True)

            (concept_dir / "TripleDomain.md").write_text(
                "---\norigin: human\ntype: concept\ndomain:\n  - macro\n  - equity\n  - portfolio\nup: ['[[02_매크로 분석]]']\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Triple",
                encoding="utf-8",
            )

            res = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(res.returncode, 1, "More than 2 domains must be flagged as violation")
            self.assertTrue(
                "domain" in res.stdout.lower() or "c1" in res.stdout.lower(),
                "Output must mention domain violation",
            )

    def test_b09_unknown_domain_code_rejected(self):
        """Rule 2.4: Domain code not in standard 7 codes is rejected."""
        self._require_linter()
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            concept_dir = vault / "100. Concepts"
            concept_dir.mkdir(parents=True)

            (concept_dir / "InvalidDomain.md").write_text(
                "---\norigin: human\ntype: concept\ndomain:\n  - crypto_defi\nup: ['[[02_매크로 분석]]']\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Invalid Domain",
                encoding="utf-8",
            )

            res = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(res.returncode, 1, "Non-standard domain code must be flagged as violation")

    def test_b10_heavy_binary_isolation_and_allowed_attachments(self):
        """Rule 1.2: Heavy binaries (.pdf, .hwpx, .xlsx, .docx) barred from vault; images in 900. config allowed."""
        self._require_linter()
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            sources_dir = vault / "300. Sources" / "310. Reports_Papers"
            sources_dir.mkdir(parents=True)
            attached_dir = vault / "900. config" / "910. Attached"
            attached_dir.mkdir(parents=True)

            # Allowed image in 900. config/910. Attached
            (attached_dir / "diagram.png").write_bytes(b"\x89PNG dummy image")

            # Valid note in sources
            (sources_dir / "ValidNote.md").write_text(
                "---\norigin: source\ntype: source\ndomain: [macro]\nup: ['[[02_매크로 분석]]']\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Valid Note",
                encoding="utf-8",
            )

            # Verify passes with image in 910. Attached
            res_pass = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(res_pass.returncode, 0, f"Image in 910. Attached must be allowed: {res_pass.stdout}")

            # Now introduce a heavy spreadsheet binary into 300. Sources
            (sources_dir / "Financials.xlsx").write_bytes(b"PK dummy zip/excel")
            res_fail = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(res_fail.returncode, 1, "Heavy binary (.xlsx) in vault must trigger C5 error")
            self.assertIn("Financials.xlsx", res_fail.stdout)


if __name__ == "__main__":
    unittest.main()
