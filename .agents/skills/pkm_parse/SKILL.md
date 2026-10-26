---
name: pkm-parse
description: "Dedicated PKM Parsing Skill: Inbox_Raw 외부 원천자료(PDF, HWPX, HWP, XLSX, DOCX, PPTX) kordoc 기반 파싱, 910. Attached 이미지 추출 및 ![[<doc_stem>/image_XXX.png]] 위키링크 리라이팅, 000. Inbox/ 플랫 적재, 2단계 하이브리드 프론트매터 생성 및 시맨틱 보강, Archive_Sources/ 아카이빙(Inbox Zero)"
---

# Dedicated PKM Parsing Skill (`pkm_parse`)

본 스킬은 `My-PKM` 시스템의 외부 원천자료 수집 큐(`Inbox_Raw/`)에 반입된 다양한 포맷의 미가공 바이너리 및 텍스트 문서(`PDF`, `HWPX`, `HWP`, `XLSX`, `DOCX`, `PPTX`, `TXT`, `MD`)를 `kordoc` 엔진으로 파싱하여 옵시디언 볼트의 1차 임시 수집 버퍼인 `./My-Wiki/000. Inbox/`에 마크다운 노트로 변환 적재하고, 원본 바이너리를 `./Archive_Sources/`로 안전하게 아카이빙(Inbox Zero)하는 전용 문서 수집·파싱 스킬입니다.

문서 파싱 시 본문에 포함된 도표(GFM 테이블)와 내장 이미지를 고품질로 추출하여 `./My-Wiki/900. config/910. Attached/<doc_stem>/image_XXX.png`에 저장하고, 마크다운 본문의 모든 이미지 링크를 옵시디언 네이티브 위키링크 임베드(`![[<doc_stem>/image_XXX.png]]`)로 정밀 리라이팅합니다.

---

## 1. 지식 볼트 헌법 및 핵심 거버넌스 원칙

본 스킬은 옵시디언 볼트 헌법(Obsidian Vault Constitution v2.1)과 SSOT(Single Source of Truth) 규정을 엄격히 준수합니다.

### 1.1 실시간 SSOT 동적 사전 검증 (Dynamic SSOT Pre-flight) 원칙
- **사전 필수 검증**: 에이전트는 문서 파싱, 프론트매터 메타데이터 추론 및 보강(Semantic Enrichment), 또는 메모 분류를 수행하기 전에 반드시 다음 2개의 마스터 문서를 실시간 SSOT로 먼저 읽고 최신 규칙을 확인해야 합니다:
  1. `./My-Wiki/400. Wiki/PKM 아키텍처.md` (복합 지식의 5차원 직교 구조화 및 상속 규칙)
  2. `./My-Wiki/400. Wiki/옵시디언 메모간 링크 연결 규칙 설계.md` (볼트 아키텍처 및 링크 설계 10대 마스터 규칙 v2.1)
- **7대 표준 도메인 코드**: `theory`, `macro`, `equity`, `portfolio`, `work`, `ai-pkm`, `education` 중 주 도메인 1개, 교차 성격 시 부 도메인 1개(최대 2개, "1+1" Rule) 부여.
- **7대 표준 노트 역할 (`type`)**: `hub`, `concept`, `analysis`, `entity`, `source`, `project`, `log`.

### 1.2 인간 주권 보호 (Human Write Sovereignty) 원칙
- `100. Concepts` (`110. Notes`, `120. Logs`) 및 `500. etc` 폴더는 사용자의 고유 사유와 투자 철학이 담긴 **인간 주권 영역**입니다.
- AI 파서(`parse_sources.py`) 및 에이전트는 사용자의 명시적인 직접 지시나 승인 없이 `100. Concepts`나 `500. etc`에 임의로 파일을 생성하거나 덮어쓰는(Unprompted write/overwrite) 것을 절대 금지합니다.
- `pkm_parse`의 산출물은 오직 임시 수집 버퍼인 `./My-Wiki/000. Inbox/`로만 제한 적재됩니다.

