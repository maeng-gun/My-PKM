import sys
import shutil
import tempfile
import datetime
from pathlib import Path

# Force UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Import clearing function
script_dir = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(script_dir))
from vault_clearing import run_clearing, STRIP_PATTERN, clean_stem

def test_clearing_engine():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_vault = Path(temp_dir) / "Test-Wiki"
        inbox = temp_vault / "000. Inbox"
        wiki = temp_vault / "400. Wiki"
        inbox.mkdir(parents=True)
        wiki.mkdir(parents=True)

        # 1. 단일 파일 (conflict)
        f1 = inbox / "테스트 메모 (conflict 2026-10-31-14-12-57).md"
        f1.write_text("# 테스트 메모 1", encoding='utf-8')

        # 2. 단일 파일 (1)
        f2 = wiki / "T1_거시경제 이론 (1).md"
        f2.write_text("# T1 이론", encoding='utf-8')

        # 3. 다중 파일 (구버전 + 최신버전 conflict)
        f3_old = wiki / "산업_바이오 연료.md"
        f3_old.write_text("# 바이오 연료 구버전", encoding='utf-8')
        # set mtime to yesterday
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=2)).timestamp()
        import os
        os.utime(f3_old, (yesterday, yesterday))

        f3_new = wiki / "산업_바이오 연료 (conflict 2026-10-31-15-00-00).md"
        f3_new.write_text("# 바이오 연료 최신본", encoding='utf-8')

        # Run clearing
        folders = ['000. Inbox', '400. Wiki']
        stats = run_clearing(
            vault_dir=temp_vault,
            target_folders=folders,
            dry_run=False
        )

        # Assertions
        assert stats['affected_groups'] == 3, f"Expected 3 groups, got {stats['affected_groups']}"
        assert stats['single_renamed'] == 2, f"Expected 2 single renamed, got {stats['single_renamed']}"
        assert stats['multi_groups_resolved'] == 1, f"Expected 1 multi resolved, got {stats['multi_groups_resolved']}"
        assert stats['deleted_losers'] == 1, f"Expected 1 deleted loser, got {stats['deleted_losers']}"

        # Verify actual files on disk
        assert (inbox / "테스트 메모.md").exists(), "f1 not renamed properly"
        assert not f1.exists(), "f1 old name still exists"

        assert (wiki / "T1_거시경제 이론.md").exists(), "f2 not renamed properly"
        assert not f2.exists(), "f2 old name still exists"

        final_bio = wiki / "산업_바이오 연료.md"
        assert final_bio.exists(), "bio fuel final note does not exist"
        assert not f3_new.exists(), "bio fuel conflict note still exists"
        assert "최신본" in final_bio.read_text(encoding='utf-8'), "winner content was not retained"

        print("\n✅ All unit test assertions passed successfully!")

if __name__ == '__main__':
    test_clearing_engine()
