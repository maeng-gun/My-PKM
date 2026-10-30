"""Unit and integration tests for My-Wiki Rules v3.0 Dynamic SSOT, compile_helper.py, and vault_linter.py v3.0."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / ".agents" / "skills" / "pkm_manager" / "scripts"
CONSTITUTION_LOADER_PATH = SCRIPTS_DIR / "constitution_loader.py"
COMPILE_HELPER_PATH = SCRIPTS_DIR / "compile_helper.py"
VAULT_LINTER_PATH = SCRIPTS_DIR / "vault_linter.py"
LIVE_VAULT_PATH = PROJECT_ROOT / "My-Wiki"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import constitution_loader  # noqa: E402


class TestV3ConstitutionLoader(unittest.TestCase):
    """Tests for dynamic SSOT parsing in constitution_loader.py."""

    def test_load_live_vault_constitution(self):
        """Verify live My-Wiki Rules.md parses with v3.0 schema, folders, domains, and indexes."""
        self.assertTrue(LIVE_VAULT_PATH.exists(), "Live My-Wiki junction must exist")
        config = constitution_loader.load_constitution(LIVE_VAULT_PATH)
        self.assertRegex(config["version"], r"^v\d+\.\d+")
        self.assertTrue(len(config["sha256"]) == 64)

        self.assertEqual(
            config["core_attributes"],
            ["origin", "type", "domain", "up", "status", "created", "updated"],
        )
        for dom in ["theory", "macro", "equity", "portfolio", "work", "ai-pkm", "education"]:
            self.assertIn(dom, config["allowed_domains"])
        self.assertNotIn("quant", config["allowed_domains"])
        self.assertNotIn("life", config["allowed_domains"])
        self.assertEqual(len(config["allowed_domains"]), 7)
        self.assertEqual(
            config["allowed_domains"],
            ["theory", "macro", "equity", "portfolio", "work", "ai-pkm", "education"],
        )

        fmap = config["folder_origin_map"]
        self.assertEqual(fmap.get("100. Concepts"), "human")
        self.assertEqual(fmap.get("200. AI_logs"), "ai")
        self.assertEqual(fmap.get("300. Sources"), "source")
        self.assertEqual(fmap.get("400. Wiki"), "wiki")
        self.assertEqual(fmap.get("500. Index"), "wiki")
        self.assertEqual(fmap.get("600. etc"), "human")

        expected_indexes = {
            "_인덱스_400_Wiki.md",
            "_인덱스_100_Concepts.md",
            "_인덱스_200_AI_logs.md",
            "_인덱스_210_뉴스큐레이팅.md",
            "_인덱스_220_산업분석.md",
            "_인덱스_300_Sources.md",
        }
        self.assertTrue(expected_indexes.issubset(set(config["index_files"])))

    def test_dynamic_ssot_live_reflection_on_rule_change(self):
        """Verify modifying My-Wiki Rules.md dynamically updates parsed domains, folders, and indexes without code edits."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "MockVault"
            vault.mkdir(parents=True)
            rules_md = vault / "My-Wiki Rules.md"
            rules_md.write_text(
                """---
origin: wiki
type: hub
domain:
  - work
  - life
up: []
status: evergreen
created: 2026-04-12
updated: 2026-10-30
---
# 🏛️ My-Wiki 지식 관리 헌법 (v3.1)

| 물리적 폴더 경로 | 직교 축 및 역할 | origin 속성값 | 주요 내용 |
| :--- | :--- | :--- | :--- |
| **`000. Inbox`** | 수집 버퍼 | *(미부여)* | 인박스 |
| **`100. Concepts`** | 인간 주권 | `origin: human` | 개념 |
| **`400. Wiki`** | 마스터 위키 | `origin: wiki` | 위키 |
| **`500. Index`** | 인덱스 | `origin: wiki` | 인덱스 |
| **`700. Lab`** | 실험실 | `origin: human` | 신규 동적 폴더 |

### Rule 2. 2계층(Two-Tier) 프론트매터 스키마와 노션 유산 청소
1. **절대 지우지 않는 7대 필수 코어 속성 (Core Schema)**:
   - `origin`: 물리적 폴더와 1:1 매핑 (`human` | `ai` | `source` | `wiki`)
   - `type`: 노트의 역할 (`hub` | `concept` | `analysis` | `entity` | `source` | `project` | `log`)
   - `domain`: 도메인 관심사 리스트 (`theory`, `macro`, `equity`, `portfolio`, `quant`, `work`, `life`, `crypto` 중 선택)
   - `up`: 직계 1촌 부모 노드의 위키링크 리스트 (`["[[부모문서명]]"]`)
   - `status`: 노트의 상태 (`seed` | `growing` | `evergreen` | `active` | `completed` | `archived`)
   - `created`: 최초 생성일 (`YYYY-MM-DD`)
   - `updated`: 최종 수정/컴파일일 (`YYYY-MM-DD`)

| 인덱스 파일명 | 관할 원본 폴더 |
| :--- | :--- |
| **`_인덱스_400_Wiki.md`** | `400. Wiki` |
| **`_인덱스_700_Lab.md`** | `700. Lab` |
""",
                encoding="utf-8",
            )

            config = constitution_loader.load_constitution(vault)
            self.assertEqual(config["version"], "v3.1")
            self.assertEqual(config["updated"], "2026-10-30")
            self.assertIn("crypto", config["allowed_domains"])
            self.assertEqual(config["folder_origin_map"].get("700. Lab"), "human")
            self.assertIn("_인덱스_700_Lab.md", config["index_files"])


