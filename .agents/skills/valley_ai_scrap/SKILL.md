---
name: valley-ai-scrap
description: >-
  Valley AI 사이트의 '월가 소식' 및 '오늘의 인사이트' 게시판에서 
  특정 날짜 범위의 게시물을 추출하여 My-Wiki/000. Inbox에 마크다운 파일로 저장하는 스킬입니다.
---

# Valley AI 매크로 뉴스 스크랩 스킬 (valley_ai_scrap)

이 스킬은 사용자의 지시(자연어 날짜)를 해석하여, 결정론적인 파이썬 스크립트(`.agents/skills/valley_ai_scrap/scripts/scrap_valley_news.py`)를 통해 크롤링 파이프라인을 구동하고 마크다운 파일로 저장하는 역할을 수행합니다.

## 작동 규칙 (규범적 지시사항)

1. **사용자 요청 분석 및 시작일 자동 결정**:
   - 사용자가 "이번 주 소식 긁어와", "어제 뉴스 스크랩해줘"와 같이 특정 날짜/기간을 지시하면, 현재 시스템 날짜를 기준으로 정확한 `YYYY-MM-DD` 형태의 `start_date`와 `end_date`를 도출하세요.
   - 예: 사용자가 "오늘"을 지시하면 `start_date`와 `end_date`는 모두 오늘 날짜입니다.
   - **시작일자를 따로 정하지 않는 경우 (자동 증분 수집)**:
     * `My-Wiki/300. Sources/310. 밸리 AI 리포트` 폴더에 있는 `밸리AI 오늘의 인사이트_YYYY-MM-DD.md`와 `밸리AI 월가소식 리포트_YYYY-MM-DD.md` 파일 중에서 각각 기준일이 가장 최근인 날짜를 찾고, **그 다음날(`최근 기준일 + 1일`)**을 각 게시판의 스크랩 대상 시작일자로 설정합니다.
     * 스크립트 실행 시 `--start` 인자를 생략하면 스크립트가 자동으로 위 폴더를 스캔하여 각 게시판별 다음날부터 종료일(`--end`, 생략 시 오늘 날짜)까지 스크랩을 수행합니다.

2. **파이썬 스크립트 실행 및 저장 규격**:
   - 프로젝트 루트의 가상환경(`.venv`) 인터프리터를 우선적으로 사용하여 스크립트를 구동하세요.
     * 시작일 미지정 (자동 증분 수집, 오늘자까지):
       - Windows: `.\.venv\Scripts\python.exe .agents/skills/valley_ai_scrap/scripts/scrap_valley_news.py`
       - Linux/macOS: `./.venv/bin/python .agents/skills/valley_ai_scrap/scripts/scrap_valley_news.py`
     * 특정 시작일/종료일 지정 시:
       - Windows: `.\.venv\Scripts\python.exe .agents/skills/valley_ai_scrap/scripts/scrap_valley_news.py --start <YYYY-MM-DD> --end <YYYY-MM-DD>`
       - Linux/macOS: `./.venv/bin/python .agents/skills/valley_ai_scrap/scripts/scrap_valley_news.py --start <YYYY-MM-DD> --end <YYYY-MM-DD>`
     * 만약 `.venv`가 없다면 현재 활성화된 가상환경의 `python` 명령어로 실행합니다.
   - **저장 위치**: 기본적으로 볼트 1차 수집 대기열인 `My-Wiki/000. Inbox/`에 플랫 저장됩니다. (필요 시 `--output-dir` 옵션으로 변경 가능)
   - **파일명 및 헤더 규칙**:
     * 월가 소식: `밸리AI 월가소식 리포트_YYYY-MM-DD.md` (상단 헤더: `# 밸리AI 월가소식 리포트 (YYYY-MM-DD)`)
     * 오늘의 인사이트: `밸리AI 오늘의 인사이트_YYYY-MM-DD.md` (상단 헤더: `# 밸리AI 오늘의 인사이트 (YYYY-MM-DD)`)
   - **프론트매터 처리 원칙**: 스크랩 단계에서는 프론트매터를 부여하지 않고 순수 마크다운으로 적재하며, 추후 `pkm-manager`의 인박스 컴파일 단계에서 일괄 정규화 및 메타데이터를 부여합니다.
   - 작업 디렉토리(CWD)는 프로젝트의 루트 폴더여야 합니다.

3. **결과 보고 및 모듈화 종료 (Handoff)**:
   - 스크립트 실행이 완료되면, 터미널에 출력된 stdout(표준 출력) 내용을 읽고 사용자에게 요약하여 보고하세요.
   - "월가 소식 O건, 인사이트 X건 수집이 완료되어 `My-Wiki/000. Inbox/`에 저장되었습니다."라고 명확히 안내합니다.
   - 해당 날짜에 수집된 데이터가 없다면(0건) 그 사실도 투명하게 전달합니다.
   - **중요**: 이 스킬은 순수 데이터 수집용이므로, 결과를 보고한 뒤에는 추가적인 분석 스킬을 알아서 호출하지 말고 **대기 상태(단순 종료)**로 들어가십시오.
