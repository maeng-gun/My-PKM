# E2E Test Infra: Valley AI Macro Lecture Pipeline

## Test Philosophy
- Opaque-box, requirement-driven testing. No dependency on implementation design.
- Methodology: Category-Partition + Boundary Value Analysis + Pairwise Combinatorial + Real-World Workload Testing.
- Ground truth: ORIGINAL_REQUEST.md requirements (R1, R2, R3, R4) and acceptance criteria.

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 |
|---|---------|---------------------|:------:|:------:|:------:|
| 1 | Dynamic Course Curriculum Parsing | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 2 | Slide Attachment Filtering (2-1 to 9-3) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 3 | Graceful Attachment-Less Skipping (1-2, 1-3) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 4 | Filename Format ({회차}_{강}_{제목}.pdf) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 5 | Session / Auth Persistence | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |
| 6 | Robust PDF Download Execution | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 7 | PDF Binary Validation (magic, EOF, size) | Acceptance Criteria | 5 | 5 | ✓ |
| 8 | kordoc Pure Text & GFM Table Parsing | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 9 | Output Placement in Inbox_temp | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 10 | DriveFS Google Drive URL Resolution | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 11 | Markdown Post-Parse Validation | Acceptance Criteria | 5 | 5 | ✓ |
| 12 | Atomic Archiving to Archive_Sources | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 13 | Inbox Zero Verification Gateway | Acceptance Criteria | 5 | 5 | ✓ |
| 14 | Unified Pipeline Execution | ORIGINAL_REQUEST §R1-R4 | 5 | 5 | ✓ |

## Test Architecture
- Test Runner: `pytest tests/e2e/test_macro_pipeline_e2e.py -v` (and integrated in `tests/e2e/run_e2e_suite.py`)
- Directory layout:
  - `tests/e2e/test_macro_pipeline_e2e.py`: Main E2E test suite covering Tiers 1-4
  - `tests/e2e/fixtures/`: Synthetic/mock fixtures for isolated offline testing
- Pass/Fail semantics: All tests must exit 0, assertions must strictly validate acceptance criteria without dummy/hardcoded mocks.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Full Traversal & Download Dry Run | F1, F2, F3, F4, F5 | Medium |
| 2 | Reference Lecture 1-1 Parse & Archive Simulation | F8, F9, F10, F11, F12, F13 | High |
| 3 | Batch Multi-Lecture Pipeline Execution (Synthetic) | F1-F14 | High |
| 4 | Session Expiry & Auto-Recovery Under Load | F5, F6 | Medium |
| 5 | Cross-Volume Fallback & Lock Recovery Archiving | F12, F13 | High |

## Coverage Thresholds
- Tier 1: ≥5 test cases per feature (happy-path isolation)
- Tier 2: ≥5 test cases per feature (boundaries, corrupt PDF, missing attachment, long titles, special characters)
- Tier 3: Pairwise coverage of major feature interactions (traversal + download, parse + placement, archive + inbox zero)
- Tier 4: ≥5 realistic application scenarios
