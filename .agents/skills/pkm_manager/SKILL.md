---
name: pkm-manager
description: "My-PKM Master Architect Skill: 옵시디언 볼트 헌법 동적 SSOT 준수, 000. Inbox 메모 분류(Triage)/링크/외과적 패치, Karpathy LLM 위키 컴파일, vault_linter 볼트 무결성 감사 및 레거시 원천자료 ETL 하위 호환"
---

# PKM Master Architect Skill (`pkm_manager`)

본 스킬은 `My-PKM` 시스템의 구글 드라이브 기반 옵시디언 볼트(`My-Wiki`)와 지식 엔지니어링 거버넌스를 총괄 제어하는 마스터 스킬입니다.

에이전트는 이 스킬을 통해 **1) 헌법 SSOT 동적 사전 검증**, **2) 원천자료 Ingestion 거버넌스 및 레거시 ETL 하위 호환**, **3) 000. Inbox 메모 분류 및 외과적 패치(Surgical Patch)**, **4) 카파시(Karpathy) LLM 위키 컴파일 순환**, 그리고 **5) vault_linter 볼트 무결성 감사**를 체계적으로 수행합니다. 외부 원천자료의 `000. Inbox` 1차 파싱 및 내장 이미지 추출은 전용 파싱 스킬인 `pkm_parse`에 위임합니다.

---

## 1. 지식 볼트 헌법 및 2계층 메타데이터 스키마

### 1.1 5대 물리 폴더 및 쓰기 주권 (Origin-Based MECE Folder & Sovereignty)
폴더는 주제(Topic)가 아니라 **생성 출처 및 가공 단계(Origin)**를 기준으로만 분리합니다.

| 폴더 경로 | `origin` | 주 관리 주체 (쓰기 주권) | 역할 및 운영 원칙 | LLM Wiki 컴파일 가중치 |
| :--- | :--- | :--- | :--- | :--- |
| `000. Inbox` | _(분류 전)_ | 사용자 / AI | 임시 메모 1차 수집 버퍼. **하위 폴더 없는 Flat 구조** | 컴파일 제외 (분류 대기) |
| `100. Concepts` | `human` | **희명님 전용**<br>(인간 주권 영역) | 사용자가 직접 작성한 통찰·분석·가설.<br>• `110. Notes`: 단일 원자적 노트<br>• `120. Logs`: 복합 일지/회의록 | **최우선 반영 (Primary Stance)**<br>희명님의 고유 관점과 철학 |
| `200. AI_logs` | `ai` | AI 에이전트 | AI와 협업 생성한 분석 및 대화.<br>• `210. Chat_Logs`: 심층 문답 기록<br>• `220. Agent_Outputs`: 자동화 봇 산출물 | **보조 참조 (Secondary Analysis)**<br>원문과 교차 검증하여 반영 |
| `300. Sources` | `source` | AI / 사용자 | 외부 원본 파일 파싱 텍스트.<br>• `310. Reports_Papers`: 리포트, 논문<br>• `320. Books_Lectures`: 도서, 강연<br>• `330. Clippings_News`: 웹 기사 스크랩<br>• `340. Work_Docs`: 사내 규정, 공문서 | **절대적 팩트 기준 (Ground Truth)**<br>수치 및 팩트의 기준점 |
| `400. Wiki` | `wiki` | AI / 사용자 | 누적 지식을 종합·연결·컴파일한 마스터 위키.<br>**하위 폴더 없는 단일 Flat 구조 유지** | **최종 산출물 (Compiled Output)**<br>볼트 전체의 백링크 허브 |
| `500. etc` | `human` | 희명님 전용 | 개인 스크랩, 취미 등 개인 보조 공간 | 컴파일 제외 |
| `900. config` | `config` | 시스템 / 사용자 | 설정, 템플릿(`930`), 첨부파일(`910`), Excalidraw(`920`) | 컴파일 제외 |

> [!WARNING]
> **인간 주권 침해 금지**: `100. Concepts`와 `500. etc`는 인간 주권 영역입니다. 사용자의 명시적 지시 없이 AI가 임의로 노트를 생성하거나 덮어쓰는(overwrite) 것은 절대 금지됩니다.

