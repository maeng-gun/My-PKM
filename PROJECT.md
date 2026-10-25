# Project: My-PKM

## Architecture
My-PKM is a Personal Knowledge Management (PKM) agent hub and automated data/knowledge engineering system. It integrates an Obsidian vault (`My-Wiki`) hosted on Google Drive, an external raw document processing pipeline (`Inbox_Raw` -> `Archive_Sources`), Korean public/office document parsing engine (`kordoc`), and existing Macro/Portfolio TAA quant scoring and Valley AI news scraping capabilities.

### System Boundaries & Data Flow
1. **Workspace Boundary**:
   - Primary Repository Root: `c:\Users\maeng-gun\Desktop\python\My_PKM` (Git tracked, `.venv` Python 3.12).
   - Antigravity Workspaces Junctions: `input_staging`, `scratch`, `archive`, `secrets`, `AGY_Artifacts` -> `G:\내 드라이브\Antigravity_Workspaces\My-PKM\...`.
   - PKM Root Junctions:
     - `./My-Wiki` -> `G:\내 드라이브\My-Wiki` (Obsidian Vault, `.md` files only).
     - `./Inbox_Raw` -> `G:\내 드라이브\Inbox_Raw` (Input queue for external raw binaries).
     - `./Archive_Sources` -> `G:\내 드라이브\Archive_Sources` (Inbox Zero archive for processed raw binaries).
2. **Hybrid Obsidian Control Protocol**:
   - Real-time active note inspection, surgical heading/block patching, viewport focus, and indexing use the `obsidian` Local REST API MCP server.
   - Batch parsing, background ETL, linting, or offline execution fallback to direct local filesystem I/O via `./My-Wiki` directory junction.
3. **ETL Data Pipeline**:
   - Raw binary placed in `./Inbox_Raw/` (HWP, HWPX, PDF, XLSX, DOCX, PPTX).
   - `ingest_sources.py` invokes `kordoc` (Python SDK `KordocClient` resident worker, or Node CLI fallback) with `--table-format gfm`.
   - 2-tier YAML frontmatter attached conforming to 7 core attributes (clean empty arrays `[]`, no ghost links `"[[]]"`).
   - Output `.md` written to `./My-Wiki/300. Sources/{subfolder}/`.
   - Raw binary archived to `./Archive_Sources/{subfolder}/` maintaining Inbox Zero.
4. **Vault Constitutional Governance**:
   - `vault_linter.py` validates compliance across 5 core rules (7 core attributes, no ghost links, no orphan notes except Level 1 hubs, folder-origin MECE alignment, no heavy binaries).
   - Human sovereignty: `100. Concepts` and `500. etc` are human-only areas where AI unprompted write/overwrite is strictly prohibited.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Rebrand Project Metadata | Update `pyproject.toml` (`name = "my-pkm"`, `requires-python = ">=3.11"`, `kordoc>=0.2.0`), `.gdrive_config.json` (`project_name: "My-PKM"`), `README.md` | M1 | survey |
| 2 | Reconnect Workspace Junctions | Re-point broken junctions (`input_staging`, `scratch`, `archive`, `secrets`, `AGY_Artifacts`) to `G:\내 드라이브\Antigravity_Workspaces\My-PKM` | M1 | survey |
| 3 | Update Git Remote & Rename Script | Update git remote origin to `https://github.com/maeng-gun/My-PKM.git` and supply `scripts/finalize_rename.ps1` | M1 | survey |
| 4 | Fix Hardcoded Skill Paths | Replace hardcoded `macro_analyzer` paths in `macro_portfolio_analysis/SKILL.md` with relative links | M1 | survey |
| 5 | Connect PKM Root Junctions | Mount `./My-Wiki`, `./Inbox_Raw`, `./Archive_Sources` as Windows junctions to `G:\내 드라이브\...` | M2 | survey |
| 6 | Gitignore PKM Junctions | Exclude `/My-Wiki/`, `/Inbox_Raw/`, `/Archive_Sources/`, and `/.agents/teamwork/` from Git tracking | M2 | survey |
| 7 | Expand AGENTS.md Persona | Integrate PKM Master Architect persona, SSOT dynamic pre-flight, human write sovereignty, binary isolation, hybrid MCP protocol, and retain macro/TAA/valley_ai | M3 | survey |
| 8 | Create pkm_manager Skill | Define `.agents/skills/pkm_manager/SKILL.md` with workflows for dynamic SSOT, ETL ingestion, surgical patching, and vault linting | M3 | survey |
| 9 | Rebuild Python 3.12 .venv | Create `.venv` with host Python 3.12.10, install dependencies and `kordoc>=0.2.0` | M4 | survey |
| 10 | Install Global kordoc CLI | Install `npm install -g kordoc` on Node.js 24 and verify `kordoc --version` | M4 | survey |
| 11 | Implement ingest_sources.py | Build ETL CLI supporting HWP/HWPX/PDF/XLSX/DOCX, GFM tables, 2-tier frontmatter, subfolder routing, and archival | M4 | survey |
| 12 | Implement vault_linter.py | Build linter CLI evaluating 5 constitutional checks (7 core attributes, ghost links, orphans, origin-folder match, binary infiltration) | M4 | survey |
| 13 | E2E Acceptance & Test Suite | 100% pass of E2E test suite (Tiers 1-4) across junctions, CLI tools, linting, and acceptance criteria | M5 | survey |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Workspace Rebranding & GDrive Migration (R1) | Update `pyproject.toml`, `.gdrive_config.json`, `README.md`, fix `SKILL.md` hardcoded paths, reconnect 5 workspace junctions, update git remote URL, create `scripts/finalize_rename.ps1` | none | DONE |
| 2 | GDrive Root 3 Junctions Connection (R2) | Create directory junctions for `My-Wiki`, `Inbox_Raw`, `Archive_Sources`; update `.gitignore` and verify `git status` clean | M1 | DONE |
| 3 | PKM Master Architect & Hybrid Directives (R3) | Update `AGENTS.md` and create `.agents/skills/pkm_manager/SKILL.md` with dynamic SSOT rules, human sovereignty, binary isolation, and hybrid protocol | none | DONE |
| 4 | Kordoc Engine Setup & CLI Implementation (R4) | Rebuild Python 3.12 `.venv`, install `kordoc` npm & Python SDK, implement `ingest_sources.py` and `vault_linter.py` with comprehensive unit tests | M1, M2, M3 | DONE |
| 5 | E2E Testing & Acceptance Verification | Execute full opaque-box E2E test suite (Tiers 1-4) and Tier 5 adversarial hardening | M1, M2, M3, M4 | DONE |

