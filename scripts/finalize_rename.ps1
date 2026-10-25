<#
.SYNOPSIS
    Finalizes the project rebranding from 'macro_analyzer' / 'My_PKM' to 'My-PKM'.

.DESCRIPTION
    This script automates the post-IDE workspace transition steps:
    1. (Optional) Cleans up the empty/stub 'macro_analyzer' directory if present.
    2. (Optional) Safely renames 'c:\Users\maeng-gun\Desktop\python\My_PKM' to 'c:\Users\maeng-gun\Desktop\python\My-PKM'.
       NOTE: Antigravity IDE and terminals pointing to My_PKM must be closed before directory rename!
    3. Rebuilds the Python virtual environment (.venv) using Python 3.12, installing project dependencies and kordoc>=0.2.0.
    4. Verifies all directory junctions (Antigravity Workspaces & PKM roots) and Git remote URL.

.PARAMETER SkipRename
    Skip renaming the folder 'My_PKM' to 'My-PKM' (e.g., if you wish to keep 'My_PKM' or if running inside active IDE).

.PARAMETER SkipVenvRebuild
    Skip rebuilding the Python 3.12 virtual environment.

.PARAMETER CleanOldMacroAnalyzer
    Automatically remove the obsolete 'macro_analyzer' stub directory if it exists.

.EXAMPLE
    # Run from an external PowerShell terminal after closing Antigravity IDE:
    powershell -ExecutionPolicy Bypass -File .\scripts\finalize_rename.ps1

    # Run without folder rename (keeping My_PKM folder name):
    powershell -ExecutionPolicy Bypass -File .\scripts\finalize_rename.ps1 -SkipRename
#>

