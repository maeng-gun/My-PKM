"""Tier 1: Feature Coverage E2E Tests for My-PKM.

Covers F1 through F8 in isolation with >= 5 test cases per feature.
Specification Sources:
- PROJECT.md (Features 1-13 & Interface Contracts)
- ORIGINAL_REQUEST.md (Requirements R1-R4 & Acceptance Criteria)
- spec_miner_survey_2/handoff.md (PKM Constitution v2.1)
- explorer_survey_3/handoff.md (Kordoc Engine & Tooling Specs)
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GDRIVE_ROOT = Path(r"G:\내 드라이브")


class TestTier1F1ProjectMetadata(unittest.TestCase):
    """F1: Project Metadata Files (pyproject.toml, .gdrive_config.json, README.md, finalize_rename.ps1)."""

    def test_f1_01_pyproject_exists_and_name(self):
        """Verify pyproject.toml exists and project name is 'my-pkm'."""
        pyproject_path = PROJECT_ROOT / "pyproject.toml"
        self.assertTrue(pyproject_path.exists(), "pyproject.toml must exist")
        content = pyproject_path.read_text(encoding="utf-8")
        self.assertRegex(
            content,
            r'name\s*=\s*["\']my-pkm["\']',
            "pyproject.toml must define name = 'my-pkm'",
        )

    def test_f1_02_pyproject_python_requires(self):
        """Verify pyproject.toml requires-python is >= 3.11."""
        pyproject_path = PROJECT_ROOT / "pyproject.toml"
        content = pyproject_path.read_text(encoding="utf-8")
        self.assertRegex(
            content,
            r'requires-python\s*=\s*["\']>=3\.1[1-9]["\']',
            "pyproject.toml must specify requires-python = '>=3.11' (for kordoc 0.2.0+)",
        )

    def test_f1_03_pyproject_kordoc_dependency(self):
        """Verify pyproject.toml includes kordoc>=0.2.0 in dependencies."""
        pyproject_path = PROJECT_ROOT / "pyproject.toml"
        content = pyproject_path.read_text(encoding="utf-8")
        self.assertRegex(
            content,
            r'["\']kordoc>=0\.2\.0["\']',
            "pyproject.toml dependencies must include 'kordoc>=0.2.0'",
        )

    def test_f1_04_gdrive_config_json_valid_and_project_name(self):
        """Verify .gdrive_config.json has project_name 'My-PKM' and required fields."""
        gdrive_config_path = PROJECT_ROOT / ".gdrive_config.json"
        self.assertTrue(gdrive_config_path.exists(), ".gdrive_config.json must exist")
        data = json.loads(gdrive_config_path.read_text(encoding="utf-8"))
        self.assertEqual(data.get("project_name"), "My-PKM")
        self.assertIn("workspace_root", data)
        self.assertIn("folders", data)

    def test_f1_05_readme_documents_pkm_identity(self):
        """Verify README.md documents My-PKM architecture and core integrations."""
        readme_path = PROJECT_ROOT / "README.md"
        self.assertTrue(readme_path.exists(), "README.md must exist")
        content = readme_path.read_text(encoding="utf-8")
        self.assertIn("My-PKM", content, "README.md must reference My-PKM")
        # Check reference to PKM or Obsidian or kordoc
        has_pkm_reference = any(
            term in content.lower()
            for term in ["pkm", "my-wiki", "kordoc", "obsidian"]
        )
        self.assertTrue(has_pkm_reference, "README.md must document PKM / Obsidian / kordoc capabilities")

    def test_f1_06_finalize_rename_script_exists_and_content(self):
        """Verify scripts/finalize_rename.ps1 exists and handles git remote origin and folder rename."""
        script_path = PROJECT_ROOT / "scripts" / "finalize_rename.ps1"
        self.assertTrue(script_path.exists(), "scripts/finalize_rename.ps1 must exist")
        content = script_path.read_text(encoding="utf-8")
        self.assertIn("https://github.com/maeng-gun/My-PKM.git", content, "Script must update git remote to My-PKM")
        self.assertIn("My-PKM", content, "Script must reference My-PKM target directory")


class TestTier1F2WorkspaceJunctions(unittest.TestCase):
    """F2: 5 Workspace directory junctions (input_staging, scratch, archive, secrets, AGY_Artifacts)."""

    def _get_junction_target(self, folder_name: str) -> str:
        folder_path = PROJECT_ROOT / folder_name
        self.assertTrue(folder_path.exists(), f"Junction {folder_name} must exist")
        try:
            target = os.readlink(folder_path)
            # Remove Windows \\?\ prefix if present
            if target.startswith("\\\\?\\"):
                target = target[4:]
            return target
        except OSError:
            # Fallback to powershell Get-Item
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"(Get-Item '{folder_path}').Target"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            return res.stdout.strip()

    def test_f2_01_input_staging_junction(self):
        """Verify input_staging junction points to My-PKM workspace."""
        target = self._get_junction_target("input_staging")
        expected_part = r"Antigravity_Workspaces\My-PKM\input_staging"
        self.assertIn(expected_part.lower(), target.lower())

    def test_f2_02_scratch_junction(self):
        """Verify scratch junction points to My-PKM workspace."""
        target = self._get_junction_target("scratch")
        expected_part = r"Antigravity_Workspaces\My-PKM\scratch"
        self.assertIn(expected_part.lower(), target.lower())

    def test_f2_03_archive_junction(self):
        """Verify archive junction points to My-PKM workspace."""
        target = self._get_junction_target("archive")
        expected_part = r"Antigravity_Workspaces\My-PKM\archive"
        self.assertIn(expected_part.lower(), target.lower())

    def test_f2_04_secrets_junction(self):
        """Verify secrets junction points to My-PKM workspace."""
        target = self._get_junction_target("secrets")
        expected_part = r"Antigravity_Workspaces\My-PKM\secrets"
        self.assertIn(expected_part.lower(), target.lower())

    def test_f2_05_agy_artifacts_junction(self):
        """Verify AGY_Artifacts junction points to My-PKM workspace."""
        target = self._get_junction_target("AGY_Artifacts")
        expected_part = r"Antigravity_Workspaces\My-PKM\AGY_Artifacts"
        self.assertIn(expected_part.lower(), target.lower())

    def test_f2_06_workspace_junctions_target_directory_reachable(self):
        """Verify all 5 workspace junctions resolve to real reachable directories."""
        for folder_name in ["input_staging", "scratch", "archive", "secrets", "AGY_Artifacts"]:
            path = PROJECT_ROOT / folder_name
            self.assertTrue(path.is_dir(), f"{folder_name} must be a reachable directory")


class TestTier1F3PKMRootJunctions(unittest.TestCase):
    """F3: 3 PKM root junctions (My-Wiki, Inbox_Raw, Archive_Sources) and .gitignore exclusion."""

    def test_f3_01_my_wiki_junction(self):
        """Verify ./My-Wiki junction exists and points to GDrive My-Wiki."""
        folder_path = PROJECT_ROOT / "My-Wiki"
        self.assertTrue(folder_path.exists(), "./My-Wiki junction must exist")
        self.assertTrue(folder_path.is_dir(), "./My-Wiki must be an accessible directory")

    def test_f3_02_inbox_raw_junction(self):
        """Verify ./Inbox_Raw junction exists and points to GDrive Inbox_Raw."""
        folder_path = PROJECT_ROOT / "Inbox_Raw"
        self.assertTrue(folder_path.exists(), "./Inbox_Raw junction must exist")
        self.assertTrue(folder_path.is_dir(), "./Inbox_Raw must be an accessible directory")

    def test_f3_03_archive_sources_junction(self):
        """Verify ./Archive_Sources junction exists and points to GDrive Archive_Sources."""
        folder_path = PROJECT_ROOT / "Archive_Sources"
        self.assertTrue(folder_path.exists(), "./Archive_Sources junction must exist")
        self.assertTrue(folder_path.is_dir(), "./Archive_Sources must be an accessible directory")

    def test_f3_04_pkm_ssot_documents_accessible_via_local_junction(self):
        """Verify SSOT documents PKM 아키텍처.md and 옵시디언 링크 연결 규칙 설계.md are readable via local junction."""
        wiki_root = PROJECT_ROOT / "My-Wiki" / "400. Wiki"
        arch_doc = wiki_root / "PKM 아키텍처.md"
        rules_doc = wiki_root / "옵시디언 메모간 링크 연결 규칙 설계.md"
        self.assertTrue(arch_doc.exists(), f"SSOT doc missing at {arch_doc}")
        self.assertTrue(rules_doc.exists(), f"SSOT doc missing at {rules_doc}")
        self.assertGreater(len(arch_doc.read_text(encoding="utf-8")), 100)
        self.assertGreater(len(rules_doc.read_text(encoding="utf-8")), 100)

    def test_f3_05_gitignore_excludes_pkm_junctions(self):
        """Verify .gitignore contains entries for /My-Wiki/, /Inbox_Raw/, and /Archive_Sources/."""
        gitignore_path = PROJECT_ROOT / ".gitignore"
        self.assertTrue(gitignore_path.exists(), ".gitignore must exist")
        content = gitignore_path.read_text(encoding="utf-8")
        self.assertRegex(content, r"/?My-Wiki/?", ".gitignore must exclude My-Wiki")
        self.assertRegex(content, r"/?Inbox_Raw/?", ".gitignore must exclude Inbox_Raw")
        self.assertRegex(content, r"/?Archive_Sources/?", ".gitignore must exclude Archive_Sources")

    def test_f3_06_git_status_does_not_track_pkm_junctions(self):
        """Verify git status / check-ignore treats PKM junctions as ignored."""
        res = subprocess.run(
            ["git", "check-ignore", "My-Wiki", "Inbox_Raw", "Archive_Sources"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        self.assertEqual(res.returncode, 0, "git check-ignore must return 0 for ignored junctions")
        ignored = res.stdout.strip().splitlines()
        self.assertIn("My-Wiki", [i.strip("/\\") for i in ignored])


class TestTier1F4AgentsConstitution(unittest.TestCase):
    """F4: AGENTS.md 4-part multi-persona & SSOT rules."""

    def setUp(self):
        agents_path = PROJECT_ROOT / "AGENTS.md"
        self.assertTrue(agents_path.exists(), "AGENTS.md must exist")
        self.content = agents_path.read_text(encoding="utf-8")

    def test_f4_01_pkm_master_architect_persona(self):
        """Verify AGENTS.md defines PKM Master Architect persona."""
        self.assertIn("PKM 마스터 아키텍트", self.content, "AGENTS.md must define PKM 마스터 아키텍트 persona")

    def test_f4_02_dynamic_ssot_preflight_rule(self):
        """Verify AGENTS.md mandates dynamic pre-flight read of PKM 아키텍처.md and 옵시디언 메모간 링크 연결 규칙 설계.md."""
        self.assertIn("PKM 아키텍처.md", self.content, "AGENTS.md must reference PKM 아키텍처.md as SSOT")
        self.assertIn("옵시디언 메모간 링크 연결 규칙 설계.md", self.content, "AGENTS.md must reference 옵시디언 링크 규칙 as SSOT")

    def test_f4_03_human_write_sovereignty(self):
        """Verify AGENTS.md enforces human write sovereignty on 100. Concepts and 500. etc."""
        self.assertIn("100. Concepts", self.content, "AGENTS.md must protect 100. Concepts")
        self.assertIn("500. etc", self.content, "AGENTS.md must protect 500. etc")
        self.assertIn("인간 주권", self.content, "AGENTS.md must declare 인간 주권 (human sovereignty)")

    def test_f4_04_vault_binary_isolation(self):
        """Verify AGENTS.md forbids heavy raw binaries inside My-Wiki vault."""
        self.assertIn("바이너리", self.content, "AGENTS.md must mention 바이너리 격리 (binary isolation)")
        self.assertIn("Inbox_Raw", self.content)
        self.assertIn("Archive_Sources", self.content)

    def test_f4_05_hybrid_obsidian_protocol(self):
        """Verify AGENTS.md specifies Hybrid Obsidian MCP + Local Junction protocol."""
        self.assertIn("obsidian", self.content.lower(), "AGENTS.md must mention Obsidian MCP")
        has_mcp_or_patch = any(term in self.content for term in ["vault_patch", "active_file_get_path", "정션"])
        self.assertTrue(has_mcp_or_patch, "AGENTS.md must detail hybrid MCP and local junction execution")

    def test_f4_06_retains_macro_and_valley_personas(self):
        """Verify AGENTS.md preserves existing Macro/TAA quant persona and Valley AI scraper persona."""
        self.assertIn("글로벌 매크로 경제 분석가", self.content, "AGENTS.md must preserve Macro persona")
        self.assertIn("calculate_metrics.py", self.content, "AGENTS.md must preserve quant engine delegation")
        self.assertIn("8대 매크로 자산군", self.content, "AGENTS.md must preserve 8 asset classes")
        self.assertIn("valley", self.content.lower(), "AGENTS.md must mention Valley AI scraper")


class TestTier1F5PKMManagerSkill(unittest.TestCase):
    """F5: pkm_manager/SKILL.md frontmatter & workflow specifications."""

    def setUp(self):
        self.skill_path = PROJECT_ROOT / ".agents" / "skills" / "pkm_manager" / "SKILL.md"

    def _require_skill_file(self) -> str:
        if not self.skill_path.exists():
            self.fail(f"SKILL.md does not exist at {self.skill_path}. Feature M3 pending.")
        return self.skill_path.read_text(encoding="utf-8")

    def test_f5_01_skill_file_exists(self):
        """Verify .agents/skills/pkm_manager/SKILL.md exists."""
        self.assertTrue(self.skill_path.exists(), f"SKILL.md must exist at {self.skill_path}")

    def test_f5_02_yaml_frontmatter_name_and_description(self):
        """Verify SKILL.md YAML frontmatter contains name: pkm-manager and description."""
        content = self._require_skill_file()
        self.assertTrue(content.startswith("---"), "SKILL.md must start with YAML frontmatter delimiter '---'")
        match = re.search(r"name:\s*(.+)", content)
        self.assertIsNotNone(match, "Frontmatter must contain 'name'")
        self.assertEqual(match.group(1).strip().strip('"').strip("'"), "pkm-manager")
        self.assertIn("description:", content, "Frontmatter must contain 'description'")

    def test_f5_03_defines_ssot_preflight_workflow(self):
        """Verify SKILL.md defines Dynamic SSOT Pre-flight workflow."""
        content = self._require_skill_file()
        self.assertIn("PKM 아키텍처.md", content, "SKILL.md must instruct reading PKM 아키텍처.md")
        self.assertIn("옵시디언 메모간 링크 연결 규칙 설계.md", content)

    def test_f5_04_defines_kordoc_ingestion_workflow(self):
        """Verify SKILL.md defines kordoc external document ingestion workflow."""
        content = self._require_skill_file()
        self.assertIn("ingest_sources.py", content, "SKILL.md must document ingest_sources.py")
        self.assertIn("kordoc", content.lower(), "SKILL.md must document kordoc integration")

    def test_f5_05_defines_vault_linter_workflow(self):
        """Verify SKILL.md defines vault_linter audit workflow."""
        content = self._require_skill_file()
        self.assertIn("vault_linter.py", content, "SKILL.md must document vault_linter.py")

    def test_f5_06_defines_surgical_patch_and_karpathy_wiki(self):
        """Verify SKILL.md details surgical note patching and Karpathy LLM Wiki compilation."""
        content = self._require_skill_file()
        has_patch = any(term in content for term in ["vault_patch", "수술", "patch"])
        has_wiki = any(term in content for term in ["400. Wiki", "컴파일", "Wiki", "compilation"])
        self.assertTrue(has_patch and has_wiki, "SKILL.md must describe surgical patch and wiki compilation")


class TestTier1F6KordocEngine(unittest.TestCase):
    """F6: kordoc engine & python SDK availability."""

    def test_f6_01_node_version_satisfies_requirement(self):
        """Verify Node.js is installed with version >= 20.0.0."""
        res = subprocess.run(["node", "-v"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        self.assertEqual(res.returncode, 0, "Node.js must be installed and executable")
        version_str = res.stdout.strip().lstrip("v")
        major_version = int(version_str.split(".")[0])
        self.assertGreaterEqual(major_version, 20, f"Node.js version {version_str} must be >= 20")

    def test_f6_02_kordoc_cli_callable(self):
        """Verify kordoc CLI is callable (via global command or npx fallback)."""
        kordoc_bin = shutil.which("kordoc")
        if kordoc_bin:
            cmd = [kordoc_bin, "--version"]
        else:
            npx_bin = shutil.which("npx")
            self.assertIsNotNone(npx_bin, "Neither kordoc nor npx is found in PATH")
            cmd = [npx_bin, "--yes", "kordoc", "--version"]
        cli_res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        self.assertEqual(cli_res.returncode, 0, f"kordoc command failed: {cli_res.stderr}")
        self.assertRegex(cli_res.stdout.strip(), r"\d+\.\d+\.\d+", "kordoc --version must output semantic version")

    def test_f6_03_python_runtime_satisfies_kordoc_requirement(self):
        """Verify Python runtime meets >= 3.11 requirement."""
        major, minor = sys.version_info.major, sys.version_info.minor
        self.assertTrue(
            (major == 3 and minor >= 11) or major > 3,
            f"Current Python runtime {major}.{minor} must be >= 3.11 for kordoc SDK",
        )

    def test_f6_04_kordoc_python_sdk_import(self):
        """Verify kordoc Python SDK can be imported and KordocClient is available."""
        try:
            import kordoc
            self.assertTrue(hasattr(kordoc, "KordocClient"), "kordoc module must export KordocClient")
        except ImportError:
            self.fail("kordoc Python SDK is not installed in the current environment")

    def test_f6_05_kordoc_table_format_gfm_flag(self):
        """Verify kordoc CLI recognizes --table-format gfm flag in help output."""
        kordoc_bin = shutil.which("kordoc")
        if kordoc_bin:
            cmd = [kordoc_bin, "--help"]
        else:
            npx_bin = shutil.which("npx")
            self.assertIsNotNone(npx_bin, "Neither kordoc nor npx is found in PATH")
            cmd = [npx_bin, "--yes", "kordoc", "--help"]
        help_res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        self.assertEqual(help_res.returncode, 0)
        self.assertIn("table-format", help_res.stdout.lower(), "kordoc --help must list --table-format option")


class TestTier1F7IngestSourcesCLI(unittest.TestCase):
    """F7: ingest_sources.py CLI flags, parsing, 7-core frontmatter, clean null []."""

    def setUp(self):
        self.script_path = PROJECT_ROOT / ".agents" / "skills" / "pkm_manager" / "scripts" / "ingest_sources.py"

    def test_f7_01_script_exists_and_executable(self):
        """Verify ingest_sources.py exists in scripts folder."""
        self.assertTrue(self.script_path.exists(), f"ingest_sources.py must exist at {self.script_path}")

    def test_f7_02_cli_help_flag(self):
        """Verify ingest_sources.py --help returns exit code 0 and lists arguments."""
        self.assertTrue(self.script_path.exists(), "ingest_sources.py missing")
        res = subprocess.run([sys.executable, str(self.script_path), "--help"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        self.assertEqual(res.returncode, 0, f"ingest_sources.py --help failed: {res.stderr}")
        out = res.stdout.lower()
        for opt in ["--inbox", "--vault", "--archive", "--subfolder", "--domain", "--up", "--dry-run"]:
            self.assertIn(opt, out, f"ingest_sources.py must support {opt}")

    def test_f7_03_cli_dry_run_flag(self):
        """Verify ingest_sources.py --dry-run previews conversion without file mutations."""
        self.assertTrue(self.script_path.exists(), "ingest_sources.py missing")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox"
            inbox.mkdir()
            test_file = inbox / "sample.txt"
            test_file.write_text("Test content", encoding="utf-8")
            res = subprocess.run(
                [
                    sys.executable,
                    str(self.script_path),
                    "--file", str(test_file),
                    "--inbox", str(inbox),
                    "--vault", str(tmp / "Vault"),
                    "--archive", str(tmp / "Archive"),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"--dry-run failed: {res.stderr}")
            self.assertTrue(test_file.exists(), "Original file must not be moved in --dry-run")
            self.assertFalse((tmp / "Vault").exists(), "Vault destination must not be created in --dry-run")

    def test_f7_04_clean_null_empty_brackets(self):
        """Verify generated frontmatter outputs up: [] when --up is omitted (never '[[]]')."""
        self.assertTrue(self.script_path.exists(), "ingest_sources.py missing")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox"
            vault = tmp / "Vault"
            archive = tmp / "Archive"
            inbox.mkdir()
            sample = inbox / "market_overview.txt"
            sample.write_text("Title: Market Overview\nBody: Sample text.", encoding="utf-8")
            res = subprocess.run(
                [
                    sys.executable,
                    str(self.script_path),
                    "--file", str(sample),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--subfolder", "310. Reports_Papers",
                    "--domain", "macro",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"Ingestion failed: {res.stderr}")
            # Locate output md
            out_files = list(vault.rglob("*.md"))
            self.assertEqual(len(out_files), 1, "Expected exactly 1 generated markdown file")
            content = out_files[0].read_text(encoding="utf-8")
            self.assertNotIn('"[[]]"', content, "Frontmatter must NEVER contain '[[]]'")
            self.assertRegex(content, r"up:\s*\[\s*\]", "Frontmatter must output clean empty array up: []")

    def test_f7_05_seven_core_attributes_in_generated_note(self):
        """Verify generated note contains all 7 core attributes."""
        self.assertTrue(self.script_path.exists(), "ingest_sources.py missing")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox"
            vault = tmp / "Vault"
            archive = tmp / "Archive"
            inbox.mkdir()
            sample = inbox / "inflation_report.txt"
            sample.write_text("# US Inflation 2026\nAnalysis of CPI data.", encoding="utf-8")
            res = subprocess.run(
                [
                    sys.executable,
                    str(self.script_path),
                    "--file", str(sample),
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
            self.assertEqual(res.returncode, 0, f"Ingestion failed: {res.stderr}")
            out_files = list(vault.rglob("*.md"))
            self.assertEqual(len(out_files), 1)
            content = out_files[0].read_text(encoding="utf-8")
            for core_key in ["origin: source", "type: source", "domain:", "up:", "status: active", "created:", "updated:"]:
                self.assertIn(core_key, content, f"Generated note must contain core key '{core_key}'")

    def test_f7_06_inbox_zero_raw_file_archival(self):
        """Verify raw source file is removed from inbox and moved to archive destination."""
        self.assertTrue(self.script_path.exists(), "ingest_sources.py missing")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox"
            vault = tmp / "Vault"
            archive = tmp / "Archive"
            inbox.mkdir()
            sample = inbox / "raw_data.txt"
            sample.write_text("Raw text payload", encoding="utf-8")
            res = subprocess.run(
                [
                    sys.executable,
                    str(self.script_path),
                    "--file", str(sample),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--subfolder", "340. Work_Docs",
                    "--domain", "work",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0)
            self.assertFalse(sample.exists(), "Raw file must be removed from Inbox (Inbox Zero)")
            archived_files = list(archive.rglob("raw_data.txt"))
            self.assertEqual(len(archived_files), 1, "Raw file must be moved to Archive destination")


class TestTier1F8VaultLinterCLI(unittest.TestCase):
    """F8: vault_linter.py 5 constitutional checks (C1-C5)."""

    def setUp(self):
        self.script_path = PROJECT_ROOT / ".agents" / "skills" / "pkm_manager" / "scripts" / "vault_linter.py"

    def test_f8_01_script_exists_and_executable(self):
        """Verify vault_linter.py exists in scripts folder."""
        self.assertTrue(self.script_path.exists(), f"vault_linter.py must exist at {self.script_path}")

    def test_f8_02_cli_help_flag(self):
        """Verify vault_linter.py --help exits with 0 and lists arguments."""
        self.assertTrue(self.script_path.exists(), "vault_linter.py missing")
        res = subprocess.run([sys.executable, str(self.script_path), "--help"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        self.assertEqual(res.returncode, 0, f"vault_linter.py --help failed: {res.stderr}")
        out = res.stdout.lower()
        for opt in ["--vault", "--fix", "--format", "--exit-zero", "--include-inbox"]:
            self.assertIn(opt, out, f"vault_linter.py must support {opt}")

    def test_f8_03_check_c1_missing_core_attributes(self):
        """Verify C1 flags notes with missing core attributes."""
        self.assertTrue(self.script_path.exists(), "vault_linter.py missing")
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "TestVault"
            concept_dir = vault / "100. Concepts"
            concept_dir.mkdir(parents=True)
            # Create invalid note missing 'origin' and 'status'
            invalid_note = concept_dir / "InvalidNote.md"
            invalid_note.write_text(
                "---\ntype: concept\ndomain: [theory]\nup: ['[[01_경제 및 금융 이론]]']\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Invalid Note",
                encoding="utf-8",
            )
            res = subprocess.run([sys.executable, str(self.script_path), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(res.returncode, 1, "vault_linter must return 1 on C1 violation")
            self.assertTrue(
                "origin" in res.stdout.lower() or "c1" in res.stdout.lower() or "core" in res.stdout.lower(),
                "Output must identify missing core attribute violation",
            )

    def test_f8_04_check_c2_ghost_links(self):
        """Verify C2 flags notes containing ghost links '[[]]'."""
        self.assertTrue(self.script_path.exists(), "vault_linter.py missing")
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "TestVault"
            concept_dir = vault / "100. Concepts"
            concept_dir.mkdir(parents=True)
            ghost_note = concept_dir / "GhostLinkNote.md"
            ghost_note.write_text(
                '---\norigin: human\ntype: concept\ndomain: [theory]\nup:\n  - "[[]]"\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Ghost Note',
                encoding="utf-8",
            )
            res = subprocess.run([sys.executable, str(self.script_path), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(res.returncode, 1, "vault_linter must return 1 on ghost link violation")
            self.assertTrue(
                "ghost" in res.stdout.lower() or "c2" in res.stdout.lower() or "[[]]" in res.stdout,
                "Output must report ghost link violation",
            )

    def test_f8_05_check_c3_orphan_notes(self):
        """Verify C3 flags orphan notes (empty up: []) on regular notes."""
        self.assertTrue(self.script_path.exists(), "vault_linter.py missing")
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "TestVault"
            concept_dir = vault / "100. Concepts"
            concept_dir.mkdir(parents=True)
            orphan_note = concept_dir / "RegularConceptNote.md"
            orphan_note.write_text(
                "---\norigin: human\ntype: concept\ndomain: [theory]\nup: []\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Regular Orphan Note",
                encoding="utf-8",
            )
            res = subprocess.run([sys.executable, str(self.script_path), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(res.returncode, 1, "vault_linter must return 1 on orphan note")
            self.assertTrue(
                "orphan" in res.stdout.lower() or "c3" in res.stdout.lower() or "up" in res.stdout.lower(),
                "Output must report orphan note violation",
            )

    def test_f8_06_check_c4_folder_origin_mismatch(self):
        """Verify C4 flags folder-origin mismatch (e.g. origin: ai in 100. Concepts)."""
        self.assertTrue(self.script_path.exists(), "vault_linter.py missing")
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "TestVault"
            concept_dir = vault / "100. Concepts"
            concept_dir.mkdir(parents=True)
            mismatch_note = concept_dir / "MismatchNote.md"
            mismatch_note.write_text(
                "---\norigin: ai\ntype: concept\ndomain: [theory]\nup:\n  - '[[01_경제 및 금융 이론]]'\nstatus: active\ncreated: 2026-10-25\nupdated: 2026-10-25\n---\n# Mismatch",
                encoding="utf-8",
            )
            res = subprocess.run([sys.executable, str(self.script_path), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(res.returncode, 1, "vault_linter must return 1 on origin-folder mismatch")
            self.assertTrue(
                "origin" in res.stdout.lower() or "c4" in res.stdout.lower() or "mismatch" in res.stdout.lower(),
                "Output must report folder-origin mismatch",
            )

    def test_f8_07_check_c5_binary_infiltration(self):
        """Verify C5 flags heavy binaries (.pdf, .hwpx, .xlsx, etc.) in vault."""
        self.assertTrue(self.script_path.exists(), "vault_linter.py missing")
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "TestVault"
            sources_dir = vault / "300. Sources" / "310. Reports_Papers"
            sources_dir.mkdir(parents=True)
            # Create a dummy binary file inside vault
            binary_file = sources_dir / "InfiltratedReport.pdf"
            binary_file.write_bytes(b"%PDF-1.4 dummy binary content")
            res = subprocess.run([sys.executable, str(self.script_path), "--vault", str(vault)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            self.assertEqual(res.returncode, 1, "vault_linter must return 1 on binary infiltration")
            self.assertTrue(
                "binary" in res.stdout.lower() or "c5" in res.stdout.lower() or "pdf" in res.stdout.lower(),
                "Output must report heavy binary infiltration",
            )


class TestTier1F9ParseSourcesCLI(unittest.TestCase):
    """F9: parse_sources.py dedicated CLI, flat 000. Inbox/ staging & embedded image extraction."""

    def setUp(self):
        self.script_path = (
            PROJECT_ROOT
            / ".agents"
            / "skills"
            / "pkm_parse"
            / "scripts"
            / "parse_sources.py"
        )
        self.skill_path = (
            PROJECT_ROOT
            / ".agents"
            / "skills"
            / "pkm_parse"
            / "SKILL.md"
        )

    def test_f9_01_script_exists_and_executable(self):
        """Verify parse_sources.py exists in .agents/skills/pkm_parse/scripts/."""
        self.assertTrue(
            self.script_path.exists(),
            f"parse_sources.py must exist at {self.script_path}",
        )

    def test_f9_02_cli_help_flag(self):
        """Verify parse_sources.py --help exits with 0 and lists all 19 required flags."""
        self.assertTrue(self.script_path.exists(), "parse_sources.py missing")
        res = subprocess.run(
            [sys.executable, str(self.script_path), "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        self.assertEqual(res.returncode, 0, f"parse_sources.py --help failed: {res.stderr}")
        out = res.stdout.lower()
        required_flags = [
            "--file", "--inbox", "--vault", "--archive", "--subfolder",
            "--domain", "--up", "--source-type", "--author", "--org",
            "--published", "--ref-date", "--aliases", "--summary",
            "--table-format", "--ocr", "--dry-run", "--force", "--verbose",
        ]
        for opt in required_flags:
            self.assertIn(opt, out, f"parse_sources.py must support {opt}")

    def test_f9_03_skill_md_contract(self):
        """Verify .agents/skills/pkm_parse/SKILL.md exists with name: pkm-parse and workflows."""
        self.assertTrue(
            self.skill_path.exists(),
            f"pkm_parse SKILL.md must exist at {self.skill_path}",
        )
        content = self.skill_path.read_text(encoding="utf-8")
        self.assertIn("name: pkm-parse", content, "SKILL.md frontmatter must define name: pkm-parse")
        self.assertTrue(
            "ssot" in content.lower() or "dynamic" in content.lower(),
            "SKILL.md must document dynamic SSOT pre-flight rule",
        )

    def test_f9_04_flat_inbox_placement(self):
        """Verify generated notes are placed flat in 000. Inbox/<stem>.md without subdirectories."""
        self.assertTrue(self.script_path.exists(), "parse_sources.py missing")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            inbox.mkdir(parents=True)
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"

            sample = inbox / "flat_test_doc.txt"
            sample.write_text("Sample text content for flat inbox placement.", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable,
                    str(self.script_path),
                    "--file", str(sample),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--subfolder", "310. Reports_Papers",
                    "--domain", "macro",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"parse_sources failed: {res.stderr}")
            expected_note = vault / "000. Inbox" / "flat_test_doc.md"
            self.assertTrue(expected_note.exists(), f"Note must reside flat in 000. Inbox/: {expected_note}")
            # Ensure no subdirectories under 000. Inbox
            inbox_subdirs = [p for p in (vault / "000. Inbox").iterdir() if p.is_dir()]
            self.assertEqual(len(inbox_subdirs), 0, "000. Inbox must not contain subdirectories")

    def test_f9_05_clean_null_empty_brackets(self):
        """Verify unanchored notes or ghost links produce clean empty brackets up: []."""
        self.assertTrue(self.script_path.exists(), "parse_sources.py missing")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            inbox.mkdir(parents=True)
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"

            sample = inbox / "clean_null_doc.txt"
            sample.write_text("Unanchored note content.", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable,
                    str(self.script_path),
                    "--file", str(sample),
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
            note_path = vault / "000. Inbox" / "clean_null_doc.md"
            self.assertTrue(note_path.exists())
            content = note_path.read_text(encoding="utf-8")
            self.assertIn("up: []", content, "Unanchored note must format up as empty array []")
            self.assertNotIn('"[[]]"', content, "Frontmatter must never contain ghost links")

    def test_f9_06_inbox_zero_movement_to_archive(self):
        """Verify raw source file is removed from Inbox_Raw and archived (Inbox Zero)."""
        self.assertTrue(self.script_path.exists(), "parse_sources.py missing")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            inbox = tmp / "Inbox_Raw"
            inbox.mkdir(parents=True)
            vault = tmp / "My-Wiki"
            archive = tmp / "Archive_Sources"

            sample = inbox / "inbox_zero_test.txt"
            sample.write_text("Content to archive.", encoding="utf-8")

            res = subprocess.run(
                [
                    sys.executable,
                    str(self.script_path),
                    "--file", str(sample),
                    "--inbox", str(inbox),
                    "--vault", str(vault),
                    "--archive", str(archive),
                    "--subfolder", "310. Reports_Papers",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(res.returncode, 0)
            self.assertFalse(sample.exists(), "Raw file must be deleted from Inbox_Raw (Inbox Zero)")
            archived = archive / "310. Reports_Papers" / "inbox_zero_test.txt"
            self.assertTrue(archived.exists(), f"Raw file must be moved to {archived}")


if __name__ == "__main__":
    unittest.main()
