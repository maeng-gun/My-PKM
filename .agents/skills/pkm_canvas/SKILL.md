---
name: pkm-canvas
description: "My-PKM Obsidian JSON Canvas 1.0 Auto-Compiler (/pkm-canvas): 특정 주제나 키워드를 입력하면 My-Wiki 볼트의 지식 연결망(400. Wiki Lv1~Lv4 및 100·200·300 원천 메모)을 탐색·선별하여 노드 겹침이나 프론트매터 가림 현상(#subpath 포커싱) 없이 My-Wiki/700. utilize/Canvas_주제명.canvas 파일로 자동 컴파일하는 스킬"
---

# My-PKM Obsidian Knowledge Canvas Skill (`pkm_canvas` / `/pkm-canvas`)

본 스킬은 사용자가 특정 주제나 질문을 입력하면 `My-Wiki` 볼트의 다층 지식 연결망(`400. Wiki`의 `Lv1~Lv4` 코어 위키 및 `100·200·300` 원천 메모)을 탐색하여, **노드 겹침이나 YAML 프론트매터 가림 현상 없이 옵시디언 `.canvas`(JSON Canvas 1.0) 파일로 자동 컴파일**하는 3단계 하이브리드 파이프라인입니다.

---

## 1. 핵심 설계 원칙 (역할 분담 및 볼트 헌법 보호)

1. **의미론적 추론(LLM)과 기하학적 연산(Python CLI)의 완전 분리**:
   - **LLM 전담 영역 (Step 2)**: 후보 노트 중 핵심 노드 선별, 소주제별 군집화(`Group`), 본문 핵심 섹션 타기팅(`#subpath`), 최상단/그룹 상단 3~4줄 맥락 브리핑 카드 작성, 15자 이내 시맨틱 엣지 라벨링.
   - **Python CLI 전담 영역 (Step 1 & Step 3)**: 볼트 전역 그래프 고속 스캔, `Lv4 ➔ Lv1` 상향 직계 계보 추적 및 상위 허브 꺾임 확장 차단(Damping), 깨진 링크/별칭(`aliases`) 자동 보정, Top-to-Bottom 스윔레인 픽셀 좌표 무충돌 계산, 사용자 수동 편집(`User Notes`) 보존 및 루트 `.trash` 선격리 교체.
2. **볼트 동기화 무결성 및 헌법(`My-Wiki Rules.md`) 준수**:
   - 중간 산출물(`subgraph_<slug>.json`, `canvas_spec_<slug>.json`)은 반드시 볼트 외부인 `scratch/canvas/`에만 저장하여 구글 드라이브 동기화 오염을 원천 차단합니다.
   - 최종 `.canvas` 파일은 `My-Wiki/700. utilize/Canvas_<주제명>.canvas`에 저장하여 `400. Wiki`의 순수 마크다운 생태계를 보호하며, `14일 Rolling Window` 삭제 대상에서 **영구 제외(`Permanent`)**하고 `500. Index/_인덱스_700_Utilize.md`의 4절 레지스트리에 등재합니다.

---

## 2. 3단계 실행 워크플로우 (Step 1 ➔ Step 2 ➔ Step 3)

사용자가 `/pkm-canvas <주제>` 또는 *"~ 주제로 옵시디언 캔버스 만들어줘"*라고 요청하면 에이전트는 아래 3단계를 순서대로 실행합니다.

### Step 1: 후보 서브그래프 고속 탐색 (`canvas_explorer.py`)

주제에서 도출한 핵심 키워드(`--query`) 또는 출발 시드 노트명(`--seeds`)으로 `canvas_explorer.py`를 실행하여 후보 서브그래프 JSON을 `scratch/canvas/`에 추출합니다.

