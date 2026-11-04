#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
밸리 AI 글로벌 매크로 실전편 강의자료 일괄 PKM 파싱 및 아카이빙 스크립트
(Batch PKM Parser & Inbox Zero Archiver for Valley AI Macro Lectures)

요구사항:
1. G:\내 드라이브\Inbox_temp 내 모든 강의자료 PDF(1회차 1강 ~ 9회차 3강, 총 25개) 탐색
2. kordoc 엔진 기반 순수 텍스트 및 GFM 표 추출 (/pkm-parse 규격 준수, 이미지 미추출)
3. My-PKM 헌법 v2.1 2계층 YAML 프론트매터 자동 결합
4. 변환된 마크다운(.md) 파일을 G:\내 드라이브\Inbox_temp\<stem>.md 로 적재
5. 파싱 완료된 원본 PDF 파일들을 Archive_Sources/310. Reports_Papers/ 로 안전 이동 (Inbox Zero 달성)
"""

import os
import sys
import time
import shutil
from pathlib import Path
from typing import List, Dict, Any

# Ensure UTF-8 standard output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Add pkm_parse scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]
PKM_PARSE_SCRIPTS = REPO_ROOT / ".agents" / "skills" / "pkm_parse" / "scripts"
if str(PKM_PARSE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PKM_PARSE_SCRIPTS))

import parse_sources

INBOX_TEMP_DIR = Path(r"G:\내 드라이브\Inbox_temp")
ARCHIVE_BASE_DIR = REPO_ROOT / "Archive_Sources" / "310. Reports_Papers"

def run_batch_parse_and_archive(
    inbox_dir: Path = INBOX_TEMP_DIR,
    archive_dir: Path = ARCHIVE_BASE_DIR,
    dry_run: bool = False
) -> int:
    print("=" * 80)
    print("밸리 AI 글로벌 매크로 실전편 강의자료 일괄 PKM 파싱 및 아카이빙")
    print(f"대상 디렉터리 : {inbox_dir}")
    print(f"아카이브 위치 : {archive_dir}")
    print(f"실행 모드     : {'[DRY-RUN]' if dry_run else '[실제 파싱 및 아카이빙]'}")
    print("=" * 80)

    if not inbox_dir.exists():
        print(f"[오류] 대상 디렉터리가 존재하지 않습니다: {inbox_dir}", file=sys.stderr)
        return 1

    archive_dir.mkdir(parents=True, exist_ok=True)

    # 1. 대상 PDF 목록 수집 (1회차 1강 ~ 9회차 3강 정렬)
    pdf_files = sorted(list(inbox_dir.glob("*.pdf")), key=lambda p: p.name)
    total_files = len(pdf_files)
    print(f"\n[1단계] 총 {total_files}개의 강의자료 PDF 파일이 감지되었습니다.\n")

    if total_files == 0:
        print("[알림] 대상 PDF 파일이 없습니다.")
        return 0

    results: List[Dict[str, Any]] = []
    success_count = 0
    fail_count = 0

    # 2. 순차 파싱 및 아카이빙
    for idx, pdf_path in enumerate(pdf_files, 1):
        stem = pdf_path.stem
        target_md_path = inbox_dir / f"{stem}.md"
        target_archive_pdf = archive_dir / pdf_path.name
        
        print(f"[{idx}/{total_files}] 파싱 진행 중: {pdf_path.name} ({pdf_path.stat().st_size / 1024 / 1024:.2f} MB)...", flush=True)
        start_time = time.time()

        if dry_run:
            print(f"  [DRY-RUN] -> 마크다운 생성 예정: {target_md_path.name}", flush=True)
            print(f"  [DRY-RUN] -> 원본 아카이빙 예정: {target_archive_pdf}", flush=True)
            success_count += 1
            continue

        try:
            # 1. kordoc 기반 본문 및 표 추출
            body_text, raw_images, meta = parse_sources.parse_source_file(
                pdf_path,
                table_format="gfm",
                ocr=False,
                verbose=False
            )

            # 2. 순수 텍스트/표 모드: 이미지 링크 제거
            clean_body = parse_sources.strip_image_links(body_text)

            # 3. Google Drive 소스 URL 확인
            gdrive_url = parse_sources.resolve_gdrive_url(pdf_path, wait_for_sync=False)
            if not gdrive_url:
                gdrive_url = f"Archive_Sources/310. Reports_Papers/{pdf_path.name}"

            # 4. 프론트매터 생성 (My-PKM 헌법 규격)
            frontmatter = parse_sources.generate_frontmatter(
                origin="source",
                note_type="source",
                domain=["macro"],
                up="[[02_매크로 분석]]",
                status="active",
                source_type="presentation",
                author="[[Valley AI]]",
                org="[[Valley AI]]",
                published="2026-11-01",
                ref_date="2026-11-01",
                aliases=[],
                summary=f"밸리 AI 글로벌 매크로 실전편 강의자료 ({stem})",
                source_url=gdrive_url,
                metadata=meta
            )

            # 5. 최종 마크다운 문서 조합
            full_md = parse_sources.assemble_markdown_document(frontmatter, clean_body, stem)

            # 6. 마크다운 파일 저장 (G:\내 드라이브\Inbox_temp\)
            target_md_path.write_text(full_md, encoding="utf-8")
            md_size_kb = target_md_path.stat().st_size / 1024

            # 7. 원본 PDF 안전 이동 (Inbox Zero 아카이빙)
            try:
                os.replace(pdf_path, target_archive_pdf)
            except Exception:
                shutil.move(str(pdf_path), str(target_archive_pdf))

            elapsed = time.time() - start_time
            print(f"  ✓ 마크다운 생성 완료: {target_md_path.name} ({md_size_kb:.1f} KB)", flush=True)
            print(f"  ✓ 원본 PDF 아카이빙: {target_archive_pdf.name} (소요시간: {elapsed:.1f}초)", flush=True)
            
            results.append({
                "stem": stem,
                "md_size_kb": md_size_kb,
                "status": "SUCCESS"
            })
            success_count += 1

        except Exception as exc:
            print(f"  ✗ 파싱 실패 ({stem}): {exc}", file=sys.stderr, flush=True)
            results.append({
                "stem": stem,
                "error": str(exc),
                "status": "FAILED"
            })
            fail_count += 1

    # 3. 결과 종합 보고
    print("\n" + "=" * 80, flush=True)
    print("PKM 일괄 파싱 및 아카이빙 완료 요약", flush=True)
    print("=" * 80, flush=True)
    print(f"• 전체 대상 파일 : {total_files}개", flush=True)
    print(f"• 파싱 성공 건수 : {success_count}개", flush=True)
    print(f"• 파싱 실패 건수 : {fail_count}개", flush=True)

    if fail_count > 0:
        print("\n[실패 목록]", flush=True)
        for r in results:
            if r["status"] == "FAILED":
                print(f" - {r['stem']}: {r.get('error')}", flush=True)
        return 1

    print("\n[성공 목록]", flush=True)
    for r in results:
        print(f" - {r['stem']}.md ({r['md_size_kb']:.1f} KB)", flush=True)

    print("\n[최종 상태] Inbox Zero 달성 및 마크다운 파일 적재 완료.", flush=True)
    return 0

if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    sys.exit(run_batch_parse_and_archive(dry_run=is_dry))
