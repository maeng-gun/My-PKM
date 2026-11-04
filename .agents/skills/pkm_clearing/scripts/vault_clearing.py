#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
My-PKM Vault Clearing Engine (vault_clearing.py)
------------------------------------------------
000 ~ 500 폴더(하위폴더 포함)의 메모 제목에서 동기화 충돌/복제 접미사
(`(1)`, `(2)`, `(conflict ...)`, `(copy)`, `(충돌 ...)` 등)를 스크리닝하여
접미사를 제거하고, 동일 제목 메모가 복수로 존재할 경우 최신 버전을 선별·통합합니다.
"""

import sys
import os
import re
import shutil
import argparse
import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Regex to detect and strip conflict or copy suffixes from filename stem
# Examples matched:
#   "메모명 (1)" -> "메모명"
#   "메모명 (2)" -> "메모명"
#   "메모명 (conflict 2026-10-31-14-12-57)" -> "메모명"
#   "메모명 (copy)" -> "메모명"
#   "메모명 (충돌 2026-10-31)" -> "메모명"
STRIP_PATTERN = re.compile(r'\s*\((?:conflict[^)]*|\d+|copy|충돌[^)]*)\)$', re.IGNORECASE)

DEFAULT_FOLDERS = [
    '000. Inbox',
    '100. Concepts',
    '200. AI_logs',
    '300. Sources',
    '400. Wiki',
    '500. Index',
]


def parse_effective_timestamp(file_path: Path) -> datetime.datetime:
    """
    파일의 수정일시(mtime), 생성일시(ctime), 그리고 파일명 내에 각인된
    conflict 타임스탬프(YYYY-MM-DD-HH-MM-SS) 중 가장 최신의 유효 시점을 반환합니다.
    """
    stat = file_path.stat()
    mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
    
    conflict_match = re.search(
        r'conflict (\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})',
        file_path.stem,
        re.IGNORECASE
    )
    if conflict_match:
        try:
            parts = [int(p) for p in conflict_match.groups()]
            c_time = datetime.datetime(*parts)
            return max(mtime, c_time)
        except Exception:
            pass
            
    return mtime


def clean_stem(stem: str) -> str:
    """접미사를 제거한 순수 기본 제목을 반환합니다."""
    return STRIP_PATTERN.sub('', stem).strip()


def scan_target_groups(
    vault_dir: Path,
    target_folders: List[str]
) -> Dict[Tuple[str, str], List[Path]]:
    """
    대상 폴더들을 재귀 탐색하여 (상대 디렉토리, 정규화된 기본 제목)을 키로 그룹핑합니다.
    """
    groups = defaultdict(list)
    for folder_name in target_folders:
        folder_path = vault_dir / folder_name
        if not folder_path.exists():
            continue
        for root, _, files in os.walk(folder_path):
            for file in files:
                if not file.endswith('.md'):
                    continue
                p = Path(root) / file
                cleaned = clean_stem(p.stem)
                rel_dir = str(p.parent.relative_to(vault_dir)).replace('\\', '/')
                groups[(rel_dir, cleaned)].append(p)
    return groups


def run_clearing(
    vault_dir: Path,
    target_folders: List[str],
    dry_run: bool = False,
    backup_base_dir: Optional[Path] = None,
    no_backup: bool = False
) -> Dict[str, int]:
    """
    볼트 내 000~500 폴더를 스캔하여 접미사 제거 및 다중 버전 통합을 수행합니다.
    """
    stats = {
        'total_scanned_files': 0,
        'affected_groups': 0,
        'single_renamed': 0,
        'multi_groups_resolved': 0,
        'deleted_losers': 0,
        'backed_up_files': 0,
    }

    if not vault_dir.exists():
        print(f"[Error] 볼트 디렉토리가 존재하지 않습니다: {vault_dir}")
        return stats

    print("=" * 80)
    print(" My-PKM Vault Clearing Engine (/pkm-clearing)")
    print(f" - 볼트 경로: {vault_dir.resolve()}")
    print(f" - 대상 폴더: {', '.join(target_folders)}")
    print(f" - 실행 모드: {'[DRY RUN - 시뮬레이션]' if dry_run else '[LIVE - 실제 파일 변경]'}")
    print("=" * 80)

    # 1. 파일 스캔 및 그룹화
    groups = scan_target_groups(vault_dir, target_folders)
    stats['total_scanned_files'] = sum(len(files) for files in groups.values())

    # 조치가 필요한 그룹 필터링 (복수 파일이거나, 단일 파일이지만 접미사가 붙어있는 경우)
    action_groups = {}
    for k, files in groups.items():
        if len(files) > 1 or any(STRIP_PATTERN.search(f.stem) for f in files):
            action_groups[k] = files

    stats['affected_groups'] = len(action_groups)

    if not action_groups:
        print("\n✨ 정리할 충돌 파일이나 번호 접미사 파일이 없습니다. 볼트가 깨끗합니다!")
        return stats

    print(f"\n🔍 처리 대상 그룹: 총 {len(action_groups)}개 그룹 (관련 파일 {sum(len(f) for f in action_groups.values())}개)")

    # 2. 백업 디렉토리 설정 및 파일 사전 백업
    backup_dir = None
    if not dry_run and not no_backup:
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if backup_base_dir:
            backup_dir = backup_base_dir / f"clearing_backup_{timestamp_str}"
        else:
            backup_dir = vault_dir.parent / ".pkm_clearing_backup" / f"backup_{timestamp_str}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n📦 [사전 백업 시작] 대상 디렉토리: {backup_dir}")

        for (rel_dir, cleaned), files in sorted(action_groups.items()):
            for f in files:
                rel_f = f.relative_to(vault_dir)
                dest = backup_dir / rel_f
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
                stats['backed_up_files'] += 1
        print(f"  ✓ {stats['backed_up_files']}개 원본 파일 백업 완료.")

    # 3. 정리 및 통합 작업 실행
    print("\n⚙️ [정리 및 통합 작업 수행]")
    for (rel_dir, cleaned), files in sorted(action_groups.items()):
        final_target = files[0].parent / f"{cleaned}.md"

        # CASE 1: 단일 파일인 경우 -> 접미사 제거 및 이름 복원
        if len(files) == 1:
            f = files[0]
            if f != final_target:
                print(f"[단일 복원] [{rel_dir}] '{f.name}' ➔ '{final_target.name}'")
                if not dry_run:
                    f.rename(final_target)
                stats['single_renamed'] += 1

        # CASE 2: 복수 파일인 경우 -> 최신 버전 채택(Winner) 및 통합 정리
        else:
            # 타임스탬프 내림차순, 크기 내림차순으로 정렬
            sorted_files = sorted(
                files,
                key=lambda x: (parse_effective_timestamp(x), x.stat().st_size),
                reverse=True
            )
            winner = sorted_files[0]
            losers = sorted_files[1:]

            w_time = parse_effective_timestamp(winner).strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[다중 통합] [{rel_dir}] 기본 제목: '{cleaned}' (총 {len(files)}개 버전)")
            print(f"  ★ 최신본 채택(Winner): '{winner.name}' (기준일시: {w_time}, {winner.stat().st_size} bytes)")

            # 구버전 파일(Losers) 삭제
            for loser in losers:
                l_time = parse_effective_timestamp(loser).strftime("%Y-%m-%d %H:%M:%S")
                print(f"  - 구버전 삭제(Loser):  '{loser.name}' (기준일시: {l_time}, {loser.stat().st_size} bytes)")
                if not dry_run:
                    loser.unlink()
                stats['deleted_losers'] += 1

            # Winner 파일이 최종 파일명이 아니면 rename
            if winner != final_target:
                if not dry_run:
                    if final_target.exists() and final_target != winner:
                        final_target.unlink()
                    winner.rename(final_target)
                print(f"  ➔ 최신본 이름 변경:   '{final_target.name}'")
            else:
                print(f"  ➔ 최신본 이름 유지:   '{final_target.name}'")

            stats['multi_groups_resolved'] += 1

    print("\n" + "=" * 80)
    print(" [정리 완료 요약 리포트]")
    print(f" - 전체 스캔 파일 수:   {stats['total_scanned_files']}개")
    print(f" - 처리 대상 그룹 수:   {stats['affected_groups']}개")
    print(f" - 단일 접미사 복원:    {stats['single_renamed']}개")
    print(f" - 다중 버전 통합 그룹: {stats['multi_groups_resolved']}개")
    print(f" - 삭제된 구버전 수:    {stats['deleted_losers']}개")
    if backup_dir:
        print(f" - 백업 디렉토리:       {backup_dir}")
    print("=" * 80)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="My-PKM Vault Clearing Engine: 000~500 폴더 내 충돌/복제 접미사 제거 및 최신본 통합"
    )
    parser.add_argument(
        "--vault",
        type=str,
        default="./My-Wiki",
        help="옵시디언 볼트 루트 디렉토리 (기본값: ./My-Wiki)"
    )
    parser.add_argument(
        "--folders",
        nargs="+",
        default=DEFAULT_FOLDERS,
        help="스캔 대상 폴더 목록 (기본값: 000~500)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 파일을 수정하지 않고 변경 계획만 시뮬레이션 출력"
    )
    parser.add_argument(
        "--backup-dir",
        type=str,
        default=None,
        help="백업 디렉토리 지정 경로"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="사전 백업을 생성하지 않고 즉시 실행"
    )

    args = parser.parse_args()
    vault_path = Path(args.vault).resolve()
    backup_path = Path(args.backup_dir).resolve() if args.backup_dir else None

    run_clearing(
        vault_dir=vault_path,
        target_folders=args.folders,
        dry_run=args.dry_run,
        backup_base_dir=backup_path,
        no_backup=args.no_backup
    )


if __name__ == '__main__':
    main()
