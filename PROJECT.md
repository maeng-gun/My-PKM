# Project: Valley AI Global Macro Advanced Lecture Scraping, PKM Parsing & Archiving Pipeline

## Architecture
This project establishes an automated, production-grade pipeline that:
1. Dynamically traverses the Valley AI Global Macro Advanced training course (`https://www.valley.town/training/global-macro-advanced`) using Playwright with persistent session authentication (`auth_state.json` with `.env` fallback).
2. Filters and downloads all lecture slide PDF attachments for 2회차 1강 through 9회차 3강 (24 target chapters) directly into `G:\내 드라이브\Inbox_temp\`, gracefully skipping lectures without attachments (e.g., 1회차 2강, 3강).
3. Executes `/pkm-parse` (`parse_sources.py` using `kordoc`) across all 25 lecture materials (including the pre-downloaded 1회차 1강) in pure text and GFM table mode (zero images extracted to optimize sync traffic and vault capacity), placing the resulting markdown files in `G:\내 드라이브\Inbox_temp\`.
4. Atomically moves the source PDFs from `G:\내 드라이브\Inbox_temp\` to `Archive_Sources/` using `os.replace` on volume `G:` with sharing-lock retry loops, achieving complete Inbox Zero in `Inbox_temp\`.
5. Enforces 3-tier verification gateways (PDF pre-parse validation, Markdown post-parse validation, and Inbox Zero cleanup verification).

### Data Flow Diagram
```
[Valley AI Course (2회차 1강 ~ 9회차 3강)]
               │
               ▼ (Playwright Traversal & Download)
[G:\내 드라이브\Inbox_temp\*.pdf] (24 new + 1 pre-existing = 25 PDFs)
               │
               ▼ (kordoc parse_sources.py: pure text + GFM tables, 0 images)
[G:\내 드라이브\Inbox_temp\*.md] (25 markdown notes with 7 core attributes)
               │
               ▼ (Atomic os.replace with exponential backoff)
[Archive_Sources/ (or Archive_Sources/320. Lectures/)] (25 source PDFs)
               │
               ▼ (Gateway 3: verify_inbox_zero)
