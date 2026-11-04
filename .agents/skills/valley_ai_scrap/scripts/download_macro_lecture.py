#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
밸리 AI 글로벌 매크로 실전편 강의자료 다운로더 (Valley AI Macro Lecture Downloader)

주요 기능:
1. Dynamic Course Curriculum Traversal: 강의 랜딩 페이지 Next.js RSC 페이로드 파싱을 통한 전 회차(1~9회차, 27개 강의) 동적 추출
2. Filtering: 2회차 1강 ~ 9회차 3강 (24개 챕터) 및 커스텀 회차/강의 범위 필터링 (--start-round, --end-round, --start-lecture, --end-lecture)
3. Graceful Skipping: 강의자료가 없는 챕터(예: 1회차 2강, 3강) 예외 없이 정상 로깅 및 건너뜀
4. Standardized Deterministic Naming: {회차}_{강}_{정제된강의명}.pdf 형식 보장 (Windows 금지문자 치환, 공백/마침표 정돈)
5. Session Persistence & Auto-Relogin: auth_state.json 재사용 및 만료 시 .env 계정 자동 재로그인
6. Hydration Race Condition Protection: wait_for(state="attached", timeout=5000)를 통한 React 클라이언트 마운트 대기
7. Anti-False-Positive Skip Protection: /login 리다이렉트 감지를 통한 세션 만료와 0개 첨부파일의 엄격한 분리
8. Ephemeral Page Architecture: 단일 BrowserContext 내 챕터별 독립 Page 생성 및 finally 해제 (메모리 누수 방지)
9. Smart Resume & Atomic Staging: 이미 유효한 파일 스킵, 임시 .tmp 다운로드 후 사전 검증 및 원자적 os.replace 적용 (--force 지원)
10. PDF Pre-Parse Validation Gateway: 파일 크기(>= 1KB), 헤더(b'%PDF'), 테일(b'%%EOF'), 정규식 파일명 5단계 무결성 검증
11. Dry-Run Mode: 실제 다운로드 없이 대상 인벤토리 및 상태 출력 (--dry-run)
"""

import argparse
import json
import os
from pathlib import Path
import random
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ==========================================
# 글로벌 상수 및 기본 설정
# ==========================================
AUTH_FILE = "auth_state.json"
BASE_URL = "https://www.valley.town"
COURSE_URL = f"{BASE_URL}/training/global-macro-advanced"
DEFAULT_TARGET_DIR = r"G:\내 드라이브\Inbox_temp"

MAX_RETRIES = 2
RETRY_BASE_DELAY = 2.0
MIN_JITTER = 1.5
MAX_JITTER = 2.5


def load_env() -> None:
    """외부 패키지(python-dotenv 등) 없이 .env 파일을 파싱하여 os.environ에 로드합니다."""
    search_paths = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(Path(__file__).resolve().parents[4], ".env") if len(Path(__file__).resolve().parents) >= 5 else "",
    ]
    for env_path in search_paths:
        if env_path and os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v
            break


def sanitize_filename(name: str) -> str:
    r"""
    Windows 파일명 금지 문자를 밑줄(_)로 치환하고 공백 및 마침표를 정돈합니다.
    1. Windows 예약 금지 문자 치환: \ / : * ? " < > |
    2. 연속된 공백(탭, 줄바꿈 포함)을 단일 공백으로 압축
    3. 앞뒤 공백 및 마침표(Windows 파일시스템 특성상 제거되는 dot) 스트립
    """
    name = re.sub(r'[\\/*?:"<>|]', '_', name)
    name = re.sub(r'\s+', ' ', name)
    name = name.strip(' .')
    return name


def validate_pdf_pre_parse(pdf_path: Path | str, check_filename: bool = True) -> Tuple[bool, str]:
    r"""
    다운로드된 PDF 파일이 PKM 파싱 게이트웨이 사양을 충족하는지 5단계로 검증합니다.
    1. 파일 존재 여부 (is_file)
    2. 크기 사양 (size >= 1024 bytes)
    3. 매직 헤더 바이트 (header starts with b'%PDF')
    4. 테일 EOF 마커 (마지막 1024바이트 내 b'%%EOF' 존재)
    5. 파일명 패턴 정규식 (선택적, ^\d+회차_\d+강_.+\.pdf$)
    """
    p = Path(pdf_path)
    if not p.exists():
        return False, "FILE_NOT_FOUND"
    if not p.is_file():
        return False, "NOT_A_REGULAR_FILE"

    try:
        size = p.stat().st_size
    except OSError as e:
        return False, f"STAT_ERROR ({e})"

    if size < 1024:
        return False, f"SIZE_UNDER_1KB ({size} bytes)"

    try:
        with open(p, "rb") as f:
            header = f.read(10)
            if not header.startswith(b"%PDF"):
                return False, f"INVALID_HEADER_MAGIC ({header[:4]!r})"

            f.seek(max(0, size - 1024))
            tail = f.read(1024)
            if b"%%EOF" not in tail:
                return False, "MISSING_EOF_MARKER"
    except Exception as e:
        return False, f"IO_ERROR ({e})"

    if check_filename and not re.match(r"^\d+회차_\d+강_.+\.pdf$", p.name):
        return False, f"INVALID_FILENAME_PATTERN ({p.name})"

    return True, "VALID_PDF"


def extract_macro_curriculum(html_text: str) -> Optional[List[Dict[str, Any]]]:
    """
    Valley AI 강의 랜딩 페이지 HTML에서 Next.js RSC(React Server Component) 페이로드를
    브래킷 깊이 매칭 알고리즘으로 파싱하여 전 회차/챕터 커리큘럼 데이터 구조를 추출합니다.
    """
    for m in re.finditer(r'\\"parts\\":\s*\[', html_text):
        idx = m.start()
        window = html_text[idx:idx + 5000]
        # 강의 목차 전용 컴포넌트 props 식별 (실전편 / 1960년대 / lectureType)
        if r'\"lectureType\"' in window and (r'실전편' in window or r'1960년대' in window or r'글로벌' in window):
            parts_start = m.end() - 1
            depth = 0
            in_string = False
            escape = False
            parts_end = -1
            for i in range(parts_start, len(html_text)):
                ch = html_text[i]
                if escape:
                    escape = False
                    continue
                if ch == '\\':
                    escape = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if not in_string:
                    if ch == '[':
                        depth += 1
                    elif ch == ']':
                        depth -= 1
                        if depth == 0:
                            parts_end = i
                            break
            if parts_end != -1:
                raw_parts = html_text[parts_start:parts_end + 1]
                unescaped = raw_parts.replace('\\"', '"').replace('\\\\', '\\').replace('\\/', '/')
                try:
                    return json.loads(unescaped)
                except Exception:
                    continue
    return None


def build_curriculum_inventory(parts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    RSC 커리큘럼 트리에서 각 회차별 챕터를 순회하여
    정규화된 번호, 제목, 파일명, 슬라이드 강의자료 ID 인벤토리 목록을 생성합니다.
    """
    inventory: List[Dict[str, Any]] = []

    for p_idx, part in enumerate(parts):
        part_key = part.get("partKey", "").strip() or f"{p_idx + 1}회차"
        part_title = part.get("partTitle", "").strip()

        m_part = re.search(r"(\d+)\s*회차", part_key)
        round_num = int(m_part.group(1)) if m_part else (p_idx + 1)

        chapters = part.get("chapters", [])
        for c_idx, chap in enumerate(chapters):
            chap_key = chap.get("chapterKey", "").strip() or f"{c_idx + 1}강"
            chap_title = chap.get("chapterTitle", "").strip()

            m_chap = re.search(r"(\d+)\s*강", chap_key)
            lecture_num = int(m_chap.group(1)) if m_chap else (c_idx + 1)

            clean_title = sanitize_filename(chap_title)
            expected_filename = f"{part_key}_{chap_key}_{clean_title}.pdf"

            lectures = chap.get("lectures", [])
            slide_materials = [
                lec for lec in lectures
                if isinstance(lec, dict)
                and lec.get("lectureType") == "material"
                and re.search(r"강의\s*자료", lec.get("lectureTitle", ""))
            ]

            other_materials = [
                lec for lec in lectures
                if isinstance(lec, dict)
                and lec.get("lectureType") == "material"
                and not re.search(r"강의\s*자료", lec.get("lectureTitle", ""))
            ]

            slide_lec = slide_materials[0] if slide_materials else None
            slide_id = slide_lec.get("lectureId") if slide_lec else None
            slide_title = slide_lec.get("lectureTitle") if slide_lec else None

            inventory.append({
                "round_num": round_num,
                "lecture_num": lecture_num,
                "part_key": part_key,
                "part_title": part_title,
                "chapter_key": chap_key,
                "chapter_title": chap_title,
                "clean_title": clean_title,
                "expected_filename": expected_filename,
                "has_slide": bool(slide_id),
                "slide_id": slide_id,
                "slide_title": slide_title,
                "total_materials": len(slide_materials) + len(other_materials),
                "raw_chapter": chap,
            })

    return inventory