> [!IMPORTANT]
> **볼트 외부 바이너리 격리 원칙**: HWP, HWPX, PDF, XLSX, DOCX, PPTX 등 무거운 원본 바이너리는 `./My-Wiki` 볼트 내부에 절대 반입하지 않습니다. 모든 바이너리는 볼트 외부 `Inbox_Raw/` 및 `Archive_Sources/`에서 관리되며, 볼트 내부에는 `kordoc`으로 변환된 순수 `.md`만 적재됩니다.

---

### 1.2 2계층 YAML 프론트매터 스키마 (2-Tier Schema)

#### Tier 1: 7대 필수 코어 속성 (All Processed Notes)
`100`, `200`, `300`, `400`에 속하는 모든 가공 노트는 아래 7개 키를 반드시 포함해야 합니다:

```yaml
---
origin: source          # Enum: [human, ai, source, wiki] (물리 폴더와 1:1 일치 필수)
type: source            # Enum: [hub, concept, analysis, entity, source, project, log]
domain:                 # List of strings (7대 표준 도메인 중 1~2개 "주 1 + 부 1")
  - macro
up:                     # List of Wiki links ["[[...]]"] (직계 1촌 부모. 비어있을 때는 반드시 [])
  - "[[02_매크로 분석]]"
status: active          # Enum: [seed, growing, evergreen, active, completed, archived]
created: 2026-10-25     # String date: YYYY-MM-DD
updated: 2026-10-25     # String date: YYYY-MM-DD
---
```

#### Tier 2: 노트 역할(`type`)별 조건부 확장 속성 (Sparse Property)
- **`type: hub`**: `level` (1 또는 2), `summary` (한 줄 정의), `aliases` (별칭 리스트)
- **`type: concept`**: `aliases` (동의어/영문명), `formula_text` (핵심 수식 텍스트), `summary`
- **`type: analysis`**: `stance` (`bullish` | `bearish` | `neutral`), `period` (예: `2026-Q4`), `ref_date` (`YYYY-MM-DD`), `prev` (선행 분석 위키링크 리스트), `source` (인용한 원천자료 리스트), `related` (동급 분석 리스트)
- **`type: entity`**: `ticker` (종목코드), `sector` (소속 섹터 위키링크), `asset_class` (`주식` | `채권` | `대체` | `현금`), `org` (소속 기관), `role` (역할), `aliases`
- **`type: source`**: `source_type` (`book` | `report` | `paper` | `lecture` | `presentation` | `news` | `work_doc`), `author` (저자 위키링크), `org` (발행기관 위키링크), `published` (발행일), `ref_date` (기준일), `source_url` (구글 드라이브 뷰어 URL 또는 원문 웹 링크)
- **`type: project`**: `target_date` (`YYYY-MM-DD`), `account` (`연금저축` | `IRP` | `ISA` | `특회`), `priority` (`high` | `medium` | `low`)
- **`type: log`**: `ref_date` (`YYYY-MM-DD`), `participants` (참석자 리스트), `action_required` (불리언)

#### Clean Null & 유령 링크 방지 원칙
- `up`, `prev`, `source`, `related`, `author`, `org` 등 링크 배열 속성에 연결할 대상이 없을 때는 **절대로 `"[[]]"`(빈 대괄호 텍스트)를 남기지 않고, 반드시 `[]`(YAML 빈 리스트)로 표기**합니다.
- 해당 없는 확장 속성은 빈 문자열(`""`)로 채우지 않고 과감히 생략(Pruning)합니다.

#### 7대 표준 도메인 코드 (Domain Max 2 "1+1" Rule)
도메인은 다음 7개 코드 중 주 도메인 1개, 교차 성격이 있을 때만 부 도메인 1개(최대 2개)를 부여합니다:
1. `theory`: 경제 및 금융 이론, 불변의 원리 및 가치평가 모델 (`01_경제 및 금융 이론`)
2. `macro`: 글로벌 매크로 분석, 금리, 환율, 원자재, 경제지표 (`02_매크로 분석`)
3. `equity`: 섹터 밸류체인 및 개별 기업 분석, 주주환원 (`03_산업 및 기업분석`)
4. `portfolio`: 가족 투자 포트폴리오, 자산배분, 절세 계좌, 리밸런싱 (`04_가족 투자 포트폴리오`)
5. `work`: 회사업무(특별회계 자금운용), 투자전략, 사내 규정 (`05_회사업무 (자산운용)`)
6. `ai-pkm`: AI 에이전트, PKM 아키텍처, 데이터 파이프라인, 바이브코딩 (`06_AI 활용 및 PKM 구축`)
7. `education`: 자녀교육, 입시 정책, 교과 학습, 답사 기록 (`07_자녀교육`)

