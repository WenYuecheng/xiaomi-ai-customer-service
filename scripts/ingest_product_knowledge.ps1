[CmdletBinding()]
param(
    [string]$BaseUrl = "http://localhost:8000/api/v1",
    [string]$Username = "operator",
    [string]$PasswordEnv = "INGEST_PASSWORD",
    [string]$DocumentsRoot = "data/knowledge"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $projectRoot
try {
    & uv run --project backend python scripts/ingest_product_knowledge.py `
        --base-url $BaseUrl `
        --username $Username `
        --password-env $PasswordEnv `
        --documents-root $DocumentsRoot
    if ($LASTEXITCODE -ne 0) {
        throw "产品知识库导入失败，退出码：$LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