[CmdletBinding(SupportsShouldProcess=$true)]
param(
    [switch]$SkipRename,
    [switch]$SkipVenvRebuild,
    [switch]$CleanOldMacroAnalyzer
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   My-PKM Workspace Transition & Rename Automation" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Dynamic detection of base directory
if ($PSScriptRoot) {
    if ((Split-Path -Leaf $PSScriptRoot) -eq "scripts") {
        $baseDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    } else {
        $baseDir = Split-Path -Parent $PSScriptRoot
    }
} else {
    $baseDir = Split-Path -Parent (Get-Location)
}

if (-not $baseDir -or -not (Test-Path $baseDir)) {
    $baseDir = "c:\Users\maeng-gun\Desktop\python"
}

$oldDir = Join-Path $baseDir "My_PKM"
$newDir = Join-Path $baseDir "My-PKM"
$stubDir = Join-Path $baseDir "macro_analyzer"

# Determine current project root
if (Test-Path $oldDir) {
    $projectDir = $oldDir
} elseif (Test-Path $newDir) {
    $projectDir = $newDir
} else {
    $projectDir = (Get-Item $PSScriptRoot).Parent.FullName
}

Write-Host "`n[Step 1/5] Checking workspace directories..." -ForegroundColor Yellow
Write-Host " - Current Project Directory : $projectDir"
Write-Host " - Target Project Directory  : $newDir"

# Optional: Clean up empty macro_analyzer stub directory
if (Test-Path $stubDir) {
    Write-Host " - Obsolete stub detected at: $stubDir" -ForegroundColor Yellow
    if ($CleanOldMacroAnalyzer) {
        $childItems = Get-ChildItem -Path $stubDir -Force -ErrorAction SilentlyContinue
        if ($childItems.Count -gt 0 -and (Test-Path (Join-Path $stubDir ".agents\teamwork"))) {
            Write-Warning "Stub directory '$stubDir' contains active teamwork metadata (.agents/teamwork). Skipping removal to preserve agent state."
        } else {
            if ($PSCmdlet.ShouldProcess($stubDir, "Remove obsolete stub directory")) {
                Write-Host "   -> Removing $stubDir..." -ForegroundColor Gray
                try {
                    Remove-Item -Path $stubDir -Recurse -Force
                    Write-Host "   -> Successfully removed $stubDir." -ForegroundColor Green
                } catch {
                    Write-Warning "Failed to remove $($stubDir): $_"
                }
            }
        }
    } else {
        Write-Host "   -> Note: You can safely remove '$stubDir' or run with -CleanOldMacroAnalyzer." -ForegroundColor Gray
    }
}

# Optional: Directory Rename (My_PKM -> My-PKM)
if (-not $SkipRename -and (Test-Path $oldDir) -and -not (Test-Path $newDir)) {
    Write-Host "`n[Step 2/5] Renaming project folder to 'My-PKM'..." -ForegroundColor Yellow
    
    if ($PSCmdlet.ShouldProcess($oldDir, "Rename project directory to '$newDir'")) {
        # Change current working directory away from My_PKM to prevent lock
        Set-Location $baseDir

        try {
            Rename-Item -Path $oldDir -NewName "My-PKM"
            $projectDir = $newDir
            Write-Host " -> Successfully renamed '$oldDir' to '$newDir'!" -ForegroundColor Green
        } catch {
            Write-Error @"
Directory rename failed. Windows may still be locking the folder.
Cause: Antigravity IDE, VSCode, or an open terminal is currently accessing '$oldDir'.
Remedy:
1. Close all IDEs, editors, and PowerShell terminals pointing to '$oldDir'.
2. Open a new PowerShell terminal and re-run:
   powershell -ExecutionPolicy Bypass -File ""$oldDir\scripts\finalize_rename.ps1""
"@
            exit 1
        }
    } else {
        Write-Host " -> [WhatIf] Skipping actual directory rename." -ForegroundColor Gray
    }
} else {
    if (Test-Path $newDir) {
        $projectDir = $newDir
        Write-Host "`n[Step 2/5] Folder is already named 'My-PKM' (or target exists)." -ForegroundColor Green
    } else {
        Write-Host "`n[Step 2/5] Skipping directory rename as requested (-SkipRename)." -ForegroundColor Gray
    }
}

Set-Location $projectDir

# Step 3: Rebuild Python 3.12 .venv
Write-Host "`n[Step 3/5] Setting up Python 3.12 virtual environment..." -ForegroundColor Yellow
if (-not $SkipVenvRebuild) {
    if ($PSCmdlet.ShouldProcess($projectDir, "Rebuild Python 3.12 virtual environment and install dependencies")) {
        # Check Python 3.12
        $py312 = $null
        try {
            $pyVersion = & py -3.12 --version 2>&1
            if ($LASTEXITCODE -eq 0 -and $pyVersion -match "Python 3\.12") {
                $py312 = "py -3.12"
                Write-Host " -> Detected host Python: $pyVersion" -ForegroundColor Green
            }
        } catch {}

        if (-not $py312) {
            Write-Warning "Python 3.12 was not found via 'py -3.12'. Checking default python..."
            $defVersion = & python --version 2>&1
            if ($defVersion -match "Python 3\.1[1-9]") {
                $py312 = "python"
                Write-Host " -> Detected compatible default python: $defVersion" -ForegroundColor Green
            } else {
                Write-Error "Python 3.11+ is required for kordoc. Please install Python 3.12."
                exit 1
            }
        }

        $venvPath = Join-Path $projectDir ".venv"
        if (Test-Path $venvPath) {
            Write-Host " -> Removing existing .venv..." -ForegroundColor Gray
            try {
                Remove-Item -Path $venvPath -Recurse -Force
                Write-Host " -> Removed existing .venv successfully." -ForegroundColor Green
            } catch {
                Write-Warning "Failed to delete old .venv directly: $_. Please make sure no Python processes are running."
            }
        }

        Write-Host " -> Creating new virtual environment with $py312..." -ForegroundColor Gray
        & cmd /c "$py312 -m venv .venv"
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to create .venv!"
            exit 1
        }

        $venvPython = Join-Path $projectDir ".venv\Scripts\python.exe"
        $venvPip = Join-Path $projectDir ".venv\Scripts\pip.exe"

        Write-Host " -> Upgrading pip and wheel..." -ForegroundColor Gray
        & $venvPython -m pip install --upgrade pip setuptools wheel --quiet

        Write-Host " -> Installing project dependencies from pyproject.toml..." -ForegroundColor Gray
        & $venvPip install -e . --quiet

        Write-Host " -> Ensuring 'kordoc>=0.2.0' is installed..." -ForegroundColor Gray
        & $venvPip install -U "kordoc>=0.2.0" --quiet

        # Verify kordoc
        try {
            $kordocCheck = & $venvPython -c "import kordoc; print('kordoc version: ' + getattr(kordoc, '__version__', 'installed'))"
            Write-Host " -> Verification SUCCESS: $kordocCheck" -ForegroundColor Green
        } catch {
            Write-Warning "Failed to import kordoc in .venv: $_"
        }
    } else {
        Write-Host " -> [WhatIf] Skipping .venv rebuild." -ForegroundColor Gray
    }
} else {
    Write-Host " -> Skipping .venv rebuild (-SkipVenvRebuild)." -ForegroundColor Gray
}

