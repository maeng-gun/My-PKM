"""Adversarial Challenge Test Suite for Milestone 4 (F7 ingest_sources.py & F8 vault_linter.py).

Authored by Challenger 1 (teamwork_preview_challenger).
Validates dual-engine document ingestion, Clean Null enforcement across bracket variations,
inbox zero movement, GFM table preservation, Level 1 hub exemptions (all 7 hubs),
vault linter --fix repair semantics, and heavy binary infiltration detection.
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

PROJECT_ROOT = Path(r"c:\Users\maeng-gun\Desktop\python\My_PKM")
INGEST_SCRIPT = (
    PROJECT_ROOT
    / ".agents"
    / "skills"
    / "pkm_manager"
    / "scripts"
    / "ingest_sources.py"
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


class TestM4AdversarialIngestSources(unittest.TestCase):
    """Adversarial stress-testing of ingest_sources.py CLI and ETL pipeline."""

    def setUp(self):
        self.assertTrue(INGEST_SCRIPT.exists(), f"Missing ingest script: {INGEST_SCRIPT}")
        self.assertTrue(PYTHON_EXE.exists(), f"Missing python exe: {PYTHON_EXE}")

    def test_adv_m4_01_real_conversion_with_korean_content_and_gfm_table(self):
        """Stress-test: Real conversion of Korean document containing GFM table and multiple domains."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"
            inbox.mkdir()

            sample_doc = inbox / "2026년_3분기_거시경제_지표.txt"
            sample_content = (
                "# 2026년 3분기 한국 거시경제 지표 점검\n\n"
                "## 1. 개요\n"
                "본 보고서는 2026년 3분기 주요 거시경제 지표를 요약 분석합니다.\n\n"
                "## 2. 주요 거시 지표 요약표\n\n"
                "| 지표명 | 2026 1Q | 2026 2Q | 2026 3Q(E) | 전년동기대비 | 평가 |\n"
                "|:---|---:|---:|---:|---:|:---|\n"
                "| GDP 성장률 (%) | 2.1 | 2.3 | 2.4 | +0.3%p | 양호 |\n"
                "| CPI 물가상승률 (%) | 2.8 | 2.5 | 2.2 | -0.6%p | 안정세 |\n"
                "| 기준금리 (%) | 3.50 | 3.25 | 3.00 | -50bp | 완화 전환 |\n"
                "| 국고채 10년물 (%) | 3.20 | 3.05 | 2.95 | -25bp | 강세 지속 |\n\n"
                "## 3. 정책적 시사점\n"
                "- 한미 금리차 축소에 따른 환율 안정화\n"
                "- 유동성 공급과 TAA 모델 리밸런싱 필요\n"
            )
            sample_doc.write_text(sample_content, encoding="utf-8")

            res = subprocess.run(
                [
                    str(PYTHON_EXE),
                    str(INGEST_SCRIPT),
                    "--file", str(sample_doc),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--subfolder", "310. Reports_Papers",
                    "--domain", "macro,portfolio",
                    "--up", "[[02_매크로 분석]]",
                    "--source-type", "report",
                    "--table-format", "gfm",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )

            self.assertEqual(res.returncode, 0, f"Ingestion failed: {res.stderr}\nOutput: {res.stdout}")

            # Verify target note created
            target_note = vault / "300. Sources" / "310. Reports_Papers" / "2026년_3분기_거시경제_지표.md"
            self.assertTrue(target_note.exists(), f"Note was not created at {target_note}")

            # Verify note content & frontmatter
            note_text = target_note.read_text(encoding="utf-8")
            parts = note_text.split("---")
            self.assertGreaterEqual(len(parts), 3, "Frontmatter must be enclosed by ---")

            fm = yaml.safe_load(parts[1])
            self.assertEqual(fm["origin"], "source")
            self.assertEqual(fm["type"], "source")
            self.assertEqual(fm["domain"], ["macro", "portfolio"])
            self.assertEqual(fm["up"], ["[[02_매크로 분석]]"])
            self.assertEqual(fm["status"], "active")
            self.assertEqual(fm["source_type"], "report")

            # Verify GFM table preserved verbatim
            self.assertIn("| GDP 성장률 (%) | 2.1 | 2.3 | 2.4 | +0.3%p | 양호 |", note_text)
            self.assertIn("| CPI 물가상승률 (%) | 2.8 | 2.5 | 2.2 | -0.6%p | 안정세 |", note_text)

            # Verify Inbox Zero: raw file deleted from inbox and moved to archive
            self.assertFalse(sample_doc.exists(), "Source file must be removed from Inbox_Raw (Inbox Zero)")
            target_archived = archive / "310. Reports_Papers" / "2026년_3분기_거시경제_지표.txt"
            self.assertTrue(target_archived.exists(), f"Source file must be moved to archive at {target_archived}")

    def test_adv_m4_02_dry_run_vs_normal_mode(self):
        """Stress-test: Verify --dry-run strictly preserves inbox files, while normal mode moves files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"
            inbox.mkdir()

            test_file = inbox / "sample_dry_run.txt"
            test_file.write_text("Dry run test content.", encoding="utf-8")

            # 1. Run --dry-run
            res_dry = subprocess.run(
                [
                    str(PYTHON_EXE),
                    str(INGEST_SCRIPT),
                    "--file", str(test_file),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--subfolder", "330. Clippings_News",
                    "--domain", "macro",
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res_dry.returncode, 0)
            self.assertIn("[DRY-RUN]", res_dry.stdout)
            self.assertTrue(test_file.exists(), "File must still exist in inbox after --dry-run")
            self.assertFalse(vault.exists(), "Vault dir must not be created during --dry-run")
            self.assertFalse(archive.exists(), "Archive dir must not be created during --dry-run")

            # 2. Run normal mode
            res_normal = subprocess.run(
                [
                    str(PYTHON_EXE),
                    str(INGEST_SCRIPT),
                    "--file", str(test_file),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--subfolder", "330. Clippings_News",
                    "--domain", "macro",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res_normal.returncode, 0)
            self.assertFalse(test_file.exists(), "File must be moved from inbox in normal mode")
            expected_note = vault / "300. Sources" / "330. Clippings_News" / "sample_dry_run.md"
            expected_archive = archive / "330. Clippings_News" / "sample_dry_run.txt"
            self.assertTrue(expected_note.exists(), "Note must exist after normal mode")
            self.assertTrue(expected_archive.exists(), "Archive file must exist after normal mode")

    def test_adv_m4_03_clean_null_comprehensive_variations(self):
        """Stress-test: Verify all empty, whitespace, and ghost link strings to --up produce clean null up: []."""
        test_cases = [
            (None, "omitted"),
            ("", "empty string"),
            ("   ", "whitespace only"),
            ("[[]]", "literal double brackets"),
            ('"[[]]"', "quoted literal double brackets"),
            (" '[[]]' ", "single quoted double brackets with spaces"),
            ("[]", "literal empty list"),
            ('""', "double double-quotes"),
            ("''", "double single-quotes"),
        ]

        for up_input, case_name in test_cases:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)
                inbox = tmp / "Inbox"
                vault = tmp / "Vault"
                archive = tmp / "Archive"
                inbox.mkdir()

                doc = inbox / "test_doc.txt"
                doc.write_text(f"Content for case: {case_name}", encoding="utf-8")

                cmd = [
                    str(PYTHON_EXE),
                    str(INGEST_SCRIPT),
                    "--file", str(doc),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--domain", "macro",
                ]
                if up_input is not None:
                    cmd.extend(["--up", up_input])

                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                self.assertEqual(res.returncode, 0, f"Failed on case '{case_name}': {res.stderr}")

                notes = list(vault.rglob("*.md"))
                self.assertEqual(len(notes), 1)
                content = notes[0].read_text(encoding="utf-8")

                self.assertNotIn('"[[]]"', content, f"Ghost link detected in case '{case_name}'")
                self.assertNotIn("'[[]]'", content, f"Ghost link detected in case '{case_name}'")
                self.assertIn("up: []", content, f"Expected clean null 'up: []' in case '{case_name}'")

    def test_adv_m4_04_table_format_validation(self):
        """Stress-test: Verify --table-format choices (gfm, html) and rejection of invalid format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox"
            inbox.mkdir()
            doc = inbox / "doc.txt"
            doc.write_text("Table format check", encoding="utf-8")

            # Valid gfm
            res_gfm = subprocess.run(
                [
                    str(PYTHON_EXE), str(INGEST_SCRIPT),
                    "--file", str(doc),
                    "--inbox", str(inbox),
                    "--vault", str(tmp / "Vault"),
                    "--archive", str(tmp / "Archive"),
                    "--table-format", "gfm",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res_gfm.returncode, 0)

            # Invalid format
            res_invalid = subprocess.run(
                [
                    str(PYTHON_EXE), str(INGEST_SCRIPT),
                    "--file", str(doc),
                    "--inbox", str(inbox),
                    "--vault", str(tmp / "Vault"),
                    "--archive", str(tmp / "Archive"),
                    "--table-format", "invalid_choice_xyz",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertNotEqual(res_invalid.returncode, 0)
            self.assertIn("invalid choice", res_invalid.stderr.lower())

    def test_adv_m4_05_heading_auto_synthesis_when_h1_missing(self):
        """Stress-test: Verify H1 heading is synthesized from file stem when source document lacks H1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox"
            vault = tmp / "Vault"
            archive = tmp / "Archive"
            inbox.mkdir()

            doc = inbox / "global_interest_rates.txt"
            # Body without any # heading
            doc.write_text("Paragraph one without H1.\nParagraph two.", encoding="utf-8")

            res = subprocess.run(
                [
                    str(PYTHON_EXE), str(INGEST_SCRIPT),
                    "--file", str(doc),
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
            self.assertEqual(res.returncode, 0)

            notes = list(vault.rglob("*.md"))
            self.assertEqual(len(notes), 1)
            content = notes[0].read_text(encoding="utf-8")
            self.assertIn("# global interest rates", content, "Heading must be synthesized from file stem")


class TestM4AdversarialVaultLinter(unittest.TestCase):
    """Adversarial stress-testing of vault_linter.py CLI and constitutional rules."""

    def setUp(self):
        self.assertTrue(LINTER_SCRIPT.exists(), f"Missing linter script: {LINTER_SCRIPT}")
        self.assertTrue(PYTHON_EXE.exists(), f"Missing python exe: {PYTHON_EXE}")

    def test_adv_m4_06_linter_fix_option_on_all_ghost_link_formats(self):
        """Stress-test: Verify --fix repairs multiline, single-line, and inline bracket ghost links."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "TestVault"
            concept_dir = vault / "100. Concepts"
            concept_dir.mkdir(parents=True)

            note_path = concept_dir / "ComplexGhostNote.md"
            original_content = (
                "---\n"
                "origin: human\n"
                "type: concept\n"
                "domain:\n"
                "  - theory\n"
                "up:\n"
                "  - \"[[]]\"\n"
                "prev: \"[[]]\"\n"
                "next: '[[]]'\n"
                "status: active\n"
                "created: 2026-10-25\n"
                "updated: 2026-10-25\n"
                "---\n"
                "# Complex Ghost Note\n\n"
                "Body content here.\n"
            )
            note_path.write_text(original_content, encoding="utf-8")

            # Audit without fix -> must report C2
            res_fail = subprocess.run(
                [str(PYTHON_EXE), str(LINTER_SCRIPT), "--vault", str(vault), "--format", "json"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res_fail.returncode, 1)
            report_fail = json.loads(res_fail.stdout)
            self.assertGreater(report_fail["summary"]["violations_by_check"]["C2"], 0)

            # Audit with --fix
            res_fix = subprocess.run(
                [str(PYTHON_EXE), str(LINTER_SCRIPT), "--vault", str(vault), "--fix"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )

            # Inspect fixed content
            fixed_content = note_path.read_text(encoding="utf-8")
            self.assertNotIn('"[[]]"', fixed_content)
            self.assertNotIn("'[[]]'", fixed_content)
            self.assertIn("up: []", fixed_content)
            self.assertIn("prev: []", fixed_content)
            self.assertIn("next: []", fixed_content)

            # Verify it parses as valid YAML
            parts = fixed_content.split("---")
            fm = yaml.safe_load(parts[1])
            self.assertEqual(fm["up"], [])
            self.assertEqual(fm["prev"], [])
            self.assertEqual(fm["next"], [])
            self.assertEqual(fm["status"], "active")

            # Re-check C2 violations: must be 0
            res_check = subprocess.run(
                [str(PYTHON_EXE), str(LINTER_SCRIPT), "--vault", str(vault), "--format", "json"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            report_check = json.loads(res_check.stdout)
            self.assertEqual(report_check["summary"]["violations_by_check"]["C2"], 0)

    def test_adv_m4_07_all_seven_level_1_hubs_exempted_from_orphan_check(self):
        """Stress-test: Verify that every one of the 7 Level 1 hubs with up: [] is exempted from C3."""
        level_1_hubs = [
            ("01_경제 및 금융 이론.md", "theory"),
            ("02_매크로 분석.md", "macro"),
            ("03_산업 및 기업분석.md", "equity"),
            ("04_가족 투자 포트폴리오.md", "portfolio"),
            ("05_회사업무 (자산운용).md", "work"),
            ("06_AI 활용 및 PKM 구축.md", "ai-pkm"),
            ("07_자녀교육.md", "education"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "My-Wiki"
            wiki_dir = vault / "400. Wiki"
            wiki_dir.mkdir(parents=True)

            for hub_name, domain_code in level_1_hubs:
                content = (
                    f"---\n"
                    f"origin: wiki\n"
                    f"type: hub\n"
                    f"level: 1\n"
                    f"domain: [{domain_code}]\n"
                    f"up: []\n"
                    f"status: active\n"
                    f"created: 2026-10-25\n"
                    f"updated: 2026-10-25\n"
                    f"---\n"
                    f"# {hub_name}\n"
                )
                (wiki_dir / hub_name).write_text(content, encoding="utf-8")

            res = subprocess.run(
                [str(PYTHON_EXE), str(LINTER_SCRIPT), "--vault", str(vault), "--format", "json"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"All 7 Level 1 hubs must pass with exit 0: {res.stdout}")
            report = json.loads(res.stdout)
            self.assertEqual(report["summary"]["total_scanned"], 7)
            self.assertEqual(report["summary"]["passed"], 7)
            self.assertEqual(report["summary"]["failed"], 0)
            self.assertEqual(report["summary"]["violations_by_check"]["C3"], 0)

            # Non-exempt note with up: [] in 400. Wiki
            (wiki_dir / "08_알 수 없는 허브.md").write_text(
                "---\norigin: wiki\ntype: concept\ndomain: [theory]\nup: []\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Non-exempt",
                encoding="utf-8",
            )
            res_bad = subprocess.run(
                [str(PYTHON_EXE), str(LINTER_SCRIPT), "--vault", str(vault), "--format", "json"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res_bad.returncode, 1)
            report_bad = json.loads(res_bad.stdout)
            self.assertEqual(report_bad["summary"]["violations_by_check"]["C3"], 1)
            self.assertEqual(report_bad["violations"][0]["filename"], "08_알 수 없는 허브.md")

    def test_adv_m4_08_binary_infiltration_comprehensive(self):
        """Stress-test: Verify C5 flags heavy binaries and allows images only in 900. config/910. Attached."""
        heavy_extensions = [".pdf", ".hwpx", ".hwp", ".xlsx", ".docx", ".pptx", ".zip"]

        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "My-Wiki"
            concept_dir = vault / "100. Concepts"
            sources_dir = vault / "300. Sources"
            config_attached_dir = vault / "900. config" / "910. Attached"

            concept_dir.mkdir(parents=True)
            sources_dir.mkdir(parents=True)
            config_attached_dir.mkdir(parents=True)

            (concept_dir / "ValidConcept.md").write_text(
                "---\norigin: human\ntype: concept\ndomain: [theory]\nup: ['[[01_경제 및 금융 이론]]']\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Valid",
                encoding="utf-8",
            )

            for ext in heavy_extensions:
                (sources_dir / f"illegal_doc{ext}").write_bytes(b"dummy binary data bytes")

            (config_attached_dir / "diagram.png").write_bytes(b"mock png")
            (config_attached_dir / "chart.svg").write_bytes(b"<svg></svg>")

            res = subprocess.run(
                [str(PYTHON_EXE), str(LINTER_SCRIPT), "--vault", str(vault), "--format", "json"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 1, "Must fail due to heavy binaries")
            report = json.loads(res.stdout)

            self.assertEqual(report["summary"]["violations_by_check"]["C5"], len(heavy_extensions))
            flagged_names = {v["filename"] for v in report["violations"] if v["check"] == "C5"}
            for ext in heavy_extensions:
                self.assertIn(f"illegal_doc{ext}", flagged_names)

            self.assertNotIn("diagram.png", flagged_names)
            self.assertNotIn("chart.svg", flagged_names)

    def test_adv_m4_09_folder_origin_mece_matrix(self):
        """Stress-test: Verify strict 1:1 MECE mapping across all 5 vault folder prefixes."""
        folder_to_origin = {
            "100. Concepts": "human",
            "200. AI_logs": "ai",
            "300. Sources": "source",
            "400. Wiki": "wiki",
            "500. etc": "human",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "My-Wiki"

            for folder, correct_origin in folder_to_origin.items():
                f_dir = vault / folder
                f_dir.mkdir(parents=True)
                note_file = f_dir / f"Correct_{folder.split('.')[0]}.md"
                note_file.write_text(
                    f"---\norigin: {correct_origin}\ntype: concept\ndomain: [theory]\nup: ['[[01_경제 및 금융 이론]]']\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# OK",
                    encoding="utf-8",
                )

            res = subprocess.run(
                [str(PYTHON_EXE), str(LINTER_SCRIPT), "--vault", str(vault), "--format", "json"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"All correct origins must pass: {res.stdout}")

            # Inverted origin: ai in 100. Concepts
            (vault / "100. Concepts" / "WrongOrigin.md").write_text(
                "---\norigin: ai\ntype: concept\ndomain: [theory]\nup: ['[[01_경제 및 금융 이론]]']\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Wrong",
                encoding="utf-8",
            )
            res_bad = subprocess.run(
                [str(PYTHON_EXE), str(LINTER_SCRIPT), "--vault", str(vault), "--format", "json"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res_bad.returncode, 1)
            report_bad = json.loads(res_bad.stdout)
            self.assertEqual(report_bad["summary"]["violations_by_check"]["C4"], 1)


if __name__ == "__main__":
    unittest.main()