class TestV3CompileHelperCLI(unittest.TestCase):
    """Tests for compile_helper.py deterministic subcommands."""

    def _run_helper(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(COMPILE_HELPER_PATH)] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

    def test_inbox_status_and_normalize_fm_and_move_note(self):
        """Verify inbox-status, normalize-fm (legacy Notion cleanup + multi-up), and move-note."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            inbox = vault / "000. Inbox"
            inbox.mkdir(parents=True)

            note_path = inbox / "LegacyNotionNote.md"
            note_path.write_text(
                """---
날짜: 2026. 10. 15.
주제: 거시경제
base: notion_export
stance: bullish
---
# 금리 인하 사이클 분석
본문 내용입니다.
""",
                encoding="utf-8",
            )

            # 1. Check inbox-status before normalization
            res_status = self._run_helper(["inbox-status", "--vault", str(vault), "--format", "json"])
            self.assertEqual(res_status.returncode, 0)
            status_data = json.loads(res_status.stdout)
            self.assertEqual(status_data["total_inbox_notes"], 1)
            self.assertEqual(status_data["legacy_notion_count"], 1)

            # 2. Run normalize-fm with multi-up and legacy Notion key stripping
            res_norm = self._run_helper(
                [
                    "normalize-fm",
                    "--vault",
                    str(vault),
                    "--file",
                    str(note_path),
                    "--origin",
                    "human",
                    "--type",
                    "analysis",
                    "--domain",
                    "macro",
                    "portfolio",
                    "--up",
                    "[[글로벌 통화정책 프레임워크]]",
                    "[[인플레이션 및 금리 사이클]]",
                    "--status",
                    "active",
                    "--updated",
                    "2026-10-29",
                ]
            )
            self.assertEqual(res_norm.returncode, 0, res_norm.stderr)
            norm_text = note_path.read_text(encoding="utf-8")
            fm_match = re.match(r"^---\r?\n(.*?)\r?\n---", norm_text, re.DOTALL)
            self.assertIsNotNone(fm_match, "Normalized note must have YAML frontmatter")
            fm = yaml.safe_load(fm_match.group(1))
            self.assertEqual(fm["origin"], "human")
            self.assertEqual(fm["type"], "analysis")
            self.assertEqual(fm["domain"], ["macro", "portfolio"])
            self.assertEqual(
                fm["up"],
                ["[[글로벌 통화정책 프레임워크]]", "[[인플레이션 및 금리 사이클]]"],
            )
            self.assertEqual(str(fm["created"]), "2026-10-15")
            self.assertEqual(str(fm["ref_date"]), "2026-10-15")
            self.assertEqual(fm["stance"], "bullish")
            self.assertNotIn("날짜", fm)
            self.assertNotIn("주제", fm)
            self.assertNotIn("base", fm)

            # 3. Move note to 100. Concepts
            res_move = self._run_helper(
                [
                    "move-note",
                    "--vault",
                    str(vault),
                    "--file",
                    str(note_path),
                ]
            )
            self.assertEqual(res_move.returncode, 0, res_move.stderr)
            self.assertFalse(note_path.exists())
            self.assertTrue((vault / "100. Concepts" / "LegacyNotionNote.md").exists())
            self.assertFalse((vault / ".trash").exists(), "agy native I/O must not create .trash")

    def test_scan_index_and_upsert_index_step4_retroactive_add_up(self):
        """Verify scan-index and upsert-index (both new row append and Step 4 --add-up existing row update)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            idx_dir = vault / "500. Index"
            idx_dir.mkdir(parents=True)
            idx_100 = idx_dir / "_인덱스_100_Concepts.md"
            idx_100.write_text(
                """---
origin: wiki
type: hub
domain:
  - work
up:
  - "[[My-Wiki Rules]]"
status: evergreen
created: 2026-04-12
updated: 2026-10-28
---
# 🗂️ 100. Concepts 통합 인덱스

| # | 노트명 (`[[링크]]`) | 작성 / 수정일 | 역할 (`type`) · 도메인 (`domain`) | 나의 핵심 관점·테제 및 주요 키워드 (1~2문장) | 연결된 상위 위키(`up`) 및 원천/선행(`source`/`prev`) |
| :---: | :--- | :---: | :---: | :--- | :--- |
| 1 | **[[기존메모A]]** | 2026-10-01 | `concept`<br>`macro` | 기존 글로벌 금리 메모 | `[[기존위키1]]` |
""",
                encoding="utf-8",
            )

            # 1. Append a new row via upsert-index
            res_insert = self._run_helper(
                [
                    "upsert-index",
                    "--vault",
                    str(vault),
                    "--index-file",
                    "_인덱스_100_Concepts.md",
                    "--note",
                    "신규메모B",
                    "--date",
                    "2026-10-29",
                    "--meta",
                    "`analysis`<br>`macro`, `equity`",
                    "--up",
                    "[[기존위키1]]",
                    "--summary",
                    "신규 금리 및 증시 영향 분석",
                ]
            )
            self.assertEqual(res_insert.returncode, 0, res_insert.stderr)
            self.assertIn("Appended new row for [[신규메모B]]", res_insert.stdout)

            # 2. Step 4 Retroactive --add-up on [[기존메모A]]
            res_step4 = self._run_helper(
                [
                    "upsert-index",
                    "--vault",
                    str(vault),
                    "--index-file",
                    "_인덱스_100_Concepts.md",
                    "--note",
                    "기존메모A",
                    "--add-up",
                    "[[신규위키2]]",
                ]
            )
            self.assertEqual(res_step4.returncode, 0, res_step4.stderr)
            self.assertIn("Updated existing row for [[기존메모A]]", res_step4.stdout)

            # 3. Verify via scan-index
            res_scan = self._run_helper(
                [
                    "scan-index",
                    "--vault",
                    str(vault),
                    "--scope",
                    "origins",
                    "--query",
                    "금리",
                    "--format",
                    "json",
                ]
            )
            self.assertEqual(res_scan.returncode, 0, res_scan.stderr)
            scan_out = json.loads(res_scan.stdout)
            self.assertEqual(scan_out["total_matches"], 2)
            row_a = next(m for m in scan_out["matches"] if "기존메모A" in m["primary_note"])
            self.assertIn("[[기존위키1]]", row_a["raw_row"])
            self.assertIn("[[신규위키2]]", row_a["raw_row"])

    def test_detect_mstep_cluster_and_lazy_sync(self):
        """Verify detect-mstep identifies >=3 cluster candidates and M-Step 5 lazy sync candidates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            wiki_dir = vault / "400. Wiki"
            wiki_dir.mkdir(parents=True)

            # Parent hub with older updated date (2026-10-10)
            (wiki_dir / "부모허브위키.md").write_text(
                """---
