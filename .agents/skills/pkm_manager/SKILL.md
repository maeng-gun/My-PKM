---
name: pkm-manager
description: "My-PKM Master Architect Skill (Pure Dynamic SSOT): My-Wiki Rules.md 동적 헌법 준수, 000. Inbox 위키 컴파일 및 역추적 재컴파일, 상향 메타 컴파일, 500. Index 분할 인덱스 관리 및 vault_linter 무결성 감사"
---

# PKM Master Architect Skill (`pkm_manager`)

본 스킬은 `My-PKM` 시스템의 구글 드라이브 마운트 옵시디언 볼트(`./My-Wiki`)와 지식 엔지니어링 거버넌스를 총괄 제어하는 마스터 스킬입니다.

> [!IMPORTANT]
> **엔진(Skill)과 헌법(`My-Wiki Rules.md`)의 완전 분리 원칙 (Pure Dynamic Pointer Architecture)**
> - `My-Wiki/My-Wiki Rules.md`는 제미나이 앱(Spark)과 수기 작업을 통해 수시로 진화하는 **유일한 단일 마스터 헌법(Single Source of Truth)**입니다.
> - 본 스킬 파일(`SKILL.md`)과 Python CLI 도구(`constitution_loader.py`, `compile_helper.py`, `vault_linter.py`)는 변하지 않는 **Antigravity(`agy`) 전용 실행 엔진** 역할을 수행합니다.
> - **순수 동적 포인터 원칙**: 모든 볼트 규칙·스키마·컴파일 단계(`Step`/`M-Step`/`A-Step`)·위키 아키타입 및 템플릿은 `./My-Wiki/My-Wiki Rules.md`를 유일한 동적 SSOT로 삼으며, 작업 전 반드시 `constitution_loader.py --vault ./My-Wiki` 및 `--section`으로 최신 헌법 조항을 런타임 조회하여 그대로 집행합니다.
> - 따라서 `My-Wiki Rules.md`가 향후 버전으로 개정되더라도 본 스킬 문서를 다시 수정할 필요가 없습니다.

---

## 1. 런타임 환경 차이 및 파일 제어 프로토콜 (`agy` vs 제미나이 앱)

`My-Wiki` 볼트는 제미나이 앱(Spark)과 Antigravity(`agy`) 양쪽에서 관리됩니다. 에이전트는 `My-Wiki Rules.md`의 `<0>` 섹션을 읽을 때 아래의 런타임 차이를 정확히 구분하여 동작합니다:

| 구분 | 제미나이 앱 (`obsidian-vault-manager`) | Antigravity (`agy` — `pkm_manager` & `pkm_parse`) |
| :--- | :--- | :--- |
| **볼트 접근 경로** | Google Drive API (`parentId` + `title` 쿼리) | 로컬 마운트 정션 (`./My-Wiki` ➔ `G:\내 드라이브\My-Wiki`) 및 `obsidian` MCP |
| **파일 생성/수정** | Google Docs 자동 변환 방지를 위해 `application/octet-stream` 업로드 + 구버전을 `.trash`로 이동하는 **`Replace-and-Trash`** 사용 | Google Drive for Desktop(`DriveFS`)이 `.md` 확장자와 `fileId`를 자동 보존하므로 **`.trash` 백업 생성 없이 로컬 파일 I/O 및 `obsidian:vault_patch`로 직접 In-Place 수정** |
| **노트 폴더 이동** | 새 폴더에 재생성 후 구 파일 `.trash` 이동 | `compile_helper.py move-note` 또는 `shutil.move`로 **직접 이동 (In-Place Move)** |
| **외부 바이너리 파싱** | 불가 (또는 제한적) | **`pkm_parse` (`parse_sources.py`) 전담**: `Inbox_Raw/` 문서를 `kordoc` 파싱 + `910. Attached` 이미지 추출 + `DriveFS` 기반 `source_url` 생성 후 `000. Inbox/` 적재 |
| **헌법 본문 보호** | 사용자 지시 시 헌법 업데이트 | 사용자의 명시적 헌법 개정 지시가 없는 한 **`./My-Wiki/My-Wiki Rules.md` 본문은 임의 수정하지 않음** |

