# Test Infrastructure: My-PKM

## 1. Overview & Testing Philosophy

This document specifies the end-to-end (E2E) testing infrastructure, methodology, execution commands, and test suites for the **My-PKM** project.
The testing framework enforces strict, requirement-driven, opaque-box (black-box) validation across all components, directory junctions, agent personas, local skills, and CLI tools (`parse_sources.py`, `ingest_sources.py`, `vault_linter.py`) in compliance with the **PKM Constitution v2.1**, **AGENTS.md**, and **PROJECT.md**.

### Testing Principles
1. **Opaque-Box Independence**: Tests interact with system components strictly through public CLI interfaces, filesystem artifacts, and documented API contracts. No private internals or mock shortcuts are used to fabricate passing results.
2. **Deterministic Output Derivation**: Expected outputs for YAML frontmatters, Clean Null arrays (`[]`), extracted images, and exit codes are derived directly from authoritative requirements in `PROJECT.md` and constitutional rules in `400. Wiki/옵시디언 메모간 링크 연결 규칙 설계.md`.
3. **Strict Isolation & Idempotence**: All tests that perform file system mutations execute inside isolated temporary directories (`tempfile.TemporaryDirectory()`). Tests never mutate, pollute, or delete data in the live vault (`./My-Wiki`) or Google Drive junctions.
4. **Zero-Regression Backward Compatibility**: Legacy pipelines and test suites (e.g., `ingest_sources.py` routing to `300. Sources/`) are preserved and verified alongside new capabilities (`parse_sources.py` routing to `000. Inbox/`).
5. **Progressive Testability (TDD)**: Tests define explicit, objective failure criteria for pending features (red baseline), enabling implementing agents to verify green transitions deterministically.

---

## 2. 4-Tier Test Architecture

The My-PKM test suite implements a hierarchical 4-tier verification architecture:

| Tier | Name | Target Scope | Methodology & Expected Output Source |
|---|---|---|---|
| **Tier 1** | **Feature Coverage** | F1 ~ F9 in isolation (>= 5 test cases per feature) | Verifies individual project artifacts, junction configurations, persona directives, skill metadata, kordoc availability, and CLI flag interfaces against explicit requirements in `PROJECT.md` and `ORIGINAL_REQUEST.md`. |
| **Tier 2** | **Boundary & Corner Cases** | Edge cases & constraints | Tests strict boundaries: ghost link prevention (`[]` vs `"[[]]"`), Level 1 Master Hub orphan exemption, excluded folder skipping (`000. Inbox`, `900. config`, `Notion`), domain code validation (1~2 standard codes only), staging buffer multi-origin support, and heavy binary isolation. |
| **Tier 3** | **Cross-Feature Combinations** | Multi-system workflows & junctions | Validates inter-module data flow: Ingestion ➔ Vault Note Creation ➔ Vault Linter Audit; local junction traversal to Google Drive; and linter auto-fix repair loops. |
| **Tier 4** | **Real-World Application Scenarios** | Full lifecycle simulations | End-to-end simulations of actual knowledge engineering pipelines: legacy source ingestion, unanchored source clean null, fault-tolerant failure cascading, multi-category batch routing, and dedicated `pkm_parse` document conversion with embedded image extraction and linter validation. |

---

## 3. Dedicated Unit & Integration Test Architecture

In addition to the 4-tier E2E test runner, dedicated unit and integration test modules provide granular test coverage:

```
c:\Users\infomax\Documents\My-PKM\
├── tests/
│   ├── test_parse_sources.py            # Dedicated unit & integration tests for pkm_parse CLI (11 tests)
│   ├── test_ingest_sources.py           # Backward compatibility tests for legacy ingest CLI (10 tests)
│   ├── test_vault_linter.py             # Unit tests for 5 constitutional checks C1-C5 (16 tests)
│   ├── test_adversarial_m5.py           # Adversarial stress tests on frontmatter & linter (12 tests)
│   ├── test_adversarial_m5_boundary.py  # Extreme boundary and fuzz tests (11 tests)
│   ├── test_m4_adversarial_challenger.py# Challenging edge cases and malformed inputs (9 tests)
│   └── e2e/
│       ├── test_tier1_features.py       # Tier 1: F1 - F9 isolated feature coverage (54 tests)
│       ├── test_tier2_boundaries.py     # Tier 2: Constitutional boundary & corner cases (10 tests)
│       ├── test_tier3_combinations.py   # Tier 3: Cross-feature pipelines & junction traversal (5 tests)
│       ├── test_tier4_scenarios.py      # Tier 4: Real-world scenarios S01 - S05 (5 tests)
│       └── run_e2e_suite.py             # Standalone test runner with Tier breakdown & CLI flags
```