origin: wiki
type: hub
domain: [equity]
up: ["[[03_주식 및 산업 분석]]"]
status: evergreen
created: 2026-10-01
updated: 2026-10-10
---
# 부모허브위키
""",
                encoding="utf-8",
            )

            # 3 child wikis sharing the same parent, with newer updated date (2026-10-28)
            for idx in range(1, 4):
                (wiki_dir / f"자식위키{idx}.md").write_text(
                    f"""---
origin: wiki
type: concept
domain: [equity]
up: ["[[부모허브위키]]"]
status: evergreen
created: 2026-10-15
updated: 2026-10-28
---
# 자식위키{idx}
""",
                    encoding="utf-8",
                )

            res = self._run_helper(["detect-mstep", "--vault", str(vault), "--format", "json"])
            self.assertEqual(res.returncode, 0, res.stderr)
            data = json.loads(res.stdout)

            clusters = data["cluster_candidates"]
            self.assertEqual(len(clusters), 1)
            self.assertEqual(clusters[0]["parent_hub"], "부모허브위키")
            self.assertEqual(clusters[0]["child_count"], 3)

            stale = data["lazy_sync_targets"]
            self.assertEqual(len(stale), 1)
            self.assertEqual(stale[0]["parent_wiki"], "부모허브위키")
            self.assertEqual(stale[0]["parent_updated"], "2026-10-10")
            self.assertEqual(max(c["child_updated"] for c in stale[0]["newer_children"]), "2026-10-28")


class TestV3VaultLinter(unittest.TestCase):
    """Tests for vault_linter.py v3.0 features (500. Index, 600. etc, \\--- autofix, C6 --check-index)."""

    def _run_linter(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(VAULT_LINTER_PATH)] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

    def test_v3_folders_and_escaped_delimiter_autofix(self):
        """Verify 500. Index, 600. etc, My-Wiki Rules.md root hub, and \\--- autofix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Vault"
            (vault / "500. Index").mkdir(parents=True)
            (vault / "600. etc").mkdir(parents=True)

            (vault / "My-Wiki Rules.md").write_text(
                """---
origin: wiki
type: hub
domain: [work, life]
up: []
status: evergreen
created: 2026-04-12
updated: 2026-10-29
---
# My-Wiki Rules
""",
                encoding="utf-8",
            )

            # Escaped \--- frontmatter in 500. Index
            idx_file = vault / "500. Index" / "_인덱스_600_etc.md"
            idx_file.write_text(
                """\\---
origin: wiki
type: hub
domain: [work]
up: ["[[My-Wiki Rules]]"]
status: evergreen
created: 2026-04-12
updated: 2026-10-29
\\---
# 600 etc Index
| 문서명 (링크) | 생성/참조일 | 역할 (Type) | 도메인 | 연결된 상위 위키 (up) | 핵심 요약 (1줄) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [[자유노트]] | 2026-10-29 | `log` | `life` | `[[07_인생 및 철학]]` | 일상 기록 |
""",
                encoding="utf-8",
            )

            (vault / "600. etc" / "자유노트.md").write_text(
                """---
origin: human
type: log
domain: [life]
up: ["[[07_인생 및 철학]]"]
status: active
created: 2026-10-29
updated: 2026-10-29
---
# 자유노트
""",
                encoding="utf-8",
            )

            # First run without --fix should flag C1 escaped delimiter on _인덱스_600_etc.md
            res_fail = self._run_linter(["--vault", str(vault)])
            self.assertEqual(res_fail.returncode, 1)

            # Run with --fix and --check-index -> repairs \--- and passes C1~C6 with 0 violations
            res_fix = self._run_linter(["--vault", str(vault), "--fix", "--check-index"])
            self.assertEqual(res_fix.returncode, 0, res_fix.stdout)
            fixed_text = idx_file.read_text(encoding="utf-8")
            self.assertTrue(fixed_text.startswith("---\n"))


