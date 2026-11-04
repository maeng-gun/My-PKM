"""Setup script for Google Drive NTFS directory junctions in My-PKM.

Connects local project workspace to Google Drive mount:
1. Workspace Directory Junctions:
   - input_staging -> G:\\내 드라이브\\Antigravity_Workspaces\\My-PKM\\input_staging
   - scratch -> G:\\내 드라이브\\Antigravity_Workspaces\\My-PKM\\scratch
   - archive -> G:\\내 드라이브\\Antigravity_Workspaces\\My-PKM\\archive
   - secrets -> G:\\내 드라이브\\Antigravity_Workspaces\\My-PKM\\secrets
   - AGY_Artifacts -> G:\\내 드라이브\\Antigravity_Workspaces\\My-PKM\\AGY_Artifacts

2. PKM Root Junctions:
   - My-Wiki -> G:\\내 드라이브\\My-Wiki
   - Inbox_Raw -> G:\\내 드라이브\\Inbox_Raw
   - Archive_Sources -> G:\\내 드라이브\\Archive_Sources

3. Restores .env and auth_state.json from secrets/ to project root.
"""

import os
import shutil
import sys
from pathlib import Path

if sys.platform != "win32":
    print("[ERROR] NTFS junctions are only supported on Windows.")
    sys.exit(1)

import _winapi

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GDRIVE_CANDIDATES = [
    Path(r"G:\내 드라이브"),
    Path(r"G:\My Drive"),
]


def find_gdrive_root() -> Path:
    for candidate in GDRIVE_CANDIDATES:
        if candidate.exists() and candidate.is_dir():
            return candidate
    raise FileNotFoundError("Google Drive mount (G:\\내 드라이브 or G:\\My Drive) not found.")


def setup_junctions():
    gdrive_root = find_gdrive_root()
    print(f"[INFO] Using Google Drive root: {gdrive_root}")

    workspace_base = gdrive_root / "Antigravity_Workspaces" / "My-PKM"

    junctions = [
        # (local_folder_name, target_path)
        ("input_staging", workspace_base / "input_staging"),
        ("scratch", workspace_base / "scratch"),
        ("archive", workspace_base / "archive"),
        ("secrets", workspace_base / "secrets"),
        ("AGY_Artifacts", workspace_base / "AGY_Artifacts"),
        ("My-Wiki", gdrive_root / "My-Wiki"),
        ("Inbox_Raw", gdrive_root / "Inbox_Raw"),
        ("Archive_Sources", gdrive_root / "Archive_Sources"),
    ]

    for link_name, target_path in junctions:
        local_path = PROJECT_ROOT / link_name
        target_str = str(target_path)

        if not target_path.exists():
            print(f"[WARN] Target directory does not exist, creating on Drive: {target_str}")
            target_path.mkdir(parents=True, exist_ok=True)

        if local_path.exists():
            print(f"[SKIP] {link_name:16} already exists.")
        else:
            _winapi.CreateJunction(target_str, str(local_path))
            print(f"[OK] Created junction: {link_name:16} -> {target_str}")

    # Restore secrets
    secrets_dir = PROJECT_ROOT / "secrets"
    if secrets_dir.exists():
        for secret_file in [".env", "auth_state.json"]:
            src = secrets_dir / secret_file
            dst = PROJECT_ROOT / secret_file
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
                print(f"[RESTORE] {secret_file} copied to project root.")


if __name__ == "__main__":
    setup_junctions()
