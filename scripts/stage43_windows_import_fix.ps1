# Corrige SOMENTE o import do broker Unix no Windows.
# Nao habilita acesso publico, nao modifica Docker, Render ou Git.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$arquivo = Join-Path (Get-Location).Path 'src/pagecheck/common/security/public_fetch_broker.py'
if (-not (Test-Path -LiteralPath $arquivo -PathType Leaf)) {
    throw "Arquivo nao encontrado: $arquivo. Execute na pasta raiz do projeto Page Check."
}

$conteudo = [System.IO.File]::ReadAllText($arquivo)
$original = 'class _BrokerServer(socketserver.UnixStreamServer):'
$atualizado = 'class _BrokerServer(_BrokerServerBase):'

if ($conteudo.Contains($atualizado) -and $conteudo.Contains('_BrokerServerBase = getattr(socketserver, "UnixStreamServer", None)')) {
    Write-Host 'STAGE43_WINDOWS_IMPORT_ALREADY_PATCHED'
    exit 0
}

$ocorrencias = ([regex]::Matches($conteudo, [regex]::Escape($original))).Count
if ($ocorrencias -ne 1) {
    throw "Esperava 1 ocorrencia da classe original, encontrei $ocorrencias. Nao alterei nada."
}

$substituto = @'
# Render runs the secure broker on Linux. Windows must be able to import the API
# for local tests, but must never substitute a TCP broker for the Unix socket.
_BrokerServerBase = getattr(socketserver, "UnixStreamServer", None)
if _BrokerServerBase is None:
    class _BrokerServerBase:
        def __new__(cls, *args, **kwargs):
            raise RuntimeError("The isolated Unix-socket broker is unavailable on this platform.")

class _BrokerServer(_BrokerServerBase):
'@

$novo = $conteudo.Replace($original, $substituto)
$backup = Join-Path ([System.IO.Path]::GetTempPath()) 'pagecheck-stage43-public_fetch_broker-before-windows-fix.py'
if (-not (Test-Path -LiteralPath $backup)) {
    [System.IO.File]::WriteAllText($backup, $conteudo, [System.Text.UTF8Encoding]::new($false))
}
[System.IO.File]::WriteAllText($arquivo, $novo, [System.Text.UTF8Encoding]::new($false))
Write-Host 'STAGE43_WINDOWS_IMPORT_FIX_APPLIED'
Write-Host 'Unix socket broker remains Linux-only and fails closed on Windows.'
Write-Host 'No Docker, Render, security flags, Git commit or push performed.'
Write-Host 'NEXT: uv run python -c "from pagecheck.api.app import app; print(''API_IMPORT_OK'')"'
Write-Host 'THEN: uv run pytest -q'