class TestV3ConstitutionLoaderCliAndSync(unittest.TestCase):
    """Tests for CLI options and SSOT deletion sync in constitution_loader.py."""

    def test_ssot_deletion_sync_removes_deleted_tokens(self):
        """Verify tokens removed from My-Wiki Rules.md are deleted from allowed_domains."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "MockVault"
            vault.mkdir(parents=True)
            rules_md = vault / "My-Wiki Rules.md"
            rules_md.write_text(
                """---
origin: wiki
type: hub
domain: [macro]
up: []
status: evergreen
created: 2026-04-12
updated: 2026-10-30
---
# My-Wiki 지식 관리 헌법 (v3.2)
### Rule 2. 2계층 프론트매터 스키마
1. **필수 코어 속성**:
   - `domain`: 도메인 관심사 리스트 (`macro`, `equity` 중 선택)
""",
                encoding="utf-8",
            )
            config = constitution_loader.load_constitution(vault)
            self.assertEqual(config["allowed_domains"], ["macro", "equity"])
            self.assertNotIn("quant", config["allowed_domains"])
            self.assertNotIn("life", config["allowed_domains"])
            self.assertNotIn("theory", config["allowed_domains"])

    def test_constitution_loader_cli_list_sections(self):
        """Verify --list-sections outputs known sections in text and JSON."""
        # Text format check
        cmd = [sys.executable, str(CONSTITUTION_LOADER_PATH), "--vault", str(LIVE_VAULT_PATH), "--list-sections"]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("schema", res.stdout)
        self.assertIn("astep", res.stdout)
        self.assertIn("compile", res.stdout)

        # JSON format check
        cmd_json = [
            sys.executable,
            str(CONSTITUTION_LOADER_PATH),
            "--vault",
            str(LIVE_VAULT_PATH),
            "--list-sections",
            "--format",
            "json",
        ]
        res_json = subprocess.run(cmd_json, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(res_json.returncode, 0, res_json.stderr)
        data = json.loads(res_json.stdout)
        self.assertIn("predefined_sections", data)
        self.assertIn("schema", data["predefined_sections"])
        self.assertIn("headings", data)
        self.assertIsInstance(data["headings"], list)
        self.assertTrue(len(data["headings"]) > 0)

        # Type hints check
        import typing

        hints = typing.get_type_hints(constitution_loader.extract_section)
        self.assertIn("return", hints)

    def test_constitution_loader_cli_section_astep(self):
        """Verify --section astep extracts the post-compilation audit checklist."""
        cmd = [sys.executable, str(CONSTITUTION_LOADER_PATH), "--vault", str(LIVE_VAULT_PATH), "--section", "astep"]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue("사후 감사" in res.stdout or "A-Step" in res.stdout)


class TestV3CompileHelperTransitiveReduction(unittest.TestCase):
    """Tests for --remove-up and --replace-up in compile_helper.py."""

    def test_normalize_fm_remove_up(self):
        """Verify compile_helper normalize-fm removes an up link."""
        with tempfile.TemporaryDirectory() as tmpdir:
            note = Path(tmpdir) / "Note.md"
            note.write_text(
                """---
