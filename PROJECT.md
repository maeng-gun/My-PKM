# Project: My-PKM — Dedicated PKM Parsing Skill (pkm_parse) Separation & Build

## Architecture
My-PKM is a Personal Knowledge Management (PKM) agent hub and automated knowledge engineering system. It integrates an Obsidian vault (`My-Wiki`) hosted on Google Drive, an external raw document processing pipeline (`Inbox_Raw` -> `000. Inbox` -> `Archive_Sources`), Korean public/office document parsing engine (`kordoc`), and existing Macro/Portfolio TAA quant scoring and Valley AI news scraping capabilities.

This project separates and builds a dedicated, standalone PKM Parsing skill (`.agents/skills/pkm_parse`) that converts raw binary and text documents (`PDF`, `HWPX`, `HWP`, `XLSX`, `DOCX`, `PPTX`, `TXT`, `MD`) in `Inbox_Raw/` into Obsidian markdown notes (`.md`) with embedded image extraction and PKM/Obsidian Constitution v2.1-compliant 2-tier YAML frontmatter, places the resulting notes into `My-Wiki/000. Inbox/` (flat staging buffer), and archives the original binaries into `Archive_Sources/` (Inbox Zero).

### System Boundaries & Governance Separation
1. **Workspace Boundary**:
   - Primary Repository Root: `C:\Users\infomax\Documents\My-PKM` (Git tracked, `.venv` Python 3.12).
   - Antigravity Workspaces Junctions: `input_staging`, `scratch`, `archive`, `secrets`, `AGY_Artifacts` -> `G:\내 드라이브\Antigravity_Workspaces\My-PKM\...`.
   - PKM Root Junctions:
     - `./My-Wiki` -> `G:\내 드라이브\My-Wiki` (Obsidian Vault, `.md` files only).
     - `./Inbox_Raw` -> `G:\내 드라이브\Inbox_Raw` (Input queue for external raw binaries).
     - `./Archive_Sources` -> `G:\내 드라이브\Archive_Sources` (Inbox Zero archive for processed raw binaries).
2. **Governance Separation**:
   - `pkm_parse` owns raw binary document ingestion (`kordoc`), image extraction to `900. config/910. Attached/<doc_stem>/`, image embed link rewriting (`![[<doc_stem>/image_XXX.png]]`), Stage 1 deterministic frontmatter generation in `000. Inbox/`, binary archival to `Archive_Sources/` (Inbox Zero), and Stage 2 AI semantic enrichment protocol.
   - `pkm_manager` retains vault constitutional governance (`vault_linter.py`), dynamic SSOT verification, note triage from `000. Inbox` to permanent folders (`100. Concepts`, `200. AI_logs`, `300. Sources`), surgical note patching, and future Karpathy LLM Wiki periodic compilation (`400. Wiki`).
   - `ingest_sources.py` is maintained as a backward-compatible facade/script routing to `300. Sources/<subfolder>/` so legacy callers and existing test suites pass without regression.
3. **Data Flow & Pipeline**:

```
[Raw Binaries in Inbox_Raw/]
           │
           ▼
[parse_sources.py CLI (pkm_parse)]
     ├── Kordoc Parsing & Embedded Image Extraction
     │      └── Saved to: My-Wiki/900. config/910. Attached/<doc_stem>/image_XXX.png
     ├── Body Link Rewriting: ![[<doc_stem>/image_XXX.png]]
     ├── 2-Tier YAML Frontmatter (7 core + Clean Null + source attributes)
     ├── Note Placement: My-Wiki/000. Inbox/<stem>.md (flat structure)
     └── Archival: Archive_Sources/<subfolder>/<filename> (Inbox Zero)
           │
           ▼
[vault_linter.py --include-inbox (pkm_manager)]
     └── Validates 000. Inbox staging, 7 core attributes, clean null, binary isolation
```