def get_authenticated_context(
    p: Any,
    session_file: str = AUTH_FILE,
    headless: bool = True
) -> Tuple[Browser, BrowserContext]:
    """
    session_file(auth_state.json)을 로드하여 세션 유효성을 확인하고,
    만료 시 .env 계정 정보(VALLEY_EMAIL, VALLEY_PASSWORD)로 자동 재로그인합니다.
    """
    load_env()
    email = os.getenv("VALLEY_EMAIL")
    password = os.getenv("VALLEY_PASSWORD")

    browser = p.chromium.launch(headless=headless)
    context_kwargs: Dict[str, Any] = {}
    if os.path.exists(session_file):
        context_kwargs["storage_state"] = session_file

    context = browser.new_context(**context_kwargs)
    test_page = context.new_page()

    print("[Auth] 세션 유효성 검사 중...", flush=True)
    try:
        test_page.goto(f"{BASE_URL}/premium/lounge", wait_until="domcontentloaded", timeout=15000)
        test_page.wait_for_timeout(1500)
    except Exception as e:
        print(f"[Auth 경고] 세션 검사 페이지 접속 지연 ({e}), 계속 진행합니다.", flush=True)

    if "/login" in test_page.url:
        print("[Auth] 기존 세션이 만료되어 자동 로그인을 시도합니다...", flush=True)
        test_page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded", timeout=30000)
        test_page.wait_for_timeout(1000)

        if not email or not password:
            print("[Auth 오류] .env에 VALLEY_EMAIL 또는 VALLEY_PASSWORD가 설정되어 있지 않습니다.", flush=True)
            test_page.close()
            context.close()
            browser.close()
            raise RuntimeError("Missing VALLEY_EMAIL or VALLEY_PASSWORD in .env")

        test_page.fill('input[name="email"]', email)
        test_page.fill('input[name="password"]', password)
        test_page.click('button[type="submit"]')
        test_page.wait_for_timeout(6000)

        if "/login" in test_page.url:
            print("[Auth 오류] 로그인 실패! 이메일 및 비밀번호를 확인해주세요.", flush=True)
            test_page.close()
            context.close()
            browser.close()
            raise RuntimeError("Authentication failed: invalid credentials or login rejected")

        print(f"[Auth] 로그인 성공! 새로운 세션을 저장합니다 -> {session_file}", flush=True)
        context.storage_state(path=session_file)

    print("[Auth] 인증 세션 준비 완료.", flush=True)
    test_page.close()
    return browser, context