origin: wiki
type: entity
domain: [macro]
up:
  - "[[Grandparent]]"
  - "[[Parent]]"
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Note
""",
                encoding="utf-8",
            )
            cmd = [
                sys.executable,
                str(COMPILE_HELPER_PATH),
                "normalize-fm",
                "--file",
                str(note),
                "--remove-up",
                "[[Grandparent]]",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res.returncode, 0, res.stderr)
            data = yaml.safe_load(note.read_text(encoding="utf-8").split("---")[1])
            self.assertEqual(data["up"], ["[[Parent]]"])

    def test_normalize_fm_replace_up(self):
        """Verify compile_helper normalize-fm replaces an up link."""
        with tempfile.TemporaryDirectory() as tmpdir:
            note = Path(tmpdir) / "Note.md"
            note.write_text(
                """---
origin: wiki
type: entity
domain: [macro]
up:
  - "[[OldParent]]"
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Note
""",
                encoding="utf-8",
            )
            cmd = [
                sys.executable,
                str(COMPILE_HELPER_PATH),
                "normalize-fm",
                "--file",
                str(note),
                "--replace-up",
                "[[OldParent]]->[[NewParent]]",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res.returncode, 0, res.stderr)
            data = yaml.safe_load(note.read_text(encoding="utf-8").split("---")[1])
            self.assertEqual(data["up"], ["[[NewParent]]"])

    def test_upsert_index_remove_and_replace_up(self):
        """Verify upsert-index applies --remove-up and --replace-up to table row up column."""
        with tempfile.TemporaryDirectory() as tmpdir:
            idx = Path(tmpdir) / "_인덱스_400_Wiki.md"
            idx.write_text(
                """---
origin: wiki
type: hub
domain: [macro]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Wiki Index
| 문서명 (링크) | 생성/참조일 | 역할 (Type) | 도메인 | 연결된 상위 위키 (up) | 핵심 요약 (1줄) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [[TargetNote]] | 2026-10-30 | `entity` | `macro` | `[[OldParent]]`, `[[DeleteParent]]` | 요약 |
""",
                encoding="utf-8",
            )
            cmd = [
                sys.executable,
                str(COMPILE_HELPER_PATH),
                "upsert-index",
                "--index",
                str(idx),
                "--note",
                "TargetNote",
                "--replace-up",
                "[[OldParent]]->[[NewParent]]",
                "--remove-up",
                "[[DeleteParent]]",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res.returncode, 0, res.stderr)
            content = idx.read_text(encoding="utf-8")
            self.assertIn("[[NewParent]]", content)
            self.assertNotIn("[[OldParent]]", content)
            self.assertNotIn("[[DeleteParent]]", content)

    def test_upsert_index_replace_up_case_b_new_row(self):
        """Verify upsert-index Case B (appending new row) succeeds with both single-arg and two-arg --replace-up."""
        with tempfile.TemporaryDirectory() as tmpdir:
            idx = Path(tmpdir) / "_인덱스_400_Wiki.md"
            idx.write_text(
                """---