```bash
# 기본 탐색 (400. Wiki 코어 2-Hop + 위키 3개 미만 시 원천 자동 결합)
.\.venv\Scripts\python.exe .agents/skills/pkm_canvas/scripts/canvas_explorer.py \
  --vault ./My-Wiki \
  --query "핵심키워드1,핵심키워드2" \
  --output scratch/canvas/subgraph_<topic_slug>.json

# 사용자가 100·200·300 원천 메모 포함을 명시적으로 요청한 경우 (--include-sources 추가)
.\.venv\Scripts\python.exe .agents/skills/pkm_canvas/scripts/canvas_explorer.py \
  --vault ./My-Wiki \
  --query "핵심키워드1,핵심키워드2" \
  --include-sources \
  --output scratch/canvas/subgraph_<topic_slug>.json
```

* **탐색 엔진 작동 규칙**:
  - **상향 직계 계보 보존**: `Lv4` 각론 시드에서 출발해도 `up` 체인을 따라 `Lv3 ➔ Lv2 ➔ Lv1`까지 끊김 없이 추적합니다.
  - **꺾임 확장 차단 (Damping)**: 상위 허브(`Lv1·Lv2`) 도달 후 시드와 무관한 타 도메인 하위 가지로 내려가는 2-Hop 번짐을 차단합니다.
  - **안전 헤딩 추출**: 각 노드의 `clean_headings`(대괄호 `[[ ]]` 등 특수문자가 없는 순수 텍스트 `##`/`###` 헤딩)와 `default_subpath`를 추출합니다.

---

### Step 2: 의미론적 구조화 및 `canvas_spec.json` 작성 (LLM)

`read_file`로 `scratch/canvas/subgraph_<topic_slug>.json`을 열람한 뒤, 아래 설계 기준에 따라 `scratch/canvas/canvas_spec_<topic_slug>.json` 파일을 작성합니다 (스키마 정의: `.agents/skills/pkm_canvas/schemas/canvas_spec.schema.json`).

1. **핵심 노드 선별 및 스윔레인(`swimlane`) 배정**:
   - 후보 노드 중 주제 설명력이 높은 **코어 위키 6~16개** 내외(상위 계보 `Lv1~Lv2` 포함)와 필요시 **원천 리프 노트(`Source`) 3~5개**를 선별합니다.
   - `swimlane` 값은 반드시 `"Lv1"`, `"Lv2"`, `"Lv3"`, `"Lv4"`, `"Source"` 중 하나로 지정합니다.
2. **소주제 그룹(`groups`) 군집화 및 브리핑 작성**:
   - `Lv3` 및 `Lv4` 코어 위키들을 2~4개의 논리적 소주제 그룹(`groups`)으로 묶고 `order_x`(`0, 1, 2...`)를 부여합니다.
   - 캔버스 최상단 `master_briefing`(`summary_lines` 3~4줄)과 각 그룹 상단 `briefing`(3~4줄 핵심 요약)을 작성하여 문서를 열지 않고도 전체 구조와 인과관계를 한눈에 파악할 수 있게 합니다.
3. **`#subpath` 핵심 섹션 포커싱**:
   - 프론트매터 속성창이 카드를 가리는 현상을 막기 위해, 각 노드의 `subpath`에 Step 1이 추출한 `clean_headings` 중 현재 캔버스 주제와 가장 직결되는 `#헤딩명`을 지정합니다 (적절한 헤딩이 없으면 `default_subpath` 사용).
   - **주의**: 문서에 존재하지 않는 헤딩을 임의로 창작하거나 `[[위키링크]]`가 포함된 헤딩을 넣지 마세요.
