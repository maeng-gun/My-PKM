---
name: pkm-parse
description: "Dedicated PKM Parsing Skill: Inbox_Raw 외부 원천자료(PDF, HWPX, HWP, XLSX, DOCX, PPTX) kordoc 기반 텍스트·표 파싱, 000. Inbox/ 순수 파싱 마크다운 플랫 적재, Archive_Sources/ 아카이빙(Inbox Zero)"
---

# Dedicated PKM Parsing Skill (`pkm_parse`)

본 스킬은 `My-PKM` 시스템의 외부 원천자료 수집 큐(`Inbox_Raw/`)에 반입된 다양한 포맷의 미가공 바이너리 및 텍스트 문서(`PDF`, `HWPX`, `HWP`, `XLSX`, `DOCX`, `PPTX`, `TXT`, `MD`)를 `kordoc` 엔진으로 파싱하여 옵시디언 볼트의 1차 임시 수집 버퍼인 `./My-Wiki/000. Inbox/`에 **프론트매터 없는 순수 파싱 마크다운 노트**로 변환 적재하고, 원본 바이너리를 `./Archive_Sources/`로 안전하게 아카이빙(Inbox Zero)하는 전용 문서 수집·파싱 실행 엔진입니다.

문서 파싱 시 본문에 포함된 텍스트와 도표(GFM 테이블)를 추출하여 순수 마크다운으로 변환하며, 불필요한 내장 이미지 추출이나 이미지 위키링크 리라이팅은 수행하지 않습니다.

> [!IMPORTANT]
> **엔진(Skill)과 헌법(`My-Wiki Rules.md`)의 완전 분리 및 미컴파일 인박스 원칙**
> - `000. Inbox`는 미컴파일 원천 메모의 시작점이자 임시 수집 버퍼입니다(`My-Wiki Rules.md` 제1조).
> - `pkm-parse`는 수집·파싱 전용 엔진으로서 **프론트매터 없이 순수 파싱 결과물(.md)**만을 `000. Inbox/<stem>.md`에 플랫하게 적재합니다.
> - 프론트매터 부여(도메인, `up` 직계 부모, 역할, 시간 속성 등) 및 위키 반영은 **인박스 컴파일 단계(`pkm-manager`)**에서 마스터 헌법(`./My-Wiki/My-Wiki Rules.md`)을 실시간 동적 참조하여 수행됩니다.
> - 따라서 마스터 헌법이 버전업되더라도 본 파싱 스킬의 코드를 변경할 필요가 없습니다.

---

## 1. 지식 볼트 헌법 및 핵심 거버넌스 원칙

본 스킬은 옵시디언 볼트 단일 마스터 헌법(`./My-Wiki/My-Wiki Rules.md`) 규정을 엄격히 준수합니다.

### 1.1 `000. Inbox/` 순수 파싱 마크다운 플랫 적재 원칙
- `000. Inbox/`는 분류 및 컴파일 대기 중인 모든 임시 메모의 1차 수집소이며, **하위 폴더가 없는 단일(Flat) 디렉터리** 구조를 유지합니다. 모든 변환 노트는 `./My-Wiki/000. Inbox/<stem>.md`로 생성됩니다.
- `000. Inbox/` 적재 시 **기본적으로 YAML 프론트매터를 포함하지 않으며 이미지 추출도 수행하지 않습니다**. 파싱된 원문 텍스트와 표 중심의 순수 마크다운으로 보관되며, 컴파일 단계에서 `pkm_manager` (`compile_helper.py normalize-fm`)를 통해 헌법 최신 스키마가 부여됩니다.