---

## 2. 5대 핵심 워크플로우 (Workflows 1 ~ 5)

### Workflow 1: 실시간 SSOT 동적 사전 검증 (Dynamic SSOT Pre-flight)

옵시디언 볼트(`./My-Wiki`)의 메모를 생성, 수정, 분류, 링크 연결, 또는 위키 컴파일하기 전에 **반드시** 아래 사전 검증을 먼저 수행합니다:

1. **헌법 SSOT 런타임 조회 및 동적 설정 로드 (`constitution_loader.py`)**:
   - 에이전트는 하드코딩된 규칙에 의존하지 않고, 작업 성격에 맞추어 `constitution_loader.py`를 실행하여 `./My-Wiki/My-Wiki Rules.md` 원문의 최신 조항을 실시간 조회합니다:
     ```bash
     # 사용 가능한 헌법 섹션 키 목록 확인
     .\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/constitution_loader.py --vault ./My-Wiki --list-sections

     # 핵심 메타데이터 및 폴더-origin 매핑, 500. Index 목록 확인
     .\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/constitution_loader.py --vault ./My-Wiki

     # 프론트매터 스키마, 표준 도메인, Clean Null 규칙 확인
     .\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/constitution_loader.py --vault ./My-Wiki --section schema

     # 링크 방향성(O/B/C), 1-Hop 연결, 이행적 축소 규칙 확인
     .\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/constitution_loader.py --vault ./My-Wiki --section links
     ```
2. **인간 주권 보호 (`100. Concepts`, `600. etc`) 및 바이너리 격리 준수 (불변 실행 원칙)**:
   - `100. Concepts` 및 `600. etc`(구 `500. etc`)는 인간 주권 영역이므로, 사용자의 명시적 인박스 컴파일·이동·링크 추가 지시 없이 임의로 노트를 생성하거나 본문을 왜곡·덮어쓰지 않습니다.
   - PDF, HWPX, HWP, XLSX, DOCX, PPTX 등 무거운 원본 바이너리는 볼트 내부에 절대 반입하지 않으며 `Inbox_Raw/` 및 `Archive_Sources/`에서만 관리합니다.

---

### Workflow 2: 1차 인박스 컴파일 및 역추적 파이프라인 (Inbox Compile Pipeline)

`000. Inbox`에 존재하는 모든 메모는 **'아직 위키 컴파일 및 인덱싱을 거치지 않은 대기 상태'**를 의미합니다. 사용자의 *"인박스 컴파일해 줘"* 명령 시(또는 `pkm_parse` 파싱 직후 원스톱 컴파일 요청 시) `constitution_loader.py --vault ./My-Wiki --section compile`을 실행하여 확인한 최신 헌법 컴파일 파이프라인 조항을 순서대로 실행합니다:

```bash
# 최신 컴파일 파이프라인 조항 런타임 조회
.\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/constitution_loader.py --vault ./My-Wiki --section compile
```

#### 사전 진단: `000. Inbox` 대기열 확인
```bash
.\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/compile_helper.py --vault ./My-Wiki inbox-status
```

#### Step 1 — 프론트매터 설정 (`normalize-fm`)
- `constitution_loader.py --vault ./My-Wiki --section schema`로 조회한 최신 스키마 규격에 따라 대상 메모에 맞는 프론트매터를 부여합니다.
- 구 레거시 속성이 남아 있는 메모는 `compile_helper.py normalize-fm`을 통해 깔끔히 제거하고 헌법 필수 코어/확장 속성으로 정규화합니다.
- 하나의 메모가 복수의 위키 주제를 다룰 경우 `up`에 복수의 위키링크를 지정하며(다대다 `N:M` 허용), 연결할 대상이 없을 때는 절대로 `"[[]]"`(빈 대괄호 텍스트)로 남겨두지 않고, 반드시 `[]`(YAML 빈 리스트)로 표기합니다.

