# Test Infrastructure: My-PKM

## 1. Overview
This document specifies the end-to-end (E2E) testing infrastructure, methodology, execution commands, and test suites for the **My-PKM** project.
The testing framework enforces strict, requirement-driven, opaque-box validation across all components, directory junctions, agent personas, local skills, and CLI tools (`ingest_sources.py`, `vault_linter.py`) in compliance with the **PKM Constitution v2.1** and **PROJECT.md**.

---

## 2. 4-Tier Test Architecture

The My-PKM test suite implements a hierarchical 4-tier verification architecture:

| Tier | Name | Target Scope | Methodology & Expected Output Source |
|---|---|---|---|
| **Tier 1** | **Feature Coverage** | F1 ~ F8 in isolation (>= 5 test cases per feature) | Verifies individual project artifacts, junction configurations, persona directives, skill metadata, kordoc availability, and CLI flag interfaces against explicit requirements in `PROJECT.md` and `ORIGINAL_REQUEST.md`. |
| **Tier 2** | **Boundary & Corner Cases** | Edge cases & constraints | Tests strict boundaries: ghost link prevention (`[]` vs `"[[]]"`), Level 1 Master Hub orphan exemption, excluded folder skipping (`000. Inbox`, `900. config`, `Notion`), domain code validation (1~2 standard codes only), and heavy binary isolation. |
| **Tier 3** | **Cross-Feature Combinations** | Multi-system workflows & junctions | Validates inter-module data flow: Ingestion ➔ Vault Note Creation ➔ Vault Linter Audit; local junction traversal to Google Drive; and linter auto-fix repair loops. |
| **Tier 4** | **Real-World Application Scenarios** | Full lifecycle simulations | End-to-end simulation: Raw file dropped in `Inbox_Raw/` ➔ `ingest_sources.py` parses with GFM table ➔ Markdown note created in `300. Sources/` ➔ Raw file safely moved to `Archive_Sources/` (Inbox Zero) ➔ `vault_linter.py` audits vault with 0 errors. |

---

## 3. Test Directory Layout

All E2E test files are organized under `c:\Users\maeng-gun\Desktop\python\My_PKM\tests\e2e\`:

```
c:\Users\maeng-gun\Desktop\python\My_PKM\
├── tests/
│   ├── __init__.py
│   └── e2e/
│       ├── __init__.py
│       ├── test_tier1_features.py       # Tier 1: F1 - F8 isolated feature coverage (>=40 tests)
│       ├── test_tier2_boundaries.py     # Tier 2: Constitutional boundary & corner cases (10 tests)
│       ├── test_tier3_combinations.py   # Tier 3: Cross-feature pipelines & junction traversal (5 tests)
│       ├── test_tier4_scenarios.py      # Tier 4: Real-world raw ingestion & audit simulations (4 tests)
│       └── run_e2e_suite.py             # Standalone test runner with Tier breakdown & CLI flags
├── TEST_INFRA.md                        # This test infrastructure specification
└── TEST_READY.md                        # Test execution report and coverage readiness summary
```

---

## 4. Test Execution Guide

### 4.1 Prerequisites
- **Python**: Python 3.12 (or >= 3.11 with `.venv`)
- **Node.js**: Node.js 24+ (`node -v >= 20.0.0`)
- **OS**: Windows 10/11 with PowerShell
- **Google Drive**: Mounted at `G:\내 드라이브` (for junction live tests)

### 4.2 Running the Full E2E Test Suite
The test suite can be run using the standalone runner (which requires zero third-party dependencies):

```powershell
# From project root:
python tests/e2e/run_e2e_suite.py
```

Or using standard Python `unittest`:
```powershell
python -m unittest discover -s tests/e2e -p "test_*.py" -v
```

If `pytest` is installed in the environment:
```powershell
pytest tests/e2e/ -v
```

### 4.3 Running Specific Tiers
The custom runner supports selective tier execution:
```powershell
# Run Tier 1 only
python tests/e2e/run_e2e_suite.py --tier 1

# Run Tier 2 only
python tests/e2e/run_e2e_suite.py --tier 2

# Run Tier 3 only
python tests/e2e/run_e2e_suite.py --tier 3

# Run Tier 4 only
python tests/e2e/run_e2e_suite.py --tier 4

# Run with verbose traceback output
python tests/e2e/run_e2e_suite.py --verbose
```

---

## 5. Feature Coverage Matrix (Tier 1)

| Feature ID | Feature Name | Minimum Tests | Specification Source |
|---|---|---|---|
| **F1** | Project Metadata Files (`pyproject.toml`, `.gdrive_config.json`, `README.md`, `finalize_rename.ps1`) | 6 | `PROJECT.md` Feature 1, 3 |
| **F2** | 5 Workspace Directory Junctions (`input_staging`, `scratch`, `archive`, `secrets`, `AGY_Artifacts`) | 6 | `PROJECT.md` Feature 2 |
| **F3** | 3 PKM Root Junctions (`My-Wiki`, `Inbox_Raw`, `Archive_Sources`) & `.gitignore` exclusion | 6 | `PROJECT.md` Feature 5, 6 |
| **F4** | `AGENTS.md` 4-Part Multi-Persona & SSOT Dynamic Pre-Flight Rules | 6 | `PROJECT.md` Feature 7; Spec Miner 2 §5.3 |
| **F5** | `.agents/skills/pkm_manager/SKILL.md` Frontmatter & 5 Workflows | 6 | `PROJECT.md` Feature 8; Spec Miner 2 §5.5 |
| **F6** | `kordoc` Engine (Node 24+, CLI, Python SDK >= 0.2.0 compatibility) | 5 | `PROJECT.md` Feature 9, 10; Explorer 3 §1.1-1.3 |
| **F7** | `ingest_sources.py` CLI flags, 2-tier frontmatter, GFM tables, clean null `[]` | 6 | `PROJECT.md` §Interface Contracts; Explorer 3 §4.1 |
| **F8** | `vault_linter.py` 5 Constitutional Checks (C1~C5), CLI flags, exit codes | 7 | `PROJECT.md` §Interface Contracts; Spec Miner 2 §5.6 |

---

## 6. Fixture & Test Isolation Strategy

1. **Read-Only Project Inspections**:
   - Tests inspecting project metadata, `AGENTS.md`, and directory junctions execute read-only checks directly against the project root.
2. **Mutating CLI & Tool Inspections**:
   - Tests that execute `ingest_sources.py` and `vault_linter.py` (Tiers 2, 3, 4) operate within **isolated temporary directories** created via Python's `tempfile.TemporaryDirectory()`.
   - Synthetic vaults and test input documents are dynamically provisioned in temp directories and cleaned up immediately upon test teardown.
   - This ensures tests are 100% self-contained, idempotent, and never alter or pollute the user's live Google Drive vault.
3. **Deterministic Output Assertion**:
   - YAML frontmatters are parsed and validated for structural correctness, required keys, and clean nulls (`[]`).
   - CLI execution return codes (`0` vs `1`) and stderr/stdout diagnostics are strictly verified.