[G:\내 드라이브\Inbox_temp\ contains only *.md, zero residual *.pdf]
```

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Dynamic Course Curriculum Traversal | Parse RSC metadata / curriculum structure from course landing page to enumerate all 9 parts and 27 chapters | M1 | Survey 1, R1 |
| 2 | Slide Attachment Filtering | Detect lectures with `lectureType == "material"` and title `'강의자료'` across 2회차 1강 ~ 9회차 3강 (24 chapters) | M1 | Survey 1, R1 |
| 3 | Graceful Attachment-Less Skipping | Skip chapters without attachments (e.g., 1회차 2강, 3강) safely without errors or unhandled exceptions | M1 | Survey 1, R1 |
| 4 | Standardized PDF Filename Formatting | Name downloaded files deterministically as `{partKey}_{chapterKey}_{clean_title}.pdf` (e.g., `2회차_1강_60년대 통사.pdf`) | M1 | Survey 1, R1 |
| 5 | Session Persistence & Auto-Relogin | Reuse `auth_state.json` with automatic fallback to `.env` credentials if session expires | M1 | Survey 1, R4 |
| 6 | Robust PDF Download Execution | Download PDFs via Playwright `expect_download` into `G:\내 드라이브\Inbox_temp\` with retry logic and rate jitter | M1 | Survey 1, R1 |
| 7 | PDF Binary Validation Gateway | Verify downloaded PDFs: size > 1KB, magic header `b'%PDF'`, tail `b'%%EOF'`, regex naming pattern | M1, M3 | Survey 3, Acceptance Criteria |
| 8 | Kordoc Pure Text & GFM Table Parsing | Parse lecture PDFs using `parse_sources.py` with `table_format='gfm'` and `--no-images` (0 images extracted) | M2 | Survey 2, R2 |
| 9 | Output Placement in Inbox_temp | Ensure all generated `.md` notes reside in `G:\내 드라이브\Inbox_temp\` to fulfill user requirement R2 | M2 | Survey 2, Survey 3, R2 |
| 10 | DriveFS Google Drive URL Resolution | Resolve cloud `source_url` via DriveFS SQLite metadata reader for YAML frontmatter | M2 | Survey 2, Survey 3, R2 |
| 11 | Markdown Post-Parse Validation Gateway | Verify generated markdown: size >= 200B, 7 core attributes, Clean Null `up: []`, non-empty text/tables | M2, M3 | Survey 3, Acceptance Criteria |
| 12 | Atomic Archiving to Archive_Sources | Move source PDFs from `Inbox_temp\` to `Archive_Sources\` atomically via `os.replace` on drive G: with retry loop | M3 | Survey 3, R3 |
| 13 | Inbox Zero Gateway Verification | Verify `glob("*.pdf") == []` in `G:\내 드라이브\Inbox_temp\` and 1:1 match with archived PDFs | M3 | Survey 3, Acceptance Criteria |
| 14 | Unified Pipeline Orchestrator CLI | Master CLI runner script that executes download, parse, output placement, archiving, and validation in sequence | M3 | All Surveys, R1-R4 |
| 15 | Opaque-Box E2E Test Suite | Comprehensive test suite (Tiers 1-4) validating curriculum parsing, skip logic, PDF validation, MD validation, and Inbox Zero | E2E-TEST | R1-R4 |
| 16 | Final Full Pipeline Run & Acceptance Verification | Pass 100% of E2E tests, execute live pipeline, verify all 25 lecture materials processed and archived | M4 | Acceptance Criteria |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E-TEST | E2E Testing Suite Track | Design E2E test infra `TEST_INFRA.md`, implement test harness in `tests/e2e/test_macro_pipeline_e2e.py` covering Tiers 1-4, publish `TEST_READY.md` | none | DONE |
| 1 | Dynamic Lecture Traversal & PDF Download Engine (M1) | Upgrade `download_macro_lecture.py` with dynamic curriculum traversal, filtering for 2회차 1강 ~ 9회차 3강, deterministic `{회차}_{강}_{제목}.pdf` naming, graceful skipping, and PDF validation | none | DONE |
| 2 | PKM Parsing & Markdown Staging Pipeline (M2) | Implement batch/per-file parsing loop with `parse_sources.py` (no images, GFM tables), place notes in `G:\내 드라이브\Inbox_temp\`, validate YAML frontmatter & markdown content | none | PLANNED |
| 3 | Inbox Zero Archiving & Production Pipeline CLI (M3) | Implement atomic archiving with retry backoff, Inbox Zero verification, and master pipeline runner `run_macro_lecture_pipeline.py` integrating M1, M2, and M3 | M1, M2 | PLANNED |
| 4 | Final Milestone: Full Pipeline Execution & E2E Acceptance Pass (M4) | Pass 100% of E2E test suite (Tiers 1-4), execute full live pipeline across all 25 lectures, verify all acceptance criteria and Inbox Zero | M1, M2, M3, E2E-TEST | PLANNED |

---

## Interface Contracts

### 1. `download_macro_lecture.py` CLI Contract
- **Executable**: `.agents/skills/valley_ai_scrap/scripts/download_macro_lecture.py`
- **CLI Options**:
  - `--start-round <int>`: Start round number (default: 2)
  - `--end-round <int>`: End round number (default: 9)
  - `--start-lecture <int>`: Start lecture number (default: 1)
  - `--end-lecture <int>`: End lecture number (default: 3)
  - `--target-dir <path>`: Output directory (default: `G:\내 드라이브\Inbox_temp`)
  - `--session-file <path>`: Auth session file (default: `auth_state.json`)
  - `--headless`: Run browser in headless mode (default: True)
  - `--dry-run`: Enumerate target lectures and attachment links without downloading
- **Naming Pattern**: `{round_num}회차_{lecture_num}강_{clean_title}.pdf`
- **Exit Code**: `0` on success, `1` on unhandled failure.

### 2. `run_macro_lecture_pipeline.py` Master CLI Contract
- **Executable**: `.agents/skills/valley_ai_scrap/scripts/run_macro_lecture_pipeline.py` (or project runner)
- **Invocation**: `python .agents/skills/valley_ai_scrap/scripts/run_macro_lecture_pipeline.py [OPTIONS]`
- **CLI Options**:
  - `--download`: Run step 1 (download 2회차 1강 ~ 9회차 3강)
  - `--parse`: Run step 2 (kordoc parse for all PDFs in `Inbox_temp`, including 1회차 1강)
  - `--archive`: Run step 3 (atomic move to `Archive_Sources/` and Inbox Zero verify)
  - `--all`: Run full sequence (download -> parse -> archive -> verify)
  - `--inbox-temp <path>`: Default `G:\내 드라이브\Inbox_temp`
  - `--archive-dir <path>`: Default `G:\내 드라이브\Archive_Sources` (or `Archive_Sources/`)
  - `--vault <path>`: Default `./My-Wiki`
  - `--dry-run`: Preview steps without downloading or moving files
- **Exit Code**: `0` on success, `1` on error.

---

## Code Layout
```
c:\Users\maeng-gun\Desktop\python\My-PKM\
├── .agents/
│   ├── skills/
│   │   ├── valley_ai_scrap/
│   │   │   └── scripts/
│   │   │       ├── download_macro_lecture.py      # Upgraded dynamic downloader (M1)
│   │   │       └── run_macro_lecture_pipeline.py  # Master pipeline CLI (M3)
│   │   └── pkm_parse/
│   │       └── scripts/
│   │           └── parse_sources.py               # kordoc parser (M2)
│   └── teamwork/                                  # Orchestration metadata & reports
├── tests/
│   └── e2e/
│       ├── test_macro_pipeline_e2e.py             # E2E test suite (Tiers 1-4)
│       └── run_e2e_suite.py                       # E2E runner
├── auth_state.json                                # Valley AI session cookies
├── .env                                           # Credentials fallback
├── PROJECT.md                                     # System architecture & milestones
├── TEST_INFRA.md                                  # E2E Test infrastructure specification
├── TEST_READY.md                                  # E2E test suite ready signal
├── Archive_Sources/                               # Junction -> G:\내 드라이브\Archive_Sources
└── G:\내 드라이브\
    ├── Inbox_temp/                                # Staging dir for downloaded PDFs and final MD notes
    └── Archive_Sources/                           # Inbox Zero destination for source PDFs
```