```bash
.\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/compile_helper.py --vault ./My-Wiki normalize-fm \
  --file "000. Inbox/대상메모.md" \
  --origin "human" \
  --type "analysis" \
  --domain "macro,equity" \
  --up "[[글로벌 매크로 동향]],[[AI CAPEX 거품론과 코스피 급락·외국인 투매]]" \
  --status "active" \
  --ref-date "2026-09-12" \
  --summary "핵심 1줄 요약"
```

#### Step 2 — 1차 위키 컴파일 (`000. Inbox` 상태에서 수행)
1. **기존 위키 매칭 스캔**:
   - `500. Index/_인덱스_400_Wiki.md`를 스캔하여 대상 메모와 연결될 기존 각론/상위 위키(1개 또는 복수)를 탐색합니다:
     ```bash
     .\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/compile_helper.py --vault ./My-Wiki scan-index \
       --scope wiki --query "핵심키워드1,핵심키워드2"
     ```
2. **`400. Wiki` 증분 반영 또는 신규 위키 생성**:
   - 컴파일 전 반드시 `constitution_loader.py --vault ./My-Wiki --section templates`를 실행하여 헌법이 규정하는 최신 위키 아키타입 내부 구조를 확인합니다.
   - **기존 위키 존재 시**: 해당 위키 노트를 열어 헌법 표준 섹션 구조에 맞춰 핵심 논거(`200·300`) 또는 나의 관점(`100`)과 `[[메모명]]` 인라인 링크를 증분 반영하고, 위키의 `updated` 날짜와 `_인덱스_400_Wiki.md`의 최종 컴파일일을 갱신합니다.
   - **신규 핵심 주제일 경우**: `400. Wiki`에 새로운 위키를 생성하고, `500. Index/_인덱스_400_Wiki.md`의 계층 트리 및 레지스트리 테이블에 즉시 등재합니다.
   - **즉시 상향 동기화**: 신규 하위 위키가 생성되어 기존 상위 추상 위키를 `up`으로 가리키거나 핵심 테제가 반전된 경우, 연결된 상위 추상 위키의 구조 맵에도 즉시 링크와 요약을 추가합니다.

#### Step 3 — 원천(`origin`)별 폴더 이동 및 `500. Index` 원천 인덱스 등록
1. **폴더 이동 (`move-note`)**:
   - 컴파일이 완료된 메모를 `origin` 및 시리즈 성격에 따라 영구 폴더로 이동합니다:
     - `origin: human` ➔ `100. Concepts/`
     - `origin: ai` ➔ `200. AI_logs/` (조간신문 큐레이팅은 `200. AI_logs/210. 뉴스 큐레이팅/`, 산업분석 단계 리포트는 `200. AI_logs/220. 산업분석/`)
     - `origin: source` ➔ `300. Sources/`
   ```bash
   .\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/compile_helper.py --vault ./My-Wiki move-note \
     --file "000. Inbox/대상메모.md" --origin "human"
   ```
2. **분할 인덱스 등재 (`upsert-index`)**:
   - `500. Index` 내 해당 원천 인덱스(`_인덱스_100_Concepts.md`, `_인덱스_200_AI_logs.md`, `_인덱스_300_Sources.md`, `_인덱스_210_뉴스큐레이팅.md`, `_인덱스_220_산업분석.md`)의 마크다운 표에 요약 행을 추가합니다:
   ```bash
   .\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/compile_helper.py --vault ./My-Wiki upsert-index \
     --index "_인덱스_100_Concepts.md" \
     --note "대상메모" \
     --date "2026-09-12<br>(2026-10-29)" \
     --meta "`analysis`<br>`macro`, `equity`" \
     --summary "• **핵심 테제**: ...<br>• **키워드**: ..." \
     --up "[[글로벌 매크로 동향]],[[AI CAPEX 거품론과 코스피 급락·외국인 투매]]"
   ```