### 1.3 볼트 외부 바이너리 격리 (Vault Binary Isolation) 및 구글 드라이브 원클릭 링크 (`source_url`) 원칙
- 4대 기기 간 동기화 병목과 스토리지 폭증을 방지하기 위해 무거운 원본 바이너리 파일(`.pdf`, `.hwpx`, `.hwp`, `.xlsx`, `.docx`, `.pptx`, `.zip` 등)은 `./My-Wiki` 볼트 내부(임시 폴더인 `000. Inbox/` 포함)에 절대 반입하지 않습니다.
- 모든 원본 바이너리는 오직 볼트 외부 디렉터리인 `Inbox_Raw/` (미가공 입력 큐) 및 `Archive_Sources/` (처리 완료 보관소)에서만 관리합니다.
- **구글 드라이브 뷰어 원클릭 링크 (`source_url`) 원칙**:
  - `Inbox_Raw/`와 `Archive_Sources/`는 구글 드라이브 마운트(`G:\내 드라이브\...`)로 연결된 NTFS 디렉터리 정션(Junction)입니다.
  - 파싱된 마크다운 노트 프론트매터의 `source_url` 속성에는 단순 로컬 상대 경로 대신, 클릭 즉시 구글 드라이브에 아카이빙된 원본 자료를 열람할 수 있는 **구글 드라이브 뷰어 링크(`https://drive.google.com/open?id=<FILE_ID>&usp=drive_fs`)**를 기입합니다.
  - `parse_sources.py`의 `resolve_gdrive_url()` 함수가 정션의 실제 타겟 경로(`Path.resolve()`)를 추적하고 Google Drive for Desktop 로컬 메타데이터 DB(`%LOCALAPPDATA%\Google\DriveFS\*\metadata_sqlite_db`)의 `items` / `stable_parents` / `stable_ids` 테이블을 조회하여 Google Drive File ID를 자동으로 추출·적용합니다. (구글 드라이브 마운트가 아닌 로컬 임시 테스트 환경 등에서만 `Archive_Sources/<subfolder>/<filename>` 상대 경로로 폴백합니다.)
- 볼트 내부 첨부파일은 오직 경량 이미지(`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`)에 한해 `./My-Wiki/900. config/910. Attached/<doc_stem>/` 하위에만 격리 보관합니다.

### 1.4 `000. Inbox/` 플랫 구조 및 유령 링크 방지 (Clean Null) 원칙
- `000. Inbox/`는 분류 대기 중인 모든 임시 메모의 1차 수집소이며, **하위 폴더가 없는 단일(Flat) 디렉터리** 구조를 유지합니다. 모든 변환 노트는 `./My-Wiki/000. Inbox/<stem>.md`로 생성됩니다.
- 링크 배열 속성(`up`, `prev`, `source`, `related`, `author`, `org` 등)에 대상이 없을 때는 절대로 `"[[]]"`(빈 대괄호 텍스트)를 남기지 않고, 반드시 `[]`(YAML 빈 리스트)로 표기합니다.

### 1.5 거버넌스 분리: `pkm_parse` vs `pkm_manager`
- **`pkm_parse`의 소유 영역**:
  - `Inbox_Raw/` 내 미가공 바이너리 스캔 및 `kordoc` 파싱
  - 내장 이미지 추출 및 `900. config/910. Attached/<doc_stem>/` 적재
  - 마크다운 본문 이미지 링크 리라이팅 (`![[<doc_stem>/image_XXX.png]]`)
  - Stage 1 결정론적 2계층 프론트매터 생성 및 `000. Inbox/<stem>.md` 플랫 적재
  - `Archive_Sources/`로의 원본 바이너리 안전 이동 (Inbox Zero 달성)
  - Stage 2 AI 에이전트 시맨틱 보강(Semantic Enrichment) 프로토콜 수행
- **`pkm_manager`의 소유 영역**:
  - 볼트 헌법 무결성 5대 감사 (`vault_linter.py`)
  - `000. Inbox/`에서 영구 폴더(`100. Concepts`, `200. AI_logs`, `300. Sources`)로의 메모 분류(Triage)
  - 외과적 정밀 패치 (Surgical Patching via Obsidian MCP / 로컬 I/O)
  - 카파시(Karpathy) 스타일 LLM 위키 주기적 종합 컴파일 (`400. Wiki`)
  - 하위 호환성 유지용 레거시 스크립트(`ingest_sources.py`) 보존