---

### 1.3 링크 방향성 원칙 (Centripetal $O \to B$ & Orthogonal Ladder)
1. **상향식·구심성 연결 대원칙 ($O \to B$)**:
   - 구체적이고 가변적인 하위·파생 노트가 아웃링크(**O**)를 쏘고, 추상적이고 안정적인 상위·원천 허브 노드가 백링크(**B**)를 받습니다.
2. **직계 1촌 부모 연결 (Direct 1-Hop)**:
   - 동일 축에서는 직계 1촌 부모에게만 `up` 아웃링크를 연결합니다. 조상 집계는 Dataview `up.up` 체이닝을 활용합니다.
   - 복수 `up`(다차원 상속)은 서로 다른 독립된 직교 축 간에만 예외적으로 허용합니다.
3. **2차원 시계열 사다리 (2D Orthogonal Ladder)**:
   - 수직 축: `up` 속성으로 직계 개념 위키(`400. Wiki`) 연결.
   - 수평 축: `prev` 속성으로 직전 시점의 선행 노트 연결 (`후행 O -> 선행 B`), `source` 속성으로 원천 팩트 노트 연결.
4. **원천자료 2축 아웃링크 (Source Dual-Outlink)**:
   - `300. Sources` 노트는 `up`(주제 위키)과 `author`/`org`(개체 허브) 2개 축으로 아웃링크를 쏘며 `source_url`을 필수 보존합니다.

---

## 2. 5대 핵심 워크플로우 (Workflows 1 ~ 5)

### Workflow 1: 실시간 SSOT 동적 사전 검증 (Dynamic SSOT Pre-flight)
옵시디언 볼트(`My-Wiki`)의 메모를 생성, 수정, 분류, 연결, 또는 위키를 컴파일하기 전에 항상 최신 헌법 문서를 실시간으로 읽어 검증합니다:

1. **SSOT 문서 읽기**:
   - `./My-Wiki/400. Wiki/PKM 아키텍처.md`
   - `./My-Wiki/400. Wiki/옵시디언 메모간 링크 연결 규칙 설계.md`
2. **최신 규칙 확인**:
   - 도메인 코드 정의, 신규 허브 링크, 2계층 스키마 규칙 변경 여부 확인.
   - 정적 지식이나 과거 컨텍스트의 가정을 배제하고 현재 읽은 SSOT 문서를 기준으로 행동 결정.

---

### Workflow 2: 외부 원천자료 Ingestion 거버넌스 및 레거시 ETL (`scripts/ingest_sources.py`)

> [!NOTE]
> **주 파싱 파이프라인 위임 안내**:
> 외부 원천자료(`Inbox_Raw/`)의 1차 마크다운 변환, 도표 GFM 추출, 내장 이미지 추출(`910. Attached/<doc_stem>/`), 옵시디언 위키링크 임베드 리라이팅(`![[<doc_stem>/image_XXX.png]]`), `000. Inbox/` 플랫 적재, 및 Stage 2 시맨틱 메타데이터 보강은 전용 스킬인 **`pkm_parse` (`.agents/skills/pkm_parse/scripts/parse_sources.py`)**가 주관합니다.
>
> `pkm_manager` 내의 `scripts/ingest_sources.py`는 기존 레거시 호출자 및 단위/통합 테스트 스위트와의 100% 하위 호환성을 보장하기 위해 유지되며, 변환된 노트를 `./My-Wiki/300. Sources/{subfolder}/`로 직접 적재합니다.

#### 1. 주 파싱 파이프라인 (`pkm_parse` 권장)
```bash
# pkm_parse를 통한 000. Inbox 플랫 적재 및 이미지 추출
.\.venv\Scripts\python.exe .agents/skills/pkm_parse/scripts/parse_sources.py \
  --file "Inbox_Raw/20261025_FOMC_Preview.pdf" \
  --subfolder "310. Reports_Papers" \
  --domain "macro" \
  --table-format gfm
```

