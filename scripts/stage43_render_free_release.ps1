# Stage43: build both updated images, verify a 512 MB isolated public-page audit,
# and only push to the existing PRIVATE Docker Hub repo when -Mode Publish is explicit.
param(
    [ValidateSet('Validate', 'Publish')]
    [string]$Mode = 'Validate'
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root
$api = 'priscilamestra/pagecheck-staging:stage43-api'
$ui = 'priscilamestra/pagecheck-staging:stage43-ui'

function Run-Docker {
    param([string[]]$DockerArgs)
    & docker @DockerArgs
    if ($LASTEXITCODE -ne 0) {
        throw ('Docker command failed (exit ' + $LASTEXITCODE + '): docker ' + ($DockerArgs -join ' '))
    }
}

Write-Host 'STAGE43: checking Docker Desktop engine...'
Run-Docker -DockerArgs @('info', '--format', '{{.ServerVersion}}')
Write-Host 'STAGE43: building the FastAPI and Streamlit images...'
Run-Docker -DockerArgs @('build', '--platform', 'linux/amd64', '-f', 'deploy/Dockerfile.api', '-t', $api, '.')
Run-Docker -DockerArgs @('build', '--platform', 'linux/amd64', '-f', 'deploy/Dockerfile.ui', '-t', $ui, '.')
Write-Host 'STAGE43: isolated 512 MB browser and public fetch validation...'
$mount = (Join-Path $root 'scripts/stage43_docker_worker_smoke.py') + ':/app/stage43_docker_worker_smoke.py:ro'
Run-Docker -DockerArgs @('run', '--rm', '--memory', '512m', '--memory-swap', '512m',
    '-v', $mount, '--entrypoint', '/app/.venv/bin/python', $api,
    '/app/stage43_docker_worker_smoke.py')
Write-Host 'STAGE43_LOCAL_GUARDED_SCAN_PASSED'
if ($Mode -eq 'Publish') {
    Write-Host 'STAGE43: uploading ONLY the two images to your existing private Docker Hub repository...'
    Run-Docker -DockerArgs @('push', $api)
    Run-Docker -DockerArgs @('push', $ui)
    Write-Host 'STAGE43_PRIVATE_IMAGES_PUBLISHED'
} else {
    Write-Host 'STAGE43_IMAGES_BUILT_LOCALLY__NOT_PUBLISHED'
}
Write-Host 'NO_GITHUB_PUSH'