---

## 2. 2단계 하이브리드 파싱 및 시맨틱 보강 워크플로우 (2-Stage Hybrid Workflow)

원천 문서의 안정적 적재와 메타데이터의 정확성을 극대화하기 위해 결정론적 파서(Stage 1)와 AI 에이전트 지능형 보강(Stage 2)을 분리 연계합니다.

```
[Inbox_Raw/ 바이너리 파일]
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ Stage 1: 결정론적 Python CLI (parse_sources.py)              │
│  - kordoc 텍스트/표/이미지 추출 (GFM 테이블, OCR 선택)       │
│  - 이미지 저장: My-Wiki/900. config/910. Attached/<doc_stem>/ │
│  - 본문 위키링크 리라이팅: ![[<doc_stem>/image_XXX.png]]     │
│  - 7대 코어 속성 + Clean Null + 기본 source 확장 속성 생성  │
│  - My-Wiki/000. Inbox/<doc_stem>.md 플랫 적재               │
│  - Archive_Sources/ 아카이빙 (Inbox Zero)                   │
│  - source_url: https://drive.google.com/open?id=<ID>&usp=drive_fs │
└─────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ Stage 2: AI 에이전트 시맨틱 보강 (Semantic Enrichment)       │
│  - 동적 SSOT 문서 사전 확인 (PKM 아키텍처.md, 링크 규칙.md) │
│  - 000. Inbox/<doc_stem>.md 문서 목차/핵심 요약 분석        │
│  - 정밀 도메인(7대 코드 중 1+1) 및 1촌 부모 up 위키링크 추론│
│  - author, org, published, aliases, summary, source_url 확인 │
│  - 외과적 패치(Surgical Patch)로 프론트매터 반영            │
│  - vault_linter.py --include-inbox 무결성 검증              │
└─────────────────────────────────────────────────────────────┘
```

---

### 2.1 Stage 1: 결정론적 Python 파서 CLI (`parse_sources.py`)

파이썬 CLI 스크립트 `.agents/skills/pkm_parse/scripts/parse_sources.py`를 호출하여 문서를 파싱하고 `000. Inbox/`에 플랫하게 적재합니다.

#### 기본 실행 명령어
```bash
# 단일 파일 파싱 (Inbox Zero 아카이빙 및 000. Inbox 플랫 적재)
.\.venv\Scripts\python.exe .agents/skills/pkm_parse/scripts/parse_sources.py \
  --file "Inbox_Raw/20261025_FOMC_Preview.pdf" \
  --subfolder "310. Reports_Papers" \
  --domain "macro" \
  --up "[[02_매크로 분석]]" \
  --source-type "report" \
  --table-format gfm

# Inbox_Raw 전체 배치 일괄 파싱
.\.venv\Scripts\python.exe .agents/skills/pkm_parse/scripts/parse_sources.py \
  --inbox "./Inbox_Raw" \
  --vault "./My-Wiki" \
  --archive "./Archive_Sources" \
  --table-format gfm

# 스캔 문서 고정밀 OCR 적용 파싱
.\.venv\Scripts\python.exe .agents/skills/pkm_parse/scripts/parse_sources.py \
  --file "Inbox_Raw/스캔보고서.pdf" \
  --ocr \
  --table-format gfm

# 변환 시뮬레이션 (Dry-Run: 파일 쓰기 및 원본 이동 없이 검증)
.\.venv\Scripts\python.exe .agents/skills/pkm_parse/scripts/parse_sources.py \
  --file "Inbox_Raw/중요자료.hwpx" \
  --dry-run
```

#### Stage 1 세부 처리 메커니즘
1. **듀얼 엔진 파싱**:
   - Python `kordoc.KordocClient` SDK 상주 워커를 우선 호출하여 문서를 고속 파싱합니다.
   - SDK 가용 불가 시 글로벌 Node.js `kordoc` CLI로 자동 폴백합니다.
   - 표 구조는 `--table-format gfm` 옵션을 통해 GitHub Flavored Markdown 표로 변환됩니다.