#### 2. 레거시 Ingestion 파이프라인 (`scripts/ingest_sources.py` 하위 호환)
`Inbox_Raw/`에 들어온 HWP, HWPX, PDF, XLSX, DOCX, PPTX 등 미가공 바이너리를 `kordoc`으로 파싱하여 볼트 내부 `300. Sources/`에 마크다운으로 직접 적재하고 원본을 아카이빙합니다.

```bash
# 단일 파일 수동 Ingestion 예시 (300. Sources 직행)
.\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/ingest_sources.py \
  --file "Inbox_Raw/20261025_FOMC_Preview.pdf" \
  --subfolder "310. Reports_Papers" \
  --domain "macro" \
  --up "[[02_매크로 분석]]" \
  --source-type "report" \
  --table-format gfm

# Inbox_Raw 전체 배치 Ingestion 예시
.\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/ingest_sources.py \
  --inbox "./Inbox_Raw" \
  --vault "./My-Wiki" \
  --archive "./Archive_Sources" \
  --table-format gfm
```

#### 세부 처리 절차 (하위 호환)
1. **문서 스캔 및 파싱**:
   - `Inbox_Raw/` 내의 바이너리 파일을 `kordoc` 엔진(Python SDK `KordocClient` 상주 워커 또는 Node CLI)을 호출하여 파싱합니다.
   - 표 구조는 `--table-format gfm` 옵션을 통해 GitHub Flavored Markdown 표로 깔끔하게 변환합니다. 이미지 OCR 필요 시 `--ocr` 플래그를 활성화합니다.
2. **2계층 메타데이터 프론트매터 결합**:
   - 7대 코어 속성(`origin: source`, `type: source`, `domain`, `up`, `status: active`, `created`, `updated`)을 구성합니다.
   - 확장 속성(`source_type`, `author`, `org`, `published`, `ref_date`, `source_url`)을 결합합니다.
   - 빈 링크 배열은 반드시 `[]`로 처리하여 유령 링크 `"[[]]"`를 차단합니다.
3. **볼트 적재 및 원본 아카이빙 (Inbox Zero)**:
   - 생성된 마크다운을 `./My-Wiki/300. Sources/{subfolder}/{filename}.md`에 저장합니다.
   - 원본 바이너리를 `./Archive_Sources/{subfolder}/{filename}`으로 안전하게 이동하여 `Inbox_Raw/`의 Inbox Zero를 달성합니다.

---

### Workflow 3: 메모 분류, 트리거 및 외과적 패치 (Note Triage & Surgical Patching)
볼트 내 메모의 분류, 부분 수정, 링크 조정을 수행합니다.

1. **`000. Inbox` 수시 분류 (Triage)**:
   - 사용자가 `000. Inbox`에 메모를 남긴 경우, 메모의 성격과 작성 주체를 파악합니다.
   - 인간의 사유/일지라면 사용자에게 `100. Concepts` 이동을 제안/안내합니다 (주권 보호).
   - AI 생성 리서치라면 `200. AI_logs/`로, 외부 파싱 글이라면 `300. Sources/`로 이동합니다.
2. **외과적 패치 (Surgical Patching)**:
   - 전체 문서를 덮어쓰지 않고, 특정 섹션이나 헤딩, 본문 블록만 부분 수정할 때는 `obsidian:vault_patch` 도구를 우선 사용합니다.
   - 예: 특정 헤딩 하단에 신규 참고자료 불릿 추가, 프론트매터의 `updated` 일자만 갱신.
   - 옵시디언 데스크톱이 닫혀 있거나 배치 처리 시에는 로컬 정션(`./My-Wiki`)의 마크다운 파일을 정규식/AST 단위로 외과적 수정(Surgical Patch)합니다.
3. **활성 뷰포트 확인 및 열기**:
   - `obsidian:active_file_get_path`를 통해 사용자가 현재 보고 있는 노트를 확인하여 맥락을 파악합니다.
   - 신규 메모를 생성하거나 위키를 수정한 후에는 `obsidian:open_file`을 실행하여 사용자 화면에 즉시 띄웁니다.

---