4. **Vault Constitutional Governance & Safety**:
   - `vault_linter.py` validates compliance across 5 core rules (7 core attributes, no ghost links, no orphan notes except Level 1 hubs, folder-origin MECE alignment, no heavy binaries).
   - Human sovereignty: `100. Concepts` and `500. etc` are human-only areas where AI unprompted write/overwrite is strictly prohibited.
   - Vault binary isolation: heavy binaries (`.pdf`, `.hwpx`, `.xlsx`, etc.) are strictly prohibited from entering `./My-Wiki`.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Dedicated Skill Directory & SKILL.md | Standalone `.agents/skills/pkm_parse/SKILL.md` with `name: pkm-parse`, 2-stage hybrid parsing workflow, dynamic SSOT pre-flight rule | M2 | R1 |
| 2 | Governance Separation in AGENTS.md | Update AGENTS.md Persona 1 & Sub-skill Orchestration Map to add `pkm-parse` and divide responsibilities | M2 | R1 |
| 3 | Documentation & Skill Updates | Update PROJECT.md and `.agents/skills/pkm_manager/SKILL.md` reflecting new governance and CLI contracts | M2 | R1 |
| 4 | Backward Compatibility for ingest_sources.py | Preserve `ingest_sources.py` in `pkm_manager` routing to `300. Sources/` with 0 regression across existing 141 tests | M2 | R1 |
| 5 | parse_sources.py CLI Flags Interface | Support all 19 CLI flags (`--file`, `--inbox`, `--vault`, `--archive`, `--subfolder`, `--domain`, `--up`, `--source-type`, `--author`, `--org`, `--published`, `--ref-date`, `--aliases`, `--summary`, `--table-format`, `--ocr`, `--dry-run`, `--force`, `--verbose`) | M1 | R3 |
| 6 | Kordoc Dual-Engine Document Parsing | Parse PDF, HWPX, HWP, XLSX, DOCX using `kordoc.KordocClient` SDK with Node CLI fallback | M1 | R2 |
| 7 | Embedded Image Extraction | Extract images from `res.images` or CLI output to `./My-Wiki/900. config/910. Attached/<doc_stem>/image_XXX.png` | M1 | R2 |
| 8 | Obsidian Native Wikilink Embed Rewriting | Rewrite markdown image references `![image](...)` and `<img>` tags to `![[<doc_stem>/image_XXX.png]]` | M1 | R2 |
| 9 | Temporary Directory Atomic Cleanup | Use `tempfile.TemporaryDirectory` context manager to guarantee zero orphaned temporary files/folders | M1 | R2 |
| 10 | 2-Tier YAML Frontmatter Generation | Strict 7 core attributes (`origin: source`, `type: source`, `domain`, `up`, `status: active`, `created`, `updated`) + sparse Tier 2 source attributes | M1 | R3 |
| 11 | Clean Null Rule Enforcement | Links arrays empty must format as `[]`, zero occurrences of `"[[]]"` | M1 | R3 |
| 12 | Flat Note Placement in 000. Inbox | Place output notes directly in `./My-Wiki/000. Inbox/<stem>.md` with no subdirectories | M1 | R3 |
| 13 | Raw Binary Archival (Inbox Zero) | Move source binaries from `Inbox_Raw/` to `Archive_Sources/` (or `Archive_Sources/<subfolder>/`) | M1 | R4 |
| 14 | Automatic source_url Population | Populate `source_url: Archive_Sources/<subfolder>/<filename>` in YAML frontmatter | M1 | R4 |
| 15 | Dry-Run Safety Mode | `--dry-run` flag previews actions without mutating disk or moving binaries | M1 | R3 |
| 16 | Missing File Error Code 1 | CLI exits 1 on missing input file | M1 | R3 |
| 17 | Batch Inbox Processing | Scan `--inbox` when `--file` is omitted | M1 | R3 |
| 18 | Vault Constitutional Linter Support | Verify `vault_linter.py --include-inbox` passes with 0 violations for structured notes in `000. Inbox/` | M2 | R4 |
| 19 | Human Write Sovereignty & Binary Isolation | Strictly preserve `100. Concepts` & `500. etc`, prevent heavy binaries in vault | M1, M2 | R4 |
| 20 | Dedicated Unit/Integration Test Suite | `tests/test_parse_sources.py` covering all 11 unit/integration test cases | E2E-TEST | R1-R4 |
| 21 | E2E Test Suite Tier 1 & Tier 4 Integration | Integrate `TestTier1F9ParseSourcesCLI` and Scenario S05 into `tests/e2e/run_e2e_suite.py` | E2E-TEST | R1-R4 |
| 22 | Final E2E 100% Pass & Adversarial Hardening | Pass 100% of all unit and E2E tests, followed by Tier 5 adversarial hardening | M3 | R1-R4 |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E-TEST | E2E Testing Suite Track | Design E2E test infra `TEST_INFRA.md`, implement `tests/test_parse_sources.py`, add Tier 1 F9 and Tier 4 S05 in `tests/e2e/`, publish `TEST_READY.md` | none | DONE |
| 1 | Core Parsing CLI & Image Extraction Engine (M1) | Implement `parse_sources.py` with 19 CLI flags, kordoc parsing, image extraction to `910. Attached/<doc_stem>/`, wikilink embed rewriting, 2-tier YAML frontmatter with Clean Null, flat `000. Inbox/<stem>.md` placement, archival to `Archive_Sources/`, and `source_url` | none | DONE |
| 2 | Skill Definition, Governance & Backward Compatibility (M2) | Create `.agents/skills/pkm_parse/SKILL.md`, update `AGENTS.md`, `PROJECT.md`, `pkm_manager/SKILL.md`, ensure `ingest_sources.py` backward compatibility, verify `vault_linter.py --include-inbox` | M1 | IN_PROGRESS |
| 3 | Final Milestone: Full E2E Test Suite Pass & Adversarial Hardening (M3) | Phase 1: 100% pass of unit tests (`tests/test_parse_sources.py`) and E2E runner (`tests/e2e/run_e2e_suite.py`). Phase 2: Tier 5 adversarial coverage hardening | M1, M2, E2E-TEST | PLANNED |