origin: wiki
type: hub
domain: [macro]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Wiki Index
| # | 문서명 (링크) | 생성/참조일 | 역할 (Type) | 핵심 요약 (1줄) | 연결된 상위 위키 (up) |
| :---: | :--- | :---: | :--- | :--- | :--- |
| 1 | [[ExistingNote]] | 2026-10-30 | entity | 기존 요약 | `[[RootHub]]` |
""",
                encoding="utf-8",
            )

            # Subtest 1: Case B append with single-argument --replace-up OLD->NEW
            cmd1 = [
                sys.executable,
                str(COMPILE_HELPER_PATH),
                "upsert-index",
                "--index",
                str(idx),
                "--note",
                "BrandNewNote1",
                "--up",
                "[[OldParent]]",
                "--replace-up",
                "[[OldParent]]->[[NewParent]]",
            ]
            res1 = subprocess.run(cmd1, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res1.returncode, 0, f"STDOUT:\n{res1.stdout}\nSTDERR:\n{res1.stderr}")
            content1 = idx.read_text(encoding="utf-8")
            self.assertIn("[[BrandNewNote1]]", content1)
            self.assertIn("`[[NewParent]]`", content1)
            self.assertNotIn("`[[OldParent]]`", content1.strip().splitlines()[-1])

            # Subtest 2: Case B append with two-argument --replace-up OLD NEW and --remove-up
            cmd2 = [
                sys.executable,
                str(COMPILE_HELPER_PATH),
                "upsert-index",
                "--index",
                str(idx),
                "--note",
                "BrandNewNote2",
                "--up",
                "[[OldParent]], [[DeleteMe]]",
                "--replace-up",
                "[[OldParent]]",
                "[[NewParent]]",
                "--remove-up",
                "[[DeleteMe]]",
            ]
            res2 = subprocess.run(cmd2, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res2.returncode, 0, f"STDOUT:\n{res2.stdout}\nSTDERR:\n{res2.stderr}")
            content2 = idx.read_text(encoding="utf-8")
            self.assertIn("[[BrandNewNote2]]", content2)
            last_line = content2.strip().splitlines()[-1]
            self.assertIn("`[[NewParent]]`", last_line)
            self.assertNotIn("DeleteMe", last_line)
            self.assertNotIn("OldParent", last_line)


class TestV3VaultLinterAStepChecks(unittest.TestCase):
    """Tests for opt-in --check-astep (C7/C8) in vault_linter.py."""

    def test_linter_default_c1_to_c5_backwards_compatible(self):
        """Default vault_linter audit must pass C1~C5 without triggering opt-in A-Step failures."""
        cmd = [sys.executable, str(VAULT_LINTER_PATH), "--vault", str(LIVE_VAULT_PATH)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(res.returncode, 0, f"Default audit must pass: {res.stdout}\n{res.stderr}")
        self.assertIn("Total Violations: 0", res.stdout)

    def test_linter_check_astep_c7_ghost_targets(self):
        """Verify --check-astep flags non-existent target wikilinks (C7)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "MockVault"
            (vault / "400. Wiki").mkdir(parents=True)
            (vault / "My-Wiki Rules.md").write_text(
                """---
origin: wiki
type: hub
domain: [macro]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Rules
""",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "ValidNote.md").write_text(
                """---
origin: wiki
type: entity
domain: [macro]
up: ["[[GhostTargetNote]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# ValidNote
Here is a ghost link to [[AnotherGhostTarget]].
""",
                encoding="utf-8",
            )
            cmd = [sys.executable, str(VAULT_LINTER_PATH), "--vault", str(vault), "--check-astep"]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertIn("C7", res.stdout, f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}\nCODE: {res.returncode}")
            self.assertIn("GhostTargetNote", res.stdout)

    def test_linter_check_astep_c8_dag_cycle_and_transitive_reduction(self):
        """Verify --check-astep flags DAG cycle (C8)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "MockVault"
            (vault / "400. Wiki").mkdir(parents=True)
            (vault / "My-Wiki Rules.md").write_text(
                """---
origin: wiki
type: hub
domain: [macro]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Rules
""",
                encoding="utf-8",
            )
            # Cycle: NodeA -> NodeB -> NodeA
            (vault / "400. Wiki" / "NodeA.md").write_text(
                """---