# Step 4: Verify Directory Junctions
Write-Host "`n[Step 4/5] Verifying Directory Junctions..." -ForegroundColor Yellow
$junctionNames = @("input_staging", "scratch", "archive", "secrets", "AGY_Artifacts", "My-Wiki", "Inbox_Raw", "Archive_Sources")
$allJunctionsValid = $true

foreach ($jName in $junctionNames) {
    $jPath = Join-Path $projectDir $jName
    if (Test-Path $jPath) {
        $item = Get-Item -Path $jPath -Force
        if ($item.LinkType -eq "Junction") {
            $target = $item.Target -join ""
            $targetExists = Test-Path $target
            if ($targetExists) {
                Write-Host " [PASS] $jName -> $target" -ForegroundColor Green
            } else {
                Write-Host " [BROKEN TARGET] $jName -> $target (Target does not exist!)" -ForegroundColor Red
                $allJunctionsValid = $false
            }
        } else {
            Write-Host " [NOT A JUNCTION] $jName (Type: $($item.LinkType))" -ForegroundColor DarkYellow
        }
    } else {
        Write-Host " [NOT MOUNTED YET] $jName" -ForegroundColor DarkGray
    }
}

# Step 5: Verify Git Remote
Write-Host "`n[Step 5/5] Verifying Git remote repository..." -ForegroundColor Yellow
try {
    $remoteUrl = (& git remote get-url origin).Trim()
    Write-Host " -> Git remote 'origin': $remoteUrl" -ForegroundColor Cyan
    if ($remoteUrl -eq "https://github.com/maeng-gun/My-PKM.git") {
        Write-Host " [PASS] Remote origin matches https://github.com/maeng-gun/My-PKM.git" -ForegroundColor Green
    } else {
        Write-Host " [UPDATE] Updating remote origin to https://github.com/maeng-gun/My-PKM.git..." -ForegroundColor Yellow
        if ($PSCmdlet.ShouldProcess("git remote origin", "Set URL to https://github.com/maeng-gun/My-PKM.git")) {
            & git remote set-url origin https://github.com/maeng-gun/My-PKM.git
            Write-Host " [PASS] Updated git remote origin." -ForegroundColor Green
        }
    }
} catch {
    Write-Warning "Git remote check failed: $_"
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "   My-PKM Workspace Transition Summary" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Workspace Path    : $projectDir"
Write-Host " Python .venv      : $(if (Test-Path '.venv\Scripts\python.exe') { 'Ready (Python 3.12)' } else { 'Pending' })"
Write-Host " Junctions Status  : $(if ($allJunctionsValid) { 'Healthy' } else { 'Attention needed' })"
Write-Host " Ready to launch   : Open Antigravity on $projectDir"
Write-Host "============================================================`n" -ForegroundColor Cyan
