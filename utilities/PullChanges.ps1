# Launches in a new PowerShell window and force syncs the current branch with origin

$repoPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoPath

Write-Host "Repository: $repoPath" -ForegroundColor Cyan

# Get current branch
$branch = git rev-parse --abbrev-ref HEAD

if ($LASTEXITCODE -ne 0) {
    Write-Host "Not a Git repository." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit
}

Write-Host "Current Branch: $branch" -ForegroundColor Yellow

Write-Host "`nFetching latest changes..."
git fetch origin

Write-Host "`nResetting local branch to origin/$branch..."
git reset --hard origin/$branch

Write-Host "`nCleaning untracked files..."
git clean -fd

Write-Host "`nDone!" -ForegroundColor Green

Read-Host "`nPress Enter to close"