origin: wiki
type: entity
domain: [macro]
up: ["[[NodeB]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# NodeA
""",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "NodeB.md").write_text(
                """---
origin: wiki
type: entity
domain: [macro]
up: ["[[NodeA]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# NodeB
""",
                encoding="utf-8",
            )
            cmd = [sys.executable, str(VAULT_LINTER_PATH), "--vault", str(vault), "--check-astep"]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res.returncode, 1, "Must fail with C8 cycle violation")
            self.assertIn("C8", res.stdout)
            self.assertIn("cycle", res.stdout.lower())

    def test_linter_check_astep_c7_index_and_self_references(self):
        """Verify --check-astep flags index references and self-references under C7."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "MockVault"
            (vault / "400. Wiki").mkdir(parents=True)
            (vault / "500. Index").mkdir(parents=True)
            (vault / "My-Wiki Rules.md").write_text(
                "---\norigin: wiki\ntype: hub\ndomain: [macro]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# Rules",
                encoding="utf-8",
            )
            # 500. Index note (should NOT trigger forbidden index reference)
            (vault / "500. Index" / "_인덱스_400_Wiki.md").write_text(
                "---\norigin: wiki\ntype: hub\ndomain: [macro]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# Index\nContains [[_인덱스_400_Wiki]]",
                encoding="utf-8",
            )
            # Regular note with index reference in frontmatter and body
            (vault / "400. Wiki" / "NoteWithIndexRef.md").write_text(
                """---
origin: wiki
type: analysis
domain: [macro]
up: []
related: ["[[_인덱스_400_Wiki]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Note
- **모니터링**: [[_인덱스_210_뉴스큐레이팅]]
Also backtick `_인덱스_100_Concepts`.
""",
                encoding="utf-8",
            )
            # Note with self-references
            (vault / "400. Wiki" / "SelfRefNote.md").write_text(
                """---
origin: wiki
type: analysis
domain: [macro]
up: []
related: ["[[SelfRefNote]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# SelfRefNote
This note links to [[SelfRefNote]] and mentions `SelfRefNote`.
""",
                encoding="utf-8",
            )

            cmd = [sys.executable, str(VAULT_LINTER_PATH), "--vault", str(vault), "--check-astep"]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res.returncode, 1)
            self.assertIn("C7", res.stdout)
            self.assertIn("Forbidden index reference detected in frontmatter", res.stdout)
            self.assertIn("Forbidden index reference detected in body", res.stdout)
            self.assertIn("Self-reference detected in related", res.stdout)
            self.assertIn("Self-reference detected in body", res.stdout)

    def test_linter_check_astep_c7_fake_ghost_backticks(self):
        """Verify --check-astep flags fake ghost note backticks (C7)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "MockVault"
            (vault / "400. Wiki").mkdir(parents=True)
            (vault / "My-Wiki Rules.md").write_text(
                "---\norigin: wiki\ntype: hub\ndomain: [macro]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# Rules",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "FakeBacktickNote.md").write_text(
                """---
origin: wiki
type: analysis
domain: [macro]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Fake Backticks
Mentions ghost hub `국내 거시경제 및 정책` in text.
Also mentions uncreated prefix note `산업_가짜산업` and `기업_가짜기업`.
Legitimate code `Python` should be fine.
""",
                encoding="utf-8",
            )
            cmd = [sys.executable, str(VAULT_LINTER_PATH), "--vault", str(vault), "--check-astep"]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res.returncode, 1)
            self.assertIn("C7", res.stdout)
            self.assertIn("Fake ghost note backtick detected", res.stdout)
            self.assertIn("Fake uncreated note backtick detected", res.stdout)
            self.assertIn("국내 거시경제 및 정책", res.stdout)
            self.assertIn("산업_가짜산업", res.stdout)

    def test_linter_check_astep_c8_tier_scope_violations(self):
        """Verify --check-astep flags 1-hop scope violations across Lv1~Lv4 and Case wikis (C8)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "MockVault"
            (vault / "400. Wiki").mkdir(parents=True)
            (vault / "300. Sources").mkdir(parents=True)
            (vault / "My-Wiki Rules.md").write_text(
                "---\norigin: wiki\ntype: hub\ndomain: [equity]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# Rules",
                encoding="utf-8",
            )
            (vault / "300. Sources" / "산업분석_AI반도체.md").write_text(
                "---\norigin: source\ntype: source\ndomain: [equity]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# Source",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "C1_AI 반도체.md").write_text(
                """---
origin: wiki
type: hub
level: 1
domain: [equity]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# C1 Hub
Invalid body link to Lv3: [[산업_반도체]]
""",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "C1-S1_AI 가속기 및 서버.md").write_text(
                """---
origin: wiki
type: concept
level: 2
domain: [equity]
up: ["[[C1_AI 반도체]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# C1-S1 Stage
Invalid body link to Lv4: [[기업_엔비디아]]
""",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "산업_반도체.md").write_text(
                """---
origin: wiki
type: concept
level: 3
domain: [equity]
up: ["[[C1-S1_AI 가속기 및 서버]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Lv3 Sub-industry
Invalid body link to Lv1: [[C1_AI 반도체]]
Invalid body link to source report: [[산업분석_AI반도체]]
""",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "기업_엔비디아.md").write_text(
                """---
origin: wiki
type: entity
level: 4
domain: [equity]
up: ["[[산업_반도체]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Lv4 Company
Invalid body link to Lv1: [[C1_AI 반도체]]
""",
                encoding="utf-8",
            )
            # Case wiki with up linking to Lv1 C1
            (vault / "400. Wiki" / "사건_AI반도체규제.md").write_text(
                """---
origin: wiki
type: analysis
domain: [equity]
up: ["[[C1_AI 반도체]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Case Wiki
""",
                encoding="utf-8",
            )

            cmd = [sys.executable, str(VAULT_LINTER_PATH), "--vault", str(vault), "--check-astep"]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res.returncode, 1)
            self.assertIn("C8", res.stdout)
            self.assertIn("1-Hop scope violation in Level 1 wiki", res.stdout)
            self.assertIn("1-Hop scope violation in Level 2 wiki", res.stdout)
            self.assertIn("1-Hop scope violation in Level 3 wiki", res.stdout)
            self.assertIn("1-Hop scope violation in Level 4 wiki", res.stdout)
            self.assertIn("1-Hop scope violation in case/event wiki", res.stdout)

    def test_linter_check_astep_c8_vertical_related_and_prev(self):
        """Verify --check-astep flags non-chronological prev and vertical hierarchy in related (C8)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "MockVault"
            (vault / "400. Wiki").mkdir(parents=True)
            (vault / "My-Wiki Rules.md").write_text(
                "---\norigin: wiki\ntype: hub\ndomain: [equity]\nup: []\nstatus: active\ncreated: 2026-10-30\nupdated: 2026-10-30\n---\n# Rules",
                encoding="utf-8",
            )
            # Stage note with prev (non-chronological prev violation) and child in related (vertical related violation)
            (vault / "400. Wiki" / "C1-S1_AI 가속기 및 서버.md").write_text(
                """---
