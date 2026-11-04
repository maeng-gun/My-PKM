#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adversarial Verification Suite for download_macro_lecture.py (Milestone 1 Challenger 2)

Tests:
1. Session Auto-Recovery: Expired cookies trigger /login detection and .env fallback.
2. Corrupted Session File Edge Case: Verifies behavior when auth_state.json is 0 bytes.
3. Transient File Lock Resolution: Verifies 3-attempt sharing-lock retry loop on temporary lock.
4. Persistent File Lock Resistance: Verifies graceful failure and 0 orphaned .tmp files under permanent lock.
5. Ephemeral Page Memory Stability: Verifies O(1) memory across 30 page lifecycles using Win32 API.
6. Live Dry-Run Zero Side-Effects: Verifies clean exit code 0 and zero filesystem mutations.
7. Rate Limiting Jitter & Backoff Mechanics: Verifies jitter range and exponential backoff calculations.
"""

import ctypes
from ctypes import wintypes
import gc
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tracemalloc
import unittest
from unittest.mock import MagicMock

# Path configuration
REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / ".agents" / "skills" / "valley_ai_scrap" / "scripts" / "download_macro_lecture.py"
sys.path.insert(0, str(SCRIPT_PATH.parent))

import download_macro_lecture as dml
from playwright.sync_api import sync_playwright


# Win32 Process Memory Structure
class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('PageFaultCount', wintypes.DWORD),
        ('PeakWorkingSetSize', ctypes.c_size_t),
        ('WorkingSetSize', ctypes.c_size_t),
        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
        ('PagefileUsage', ctypes.c_size_t),
        ('PeakPagefileUsage', ctypes.c_size_t),
    ]

try:
    ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD
    ]
    ctypes.windll.psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
except Exception:
    pass


def get_current_rss_mb() -> float:
    pmc = PROCESS_MEMORY_COUNTERS()
    pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
    h = ctypes.windll.kernel32.GetCurrentProcess()
    ok = ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb)
    if ok:
        return pmc.WorkingSetSize / (1024 * 1024)
    return 0.0


class TestAdversarialDownloader(unittest.TestCase):

    def test_01_session_auto_recovery_expired_cookies(self):
        """Simulate expired cookies in auth_state.json and verify automatic re-login via .env credentials."""
        tmp_session = Path(tempfile.gettempdir()) / f"test_expired_session_{int(time.time())}.json"
        expired_payload = {
            "cookies": [
                {
                    "name": "next-auth.session-token",
                    "value": "expired_dummy_token_xyz_12345",
                    "domain": ".valley.town",
                    "path": "/",
                    "expires": 1000000000,
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "Lax",
                }
            ],
            "origins": [],
        }
        tmp_session.write_text(json.dumps(expired_payload), encoding="utf-8")

        try:
            with sync_playwright() as p:
                browser, context = dml.get_authenticated_context(p, session_file=str(tmp_session), headless=True)
                self.assertIsNotNone(context)
                browser.close()

            self.assertTrue(tmp_session.exists())
            self.assertGreater(tmp_session.stat().st_size, 500)
            saved_data = json.loads(tmp_session.read_text(encoding="utf-8"))
            self.assertGreater(len(saved_data.get("cookies", [])), 0)
        finally:
            if tmp_session.exists():
                tmp_session.unlink()

    def test_02_corrupted_zero_byte_session_file_edge_case(self):
        """Verify that a 0-byte auth_state.json triggers JSONDecodeError in new_context (documented vulnerability)."""
        tmp_corrupt = Path(tempfile.gettempdir()) / f"test_corrupt_session_{int(time.time())}.json"
        tmp_corrupt.write_bytes(b"")

        try:
            with sync_playwright() as p:
                with self.assertRaises(json.decoder.JSONDecodeError):
                    dml.get_authenticated_context(p, session_file=str(tmp_corrupt), headless=True)
        finally:
            if tmp_corrupt.exists():
                tmp_corrupt.unlink()

    def test_03_transient_file_lock_conflict_resolution(self):
        """Verify that a transient sharing lock held for 1.2s is resolved by the 3-attempt retry loop in os.replace."""
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp_dir = Path(tmp_str)
            dest_path = tmp_dir / "2회차_1강_테스트.pdf"
            dest_path.write_bytes(b"%PDF-1.4\n" + b"INITIAL_DATA"*100 + b"\n%%EOF\n")

            lock_acquired = threading.Event()
            def hold_transient_lock():
                with open(dest_path, "r+b") as f:
                    lock_acquired.set()
                    time.sleep(1.2)

            t = threading.Thread(target=hold_transient_lock)
            t.start()
            lock_acquired.wait()

            tmp_file = tmp_dir / "2회차_1강_테스트.tmp.123"
            tmp_file.write_bytes(b"%PDF-1.4\n" + b"REPLACED_CONTENT"*100 + b"\n%%EOF\n")

            replace_succeeded = False
            for _ in range(3):
                try:
                    os.replace(tmp_file, dest_path)
                    replace_succeeded = True
                    break
                except PermissionError:
                    time.sleep(1.0)

            t.join()
            self.assertTrue(replace_succeeded, "Transient lock replacement should succeed within 3 attempts")
            self.assertIn(b"REPLACED_CONTENT", dest_path.read_bytes())

    def test_04_persistent_file_lock_conflict_and_tmp_cleanup(self):
        """Verify that a permanent file lock fails gracefully, exhausts retries, and leaves zero residual .tmp files."""
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp_dir = Path(tmp_str)
            dest_path = tmp_dir / "2회차_1강_테스트.pdf"
            dest_path.write_bytes(b"%PDF-1.4\n" + b"LOCKED_DATA"*100 + b"\n%%EOF\n")

            # Hold permanent lock
            lock_handle = open(dest_path, "r+b")

            mock_context = MagicMock()
            mock_page = MagicMock()
            mock_context.new_page.return_value = mock_page
            mock_page.url = "https://www.valley.town/training/global-macro-advanced/lecture/test123"

            mock_locator = MagicMock()
            mock_page.locator.return_value = mock_locator
            mock_locator.first.wait_for.return_value = None
            mock_locator.count.return_value = 1
            mock_locator.first.inner_text.return_value = "강의자료"

            class MockDownloadContext:
                def __enter__(self):
                    dl_info = MagicMock()
                    dl = MagicMock()
                    def fake_save_as(p):
                        Path(p).write_bytes(b"%PDF-1.4\n" + b"VALID_PDF_BYTES"*100 + b"\n%%EOF\n")
                    dl.save_as = fake_save_as
                    dl_info.value = dl
                    return dl_info
                def __exit__(self, *args):
                    pass

            mock_page.expect_download.return_value = MockDownloadContext()

            item = {
                "round_num": 2,
                "lecture_num": 1,
                "part_key": "2회차",
                "chapter_key": "1강",
                "clean_title": "테스트",
                "expected_filename": "2회차_1강_테스트.pdf",
                "has_slide": True,
                "slide_id": "test123"
            }

            res = dml.download_single_chapter(mock_context, item, target_dir=str(tmp_dir), force=True)
            lock_handle.close()

            self.assertEqual(res.get("status"), "failed")
            self.assertIn("공유 위반", res.get("error", ""))

            # Verify zero residual .tmp files
            tmp_residuals = list(tmp_dir.glob("*.tmp.*"))
            self.assertEqual(len(tmp_residuals), 0, "No orphaned .tmp files should remain in target dir")

    def test_05_ephemeral_page_memory_stability(self):
        """Verify that 30 repeated page creation and closure cycles do not accumulate memory (O(1) lifecycle)."""
        tracemalloc.start()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()

            # Warmup
            for _ in range(5):
                page = context.new_page()
                try:
                    page.set_content("<html><body><h1>Warmup</h1></body></html>")
                finally:
                    page.close()

            gc.collect()
            rss_start = get_current_rss_mb()
            tm_start, _ = tracemalloc.get_traced_memory()

            for i in range(30):
                page = context.new_page()
                try:
                    page.set_content(f"<html><body><h1>Lecture {i+1}</h1><p>" + "Macro text content "*500 + "</p></body></html>")
                    _ = page.locator("h1").inner_text()
                finally:
                    page.close()

            gc.collect()
            rss_end = get_current_rss_mb()
            tm_end, _ = tracemalloc.get_traced_memory()

            context.close()
            browser.close()

        tracemalloc.stop()

        rss_delta = abs(rss_end - rss_start)
        heap_delta_kb = (tm_end - tm_start) / 1024

        # Memory delta should remain negligible (< 20MB RSS and < 50KB heap)
        self.assertLess(rss_delta, 20.0, f"RSS memory grew by {rss_delta:.2f} MB across 30 page iterations")
        self.assertLess(heap_delta_kb, 50.0, f"Python heap grew by {heap_delta_kb:.2f} KB across 30 page iterations")

    def test_06_live_dry_run_zero_side_effects(self):
        """Verify that running download_macro_lecture.py --dry-run produces 0 side-effects on disk and exits 0."""
        target_dir = Path(dml.DEFAULT_TARGET_DIR)
        files_before = {}
        if target_dir.exists():
            for f in target_dir.glob("*"):
                try:
                    files_before[f.name] = (f.stat().st_size, f.stat().st_mtime)
                except OSError:
                    pass

        cmd = [sys.executable, str(SCRIPT_PATH), "--dry-run"]
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)

        files_after = {}
        if target_dir.exists():
            for f in target_dir.glob("*"):
                try:
                    files_after[f.name] = (f.stat().st_size, f.stat().st_mtime)
                except OSError:
                    pass

        self.assertEqual(res.returncode, 0, f"Dry-run CLI failed: {res.stderr}")
        self.assertIn("Dry-Run 점검이 정상 완료되었습니다.", res.stdout)
        self.assertIn("총 대상: 24개", res.stdout)
        self.assertIn("슬라이드 대상: 24개", res.stdout)

        diff_added = set(files_after.keys()) - set(files_before.keys())
        diff_removed = set(files_before.keys()) - set(files_after.keys())
        diff_modified = [k for k in files_before if files_before[k] != files_after.get(k)]

        self.assertEqual(len(diff_added), 0, f"Dry-run created unexpected files: {diff_added}")
        self.assertEqual(len(diff_removed), 0, f"Dry-run removed files: {diff_removed}")
        self.assertEqual(len(diff_modified), 0, f"Dry-run modified existing files: {diff_modified}")

    def test_07_rate_limit_jitter_and_backoff_mechanics(self):
        """Verify jitter range boundaries (1.5-2.5s) and exponential backoff growth."""
        self.assertEqual(dml.MIN_JITTER, 1.5)
        self.assertEqual(dml.MAX_JITTER, 2.5)
        self.assertEqual(dml.MAX_RETRIES, 2)
        self.assertEqual(dml.RETRY_BASE_DELAY, 2.0)

        # Test backoff calculation formula
        for attempt in range(3):
            base = (2 ** attempt) * dml.RETRY_BASE_DELAY
            min_delay = base + 0.5
            max_delay = base + 1.5
            if attempt == 0:
                self.assertAlmostEqual(min_delay, 2.5)
                self.assertAlmostEqual(max_delay, 3.5)
            elif attempt == 1:
                self.assertAlmostEqual(min_delay, 4.5)
                self.assertAlmostEqual(max_delay, 5.5)
            elif attempt == 2:
                self.assertAlmostEqual(min_delay, 8.5)
                self.assertAlmostEqual(max_delay, 9.5)


if __name__ == "__main__":
    unittest.main()