### 1.2 인간 주권 보호 (Human Write Sovereignty) 원칙
- `100. Concepts` 및 `600. etc`(구 `500. etc`) 폴더는 사용자의 고유 사유와 투자 철학이 담긴 **인간 주권 영역**입니다.
- AI 파서(`parse_sources.py`) 및 에이전트는 사용자의 명시적인 직접 지시나 승인 없이 `100. Concepts`나 `600. etc`에 임의로 파일을 생성하거나 덮어쓰는(Unprompted write/overwrite) 것을 절대 금지합니다.
- `pkm_parse`의 산출물은 오직 임시 수집 버퍼인 `./My-Wiki/000. Inbox/`로만 제한 적재됩니다.

### 1.3 볼트 외부 바이너리 격리 (Vault Binary Isolation) 및 아카이빙 (Inbox Zero)
- 4대 기기 간 동기화 병목과 스토리지 폭증을 방지하기 위해 무거운 원본 바이너리 파일(`.pdf`, `.hwpx`, `.hwp`, `.xlsx`, `.docx`, `.pptx`, `.zip` 등)은 `./My-Wiki` 볼트 내부(임시 폴더인 `000. Inbox/` 포함)에 절대 반입하지 않습니다.
- 모든 원본 바이너리는 오직 볼트 외부 디렉터리인 `Inbox_Raw/` (미가공 입력 큐) 및 `Archive_Sources/` (처리 완료 보관소)에서만 관리합니다.
- 파싱이 완료된 원본 파일은 즉시 `Archive_Sources/<subfolder>/`로 이동하여 `Inbox_Raw/`의 Inbox Zero를 달성합니다.

### 1.4 거버넌스 분리: `pkm_parse` vs `pkm_manager`
- **`pkm_parse` (수집 및 파싱 엔진)**:
  - `Inbox_Raw/` 내 미가공 바이너리 스캔 및 `kordoc` 기반 텍스트·표 파싱
  - `000. Inbox/<stem>.md`에 순수 파싱 마크다운 플랫 적재 (프론트매터 및 이미지 추출 없음)
  - `Archive_Sources/`로의 원본 바이너리 안전 이동 (Inbox Zero 달성)
  - 구글 드라이브 파일 ID 해석 및 뷰어 URL 확인
- **`pkm_manager` (위키 컴파일 및 거버넌스 엔진)**:
  - `My-Wiki/My-Wiki Rules.md` 동적 SSOT 로드(`constitution_loader.py`)
  - `000. Inbox/`에 대기 중인 순수 파싱 노트를 읽고 최신 헌법 스키마에 따라 프론트매터 생성 및 정규화 (`compile_helper.py normalize-fm`)
  - `400. Wiki` 컴파일, `300. Sources/` 이동 및 `500. Index/_인덱스_300_Sources.md` 등재
  - 기존 관련 메모 역추적 재컴파일 및 볼트 헌법 무결성 감사(`vault_linter.py`)

---

## 2. 문서 파싱 및 연계 워크플로우

```
[Inbox_Raw/ 미가공 바이너리]
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ pkm_parse 엔진 실행 (parse_sources.py)                      │
│  - kordoc 텍스트/표 추출 (GFM 테이블, OCR 선택)              │
│  - My-Wiki/000. Inbox/<doc_stem>.md 순수 마크다운 플랫 적재 │
│  - Archive_Sources/ 원본 아카이빙 (Inbox Zero 달성)          │
│  - DriveFS 로컬 DB 기반 구글 드라이브 URL 확인             │
└─────────────────────────────────────────────────────────────┘
           │
           ▼ (컴파일 요청 시 pkm_manager로 핸드오프)
┌─────────────────────────────────────────────────────────────┐
│ pkm_manager 인박스 컴파일 파이프라인 (compile_helper.py)     │
│  - constitution_loader로 My-Wiki Rules.md 최신 스키마 조회 │
│  - compile_helper.py normalize-fm: 프론트매터 부여/정규화   │
│  - 400. Wiki 컴파일 및 300. Sources/ 폴더 이동              │
│  - 500. Index/_인덱스_300_Sources.md 등재 및 사후 감사      │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. CLI 실행 명령어

파이썬 CLI 스크립트 `.agents/skills/pkm_parse/scripts/parse_sources.py`를 호출하여 문서를 파싱합니다.

```bash
# 단일 파일 파싱 (기본: 순수 마크다운 000. Inbox 적재 + Inbox Zero 아카이빙)
.\.venv\Scripts\python.exe .agents/skills/pkm_parse/scripts/parse_sources.py \
  --file "Inbox_Raw/20261025_FOMC_Preview.pdf" \
  --subfolder "310. Reports_Papers" \
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