def fetch_curriculum_from_page(
    context: BrowserContext,
    course_url: str = COURSE_URL
) -> List[Dict[str, Any]]:
    """
    강의 메인 페이지에 접속하여 Next.js RSC 페이로드를 읽고
    전 회차 인벤토리를 생성합니다. Ephemeral Page 패턴을 사용합니다.
    """
    page = context.new_page()
    try:
        print(f"[Curriculum] 코스 페이지 접속 중: {course_url} ...", flush=True)
        page.goto(course_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)

        if "/login" in page.url:
            raise RuntimeError(f"접근 거부: 코스 페이지가 로그인 페이지로 리다이렉트되었습니다 ({page.url})")

        content = page.content()
        parts = extract_macro_curriculum(content)
        if not parts:
            raise RuntimeError("코스 페이지 HTML에서 커리큘럼 RSC 페이로드를 추출하지 못했습니다.")

        inventory = build_curriculum_inventory(parts)
        print(f"[Curriculum] 총 {len(parts)}개 회차, {len(inventory)}개 챕터 인벤토리 추출 성공.", flush=True)
        return inventory
    finally:
        page.close()


def filter_inventory(
    inventory: List[Dict[str, Any]],
    start_round: int = 2,
    end_round: int = 9,
    start_lecture: int = 1,
    end_lecture: int = 3,
    specific_round: Optional[int] = None,
    specific_lecture: Optional[int] = None,
    include_all: bool = False
) -> List[Dict[str, Any]]:
    """
    CLI 인자에 따라 커리큘럼 인벤토리를 필터링합니다.
    - include_all이 True이면 1회차 1강 ~ 9회차 3강 전체
    - specific_round/specific_lecture가 지정되면 단일 회차/강의
    - 기본값은 start_round(2) ~ end_round(9), start_lecture(1) ~ end_lecture(3)
    """
    if include_all:
        start_round, end_round = 1, 9
        start_lecture, end_lecture = 1, 3
    elif specific_round is not None:
        start_round = end_round = specific_round
        if specific_lecture is not None:
            start_lecture = end_lecture = specific_lecture

    filtered: List[Dict[str, Any]] = []
    for item in inventory:
        r = item["round_num"]
        lec = item["lecture_num"]
        if start_round <= r <= end_round:
            if start_lecture <= lec <= end_lecture:
                filtered.append(item)

    return filtered