---

## Interface Contracts

### 1. `parse_sources.py` CLI Contract
- **Executable**: `.agents/skills/pkm_parse/scripts/parse_sources.py`
- **Invocation**: `python .agents/skills/pkm_parse/scripts/parse_sources.py [OPTIONS]`
- **Required CLI Options**:
  - `--file <path>`: Specific file to parse (if omitted, processes all in `--inbox`). Returns exit code 1 if file missing.
  - `--inbox <path>`: Input folder (default: `./Inbox_Raw`)
  - `--vault <path>`: Obsidian vault root (default: `./My-Wiki`)
  - `--archive <path>`: Archive root (default: `./Archive_Sources`)
  - `--subfolder <name>`: Archive subfolder (e.g. `310. Reports_Papers`). Does not affect flat `000. Inbox/` placement.
  - `--domain <codes>`: 1-2 comma-separated domain codes from 7 standard domains (default: `macro`)
  - `--up <wikilink>`: 1-hop parent wikilink (e.g. `"[[02_매크로 분석]]"`). Sanitized to `[]` if omitted or ghost `[[]]`.
  - `--source-type <type>`: `report`, `paper`, `book`, `clipping`, `work_doc`, `presentation`, `news` (default: `report`)
  - `--author <name>`: Author entity string or wikilink
  - `--org <name>`: Organization entity string or wikilink
  - `--published <date>`: Publication date (`YYYY-MM` or `YYYY-MM-DD`)
  - `--ref-date <date>`: Reference date (default: system date `YYYY-MM-DD`)
  - `--aliases <titles>`: Comma-separated alias titles
  - `--summary <text>`: Executive summary string
  - `--table-format <gfm|html>`: Table format (default: `gfm`)
  - `--ocr`: Enable PP-OCRv5 Korean OCR in kordoc
  - `--dry-run`: Preview without file writes, image extractions, or moves
  - `--force`: Overwrite existing target note or archive binary
  - `--verbose`: Detailed execution logs