---

## Interface Contracts

### 1. `ingest_sources.py` CLI Contract
- **Invocation**: `python .agents/skills/pkm_manager/scripts/ingest_sources.py [OPTIONS]`
- **Parameters**:
  - `--file <path>`: Path to specific input file (optional; scans `--inbox` if omitted)
  - `--inbox <path>`: Input folder (default: `./Inbox_Raw`)
  - `--vault <path>`: Vault folder (default: `./My-Wiki`)
  - `--archive <path>`: Archive folder (default: `./Archive_Sources`)
  - `--subfolder <name>`: Target subfolder (`310. Reports_Papers`, `320. Books_Lectures`, `330. Clippings_News`, `340. Work_Docs`)
  - `--domain <codes>`: 1-2 comma-separated domain codes from `[theory, macro, equity, portfolio, work, ai-pkm, education]`
  - `--up <wikilink>`: Parent wikilink (e.g. `"[[02_매크로 분석]]"`). If empty, generates `[]`
  - `--source-type <type>`: `report`, `paper`, `book`, `clipping`, `work_doc`, `presentation`
  - `--table-format <gfm|html>`: Table output format (default: `gfm`)
  - `--ocr`: Boolean flag to trigger PP-OCRv5 Korean OCR
  - `--dry-run`: Preview without file writes or moves
- **Output Artifacts**:
  - Target note: `./My-Wiki/300. Sources/{subfolder}/{basename}.md`
  - Archived source: `./Archive_Sources/{subfolder}/{basename}.{ext}`
- **Exit Code**: `0` on success, `1` on error.

### 2. `vault_linter.py` CLI Contract
- **Invocation**: `python .agents/skills/pkm_manager/scripts/vault_linter.py [OPTIONS]`
- **Parameters**:
  - `--vault <path>`: Vault path (default: `./My-Wiki`)
  - `--fix`: Automatically fix safe violations (replace `"[[]]"` with `[]` in YAML)
  - `--format <text|json|markdown>`: Output format (default: `text`)
  - `--exit-zero`: Force exit code 0 even if violations found
  - `--include-inbox`: Include `000. Inbox` in check (default: excluded)
- **Output Report**:
  - Summary counts: total scanned, pass, fail, errors by check code (C1-C5).
  - Per-file error list with line numbers and violation descriptions.
- **Exit Code**: `0` if 0 violations found; `1` if 1 or more violations found.

---

## Code Layout
```
c:\Users\maeng-gun\Desktop\python\My_PKM\
├── .agents/
│   ├── skills/
│   │   ├── macro_portfolio_analysis/    # Existing TAA quant skill (preserved)
│   │   ├── valley_ai_scrap/             # Existing Valley AI scraper (preserved)
│   │   └── pkm_manager/                 # New PKM Master Architect skill
│   │       ├── SKILL.md
│   │       └── scripts/
│   │           ├── ingest_sources.py    # kordoc ETL CLI
│   │           └── vault_linter.py      # Vault Constitution audit CLI
│   └── teamwork/                        # Teamwork coordination metadata
├── scripts/
│   └── finalize_rename.ps1              # Workspace post-IDE rename automation
├── tests/
│   ├── test_ingest_sources.py           # Unit & integration tests for ingest_sources
│   ├── test_vault_linter.py             # Unit tests for vault_linter
│   └── e2e/                             # Opaque-box E2E test suite (Tiers 1-4)
├── AGENTS.md                            # Unified multi-persona constitution
├── pyproject.toml                       # Project metadata & dependencies
├── .gdrive_config.json                  # Google Drive sync config
├── .gitignore                           # Git ignore rules
├── README.md                            # Project documentation
├── My-Wiki/                             # Junction -> G:\내 드라이브\My-Wiki
├── Inbox_Raw/                           # Junction -> G:\내 드라이브\Inbox_Raw
├── Archive_Sources/                     # Junction -> G:\내 드라이브\Archive_Sources
├── input_staging/                       # Junction -> G:\내 드라이브\Antigravity_Workspaces\My-PKM\input_staging
├── scratch/                             # Junction -> G:\내 드라이브\Antigravity_Workspaces\My-PKM\scratch
├── archive/                             # Junction -> G:\내 드라이브\Antigravity_Workspaces\My-PKM\archive
├── secrets/                             # Junction -> G:\내 드라이브\Antigravity_Workspaces\My-PKM\secrets
└── AGY_Artifacts/                       # Junction -> G:\내 드라이브\Antigravity_Workspaces\My-PKM\AGY_Artifacts
```