4. **시맨틱 엣지(`edges`) 라벨링 및 무충돌 라우팅 규칙**:
   - `relation_type`을 지정하면 Step 3 컴파일러가 시선의 흐름과 라벨 충돌 회피에 맞춰 화살표 방향과 포트를 자동 정규화합니다:
     - `"hierarchy"`: 코어 위키 상하 소속 위계 (`Lv1 ➔ Lv2 ➔ Lv3 ➔ Lv4` 하향 화살표). **1:N 팬아웃 중점 겹침과 시각적 노이즈를 방지하기 위해 `hierarchy` 선은 라벨을 생략(`""`)하고 깔끔한 컬러 실선 화살표로만 렌더링합니다.**
     - `"related"` / `"prev"` / `"strategy_pull"` / `"source"`: 핵심 인과·전이·비교·근거 연결선에만 **10~15자 이내**의 간결한 시맨틱 라벨(예: `"모라토리엄·부채 리스크"`, `"탄광 속 카나리아"`, `"데이터센터 규제 실체"`)을 부여합니다.
     - 그룹별 요약(`briefing`)은 `Lv2 ➔ Lv3` 화살표 통로를 가로막지 않도록 최상단 `Master Briefing` 카드에 자동 통합됩니다.
     - **줌아웃 가시성 보장 및 가로 폭 최적화**: 옵시디언 캔버스는 성능을 위해 줌아웃 시 카드의 본문 텍스트를 숨기고 스켈레톤 아이콘(`≡`)으로 축소하는 내장 가상화(LOD) 엔진이 작동하므로, 상단 전체 요약 영역을 **`type: "group"`(보라색) 컨테이너로 감싸 상단 그룹 라벨(`🧭 마스터 브리핑: <주제>`)을 부여**합니다. 이를 통해 어떤 줌 레벨에서도 휑한 빈 박스 대신 선명하고 거대한 타이틀이 화면에 비춰지며, 가로 폭은 전체 캔버스 스팬의 절반(약 `1800px ~ 2000px`, 48~50%)으로 균형 있게 배치됩니다.
     - 중단 소주제 그룹(`Lv3~Lv4`) 하단과 `Source Dock` 컨테이너 상단 사이에는 `SOURCE_DOCK_GAP_Y = 560px` 이상의 넓은 수직 통로를 자동 확보하여, `Source ➔ Lv4` 엣지 설명 박스가 `Source Dock` 박스나 그룹 타이틀 탭을 가리지 않도록 보장합니다.

#### `canvas_spec.json` 작성 예시
```json
{
  "topic": "AI CAPEX 사이클과 데이터센터 전력·부채 리스크",
  "canvas_filename": "Canvas_AI_CAPEX와_전력_부채_리스크.canvas",
  "master_briefing": {
    "title": "AI CAPEX 사이클과 데이터센터 전력·부채 리스크 지식 맵",
    "summary_lines": [
      "빅테크와 네오클라우드의 AI 인프라 CAPEX 경쟁이 전력망 병목(C2) 및 사모크레딧·ABS 부채 조달 리스크(T2-S3)로 전이되는 다층 구조를 조망합니다.",
      "상단(Lv1~Lv2)은 거시·이론·밸류체인 상위 기둥을, 중단 그룹(Lv3~Lv4)은 핵심 각론과 개별 기업을, 하단 Source Dock은 핵심 원천 리포트를 배치했습니다.",
      "각 노드는 YAML 프론트매터 대신 본문 핵심 섹션(#subpath)으로 즉시 포커싱되어 있습니다."
    ]
  },
  "groups": [
    {
      "group_id": "grp_capex_bubble",
      "label": "1. AI 인프라 CAPEX 패권 경쟁과 수익성 논쟁",
      "color": "4",
      "order_x": 0,
      "briefing": "- 빅테크의 과잉투자 우려보다 과소투자(Under-investing) 리스크가 우선시되는 게임이론적 구도\n- 모델 학습에서 추론(Inference) 및 에이전틱 워크플로우로의 전환이 재원 조달 구조를 변화시킴"
    },
    {
      "group_id": "grp_debt_credit",
      "label": "2. 네오클라우드 부채 조달(ABS·CMBS) 및 수급 충격",
      "color": "1",
      "order_x": 1,
      "briefing": "- GPU 담보 대출 및 데이터센터 ABS/CMBS 발행을 통한 레버리지 확대\n- 전력 인허가 지연(모라토리엄) 시 크레딧 스프레드 확대 및 국내외 반도체 수급 발작 유발"
    }
  ],
  "nodes": [
    {
      "node_id": "n_c1",
      "note_title": "C1_AI 컴퓨팅·반도체·디지털 인프라",
      "file_path": "400. Wiki/C1_AI 컴퓨팅·반도체·디지털 인프라.md",
      "swimlane": "Lv1",
      "group_id": null,
      "role": "lineage_ancestor",
      "subpath": "#1. 밸류체인 정의 및 핵심 메커니즘",
      "color": "6",
      "order_in_row": 0
    },
    {
      "node_id": "n_capex_hub",
      "note_title": "AI 인프라 CAPEX 사이클과 빅테크·네오클라우드 패권 경쟁",
      "file_path": "400. Wiki/AI 인프라 CAPEX 사이클과 빅테크·네오클라우드 패권 경쟁.md",
      "swimlane": "Lv3",
      "group_id": "grp_capex_bubble",
      "role": "seed",
      "subpath": "#1. 핵심 정의 및 프레임워크 (Core Thesis)",
      "color": "4",
      "order_in_row": 0
    }
  ],
  "edges": [
    {
      "from_node": "n_c1",
      "to_node": "n_capex_hub",
      "relation_type": "hierarchy",
      "label": "AI 인프라 밸류체인 총괄",
      "color": "5"
    }
  ]
}
```