#### Step 4 — [신규 위키 생성 시 필수] 기존 `100·200·300` 메모 역추적 재컴파일 (Retroactive Re-compilation)
- Step 2에서 **신규 위키 노트가 생성**되었다면, 즉시 `500. Index`의 모든 원천 분할 인덱스를 전수 스캔하여 과거에 이미 `100·200·300`으로 이동된 연관 메모들을 역추적합니다:
  ```bash
  .\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/compile_helper.py --vault ./My-Wiki scan-index \
    --scope origins --query "신규위키관련키워드1,키워드2"
  ```
- 발굴된 기존 `100·200·300` 메모들의 원문을 읽어 신규 위키 본문에 통합 컴파일하고, 해당 기존 메모들의 프론트매터 `up`(다중 연결 추가) 및 분할 인덱스 표 행에도 `[[신규 위키명]]`을 추가합니다:
  ```bash
  .\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/compile_helper.py --vault ./My-Wiki upsert-index \
    --index "_인덱스_200_AI_logs.md" \
    --note "기존연관메모명" \
    --add-up "[[신규 위키명]]"
  ```

---

### Workflow 3: 2차 상향 메타 컴파일 및 다대다(`N:M`) 동기화 (Meta Compilation)

구체적인 각론/개체 위키들 위에 추상도를 높인 상위 추상(총론) 위키를 구축하고 유지보수할 때는 `constitution_loader.py --vault ./My-Wiki --section mstep`을 실행하여 확인한 최신 메타 컴파일 조항을 준수합니다:

```bash
# 최신 상향 메타 컴파일(M-Step) 규격 런타임 조회
.\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/constitution_loader.py --vault ./My-Wiki --section mstep
```

1. **클러스터 및 지연 동기화 진단 (`detect-mstep`)**:
   ```bash
   .\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/compile_helper.py --vault ./My-Wiki detect-mstep
   ```
   - 컴파일 완료 후 `detect-mstep` 진단 결과를 바탕으로 헌법 기준에 따라 상향 컴파일 후보군을 사용자에게 제안하거나(바텀업 창발), 사전 합의된 탑다운 골격 및 사용자 지시 시 실행합니다.
2. **동적 메타 컴파일 집행**:
   - **재귀적 입력 제한**: `My-Wiki Rules.md` 헌법에 따라 토큰 초과를 방지하기 위해 하위 원천 메모를 직접 읽지 않고 묶음 대상 위키 본문과 인덱스만 열람합니다.
   - **1-Hop 직계 재연결 및 이행적 축소**: 신규 상위/중간 위키 신설 시 `compile_helper.py normalize-fm`의 `--remove-up` 및 `--replace-up` 옵션을 활용하여 1-Hop 직계 연결을 원자적으로 재구성합니다.
   - **상향 동기화 이원화**: 즉시 반영 대상(신규 자식 편입, 관점 반전)과 지연 배치 반영 대상을 헌법 조항에 따라 구분하여 집행합니다.

---

### Workflow 4: 도메인별 복합 지식 구조화 규격 (Domain-Specific Structural Patterns)

독서모임, 뉴스 큐레이팅, 산업·기업 분류 체계 등 복합 지식 구조화는 세부 조항을 하드코딩하지 않고, 항상 `constitution_loader.py --vault ./My-Wiki --section cases`를 실행하여 헌법 원문의 최신 규격을 런타임 조회하여 수행합니다:

```bash
# 도메인별 복합 지식 구조화 실전 규격 런타임 조회
.\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/constitution_loader.py --vault ./My-Wiki --section cases
```