2. **내장 이미지 추출 및 링크 리라이팅**:
   - PDF/HWPX 내 이미지 객체는 임시 디렉터리(`tempfile.TemporaryDirectory`)에서 안전하게 수집된 후 `./My-Wiki/900. config/910. Attached/<doc_stem>/image_XXX.png`에 저장됩니다.
   - 마크다운 본문의 `![alt](url)` 및 `<img src="...">` 태그는 모두 옵시디언 네이티브 임베드인 `![[<doc_stem>/image_XXX.png]]`로 자동 변환됩니다.
   - 이미지 추출 완료 후 임시 디렉터리는 잔여 파일 없이 원자적으로 정리(Cleanup)됩니다.
3. **2계층 프론트매터 자동 결합 (Clean Null 준수)**:
   - 7대 코어 속성(`origin: source`, `type: source`, `domain`, `up`, `status: active`, `created`, `updated`)을 구성합니다.
   - `--up`이 지정되지 않았거나 빈 대괄호인 경우 유령 링크 `"[[]]"`를 생성하지 않고 엄격히 `up: []`로 출력합니다.
   - 확장 속성(`source_type`, `author`, `org`, `published`, `ref_date`, `aliases`, `summary`, `source_url`)을 결합합니다.
4. **`000. Inbox/` 플랫 적재, 아카이빙(Inbox Zero) 및 구글 드라이브 `source_url` 연결**:
   - 원본 바이너리를 `./Archive_Sources/<subfolder>/<filename>` (또는 루트 `./Archive_Sources/<filename>`)으로 안전하게 이동합니다.
   - 정션(`Archive_Sources/` ➔ `G:\내 드라이브\Archive_Sources\`) 및 Google Drive for Desktop(`DriveFS`) 로컬 SQLite DB(`%LOCALAPPDATA%\Google\DriveFS\*\metadata_sqlite_db`)를 조회하여 아카이빙된 원본 파일의 Google Drive File ID를 추출하고, 프론트매터의 `source_url` 속성에 **`https://drive.google.com/open?id=<FILE_ID>&usp=drive_fs`** 링크를 자동 기록합니다 (구글 드라이브 비연결 로컬 테스트 환경에서만 `Archive_Sources/...` 상대 경로로 폴백).
   - 변환된 마크다운을 `./My-Wiki/000. Inbox/<stem>.md`에 플랫하게 기록합니다.

---

### 2.2 Stage 2: AI 에이전트 시맨틱 보강 프로토콜 (Semantic Enrichment Protocol)

Stage 1 파싱 완료 후 에이전트는 아래 5단계 프로토콜에 따라 노트의 메타데이터를 지능적으로 보강합니다.

#### Step 1: 동적 SSOT 마스터 문서 읽기 (Pre-flight)
에이전트는 볼트 내 최신 규칙을 확인합니다:
- `view_file`로 `./My-Wiki/400. Wiki/PKM 아키텍처.md` 및 `./My-Wiki/400. Wiki/옵시디언 메모간 링크 연결 규칙 설계.md` 확인.
- 도메인 정의 및 계층 구조(1촌 부모 위키)의 최신 상태 파악.

#### Step 2: 파싱된 노트 본문 검토
- `view_file`을 통해 `./My-Wiki/000. Inbox/<doc_stem>.md`의 상단 프론트매터, 제목, 목차, 서론, 요약 문단을 읽습니다.

#### Step 3: 시맨틱 메타데이터 정밀 추론
1. **도메인 (`domain`)**:
   - 7대 표준 도메인(`theory`, `macro`, `equity`, `portfolio`, `work`, `ai-pkm`, `education`) 중 문서의 주제와 가장 밀접한 주 도메인 1개(+ 교차 성격 시 부 도메인 1개)를 결정합니다.
2. **직계 1촌 부모 (`up`)**:
   - 동일 도메인 축의 직계 1촌 상위 개념 위키 문서(예: `"[[02_매크로 분석]]"`, `"[[03_산업 및 기업분석]]"`, `"[[글로벌 매크로 동향]]"`)를 지정합니다. 독립적인 원천자료로서 부모 연결이 불필요한 경우 `[]`를 유지합니다. (조상 노트를 건너뛰는 Hairball 직결 금지).
3. **문서 메타데이터 확장 및 `source_url` 구글 드라이브 링크 검증**:
   - `author`: 문서 본문에서 추출한 실제 저자명 (예: `["[[홍길동]]"]` 또는 `"홍길동"`)
   - `org`: 발행 증권사, 연구기관, 부서명 (예: `["[[삼성증권]]"]` 또는 `"삼성증권"`)
   - `published`: 리포트 발행일 (`YYYY-MM-DD` 또는 `YYYY-MM`)
   - `aliases`: 리포트 부제, 영문명, 핵심 키워드 리스트
   - `summary`: 문서 전체의 핵심 결론 및 시사점을 담은 1~3문장의 명확한 한국어 요약
   - `source_url`: 프론트매터의 `source_url`이 클릭 즉시 구글 드라이브 원문을 여는 **`https://drive.google.com/open?id=<FILE_ID>&usp=drive_fs`** 형태로 기입되어 있는지 확인합니다. 만약 동기화 지연으로 인해 로컬 상대 경로(`Archive_Sources/...`)로 남아 있다면, `resolve_gdrive_url(Path("Archive_Sources/..."))`를 재호출하여 반드시 구글 드라이브 연결 링크로 업데이트합니다.

#### Step 4: 외과적 정밀 수정 (Surgical Patch)
- `obsidian:vault_patch` 도구 또는 파일 편집 도구를 사용하여 전체 본문을 훼손하지 않고 YAML 프론트매터 블록만 외과적으로 갱신합니다.
- `updated` 날짜를 현재 시스템 일자(`YYYY-MM-DD`)로 갱신합니다.

#### Step 5: 볼트 헌법 무결성 검증
보강 완료 후 `vault_linter.py`를 실행하여 헌법 준수 여부를 검증합니다:
```bash
.\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/vault_linter.py --vault ./My-Wiki --include-inbox
```
- 모든 가공 노트의 7대 코어 속성(C1), 유령 링크 부재(C2), 고립 여부(C3), origin 정합성(C4), 바이너리 격리(C5)가 100% 통과되는지 확인합니다.

---

## 3. CLI 19개 플래그 상세 레퍼런스 (19 CLI Flags)

`parse_sources.py`는 메타데이터 설정, 파싱 제어, 안전성을 위한 19개의 CLI 플래그를 완벽히 지원합니다:

| # | 플래그 (Flag) | 타입 (Type) | 기본값 (Default) | 상세 설명 및 동작 원칙 |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `--file` | `str` | `None` | 파싱할 단일 입력 파일 경로. 생략 시 `--inbox` 전체 배치 처리. 파일 미존재 시 Exit code 1 반환. |
| 2 | `--inbox` | `str` | `./Inbox_Raw` | 미가공 입력 파일이 위치한 원천 큐 폴더 경로. |
| 3 | `--vault` | `str` | `./My-Wiki` | 옵시디언 볼트 루트 경로. |
| 4 | `--archive` | `str` | `./Archive_Sources` | 파싱 완료된 원본 바이너리를 이동 보관할 아카이브 루트 경로. |
| 5 | `--subfolder` | `str` | `None` | 아카이브 내 분류 하위 폴더 (`310. Reports_Papers` 등). 볼트 노트는 이에 영향받지 않고 `000. Inbox`에 플랫 저장됨. |
| 6 | `--domain` | `str` | `macro` | 7대 표준 도메인 코드 (쉼표 구분 최대 2개 지원). |
| 7 | `--up` | `str` | `None` | 직계 1촌 부모 위키링크 (`"[[02_매크로 분석]]"`). 생략되거나 빈 대괄호 입력 시 clean null `[]`로 정규화. |
| 8 | `--source-type` | `str` | `report` | 원천 문서 유형 (`report`, `paper`, `book`, `clipping`, `work_doc`, `presentation`, `news`). |
| 9 | `--author` | `str` | `None` | 저자 엔티티 명칭 또는 위키링크. |
| 10 | `--org` | `str` | `None` | 발행 기관/조직 엔티티 명칭 또는 위키링크. |
| 11 | `--published` | `str` | `None` | 원문 발행일자 (`YYYY-MM` 또는 `YYYY-MM-DD`). |
| 12 | `--ref-date` | `str` | `None` | 참조 기준일 (생략 시 현재 시스템 날짜 `YYYY-MM-DD`). |
| 13 | `--aliases` | `str` | `None` | 쉼표로 구분된 문서 별칭 및 영문 제목 리스트. |
| 14 | `--summary` | `str` | `None` | 한 줄 개요 또는 핵심 요약문. |
| 15 | `--table-format` | `str` | `gfm` | 표 변환 포맷 (`gfm` 또는 `html`). GitHub Flavored Markdown 표 권장. |
| 16 | `--ocr` | `flag` | `False` | 스캔된 이미지 문서에 대해 kordoc 내장 PP-OCRv5 한국어 광학 문자 인식 활성화. |
| 17 | `--dry-run` | `flag` | `False` | 디스크 파일 생성 및 원본 이동 없이 변환 결과 및 경로를 사전 점검하는 안전 모드. |
| 18 | `--force` | `flag` | `False` | 볼트 내 기생성된 노트나 아카이브 대상 파일이 존재해도 덮어쓰기 허용. |
| 19 | `--verbose` | `flag` | `False` | 파싱 과정 및 세부 로그 콘솔 출력. |

---

## 4. 프론트매터 스키마 명세 (2-Tier Frontmatter Schema)

`parse_sources.py`가 생성하고 Stage 2에서 보강하는 YAML 프론트매터 표준 양식입니다:

```yaml
---
# Tier 1: 7대 필수 코어 속성 (Core Mandatory)
origin: source                  # Enum: [source] (000. Inbox staging buffer)
type: source                    # Enum: [source]
domain:                         # List of standard domains (1~2개 "1+1" Rule)
  - macro
up:                             # 1-hop parent wikilink. 대상 없을 시 반드시 []
  - "[[02_매크로 분석]]"
status: active                  # Enum: active
created: 2026-10-26             # YYYY-MM-DD
updated: 2026-10-26             # YYYY-MM-DD

# Tier 2: source 역할 확장 속성 (Sparse Extended Properties)
source_type: report             # Enum: [report, paper, book, clipping, work_doc, presentation, news]
author: "홍길동 연구위원"
org: "미래에셋증권"
published: 2026-10-25
ref_date: 2026-10-26
aliases:
  - "2026 FOMC 프리뷰"
summary: "11월 FOMC 금리 동결 전망 및 점도표 변화 시나리오 분석"
source_url: https://drive.google.com/open?id=1J5kAHs7MlHgJZg6ItDd7neNu3r_4kJZs&usp=drive_fs
---
```

---

## 5. 볼트 린터 검증 및 안정성 보장

- **`vault_linter.py --include-inbox` 호환성**:
  - `000. Inbox/`는 분류 대기 버퍼이므로 `origin: source`, `origin: ai`, `origin: human`, `origin: wiki` 노트가 모두 C4 위반 없이 허용됩니다.
  - `type: source` 노트는 직계 상위 링크가 지정되지 않아 `up: []` 상태여도 C3(Orphan) 검사에서 적법한 예외로 간주되어 통과합니다.
- **아카이빙 충돌 방지**:
  - 원본 파일을 아카이브 폴더로 이동 시 대상 파일이 이미 존재하더라도 안전하게 덮어쓰거나 락 충돌을 방지합니다.
- **원자적 임시 디렉터리 정리**:
  - 이미지 추출 및 파싱 중 생성되는 모든 중간 디렉터리는 `tempfile.TemporaryDirectory` 컨텍스트 매니저를 통해 작업 종료 즉시 100% 원자적으로 삭제됩니다.