origin: wiki
type: concept
level: 2
domain: [equity]
up: []
prev: ["[[C1-S2_구동 부품]]"]
related: ["[[산업_반도체]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Stage
""",
                encoding="utf-8",
            )
            (vault / "400. Wiki" / "C1-S2_구동 부품.md").write_text(
                """---
origin: wiki
type: concept
level: 2
domain: [equity]
up: []
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Stage 2
""",
                encoding="utf-8",
            )
            # Sub-industry note with parent in up
            (vault / "400. Wiki" / "산업_반도체.md").write_text(
                """---
origin: wiki
type: concept
level: 3
domain: [equity]
up: ["[[C1-S1_AI 가속기 및 서버]]"]
status: active
created: 2026-10-30
updated: 2026-10-30
---
# Sub-industry
""",
                encoding="utf-8",
            )

            cmd = [sys.executable, str(VAULT_LINTER_PATH), "--vault", str(vault), "--check-astep"]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(res.returncode, 1)
            self.assertIn("C8", res.stdout)
            self.assertIn("Non-chronological prev detected", res.stdout)
            self.assertIn("Vertical hierarchy in related detected", res.stdout)


class TestV3FallbackWhenSSOTAbsent(unittest.TestCase):
    """Tests for fallback when exact My-Wiki Rules.md is absent."""

    def test_fallback_to_glob_or_default_when_ssot_renamed(self):
        """Verify constitution_loader falls back to glob pattern when My-Wiki Rules.md is renamed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "MockVault"
            vault.mkdir(parents=True)
            # Renamed to My-Wiki Rules_v3.2.md
            (vault / "My-Wiki Rules_v3.2.md").write_text(
                """---
origin: wiki
type: hub
domain: [equity]
up: []
status: evergreen
created: 2026-04-12
updated: 2026-10-30
---
# My-Wiki 지식 관리 헌법 (v3.2)
""",
                encoding="utf-8",
            )
            config = constitution_loader.load_constitution(vault)
            self.assertEqual(config["version"], "v3.2")
            self.assertTrue(len(config["sha256"]) == 64)


if __name__ == "__main__":
    unittest.main()