- **독서모임 & 투자 리서치 직교 구조화**: 헌법 Case 1에 정의된 주체별 분리, 수직 `up` 및 수평 시계열 사다리(`source` ➔ `prev`), 엔티티 분리 규격 준수.
- **조간신문 큐레이팅 리포트 사건 트래킹**: 헌법 Case 2에 정의된 일별 리포트 전용 인덱스 단일 귀속 및 섹션별 1-Hop 사건 태깅, 경량 타임라인 규격 준수.
- **산업·기업 다계층 위키 체계 및 N:1:N 매핑**: 헌법 Case 3에 정의된 계층별 표준 파일명 접두사, 수직 1-Hop 연결 및 개별 기업 위키의 다중 세부산업 매핑(`1:N`), 각론 ➔ 기업 ➔ 산업 모래시계 수렴·발산 컴파일 규격 준수.

---

### Workflow 5: 외부 원천자료 파싱(`pkm_parse`) 연계 및 볼트 무결성 감사 (`vault_linter.py`)

#### 1. 외부 원천자료 파싱(`pkm_parse`)과의 투트랙(Two-Track) 연계
- `Inbox_Raw/`에 반입된 PDF, HWPX, HWP, XLSX, DOCX, PPTX 문서는 전용 파싱 스킬인 **`pkm_parse` (`.agents/skills/pkm_parse/scripts/parse_sources.py`)**를 호출하여 `900. config/910. Attached/<doc_stem>/` 이미지 추출 및 `DriveFS` 기반 `source_url` 부여 후 `000. Inbox/`에 플랫 적재합니다.
- **투트랙 운영**:
  - **Track A (파싱 단독 실행)**: 사용자가 *"파싱만 해 줘"* 또는 *"인박스에 넣어 줘"*라고 지시하면 `pkm_parse`의 Stage 1~2(`000. Inbox` 적재 및 시맨틱 프론트매터 보강)까지만 수행하고 대기합니다.
  - **Track B (파싱 + 위키 컴파일 원스톱 실행)**: 사용자가 *"이 자료 파싱해서 위키에 컴파일/반영해 줘"*라고 지시하면 `pkm_parse` 실행 직후 즉시 본 스킬(`pkm_manager`)의 **Workflow 2**를 연속 실행하여 `400. Wiki` 컴파일, `300. Sources` 이동, `_인덱스_300_Sources.md` 등재 및 기존 노트 역추적 재컴파일까지 원스톱으로 완료합니다.
- *(참고: `.agents/skills/pkm_manager/scripts/ingest_sources.py`는 기존 레거시 테스트 스위트 하위 호환용으로만 유지됩니다.)*

#### 2. 볼트 헌법 및 분할 인덱스 무결성 감사 (`vault_linter.py`)
컴파일 작업 완료 후 최신 헌법 사후 감사 체크리스트(`constitution_loader.py --vault ./My-Wiki --section astep`)를 참조하고, `vault_linter.py`를 실행하여 헌법 준수 여부를 종합 검증합니다:

```bash
# 최신 헌법 통합 사후 감사(A-Step) 체크리스트 런타임 조회
.\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/constitution_loader.py --vault ./My-Wiki --section astep

# 기본 헌법 감사 (C1 코어속성/도메인, C2 유령링크, C3 고립노트, C4 폴더-origin 정합성, C5 바이너리 격리)
.\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/vault_linter.py --vault ./My-Wiki

# 분할 인덱스(500. Index) 등재 누락 여부 통합 감사 (--check-index)
.\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/vault_linter.py --vault ./My-Wiki --check-index

# 범용 그래프 위상·유령 노드·이행적 축소 감사 (--check-astep: C7, C8)
.\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/vault_linter.py --vault ./My-Wiki --check-astep

# C2. 유령 링크("[[]]") 및 이스케이프된 프론트매터(\---) 발견 시 --fix 옵션을 통해 clean null []로 자동 교정
.\.venv\Scripts\python.exe .agents/skills/pkm_manager/scripts/vault_linter.py --vault ./My-Wiki --fix
```
