# My-PKM (Personal Knowledge Management Agent Hub & Global Macro Portfolio Analyzer)

이 프로젝트는 구글 드라이브 기반의 옵시디언 볼트(`My-Wiki`), 외부 원천자료 수집 파이프라인(`Inbox_Raw` ➔ `Archive_Sources`), 한국형 문서 파서 `kordoc`을 결합한 개인지식관리(PKM) 에이전트 허브이자, 일일 거시경제 리포트와 뉴스를 수집/분석하여 8대 매크로 자산군에 대한 정량 파라미터를 산출하고 TAA(Tactical Asset Allocation) 리밸런싱 액션 플랜을 도출하는 퀀트 포트폴리오 관리 시스템입니다.

---

## 🚀 Google Drive 로컬 가상 드라이브 연동 (`gdrive-storage`)

이 프로젝트는 무거운 데이터 및 결과물(`input_staging`, `scratch`, `archive`)과 GitHub에 올릴 수 없는 보안 필수 파일(`.env`, `auth_state.json` 등)을 Google Drive 데스크톱 앱 기반의 가상 드라이브와 **디렉터리 정션(Junction)**으로 연동하여 실시간 클라우드 동기화합니다.

* **로컬 I/O 속도 보장**: 모든 읽기/쓰기는 로컬 가상 드라이브 속도로 즉시 처리됩니다.
* **백그라운드 자동 동기화**: Google Drive 데스크톱 앱이 변경 사항을 백그라운드에서 실시간 클라우드 업로드/다운로드합니다.
* **기존 코드 무수정**: 모든 파이썬 스크립트와 워크플로우는 기존 로컬 상대경로 그대로 동작합니다.

---

## 💻 새로운 PC(다른 환경)에서의 1회 초기 설정 방법

GitHub에서 이 저장소를 새로 `git clone` 한 새로운 PC 환경에서는 다음 순서로 1회만 설정하면 즉시 모든 환경이 복원됩니다:

### 1. 사전 준비
1. PC에서 **Google Drive 데스크톱 앱**이 실행 및 로그인되어 있는지 확인합니다. (가상 드라이브 마운트 상태)
2. `agy-global-skills`의 글로벌 스킬이 배포되어 있는지 확인합니다. (미배포 시 `agy-global-skills`에서 `.\deploy.ps1` 실행)

### 2. 원클릭 초기화 명령어 실행
프로젝트 루트 폴더에서 아래 명령어를 1회 실행합니다:

```bash
# Windows
py ~/.gemini/config/skills/gdrive-storage/scripts/gdrive_manager.py init

# 또는
python ~/.gemini/config/skills/gdrive-storage/scripts/gdrive_manager.py init
```

### 3. 자동 처리 내용
1. 구글 드라이브 내 워크스페이스(`내 드라이브\Antigravity_Workspaces\My-PKM\`)를 자동 감지합니다.
2. `input_staging`, `scratch`, `archive`, `secrets` 폴더가 구글 드라이브와 1:1 정션(`mklink /J`)으로 즉시 연결됩니다.
3. 구글 드라이브 `secrets/` 금고에 보관된 최신 `.env`와 `auth_state.json` 파일이 프로젝트 루트로 자동 복원됩니다.
4. 모든 설정이 완료되어 기존 스크립트들을 즉시 실행할 수 있습니다.

---

## 📁 주요 폴더 및 파일 구성

* `input_staging/`: 수집된 매크로 기사 및 PDF/마크다운 파일 (구글 드라이브 정션)
* `scratch/`: 임시 파싱 결과, 퀀트 엔진 연산 중간 JSON 등 (구글 드라이브 정션)
* `archive/`: 최종 분석 리포트 마크다운 보관소 (구글 드라이브 정션)
* `secrets/`: 보안 필수 파일 마스터 보관소 (구글 드라이브 정션)
* `.env`: Supabase, Valley AI, Notion API 설정 (루트에 유지되며 `secrets/`와 동기화)
* `auth_state.json`: Valley AI 로그인 인증 세션 (루트에 유지되며 `secrets/`와 동기화)
* `.gdrive_config.json`: 구글 드라이브 연동 설정 메타데이터
