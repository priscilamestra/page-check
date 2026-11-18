# Offline Chromium smoke with a hard 512 MiB memory limit matching Render Free.
# No network audit, no API call, no GitHub interaction, no image publication.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$scriptFile = (Resolve-Path (Join-Path $root 'scripts/stage36_browser_kernel_smoke.py')).Path

& docker image inspect 'pagecheck-api:stage40' --format '{{.Id}}' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Missing local pagecheck-api:stage40 image.' }

$volume = 'type=bind,source=' + $scriptFile + ',target=/app/stage36_browser_kernel_smoke.py,readonly'
& docker run --rm `
  --memory 512m --memory-swap 512m `
  --mount $volume `
  --entrypoint /app/.venv/bin/python `
  pagecheck-api:stage40 /app/stage36_browser_kernel_smoke.py
if ($LASTEXITCODE -ne 0) {
    throw 'Guarded browser failed under 512 MB. Inspect errors/OOM before continuing; do not enable public audits.'
}
Write-Host 'STAGE41_GUARDED_CHROMIUM_512MB_SMOKE_PASSED'
Write-Host 'FULL_PUBLIC_AUDIT_NOT_TESTED__PUBLIC_AUDITS_STILL_DISABLED'