### Workflow 4: 카파시(Karpathy) LLM 위키 컴파일 순환 (`400. Wiki` Synthesis)
단순한 검색(RAG)을 넘어 지식이 복리로 누적되도록 주기적으로 `400. Wiki` 마스터 문서를 재컴파일합니다.

1. **상호 링크 점진적 승격 (Lazy Cross-Linking)**:
   - 초기에는 신규 노트(A)에서 기존 노트(B)로 단방향 아웃링크($A \to B$)만 연결합니다.
   - 기존 노트(B)를 재검토할 때 백링크에 모인 A를 확인하고, 동등한 비교/융합 관계일 때만 양방향 상호 링크($A \leftrightarrow B$, `related` 속성)로 승격합니다.
2. **`400. Wiki` 종합 컴파일 주기**:
   - `100. Concepts`(인간 Stance), `200. AI_logs`(보조 분석), `300. Sources`(팩트 원천)의 하위 노트들이 일정 수준 축적되었을 때 위키 컴파일을 실행합니다.
   - `400. Wiki/{Topic}.md` 문서의 상단 종합 서술문(Comprehensive Synthesis)을 최신 합의 상태(Current State of Truth)로 재작성합니다.
   - 본문 문장 속에 근거 노트들을 인라인 링크(`[[근거노트명]]`)로 역참조 배치합니다.
   - 프론트매터의 `updated` 날짜를 오늘 시스템 날짜(`YYYY-MM-DD`)로 갱신합니다.
   - `400. Wiki`는 하위 폴더가 없는 단일 Flat 디렉터리로 유지합니다.

---

### Workflow 5: 볼트 무결성 감사 (`scripts/vault_linter.py`)
`vault_linter.py` CLI를 주기적으로 실행하여 볼트의 5대 헌법 무결성을 진단하고 자동 교정합니다.

```bash
# 전체 볼트 헌법 검사 실행
.\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/vault_linter.py --vault ./My-Wiki

# 유령 링크 등 안전한 위반 사항 자동 교정 (--fix)
.\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/vault_linter.py --vault ./My-Wiki --fix

# JSON 출력 포맷으로 감사 결과 보고
.\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/vault_linter.py --vault ./My-Wiki --format json
```

#### 5대 헌법 감사 체크리스트 (C1 ~ C5)
1. **C1. 7대 필수 코어 속성 검사**:
   - `100`, `200`, `300`, `400` 내 모든 노트에 `origin`, `type`, `domain`, `up`, `status`, `created`, `updated`가 정상 존재하는지 검증.
2. **C2. 유령 링크(`"[[]]"`) 검사 및 교정**:
   - 프론트매터나 본문에 빈 대괄호 `"[[]]"`가 존재하는지 탐지. (`--fix` 옵션 시 빈 배열 `[]`로 자동 치환).
3. **C3. 고립 노트(Orphan Note) 검사**:
   - `up` 속성이 비어 있는 노트 탐지. (단, `01_` ~ `07_` Level 1 마스터 도메인 허브는 적법한 고립 예외로 허용).
4. **C4. 폴더-origin 정합성 및 쓰기 주권 검사**:
   - `100. Concepts` ➔ `origin == human`
   - `200. AI_logs` ➔ `origin == ai`
   - `300. Sources` ➔ `origin == source`
   - `400. Wiki` ➔ `origin == wiki`
   - 불일치 발생 시 쓰기 주권 침해 또는 오분류 에러 보고.
5. **C5. 볼트 내부 바이너리 반입 검사**:
   - `./My-Wiki` 내부에 무거운 바이너리(`.pdf`, `.hwpx`, `.hwp`, `.xlsx`, `.docx`, `.pptx`, `.zip` 등)가 존재하는지 스캔하여 즉시 격리 조치 리포트. (`900. config/910. Attached`의 허용 이미지/다이어그램 제외).

---

## 3. 하이브리드 도구 사용 수칙 요약

- **UI / 인터랙티브 / 정밀 수정**: `obsidian` MCP (`active_file_get_path`, `open_file`, `vault_patch`, `search_simple`)
- **배치 / Ingestion / 린팅 감사 / 오프라인**: 로컬 정션(`./My-Wiki`, `./Inbox_Raw`, `./Archive_Sources`) 직접 파일시스템 I/O