- **Output Artifacts**:
  - Markdown note: `./My-Wiki/000. Inbox/<stem>.md` (flat structure)
  - Embedded images: `./My-Wiki/900. config/910. Attached/<doc_stem>/image_XXX.png`
  - Body links: `![[<doc_stem>/image_XXX.png]]`
  - Archived binary: `./Archive_Sources/<subfolder>/<filename>` (or `./Archive_Sources/<filename>`)
  - Frontmatter `source_url`: `Archive_Sources/<subfolder>/<filename>` (forward slashes)
- **Exit Code**: `0` on success, `1` on error.

### 2. Backward Compatibility Contract: `ingest_sources.py`
- **Executable**: `.agents/skills/pkm_manager/scripts/ingest_sources.py`
- Must retain its existing CLI interface and behavior: writing notes to `./My-Wiki/300. Sources/<subfolder>/<stem>.md`.
- All existing 141 tests in `tests/` must pass without modification.

### 3. Vault Linter Contract: `vault_linter.py`
- **Invocation**: `python .agents/skills/pkm_manager/scripts/vault_linter.py --vault ./My-Wiki --include-inbox`
- Notes in `000. Inbox/` are validated for 7 core attributes, clean null `up: []`, and allowed origins (`source`, `ai`, `human`, `wiki`) without false C4 mismatch errors.
- Exit code 0 on compliant vault notes.

---

## Code Layout
```
C:\Users\infomax\Documents\My-PKM\
├── .agents/
│   ├── skills/
│   │   ├── pkm_parse/                       # NEW dedicated parsing skill
│   │   │   ├── SKILL.md                     # Skill definition & 2-stage workflow
│   │   │   └── scripts/
│   │   │       └── parse_sources.py         # 19-flag CLI & kordoc image extractor
│   │   ├── pkm_manager/                     # Constitutional governance & wiki compiler
│   │   │   ├── SKILL.md                     # Updated governance workflows
│   │   │   └── scripts/
│   │   │       ├── vault_linter.py          # 5-check constitutional auditor
│   │   │       └── ingest_sources.py        # Backward-compatible facade
│   │   ├── macro_portfolio_analysis/        # Existing TAA quant skill (preserved)
│   │   └── valley_ai_scrap/                 # Existing Valley AI scraper (preserved)
│   └── teamwork/                            # Orchestration metadata
├── scripts/
│   └── finalize_rename.ps1                  # Workspace post-IDE rename automation
├── tests/
│   ├── test_parse_sources.py                # NEW unit & integration test suite (11 tests)
│   ├── test_ingest_sources.py               # Existing unit tests (preserved)
│   ├── test_vault_linter.py                 # Existing unit tests (preserved)
│   └── e2e/
│       ├── run_e2e_suite.py                 # Full E2E runner (Tiers 1-4)
│       ├── test_tier1_features.py           # Includes TestTier1F9ParseSourcesCLI
│       └── test_tier4_scenarios.py          # Includes Scenario S05
├── AGENTS.md                                # Updated unified multi-persona constitution
├── PROJECT.md                               # Living system architecture & contracts
├── pyproject.toml                           # Project metadata & dependencies
├── .gdrive_config.json                      # Google Drive sync config
├── .gitignore                               # Git ignore rules
├── README.md                                # Project documentation
├── My-Wiki/                                 # Junction -> G:\내 드라이브\My-Wiki
│   ├── 000. Inbox/                          # Staging buffer for newly parsed notes
│   ├── 300. Sources/                        # Permanent ground-truth notes
│   └── 900. config/
│       └── 910. Attached/                   # Image attachments (<doc_stem>/image_XXX.png)
├── Inbox_Raw/                               # Raw binary input queue
└── Archive_Sources/                         # Inbox Zero archival store
```