### 3.1 `tests/test_parse_sources.py` (11 Unit/Integration Tests)
Dedicated test suite verifying the standalone `parse_sources.py` script:
1. `test_cli_help_lists_all_19_flags`: Asserts exit code 0 and presence of all 19 CLI options.
2. `test_clean_null_when_up_omitted`: Verifies `up: []` without ghost links when `--up` is omitted.
3. `test_clean_null_when_ghost_link_passed`: Verifies ghost link variants (`"[[]]"`, `"[]"`) sanitize cleanly to `up: []`.
4. `test_flat_note_placement_in_000_inbox`: Asserts target note is placed flat in `000. Inbox/<stem>.md` without subdirectories even when `--subfolder` is specified.
5. `test_seven_core_and_extended_frontmatter_attributes`: Verifies 7 core attributes + extended attributes (`source_type`, `author`, `org`, `published`, `ref_date`, `aliases`, `summary`, `source_url`).
6. `test_inbox_zero_movement_to_archive`: Verifies raw file is removed from `Inbox_Raw/` and stored in `Archive_Sources/` (Inbox Zero).
7. `test_source_url_relative_path_format`: Asserts `source_url` uses forward slashes (`Archive_Sources/...`) across all platforms.
8. `test_image_extraction_and_wikilink_embed_rewriting`: Tests extraction of embedded images to `900. config/910. Attached/<doc_stem>/image_XXX.png` and body link rewriting to `![[<doc_stem>/image_XXX.png]]`.
9. `test_dry_run_leaves_directories_and_files_untouched`: Verifies `--dry-run` previews conversion without mutating disk or moving binaries.
10. `test_missing_input_file_returns_error_code_1`: Verifies CLI returns exit code 1 when target file is missing.
11. `test_batch_inbox_processing_when_file_omitted`: Verifies batch scanning of `--inbox` when `--file` is omitted.

---

## 4. Feature Inventory & Traceability Mapping

| Feature ID | Feature Name | Minimum Tests | Specification Source | Target Test Files |
|---|---|---|---|---|
| **F1** | Project Metadata Files (`pyproject.toml`, `.gdrive_config.json`, `README.md`, `finalize_rename.ps1`) | 6 | `PROJECT.md` Feature 1, 3 | `tests/e2e/test_tier1_features.py` (`TestTier1F1ProjectMetadata`) |
| **F2** | 5 Workspace Directory Junctions (`input_staging`, `scratch`, `archive`, `secrets`, `AGY_Artifacts`) | 6 | `PROJECT.md` Feature 2 | `tests/e2e/test_tier1_features.py` (`TestTier1F2WorkspaceJunctions`) |
| **F3** | 3 PKM Root Junctions (`My-Wiki`, `Inbox_Raw`, `Archive_Sources`) & `.gitignore` exclusion | 6 | `PROJECT.md` Feature 5, 6 | `tests/e2e/test_tier1_features.py` (`TestTier1F3PKMRootJunctions`) |
| **F4** | `AGENTS.md` 4-Part Multi-Persona & SSOT Dynamic Pre-Flight Rules | 6 | `PROJECT.md` Feature 7; Spec Miner 2 §5.3 | `tests/e2e/test_tier1_features.py` (`TestTier1F4AgentsConstitution`) |
| **F5** | `.agents/skills/pkm_manager/SKILL.md` Frontmatter & 5 Workflows | 6 | `PROJECT.md` Feature 8; Spec Miner 2 §5.5 | `tests/e2e/test_tier1_features.py` (`TestTier1F5PKMManagerSkill`) |
| **F6** | `kordoc` Engine (Node 24+, CLI, Python SDK >= 0.2.0 compatibility) | 5 | `PROJECT.md` Feature 9, 10; Explorer 3 §1.1-1.3 | `tests/e2e/test_tier1_features.py` (`TestTier1F6KordocEngine`) |
| **F7** | `ingest_sources.py` Legacy CLI flags, 2-tier frontmatter, GFM tables, clean null `[]` | 6 | `PROJECT.md` §Interface Contracts; Explorer 3 §4.1 | `tests/e2e/test_tier1_features.py` (`TestTier1F7IngestSourcesCLI`), `tests/test_ingest_sources.py` |
| **F8** | `vault_linter.py` 5 Constitutional Checks (C1~C5), CLI flags, exit codes | 7 | `PROJECT.md` §Interface Contracts; Spec Miner 2 §5.6 | `tests/e2e/test_tier1_features.py` (`TestTier1F8VaultLinterCLI`), `tests/test_vault_linter.py` |
| **F9** | `parse_sources.py` Dedicated CLI (19 flags), Flat `000. Inbox/` Staging & Embedded Image Extraction | 6 | `ORIGINAL_REQUEST.md` R1-R4; `PROJECT.md` §Interface Contracts | `tests/e2e/test_tier1_features.py` (`TestTier1F9ParseSourcesCLI`), `tests/test_parse_sources.py` |
| **B01-B10**| Constitutional Boundaries (Clean Null, Linter Fix, Master Hub Exemption, Inboxes, Binary Isolation) | 10 | PKM Constitution v2.1; `ORIGINAL_REQUEST.md` R3, R4 | `tests/e2e/test_tier2_boundaries.py` |
| **C01-C05**| Cross-Feature Pipelines (Ingest-to-Linter, Junction Traversal, Auto-Repair, Polyhierarchy) | 5 | `PROJECT.md` Features 1-13 | `tests/e2e/test_tier3_combinations.py` |
| **S01** | Full Lifecycle Ingestion & Audit Simulation (`ingest_sources.py` -> `300. Sources/`) | 1 | `ORIGINAL_REQUEST.md` § Acceptance Criteria 3 | `tests/e2e/test_tier4_scenarios.py` (`test_s01`) |
| **S02** | Unanchored Source Note Clean Null (`up: []` without ghost links) | 1 | `ORIGINAL_REQUEST.md` R3 | `tests/e2e/test_tier4_scenarios.py` (`test_s02`) |
| **S03** | Error Resilience on Missing/Corrupt Inputs | 1 | `PROJECT.md` Error Behavior | `tests/e2e/test_tier4_scenarios.py` (`test_s03`) |
| **S04** | Multi-Subfolder Routing across 310, 320, 330, and 340 Source Categories | 1 | `PROJECT.md` § Interface Contracts | `tests/e2e/test_tier4_scenarios.py` (`test_s04`) |
| **S05** | Dedicated `pkm_parse` Full Lifecycle Ingestion, Image Extraction, Inbox Staging & Linter Audit | 1 | `ORIGINAL_REQUEST.md` R1-R4; `PROJECT.md` Feature 21 | `tests/e2e/test_tier4_scenarios.py` (`test_s05`) |

