# Page Check Stage40: build and optionally publish TWO Linux/amd64 Docker images
# to ONE PRIVATE Docker Hub repository. NEVER interacts with GitHub or Git remote.
# Run from Windows PowerShell in the project's root:
#   .\scripts\stage40_render_free_images.ps1 -Mode Build
#   .\scripts\stage40_render_free_images.ps1 -Mode Publish -DockerHubUser YOUR_USER
[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [ValidateSet('Build', 'Publish')]
    [string]$Mode = 'Build',

    [Parameter(Mandatory = $false)]
    [ValidatePattern('^[a-z0-9][a-z0-9_-]{1,61}$')]
    [string]$DockerHubUser,

    [Parameter(Mandatory = $false)]
    [ValidatePattern('^[a-z0-9][a-z0-9_.-]{1,61}$')]
    [string]$DockerHubRepo = 'pagecheck-staging',

    [Parameter(Mandatory = $false)]
    [switch]$PrivateRepositoryConfirmed
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-Docker {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker failed with exit code $LASTEXITCODE. Command: docker $($Arguments -join ' ')"
    }
}

function Assert-LinuxAmd64 {
    param([Parameter(Mandatory = $true)][string]$Image)
    $arch = (& docker image inspect --format '{{.Os}}/{{.Architecture}}' $Image 2>$null)
    if ($LASTEXITCODE -ne 0 -or $arch.Trim() -ne 'linux/amd64') {
        throw "Missing or incompatible image '$Image'. Expected linux/amd64; run -Mode Build first."
    }
    Write-Host "VERIFIED_LINUX_AMD64 $Image"
}

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $projectRoot
try {
    # Fail fast if the Docker Engine isn't available; Docker Desktop must be started.
    Invoke-Docker -Arguments @('info', '--format', '{{.ServerVersion}}')

    if ($Mode -eq 'Build') {
        foreach ($path in @('deploy/Dockerfile.api', 'deploy/Dockerfile.ui', '.dockerignore', 'uv.lock', 'deploy/browser_no_net.c')) {
            if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
                throw "Required project file is missing: $path"
            }
        }

        # NEVER use --build-arg for a password, API key or Neon connection string.
        Invoke-Docker -Arguments @('build', '--platform', 'linux/amd64', '--file', 'deploy/Dockerfile.api', '--tag', 'pagecheck-api:stage40', '.')
        Invoke-Docker -Arguments @('build', '--platform', 'linux/amd64', '--file', 'deploy/Dockerfile.ui', '--tag', 'pagecheck-ui:stage40', '.')
        Assert-LinuxAmd64 'pagecheck-api:stage40'
        Assert-LinuxAmd64 'pagecheck-ui:stage40'
        Invoke-Docker -Arguments @('run', '--rm', '--entrypoint', '/usr/local/bin/pagecheck-chromium-sandbox', 'pagecheck-api:stage40', '--self-test')

        Write-Host 'STAGE40_LOCAL_IMAGES_READY'
        Write-Host 'NO_IMAGE_PUBLISHED__NO_GITHUB_PUSH'
        Write-Host 'NEXT: Create ONE PRIVATE Docker Hub repository named pagecheck-staging.'
        Write-Host 'After docker login, run this script with -Mode Publish and -DockerHubUser.'
    }
    else {
        if ([string]::IsNullOrWhiteSpace($DockerHubUser)) {
            throw 'Publish requires -DockerHubUser YOUR_DOCKER_HUB_USERNAME.'
        }
        if (-not $PrivateRepositoryConfirmed) {
            throw 'Before publishing, verify the Docker Hub repository is PRIVATE, then pass -PrivateRepositoryConfirmed.'
        }
        Assert-LinuxAmd64 'pagecheck-api:stage40'
        Assert-LinuxAmd64 'pagecheck-ui:stage40'

        Write-Host 'PUBLISHING_TO_DOCKER_HUB_PRIVATE_REGISTRY__NOT_GITHUB'
        Write-Host 'The Docker Hub repository MUST be private. This script cannot check or change its visibility.'
        $api = "docker.io/$($DockerHubUser)/$($DockerHubRepo):stage40-api"
        $ui = "docker.io/$($DockerHubUser)/$($DockerHubRepo):stage40-ui"
        Invoke-Docker -Arguments @('tag', 'pagecheck-api:stage40', $api)
        Invoke-Docker -Arguments @('tag', 'pagecheck-ui:stage40', $ui)
        Invoke-Docker -Arguments @('push', $api)
        Invoke-Docker -Arguments @('push', $ui)
        Write-Host "RENDER_IMAGE_API=$api"
        Write-Host "RENDER_IMAGE_UI=$ui"
        Write-Host 'STAGE40_PRIVATE_IMAGE_UPLOAD_COMPLETED'
        Write-Host 'NO_GITHUB_PUSH'
    }
}
finally {
    Pop-Location
}
