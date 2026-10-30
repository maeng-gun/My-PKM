"""Unit and integration tests for vault_linter.py CLI."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LINTER_PATH = (
    PROJECT_ROOT
    / ".agents"
    / "skills"
    / "pkm_manager"
    / "scripts"
    / "vault_linter.py"
)


class TestVaultLinterUnit(unittest.TestCase):
    """Unit tests for vault_linter 5 constitutional checks and CLI options."""

    def setUp(self):
        self.assertTrue(LINTER_PATH.exists(), f"vault_linter.py must exist at {LINTER_PATH}")

    def test_cli_help(self):
        """Verify CLI help outputs options cleanly."""
        res = subprocess.run(
            [sys.executable, str(LINTER_PATH), "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        self.assertEqual(res.returncode, 0)
        out = res.stdout.lower()
        for opt in ["--vault", "--fix", "--format", "--exit-zero", "--include-inbox", "--verbose"]:
            self.assertIn(opt, out)

    def test_clean_vault_passes_with_zero_violations(self):
        """Verify clean compliant vault passes with exit code 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            concept_dir = vault / "100. Concepts"
            concept_dir.mkdir(parents=True)
            (concept_dir / "ValidConcept.md").write_text(
                "---\norigin: human\ntype: concept\ndomain: [theory]\nup: ['[[01_경제 및 금융 이론]]']\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Valid Concept",
                encoding="utf-8",
            )
            res = subprocess.run(
                [sys.executable, str(LINTER_PATH), "--vault", str(vault)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"Clean vault must pass: {res.stdout}")

    def test_check_c1_missing_required_keys(self):
        """Verify C1 flags missing core attributes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            concept_dir = vault / "100. Concepts"
            concept_dir.mkdir(parents=True)
            (concept_dir / "MissingOrigin.md").write_text(
                "---\ntype: concept\ndomain: [theory]\nup: ['[[01_경제 및 금융 이론]]']\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Missing Origin",
                encoding="utf-8",
            )
            res = subprocess.run(
                [sys.executable, str(LINTER_PATH), "--vault", str(vault)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 1)
            self.assertIn("origin", res.stdout.lower())

    def test_check_c1_domain_validation_max_2_rule(self):
        """Verify C1 rejects notes with more than 2 domains."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            concept_dir = vault / "100. Concepts"
            concept_dir.mkdir(parents=True)
            (concept_dir / "TooManyDomains.md").write_text(
                "---\norigin: human\ntype: concept\ndomain:\n  - macro\n  - equity\n  - portfolio\nup: ['[[02_매크로 분석]]']\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Three Domains",
                encoding="utf-8",
            )
            res = subprocess.run(
                [sys.executable, str(LINTER_PATH), "--vault", str(vault)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 1)
            self.assertTrue("domain" in res.stdout.lower() or "c1" in res.stdout.lower())

    def test_check_c1_domain_validation_unknown_code(self):
        """Verify C1 rejects notes with non-standard domain codes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            concept_dir = vault / "100. Concepts"
            concept_dir.mkdir(parents=True)
            (concept_dir / "UnknownDomain.md").write_text(
                "---\norigin: human\ntype: concept\ndomain:\n  - artificial_general_intelligence\nup: ['[[06_AI 활용 및 PKM 구축]]']\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Unknown",
                encoding="utf-8",
            )
            res = subprocess.run(
                [sys.executable, str(LINTER_PATH), "--vault", str(vault)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 1)
            self.assertIn("artificial_general_intelligence", res.stdout)

    def test_check_c2_ghost_link_detection_and_fix(self):
        """Verify C2 flags '[[]]' and --fix repairs it to clean null []."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            concept_dir = vault / "100. Concepts"
            concept_dir.mkdir(parents=True)
            note_file = concept_dir / "GhostLinkNote.md"
            note_file.write_text(
                '---\norigin: human\ntype: concept\ndomain: [theory]\nup:\n  - "[[01_경제 및 금융 이론]]"\nprev:\n  - "[[]]"\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Ghost Note',
                encoding="utf-8",
            )

            # Audit without fix: must fail
            res_fail = subprocess.run(
                [sys.executable, str(LINTER_PATH), "--vault", str(vault)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res_fail.returncode, 1)
            self.assertTrue("ghost" in res_fail.stdout.lower() or "[[]]" in res_fail.stdout)

            # Audit with --fix
            res_fix = subprocess.run(
                [sys.executable, str(LINTER_PATH), "--vault", str(vault), "--fix"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )

            # Verify note was repaired
            fixed_text = note_file.read_text(encoding="utf-8")
            self.assertNotIn('"[[]]"', fixed_text)
            self.assertIn("prev: []", fixed_text)

            # Re-audit: must pass
            res_pass = subprocess.run(
                [sys.executable, str(LINTER_PATH), "--vault", str(vault)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res_pass.returncode, 0)

    def test_check_c3_orphan_detection_and_level_1_hub_exemption(self):
        """Verify C3 flags orphan notes on concepts but exempts Level 1 hubs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            concept_dir = vault / "100. Concepts"
            wiki_dir = vault / "400. Wiki"
            concept_dir.mkdir(parents=True)
            wiki_dir.mkdir(parents=True)

            # Master hub with up: [] (exempt)
            (wiki_dir / "02_매크로 분석.md").write_text(
                "---\norigin: wiki\ntype: hub\nlevel: 1\ndomain: [macro]\nup: []\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# 02_매크로 분석",
                encoding="utf-8",
            )

            # Audit: must pass (hub exempt)
            res1 = subprocess.run(
                [sys.executable, str(LINTER_PATH), "--vault", str(vault)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res1.returncode, 0)

            # Add regular concept with up: [] (violation)
            (concept_dir / "OrphanConcept.md").write_text(
                "---\norigin: human\ntype: concept\ndomain: [theory]\nup: []\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Orphan Concept",
                encoding="utf-8",
            )

            # Audit: must fail on concept orphan
            res2 = subprocess.run(
                [sys.executable, str(LINTER_PATH), "--vault", str(vault)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res2.returncode, 1)
            self.assertIn("OrphanConcept.md", res2.stdout)

    def test_check_c3_orphan_wiki_case_and_l1_exemption(self):
        """Verify C3 exempts Lv1 hubs and case/event wikis with up: [] in 400. Wiki,
        while rejecting Lv2/Lv3/Lv4 and 100. Concepts with up: []."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            wiki_dir = vault / "400. Wiki"
            concept_dir = vault / "100. Concepts"
            wiki_dir.mkdir(parents=True)
            concept_dir.mkdir(parents=True)

            # Lv1 Hub in 400. Wiki with up: [] -> EXEMPT
            (wiki_dir / "C1_AI 반도체.md").write_text(
                "---\norigin: wiki\ntype: hub\nlevel: 1\ndomain: [equity]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# C1",
                encoding="utf-8",
            )
            # Case/event wiki in 400. Wiki with up: [] -> EXEMPT
            (wiki_dir / "2026 금통위 동결 논란.md").write_text(
                "---\norigin: wiki\ntype: analysis\ndomain: [macro]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# Case Wiki",
                encoding="utf-8",
            )
            # Audit passes for Lv1 hub and case wiki
            res = subprocess.run([sys.executable, str(LINTER_PATH), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res.returncode, 0, f"Lv1 and Case wiki with up: [] must pass C3: {res.stdout}")

            # Lv3 Sub-industry with up: [] -> VIOLATION
            (wiki_dir / "산업_반도체.md").write_text(
                "---\norigin: wiki\ntype: concept\nlevel: 3\ndomain: [equity]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# Sub-industry",
                encoding="utf-8",
            )
            res_lv3 = subprocess.run([sys.executable, str(LINTER_PATH), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res_lv3.returncode, 1)
            self.assertIn("산업_반도체.md", res_lv3.stdout)

            # Lv2 Stage with up: [] -> VIOLATION
            (wiki_dir / "산업_반도체.md").unlink()
            (wiki_dir / "C1-S1_AI 가속기 및 서버.md").write_text(
                "---\norigin: wiki\ntype: concept\nlevel: 2\ndomain: [equity]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# Stage",
                encoding="utf-8",
            )
            res_lv2 = subprocess.run([sys.executable, str(LINTER_PATH), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res_lv2.returncode, 1)
            self.assertIn("C1-S1_AI 가속기 및 서버.md", res_lv2.stdout)

            # Lv4 Company with up: [] -> VIOLATION
            (wiki_dir / "C1-S1_AI 가속기 및 서버.md").unlink()
            (wiki_dir / "기업_삼성전자.md").write_text(
                "---\norigin: wiki\ntype: entity\nlevel: 4\ndomain: [equity]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# Company",
                encoding="utf-8",
            )
            res_lv4 = subprocess.run([sys.executable, str(LINTER_PATH), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res_lv4.returncode, 1)
            self.assertIn("기업_삼성전자.md", res_lv4.stdout)

            # 100. Concepts with up: [] -> VIOLATION
            (wiki_dir / "기업_삼성전자.md").unlink()
            (concept_dir / "인간통찰.md").write_text(
                "---\norigin: human\ntype: concept\ndomain: [theory]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# Human Insight",
                encoding="utf-8",
            )
            res_concept = subprocess.run([sys.executable, str(LINTER_PATH), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res_concept.returncode, 1)
            self.assertIn("인간통찰.md", res_concept.stdout)

    def test_check_c4_folder_origin_mismatch(self):
        """Verify C4 detects origin attribute mismatch with folder prefix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            concept_dir = vault / "100. Concepts"
            concept_dir.mkdir(parents=True)
            (concept_dir / "AIOriginInHumanFolder.md").write_text(
                "---\norigin: ai\ntype: concept\ndomain: [theory]\nup: ['[[01_경제 및 금융 이론]]']\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Mismatch",
                encoding="utf-8",
            )
            res = subprocess.run(
                [sys.executable, str(LINTER_PATH), "--vault", str(vault)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 1)
            self.assertIn("AIOriginInHumanFolder.md", res.stdout)
            self.assertTrue("c4" in res.stdout.lower() or "origin" in res.stdout.lower())

    def test_check_c5_binary_infiltration(self):
        """Verify C5 flags heavy binaries anywhere inside the vault."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            sources_dir = vault / "300. Sources"
            sources_dir.mkdir(parents=True)
            (sources_dir / "IllegalDoc.hwpx").write_bytes(b"PK mock hwpx binary")

            res = subprocess.run(
                [sys.executable, str(LINTER_PATH), "--vault", str(vault)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 1)
            self.assertIn("IllegalDoc.hwpx", res.stdout)
            self.assertTrue("c5" in res.stdout.lower() or "binary" in res.stdout.lower())

    def test_format_json_output(self):
        """Verify --format json outputs valid JSON with summary and violations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            concept_dir = vault / "100. Concepts"
            concept_dir.mkdir(parents=True)
            (concept_dir / "BadNote.md").write_text("No frontmatter content", encoding="utf-8")

            res = subprocess.run(
                [sys.executable, str(LINTER_PATH), "--vault", str(vault), "--format", "json"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 1)
            parsed = json.loads(res.stdout)
            self.assertIn("summary", parsed)
            self.assertIn("violations", parsed)
            self.assertEqual(parsed["summary"]["failed"], 1)

    def test_exit_zero_flag(self):
        """Verify --exit-zero forces exit code 0 even when violations are present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            concept_dir = vault / "100. Concepts"
            concept_dir.mkdir(parents=True)
            (concept_dir / "BadNote.md").write_text("No frontmatter content", encoding="utf-8")

            res = subprocess.run(
                [sys.executable, str(LINTER_PATH), "--vault", str(vault), "--exit-zero"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0, "--exit-zero must return 0")


if __name__ == "__main__":
    unittest.main()
