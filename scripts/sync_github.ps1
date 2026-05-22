# sync_github.ps1
# Utility script for syncing the repository to GitHub from Windows (ROG Ally X).
# PLACEHOLDER — fill in your remote URL and branch before use.
#
# Usage: .\scripts\sync_github.ps1 ["commit message"]

param(
    [string]$Message = "chore: sync"
)

$Branch = "main"

Write-Host "[sync] Staging all changes..."
git add -A

Write-Host "[sync] Committing: '$Message'"
git commit -m $Message

Write-Host "[sync] Pushing to origin/$Branch..."
git push origin $Branch

Write-Host "[sync] Done."