def download_single_chapter(
    context: BrowserContext,
    item: Dict[str, Any],
    target_dir: str = DEFAULT_TARGET_DIR,
    force: bool = False
) -> Dict[str, Any]:
    """
    단일 챕터의 강의자료 슬라이드 PDF를 다운로드합니다.
    - Ephemeral Page 패턴 적용 (context.new_page() -> try-finally page.close())
    - 강의자료가 없는 경우 (has_slide=False) Graceful Skip 수행
    - 기존 파일 존재 및 무결성 충족 시 Smart Resume 스킵
    - .tmp 임시 파일 다운로드 -> 5단계 PDF 사전 무결성 검증 -> os.replace 원자적 이동
    - 일시적 네트워크 장애에 대해 지수 백오프 기반 최대 2회 재시도 (MAX_RETRIES)
    """
    dest_name = item["expected_filename"]
    dest_path = Path(target_dir) / dest_name

    # 1. 강의자료 슬라이드 존재 여부 확인 (Graceful Skip)
    if not item["has_slide"] or not item["slide_id"]:
        print(f"  [건너뜀] {item['part_key']} {item['chapter_key']}: 강의자료(material) 슬라이드가 없습니다.", flush=True)
        return {"status": "skipped_no_material", "filename": dest_name, "reason": "NO_SLIDE_MATERIAL"}

    # 2. Smart Resume 검사 (이미 다운로드되어 유효한 파일 스킵)
    if not force and dest_path.exists():
        is_valid, reason = validate_pdf_pre_parse(dest_path, check_filename=True)
        if is_valid:
            size = dest_path.stat().st_size
            print(f"  [스킵] {dest_name} (이미 존재하는 유효한 PDF, {size:,} bytes)", flush=True)
            return {"status": "skipped_existing", "filename": dest_name, "path": str(dest_path), "size": size}
        else:
            print(f"  [재다운로드] {dest_name} 기존 파일이 손상되었거나 유효하지 않음 ({reason}), 다시 다운로드합니다.", flush=True)

    target_lecture_url = f"{COURSE_URL}/lecture/{item['slide_id']}"
    last_error: Optional[Exception] = None

    for attempt in range(MAX_RETRIES + 1):
        page = context.new_page()
        tmp_path = dest_path.with_suffix(f".tmp.{os.getpid()}_{int(time.time()*1000)}")
        try:
            print(f"  -> [{attempt + 1}/{MAX_RETRIES + 1}] {item['part_key']} {item['chapter_key']} 접속 중 ({target_lecture_url})...", flush=True)
            page.goto(target_lecture_url, wait_until="domcontentloaded", timeout=30000)

            # 3. Anti-False-Positive Skip 방지: 세션 만료로 인한 /login 리다이렉트 감지
            if "/login" in page.url:
                raise RuntimeError("페이지가 /login으로 리다이렉트되었습니다. 세션이 만료되었습니다.")

            # 4. React Client Hydration Race Condition 방지: 첨부파일 링크 attached 대기
            attachment_links = page.locator("a[href*='/attachment/']")
            try:
                attachment_links.first.wait_for(state="attached", timeout=5000)
                count = attachment_links.count()
            except Exception:
                count = 0

            if count == 0:
                print(f"  [건너뜀] {dest_name}: 강의 페이지 내 첨부파일 링크(a[href*='/attachment/']) 없음", flush=True)
                return {"status": "skipped_no_attachment", "filename": dest_name, "reason": "ATTACHMENT_LINK_NOT_FOUND"}

            first_link = attachment_links.first
            link_text = first_link.inner_text().strip() or "강의자료"
            print(f"     첨부파일 링크 확인: '{link_text}' (총 {count}개 발견, 첫 번째 슬라이드 다운로드 시작)", flush=True)

            # 5. 다운로드 이벤트 트리거 및 임시 경로 저장
            with page.expect_download(timeout=30000) as download_info:
                first_link.click()
            download = download_info.value

            download.save_as(str(tmp_path))

            # 6. PDF Pre-Parse Gateway 바이너리 사전 검증 (임시 파일 상태에서 검증)
            is_valid, val_reason = validate_pdf_pre_parse(tmp_path, check_filename=False)
            if not is_valid:
                tmp_path.unlink(missing_ok=True)
                raise ValueError(f"다운로드된 PDF 사전 검증 실패: {val_reason}")

            # 7. 원자적 치환 (os.replace) 및 Windows 공유 위반(Sharing Lock) 재시도
            os.makedirs(target_dir, exist_ok=True)
            replace_succeeded = False
            for r_attempt in range(3):
                try:
                    os.replace(tmp_path, dest_path)
                    replace_succeeded = True
                    break
                except PermissionError:
                    time.sleep(1.0)

            if not replace_succeeded:
                tmp_path.unlink(missing_ok=True)
                raise PermissionError(f"대상 파일({dest_path}) 치환 중 공유 위반(Lock) 발생")

            # 8. 최종 커밋 파일 재검증 (파일명 정규식 포함)
            final_valid, final_reason = validate_pdf_pre_parse(dest_path, check_filename=True)
            if not final_valid:
                raise ValueError(f"커밋된 PDF 최종 검증 실패: {final_reason}")

            final_size = dest_path.stat().st_size
            print(f"  [다운로드 성공] {dest_name} ({final_size:,} bytes)", flush=True)
            return {
                "status": "downloaded",
                "filename": dest_name,
                "path": str(dest_path),
                "size": final_size,
            }

        except Exception as e:
            last_error = e
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass

            if attempt < MAX_RETRIES:
                retry_delay = (2 ** attempt) * RETRY_BASE_DELAY + random.uniform(0.5, 1.5)
                print(f"  [재시도 경고] {dest_name} 시도 실패 ({e}), {retry_delay:.1f}초 후 재시도합니다...", flush=True)
                time.sleep(retry_delay)
            else:
                print(f"  [다운로드 최종 실패] {dest_name}: {e}", flush=True)
        finally:
            page.close()

    return {
        "status": "failed",
        "filename": dest_name,
        "error": str(last_error) if last_error else "UNKNOWN_ERROR",
    }


