---
name: pkm-clearing
description: "My-PKM Vault Clearing Skill (/pkm-clearing): 000~500 폴더(하위폴더 포함) 내 동기화 충돌/복제 접미사((1), (2), (conflict ...), (copy), (충돌 ...)) 스크리닝, 접미사 제거 및 동일 제목 다중 메모 최신본 자동 통합"
---

# My-PKM Vault Clearing Skill (`pkm_clearing` / `/pkm-clearing`)

본 스킬은 구글 드라이브(DriveFS) 및 다중 디바이스 동기화 과정에서 빈번하게 발생하는 **파일명 충돌 접미사(`(conflict ...)`) 및 중복 번호(`(1)`, `(2)`, `(copy)`, `(충돌 ...)`)**를 볼트 전역에서 자동으로 스크리닝하고 정규화·통합하는 전용 지식 볼트 클리닝 스킬입니다.

---

## 1. 핵심 목적 및 동작 원칙

1. **위키링크 무결성 복원**: 파일명 뒤에 ` (1)`이나 ` (conflict ...)`가 붙어 깨져버린 옵시디언 위키링크(`[[노트명]]`)를 원래 제목으로 원복하여 즉각 정상화합니다.
2. **단일 메모 접미사 제거**: 원본 파일 없이 충돌/번호 접미사만 붙어 있는 파일은 접미사를 떼어내어 순수 원본 제목으로 복원합니다.
3. **다중 충돌 메모 결정론적 통합**: 동일 기본 제목을 가진 파일이 2개 이상 존재하는 경우, **가장 나중에 생성/수정된 최신 버전(Winner)**을 채택하여 접미사를 떼고 유지하며, 구버전(Loser)은 안전하게 정리합니다.
4. **절대적 데이터 보존 (Safe Backup)**: 정리 대상이 되는 모든 파일은 삭제·변경 전 반드시 볼트 외부의 백업 디렉토리에 타임스탬프 기반으로 자동 복사(사전 백업)됩니다.

---

## 2. 감지 대상 폴더 및 정규식 패턴

### 2.1 스캔 대상 폴더 (000 ~ 500 전역 하위폴더 포함)
* `000. Inbox`: 1차 수집 대기열
* `100. Concepts`: 인간 주권 통찰 메모
* `200. AI_logs`: AI 협업 리서치 로그 (하위 `210.`, `220.` 등 포함)
* `300. Sources`: 원천 자료 파싱본
* `400. Wiki`: 종합 컴파일된 각론/총론 위키 노트
* `500. Index`: MOC 및 분할 인덱스 레지스트리

### 2.2 충돌/복제 접미사 정규식 패턴
```regex
\s*\((?:conflict[^)]*|\d+|copy|충돌[^)]*)\)$
```
* **매칭 예시**:
  - `산업_바이오 연료 (conflict 2026-10-31-14-12-57).md` ➔ `산업_바이오 연료.md`
  - `T1_거시경제·성장 및 경기순환 이론 (1).md` ➔ `T1_거시경제·성장 및 경기순환 이론.md`
  - `기업_Alphabet(GOOGL) (2).md` ➔ `기업_Alphabet(GOOGL).md`
  - `메모명 (copy).md` ➔ `메모명.md`
  - `메모명 (충돌 2026-10-31).md` ➔ `메모명.md`

---

## 3. 실행 방법 (CLI Commands)

가상환경 Python을 통해 전용 엔진(`vault_clearing.py`)을 구동합니다:

### 3.1 기본 실행 (실제 정리 및 자동 사전 백업)
```bash
.\.venv\Scripts\python.exe .agents/skills/pkm_clearing/scripts/vault_clearing.py --vault ./My-Wiki
```

### 3.2 시뮬레이션 모드 (Dry-run: 실제 파일 변경 없이 대상 목록만 미리보기)
```bash
.\.venv\Scripts\python.exe .agents/skills/pkm_clearing/scripts/vault_clearing.py --vault ./My-Wiki --dry-run
```

### 3.3 백업 위치 지정 또는 특정 폴더만 스캔
```bash
# 특정 백업 폴더 지정
.\.venv\Scripts\python.exe .agents/skills/pkm_clearing/scripts/vault_clearing.py --vault ./My-Wiki --backup-dir ./my_backups

# 특정 폴더(예: 400. Wiki)만 한정 스캔
.\.venv\Scripts\python.exe .agents/skills/pkm_clearing/scripts/vault_clearing.py --vault ./My-Wiki --folders "400. Wiki"
```

---

## 4. 슬래시 커맨드 `/pkm-clearing` 워크플로우

사용자가 대화창에서 `/pkm-clearing` 또는 *"충돌 메모 정리해줘"*, *"뒤에 (1) 붙은 거 떼줘"* 등의 지시를 내리면 에이전트는 다음 절차를 즉시 수행합니다:

1. **사전 검사**: `vault_clearing.py --vault ./My-Wiki --dry-run`으로 정리 대상 건수 및 그룹 확인
2. **클리닝 및 통합 집행**: `vault_clearing.py --vault ./My-Wiki` 실행 (자동 백업 및 파일 정리)
3. **사후 무결성 검증**: 잔여 충돌 파일 0건 여부 및 `vault_linter.py` 실행을 통한 볼트 헌법 검증
4. **결과 리포트 출력**: 단일 복원 건수, 다중 버전 통합 건수, 최신본 유지 내역을 사용자에게 간결한 표로 보고