---

## 5. Test Execution Guide

### 5.1 Prerequisites
- **Python**: Python 3.12 (or >= 3.11 with `.venv`)
- **Node.js**: Node.js 24+ (`node -v >= 20.0.0`)
- **OS**: Windows 10/11 with PowerShell
- **Google Drive**: Mounted at `G:\내 드라이브` (for junction live tests)

### 5.2 Running the Full Test Suite
To run all tests (unit, integration, and E2E) across the repository:
```powershell
# Unittest discovery across all tests (152+ tests)
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

### 5.3 Running the Dedicated PKM Parsing Unit Test Suite
```powershell
.\.venv\Scripts\python.exe -m unittest tests/test_parse_sources.py -v
```

### 5.4 Running the Unified E2E Test Suite
The custom standalone runner executes tests across all 4 tiers:
```powershell
# Run all 4 tiers (74 tests total: 54 in Tier 1, 10 in Tier 2, 5 in Tier 3, 5 in Tier 4)
.\.venv\Scripts\python.exe tests/e2e/run_e2e_suite.py

# Or with verbose test-by-test reporting
.\.venv\Scripts\python.exe tests/e2e/run_e2e_suite.py --verbose

# Run specific tiers
.\.venv\Scripts\python.exe tests/e2e/run_e2e_suite.py --tier 1
.\.venv\Scripts\python.exe tests/e2e/run_e2e_suite.py --tier 2
.\.venv\Scripts\python.exe tests/e2e/run_e2e_suite.py --tier 3
.\.venv\Scripts\python.exe tests/e2e/run_e2e_suite.py --tier 4
```

---

## 6. Fixture & Test Isolation Strategy

1. **Read-Only Project Inspections**:
   - Tests inspecting project metadata, `AGENTS.md`, and directory junctions execute read-only checks directly against the project root.
2. **Mutating CLI & Tool Inspections**:
   - Tests that execute `parse_sources.py`, `ingest_sources.py`, and `vault_linter.py` operate within **isolated temporary directories** created via Python's `tempfile.TemporaryDirectory()`.
   - Synthetic vaults and test input documents are dynamically provisioned in temp directories and cleaned up immediately upon test teardown.
   - This ensures tests are 100% self-contained, idempotent, and never alter or pollute the user's live Google Drive vault.
3. **Deterministic Output Assertion**:
   - YAML frontmatters are parsed and validated for structural correctness, required keys, and clean nulls (`[]`).
   - CLI execution return codes (`0` vs `1`) and stderr/stdout diagnostics are strictly verified.
4. **Image Extraction Validation**:
   - Extracted images are verified at `vault / "900. config" / "910. Attached" / <doc_stem> / "image_XXX.png"`.
   - Note bodies are inspected to verify regex replacement of original image references to `![[<doc_stem>/image_XXX.png]]`.