---

### Step 3: 픽셀 좌표 연산 및 `.canvas` 파일 컴파일 (`canvas_compiler.py`)

작성된 `canvas_spec_<topic_slug>.json`을 입력으로 `canvas_compiler.py`를 실행합니다.

```bash
.\.venv\Scripts\python.exe .agents/skills/pkm_canvas/scripts/canvas_compiler.py \
  --vault ./My-Wiki \
  --spec scratch/canvas/canvas_spec_<topic_slug>.json
```

* **컴파일러 자동 보장 사항**:
  1. **Broken Link 차단 및 `aliases` 보정**: 통폐합 등으로 이동·개명된 노트는 `aliases` 역매핑으로 실제 파일 경로를 복원하며, `.trash`로 격리된 노드는 자동 제외하여 빈 카드를 방지합니다.
  2. **수동 편집 보존 (`User Notes`)**: 동일 주제의 `.canvas`를 재생성할 때, 사용자가 옵시디언에서 직접 추가한 노드(`auto-` 프리픽스가 없는 노드)는 삭제하지 않고 우측 `✍️ User Notes (사용자 수동 편집 보존 영역)` 그룹으로 자동 이관합니다.
  3. **구버전 루트 `.trash` 선격리 (`Trash-First-Then-Write`)**: 기존 `.canvas` 파일을 구글 드라이브 루트 직속 `.trash`로 백업 이동한 뒤 새 파일을 생성하여 `(1)` 동기화 충돌 파일 생성을 원천 차단합니다.
  4. **`_인덱스_700_Utilize.md` 자동 등재**: `500. Index/_인덱스_700_Utilize.md` 하단 `4절. 인터랙티브 지식 캔버스 레지스트리` 표에 생성/갱신 내역을 자동 기록합니다.

---

## 3. 완료 보고 양식

Step 3 실행 완료 후 사용자에게 아래 항목을 간결하게 요약 보고합니다:
- 생성된 캔버스 파일 경로 (`My-Wiki/700. utilize/Canvas_<주제명>.canvas`)
- 스윔레인별(`Lv1 ~ Lv4` 및 `Source Dock`) 배치 노드 수 및 소주제 그룹 구성
- 보존된 사용자 수동 노드 수(재생성 시) 및 `_인덱스_700_Utilize.md` 레지스트리 반영 여부