# [옵션] 프론트매터를 포함하여 파싱할 경우 (--include-frontmatter)
.\.venv\Scripts\python.exe .agents/skills/pkm_parse/scripts/parse_sources.py \
  --file "Inbox_Raw/20261025_FOMC_Preview.pdf" \
  --subfolder "310. Reports_Papers" \
  --include-frontmatter \
  --domain "macro" \
  --up "[[02_매크로 분석]]"
```

---

## 4. CLI 플래그 레퍼런스

`parse_sources.py`가 지원하는 CLI 플래그 목록입니다:

| 플래그 (Flag) | 타입 (Type) | 기본값 (Default) | 설명 |
| :--- | :--- | :--- | :--- |
| `--file` | `str` | `None` | 파싱할 단일 입력 파일 경로 (생략 시 `--inbox` 전체 배치 처리). |
| `--inbox` | `str` | `./Inbox_Raw` | 미가공 입력 파일이 위치한 원천 큐 폴더 경로. |
| `--vault` | `str` | `./My-Wiki` | 옵시디언 볼트 루트 경로. |
| `--archive` | `str` | `./Archive_Sources` | 파싱 완료된 원본 바이너리를 이동 보관할 아카이브 루트 경로. |
| `--subfolder` | `str` | `None` | 아카이브 내 분류 하위 폴더 (`310. Reports_Papers` 등). |
| `--include-frontmatter`| `flag` | `False` | 000. Inbox 적재 시 YAML 프론트매터 포함 여부 (기본값: False, 순수 마크다운). |
| `--domain` | `str` | `macro` | 표준 도메인 코드 (쉼표 구분 최대 2개 지원, constitution_loader 연동). |
| `--up` | `str` | `None` | 직계 1촌 부모 위키링크. 미지정 시 clean null `[]`로 정규화. |
| `--source-type` | `str` | `report` | 원천 문서 유형 (`report`, `paper`, `book`, `clipping`, `work_doc`, `presentation`, `news`). |
| `--author` | `str` | `None` | 저자 엔티티 명칭 또는 위키링크. |
| `--org` | `str` | `None` | 발행 기관/조직 엔티티 명칭 또는 위키링크. |
| `--published` | `str` | `None` | 원문 발행일자 (`YYYY-MM` 또는 `YYYY-MM-DD`). |
| `--ref-date` | `str` | `None` | 참조 기준일 (생략 시 현재 시스템 날짜 `YYYY-MM-DD`). |
| `--aliases` | `str` | `None` | 쉼표로 구분된 문서 별칭 리스트. |
| `--summary` | `str` | `None` | 한 줄 개요 또는 핵심 요약문. |
| `--source-url` | `str` | `None` | 명시적 `source_url` 오버라이드 (미지정 시 Google Drive File ID 자동 조회). |
| `--table-format` | `str` | `gfm` | 표 변환 포맷 (`gfm` 또는 `html`). |
| `--ocr` | `flag` | `False` | 스캔된 이미지 문서에 대해 PP-OCRv5 한국어 OCR 활성화. |
| `--dry-run` | `flag` | `False` | 파일 생성 및 원본 이동 없이 변환 결과 및 경로 사전 점검. |
| `--force` | `flag` | `False` | 목적지 파일이 이미 존재할 경우 덮어쓰기 허용. |
| `--verbose` | `flag` | `False` | 세부 콘솔 로그 출력 활성화. |
