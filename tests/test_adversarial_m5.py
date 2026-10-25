"""Milestone 5 Adversarial Stress Testing Suite for My-PKM.

Covers:
1. Ghost Link Elimination & Auto-Fixing Edge Cases
2. Level 1 Master Hub Orphan Exemption & False Exemption Probes
3. Folder-Origin MECE Alignment Across All Standard Folders
4. Ingest Sources Ghost Link Immunization
"""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(r"c:\Users\maeng-gun\Desktop\python\My_PKM")
LINTER_SCRIPT = PROJECT_ROOT / ".agents" / "skills" / "pkm_manager" / "scripts" / "vault_linter.py"
INGEST_SCRIPT = PROJECT_ROOT / ".agents" / "skills" / "pkm_manager" / "scripts" / "ingest_sources.py"

LEVEL_1_HUBS = [
    "01_경제 및 금융 이론.md",
    "02_매크로 분석.md",
    "03_산업 및 기업분석.md",
    "04_가족 투자 포트폴리오.md",
    "05_회사업무 (자산운용).md",
    "06_AI 활용 및 PKM 구축.md",
    "07_자녀교육.md",
]


class TestAdversarialGhostLinks(unittest.TestCase):
    """Stress tests for ghost link detection and --fix behavior."""

    def test_adv_ghost_in_frontmatter_single_line_unquoted(self):
        """Stress test: Unquoted up: [[]] in YAML frontmatter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "100. Concepts").mkdir(parents=True)
            note = vault / "100. Concepts" / "UnquotedGhost.md"
            note.write_text(
                "---\norigin: human\ntype: concept\ndomain: [theory]\nup: [[]]\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Unquoted Ghost",
                encoding="utf-8",
            )
            # Detect
            res1 = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(res1.returncode, 1, "Must detect unquoted up: [[]] as ghost link")
            
            # Auto-fix
            res_fix = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault), "--fix"], capture_output=True, text=True, encoding="utf-8", errors="replace")
            content_after = note.read_text(encoding="utf-8")
            
            # Re-audit
            res2 = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace")
            print(f"\n[ADV 1.1 Unquoted up: [[]]] After --fix: exit_code={res2.returncode}, content:\n{content_after}")
            self.assertIn("up: []", content_after, "Unquoted up: [[]] must be repaired to up: []")
            self.assertNotIn("[[]]", content_after, "All ghost links in frontmatter must be removed")
            self.assertNotIn("[C2]", res2.stdout, "Ghost link C2 violation must be completely resolved after --fix")

    def test_adv_ghost_in_markdown_body_preservation(self):
        """Stress test: Does --fix corrupt markdown body text mentioning '[[]]'?"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "100. Concepts").mkdir(parents=True)
            note = vault / "100. Concepts" / "BodyWithGhostExample.md"
            original_body = "# Note Title\n\nHere is an explanation of ghost links:\nDo not use \"[[]]\" in frontmatter.\nAlso avoid `[[]]` in links."
            note.write_text(
                f"---\norigin: human\ntype: concept\ndomain: [theory]\nup: ['[[01_경제 및 금융 이론]]']\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n{original_body}",
                encoding="utf-8",
            )

            # Audit
            res1 = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace")
            print(f"\n[ADV 1.2 Body Text Ghost Link Audit]: exit_code={res1.returncode}, stdout:\n{res1.stdout}")

            # Run --fix
            res_fix = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault), "--fix"], capture_output=True, text=True, encoding="utf-8", errors="replace")
            content_after = note.read_text(encoding="utf-8")
            print(f"[ADV 1.2 Body Text After --fix]:\n{content_after}")

            # Check if body was mutated
            body_after = content_after.split("---", 2)[-1].strip()
            self.assertEqual(body_after, original_body.strip(), "Markdown body text must be completely preserved by --fix")
            self.assertNotIn('Do not use "[]" in frontmatter', body_after)
            self.assertIn('Do not use "[[]]" in frontmatter', body_after)

    def test_adv_ghost_multiline_mixed_list(self):
        """Stress test: Frontmatter list with valid link AND ghost link."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "100. Concepts").mkdir(parents=True)
            note = vault / "100. Concepts" / "MixedList.md"
            note.write_text(
                '---\norigin: human\ntype: concept\ndomain: [theory]\nup: ["[[01_경제 및 금융 이론]]"]\nprev:\n  - "[[02_매크로 분석]]"\n  - "[[]]"\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Mixed List',
                encoding="utf-8",
            )
            # Run --fix
            res_fix = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault), "--fix"], capture_output=True, text=True, encoding="utf-8", errors="replace")
            content_after = note.read_text(encoding="utf-8")
            print(f"\n[ADV 1.3 Mixed List After --fix]:\n{content_after}")

            # Re-audit
            res2 = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace")
            print(f"[ADV 1.3 Mixed List Re-Audit]: exit_code={res2.returncode}")


class TestAdversarialOrphanExemptions(unittest.TestCase):
    """Stress tests for Level 1 Master Hub orphan exemptions."""

    def test_adv_all_seven_master_hubs_pass(self):
        """Verify all 7 Level 1 Master Hubs pass orphan check with up: []."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            wiki_dir = vault / "400. Wiki"
            wiki_dir.mkdir(parents=True)

            for hub in LEVEL_1_HUBS:
                (wiki_dir / hub).write_text(
                    f"---\norigin: wiki\ntype: hub\nlevel: 1\ndomain: [theory]\nup: []\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# {hub}",
                    encoding="utf-8",
                )

            res = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(res.returncode, 0, f"All 7 Master Hubs must pass: {res.stdout}")

    def test_adv_false_positive_prefix_match_in_concepts(self):
        """Stress test: Does 01_foo.md in 100. Concepts get mistakenly exempted from orphan check?"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "100. Concepts").mkdir(parents=True)
            fake_hub = vault / "100. Concepts" / "01_초보경제학.md"
            fake_hub.write_text(
                "---\norigin: human\ntype: concept\ndomain: [theory]\nup: []\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Fake Hub",
                encoding="utf-8",
            )
            res = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace")
            print(f"\n[ADV 2.2 Concept starting with '01_' up: []]: exit_code={res.returncode}, stdout:\n{res.stdout}")
            self.assertEqual(res.returncode, 1, "Concept file starting with '01_' in 100. Concepts must NOT be exempted from orphan check")
            self.assertIn("C3", res.stdout, "Must flag C3 Orphan note violation")


class TestAdversarialFolderOriginMECE(unittest.TestCase):
    """Stress tests for Folder-Origin MECE mapping across all folders."""

    def test_adv_all_standard_folders_valid(self):
        """Verify 100, 200, 300, 400, 500 folder-origin mapping."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            cases = [
                ("100. Concepts/Concept.md", "human", "concept"),
                ("200. AI_logs/Log.md", "ai", "log"),
                ("300. Sources/Source.md", "source", "source"),
                ("400. Wiki/01_경제 및 금융 이론.md", "wiki", "hub"),
                ("500. etc/Private.md", "human", "concept"),
            ]
            for rel_path, origin, note_type in cases:
                p = vault / rel_path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(
                    f"---\norigin: {origin}\ntype: {note_type}\ndomain: [theory]\nup: ['[[01_경제 및 금융 이론]]']\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Note",
                    encoding="utf-8",
                )

            res = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(res.returncode, 0, f"All valid folder-origin notes must pass: {res.stdout}")

    def test_adv_all_mismatches_flagged(self):
        """Verify mismatched origins in 100, 200, 300, 400, 500 are all flagged."""
        mismatches = [
            ("100. Concepts/Concept.md", "ai"),
            ("200. AI_logs/Log.md", "human"),
            ("300. Sources/Source.md", "wiki"),
            ("400. Wiki/Wiki.md", "source"),
            ("500. etc/Private.md", "ai"),
        ]
        for rel_path, wrong_origin in mismatches:
            with tempfile.TemporaryDirectory() as tmpdir:
                vault = Path(tmpdir) / "Vault"
                p = vault / rel_path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(
                    f"---\norigin: {wrong_origin}\ntype: concept\ndomain: [theory]\nup: ['[[01_경제 및 금융 이론]]']\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Mismatch",
                    encoding="utf-8",
                )
                res = subprocess.run([sys.executable, str(LINTER_SCRIPT), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace")
                self.assertEqual(res.returncode, 1, f"Mismatch in {rel_path} with origin {wrong_origin} must fail")
                self.assertIn("C4", res.stdout)


class TestAdversarialIngestSourcesGhostElimination(unittest.TestCase):
    """Stress tests on ingest_sources.py ghost link immunization."""

    def test_adv_ingest_sources_empty_up_variants(self):
        """Verify ingest_sources generate_frontmatter immunizes against ghost link representations."""
        sys.path.insert(0, str(INGEST_SCRIPT.parent))
        from ingest_sources import generate_frontmatter

        variants = [None, "", "[]", "[[]]", '"[[]]"', "'[[]]'", '""[[]]""']
        for v in variants:
            fm = generate_frontmatter(
                origin="source",
                note_type="source",
                domain=["macro"],
                up=v,
                status="active",
                created="2026-10-25",
                updated="2026-10-25",
                source_type="report",
            )
            self.assertIn("up: []", fm, f"Variant {repr(v)} must produce 'up: []'")
            self.assertNotIn('"[[]]"', fm)
            self.assertNotIn("[[]]", fm)


if __name__ == "__main__":
    unittest.main(verbosity=2)