def execute_downloader(
    start_round: int = 2,
    end_round: int = 9,
    start_lecture: int = 1,
    end_lecture: int = 3,
    specific_round: Optional[int] = None,
    specific_lecture: Optional[int] = None,
    include_all: bool = False,
    target_dir: str = DEFAULT_TARGET_DIR,
    session_file: str = AUTH_FILE,
    headless: bool = True,
    dry_run: bool = False,
    force: bool = False
) -> int:
    """
    메인 다운로더 실행 파이프라인.
    """
    print("=" * 75, flush=True)
    print("Valley AI 글로벌 매크로 실전편 강의자료 다운로더 (Milestone 1)")
    print(f"저장 대상 폴더 : {target_dir}")
    print(f"세션 파일      : {session_file}")
    print(f"브라우저 모드  : {'Headless' if headless else 'Headed'}")
    print(f"실행 모드      : {'[DRY-RUN 모드 (다운로드 없이 인벤토리 검사)]' if dry_run else '실전 다운로드'}")
    print(f"강제 덮어쓰기  : {force}")
    print("=" * 75, flush=True)

    with sync_playwright() as p:
        browser, context = get_authenticated_context(p, session_file=session_file, headless=headless)
        try:
            # 1. 코스 페이지로부터 전체 인벤토리 동적 추출
            all_inventory = fetch_curriculum_from_page(context, course_url=COURSE_URL)

            # 2. 지정된 조건으로 인벤토리 필터링
            targets = filter_inventory(
                all_inventory,
                start_round=start_round,
                end_round=end_round,
                start_lecture=start_lecture,
                end_lecture=end_lecture,
                specific_round=specific_round,
                specific_lecture=specific_lecture,
                include_all=include_all
            )

            print(f"\n[필터링 결과] 대상 챕터 수: 총 {len(targets)}개 챕터", flush=True)

            # 3. Dry-Run 모드 처리
            if dry_run:
                print("\n" + "-" * 75, flush=True)
                print(f"{'순번':<4} {'회차':<6} {'강':<4} {'슬라이드 유무':<10} {'예상 파일명'}")
                print("-" * 75, flush=True)

                slide_count = 0
                skip_count = 0
                existing_valid_count = 0

                for idx, t in enumerate(targets):
                    has_slide_str = "슬라이드 있음" if t["has_slide"] else "없음(스킵)"
                    fn = t["expected_filename"]
                    dest_p = Path(target_dir) / fn
                    extra = ""
                    if dest_p.exists():
                        ok, r = validate_pdf_pre_parse(dest_p, check_filename=True)
                        if ok:
                            extra = " [기존 유효 파일 존재]"
                            existing_valid_count += 1
                        else:
                            extra = f" [기존 파일 손상: {r}]"

                    if t["has_slide"]:
                        slide_count += 1
                    else:
                        skip_count += 1

                    print(f"{idx+1:<4} {t['part_key']:<6} {t['chapter_key']:<4} {has_slide_str:<10} {fn}{extra}", flush=True)

                print("-" * 75, flush=True)
                print(f"[Dry-Run 요약] 총 대상: {len(targets)}개 | 슬라이드 대상: {slide_count}개 | 슬라이드 없음(건너뜀): {skip_count}개 | 이미 존재하는 유효 파일: {existing_valid_count}개")
                print("Dry-Run 점검이 정상 완료되었습니다.", flush=True)
                return 0

            # 4. 실전 다운로드 실행
            os.makedirs(target_dir, exist_ok=True)
            results = []

            print("\n[다운로드 파이프라인 가동 시작]", flush=True)
            for idx, item in enumerate(targets):
                print(f"\n[{idx + 1}/{len(targets)}] {item['part_key']} {item['chapter_key']} - '{item['clean_title']}'", flush=True)
                res = download_single_chapter(context, item, target_dir=target_dir, force=force)
                results.append(res)

                # 슬라이드가 다운로드된 경우에만 Cloudflare WAF 친화적 지터 딜레이 적용
                if res.get("status") == "downloaded":
                    jitter = random.uniform(MIN_JITTER, MAX_JITTER)
                    time.sleep(jitter)

            # 5. 최종 결과 집계 및 보고
            print("\n" + "=" * 75, flush=True)
            print("다운로드 작업 완료 요약")
            print("=" * 75, flush=True)

            downloaded = [r for r in results if r["status"] == "downloaded"]
            skipped_existing = [r for r in results if r["status"] == "skipped_existing"]
            skipped_no_material = [r for r in results if r["status"] in ("skipped_no_material", "skipped_no_attachment")]
            failed = [r for r in results if r["status"] == "failed"]

            print(f"• 신규 다운로드 성공 : {len(downloaded)}개")
            print(f"• 기존 유효 파일 스킵 : {len(skipped_existing)}개")
            print(f"• 자료 없음 건너뜀   : {len(skipped_no_material)}개")
            print(f"• 실패 건수           : {len(failed)}개")

            if failed:
                print("\n[실패 목록]")
                for f_item in failed:
                    print(f" - {f_item['filename']}: {f_item.get('error')}")
                return 1

            print("\n[최종 상태] 모든 대상 챕터 처리 완료.")
            return 0

        finally:
            context.close()
            browser.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valley AI 글로벌 매크로 실전편 강의자료 다운로더 (Milestone 1)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # 범위 지정 파라미터
    parser.add_argument("--start-round", type=int, default=2, help="시작 회차 번호 (기본: 2)")
    parser.add_argument("--end-round", type=int, default=9, help="종료 회차 번호 (기본: 9)")
    parser.add_argument("--start-lecture", type=int, default=1, help="시작 강의 번호 (기본: 1)")
    parser.add_argument("--end-lecture", type=int, default=3, help="종료 강의 번호 (기본: 3)")

    # 편의/하위호환 플래그
    parser.add_argument("--round", type=int, default=None, help="특정 단일 회차 지정 (지정 시 start-round와 end-round 일치)")
    parser.add_argument("--lecture", type=int, default=None, help="특정 단일 강의 지정 (지정 시 start-lecture와 end-lecture 일치)")
    parser.add_argument("--all", action="store_true", help="1회차 1강부터 9회차 3강까지 전체 대상 지정")

    # 경로 및 파일 옵션
    parser.add_argument("--target-dir", default=DEFAULT_TARGET_DIR, help=f"PDF 저장 폴더 (기본: {DEFAULT_TARGET_DIR})")
    parser.add_argument("--output-dir", default=None, help="--target-dir의 하위호환 별칭")
    parser.add_argument("--session-file", default=AUTH_FILE, help=f"인증 세션 파일 경로 (기본: {AUTH_FILE})")

    # 브라우저 및 실행 제어 플래그
    parser.add_argument("--headless", action="store_true", default=True, help="헤드리스 모드로 실행 (기본값)")
    parser.add_argument("--headed", action="store_false", dest="headless", help="브라우저 UI 창을 화면에 표시")
    parser.add_argument("--dry-run", action="store_true", help="실제 다운로드 없이 대상 인벤토리 및 상태만 출력")
    parser.add_argument("--force", action="store_true", help="이미 존재하는 유효한 파일도 강제로 재다운로드")

    args = parser.parse_args()

    # output-dir 별칭 처리
    target_directory = args.output_dir if args.output_dir else args.target_dir

    try:
        return execute_downloader(
            start_round=args.start_round,
            end_round=args.end_round,
            start_lecture=args.start_lecture,
            end_lecture=args.end_lecture,
            specific_round=args.round,
            specific_lecture=args.lecture,
            include_all=args.all,
            target_dir=target_directory,
            session_file=args.session_file,
            headless=args.headless,
            dry_run=args.dry_run,
            force=args.force
        )
    except KeyboardInterrupt:
        print("\n[중단] 사용자에 의해 다운로드가 중단되었습니다.", flush=True)
        return 130
    except Exception as e:
        print(f"\n[치명적 오류] {e}", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
