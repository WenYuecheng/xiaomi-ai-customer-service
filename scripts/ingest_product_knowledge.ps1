[CmdletBinding()]
param(
    [string]$BaseUrl = "http://localhost:8000/api/v1",
    [string]$Username = "admin",
    [string]$KnowledgeBaseId,
    [string]$KnowledgeBaseName = "近两年产品参数知识库",
    [string]$DocumentsPath,
    [ValidateRange(200, 4000)]
    [int]$ChunkSize = 800,
    [ValidateRange(0, 800)]
    [int]$ChunkOverlap = 120,
    [ValidateRange(5, 120)]
    [int]$TimeoutMinutes = 45
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Net.Http

if (-not $DocumentsPath) {
    $DocumentsPath = Join-Path $PSScriptRoot "..\近两年产品参数知识库_待审核"
}

if ($ChunkOverlap -ge $ChunkSize) {
    throw "ChunkOverlap 必须小于 ChunkSize。"
}

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$documentsRoot = (Resolve-Path $DocumentsPath).Path
$envFile = Join-Path $projectRoot ".env"
$resultFile = Join-Path $projectRoot "data\imports\product-vector-import-result.json"

function Get-DotEnvValue {
    param([string]$Name)

    if (-not (Test-Path -LiteralPath $envFile)) {
        return $null
    }
    $line = Get-Content -LiteralPath $envFile -Encoding UTF8 |
        Where-Object { $_ -match "^$([regex]::Escape($Name))=" } |
        Select-Object -Last 1
    if (-not $line) {
        return $null
    }
    return ($line -split "=", 2)[1].Trim()
}

function Invoke-Api {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Path,
        [hashtable]$Headers,
        [object]$Body,
        [string]$ContentType = "application/json"
    )

    $parameters = @{
        Method = $Method
        Uri = "$BaseUrl$Path"
        ErrorAction = "Stop"
    }
    if ($Headers) { $parameters.Headers = $Headers }
    if ($null -ne $Body) {
        $parameters.Body = if ($ContentType -eq "application/json") {
            $Body | ConvertTo-Json -Depth 8
        } else {
            $Body
        }
        $parameters.ContentType = $ContentType
    }
    return Invoke-RestMethod @parameters
}

function Send-MarkdownFile {
    param(
        [Parameter(Mandatory = $true)][System.IO.FileInfo]$File,
        [Parameter(Mandatory = $true)][string]$Token,
        [Parameter(Mandatory = $true)][string]$TargetKnowledgeBaseId
    )

    $client = [System.Net.Http.HttpClient]::new()
    $client.Timeout = [TimeSpan]::FromMinutes(10)
    $client.DefaultRequestHeaders.Authorization =
        [System.Net.Http.Headers.AuthenticationHeaderValue]::new("Bearer", $Token)
    $form = [System.Net.Http.MultipartFormDataContent]::new()
    try {
        $form.Add([System.Net.Http.StringContent]::new($TargetKnowledgeBaseId), "knowledge_base_id")
        $form.Add([System.Net.Http.StringContent]::new([string]$ChunkSize), "chunk_size")
        $form.Add([System.Net.Http.StringContent]::new([string]$ChunkOverlap), "chunk_overlap")

        $stream = [System.IO.File]::OpenRead($File.FullName)
        $fileContent = [System.Net.Http.StreamContent]::new($stream)
        $fileContent.Headers.ContentType =
            [System.Net.Http.Headers.MediaTypeHeaderValue]::new("text/markdown")
        $form.Add($fileContent, "file", $File.Name)

        $response = $client.PostAsync("$BaseUrl/documents/upload", $form).GetAwaiter().GetResult()
        $content = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) {
            throw "上传 $($File.Name) 失败：HTTP $([int]$response.StatusCode) $content"
        }
        return $content | ConvertFrom-Json
    }
    finally {
        $form.Dispose()
        $client.Dispose()
    }
}

try {
    $health = Invoke-Api -Method Get -Path "/health"
} catch {
    throw "后端未运行或无法访问 $BaseUrl。请先启动 Docker Desktop，再执行 docker compose up -d。原始错误：$($_.Exception.Message)"
}
if ($health.status -ne "ok") {
    throw "后端健康检查未通过。"
}

$token = $env:INGEST_ACCESS_TOKEN
if (-not $token) {
    $password = $env:INGEST_PASSWORD
    if (-not $password) {
        $passwordVariable = if ($Username -eq "admin") {
            "INITIAL_ADMIN_PASSWORD"
        } elseif ($Username -eq "operator") {
            "INITIAL_OPERATOR_PASSWORD"
        } else {
            $null
        }
        if ($passwordVariable) {
            $password = Get-DotEnvValue -Name $passwordVariable
        }
    }
    if (-not $password) {
        throw "未找到登录密码。请先设置 `$env:INGEST_PASSWORD，然后重新运行脚本。"
    }
    try {
        $login = Invoke-Api -Method Post -Path "/auth/login" -Body @{
            username = $Username
            password = $password
        } -ContentType "application/x-www-form-urlencoded"
        $token = $login.access_token
    } catch {
        throw "登录失败。当前数据库账号密码可能与 .env 的初始化密码不同。请用当前有效密码设置 `$env:INGEST_PASSWORD 后重试。"
    }
}
$headers = @{ Authorization = "Bearer $token" }
$null = Invoke-Api -Method Get -Path "/auth/me" -Headers $headers

if (-not $KnowledgeBaseId) {
    $query = [Uri]::EscapeDataString($KnowledgeBaseName)
    $list = Invoke-Api -Method Get -Path "/knowledge-bases?q=$query" -Headers $headers
    $existing = $list.items | Where-Object { $_.name -eq $KnowledgeBaseName } | Select-Object -First 1
    if ($existing) {
        $KnowledgeBaseId = $existing.id
        Write-Host "复用知识库：$KnowledgeBaseName ($KnowledgeBaseId)"
    } else {
        $embeddingModel = Get-DotEnvValue -Name "EMBEDDING_MODEL"
        $payload = @{
            name = $KnowledgeBaseName
            description = "近两年手机、平板、手表手环及家电产品参数与价格资料，共 50 份 Markdown。"
        }
        if ($embeddingModel) { $payload.embedding_model = $embeddingModel }
        $created = Invoke-Api -Method Post -Path "/knowledge-bases" -Headers $headers -Body $payload
        $KnowledgeBaseId = $created.id
        Write-Host "已创建知识库：$KnowledgeBaseName ($KnowledgeBaseId)"
    }
} else {
    $null = Invoke-Api -Method Get -Path "/knowledge-bases/$KnowledgeBaseId" -Headers $headers
    Write-Host "使用指定知识库：$KnowledgeBaseId"
}

$files = @(Get-ChildItem -LiteralPath $documentsRoot -Recurse -File -Filter "PROD-*.md" | Sort-Object Name)
if ($files.Count -ne 50) {
    throw "预期找到 50 份产品文档，实际找到 $($files.Count) 份：$documentsRoot"
}

$documentList = Invoke-Api -Method Get -Path "/documents?knowledge_base_id=$KnowledgeBaseId" -Headers $headers
$existingByName = @{}
foreach ($document in $documentList.items) {
    $existingByName[$document.original_filename] = $document
}

$uploaded = 0
$skipped = 0
foreach ($file in $files) {
    if ($existingByName.ContainsKey($file.Name)) {
        Write-Host "跳过已存在：$($file.Name) [$($existingByName[$file.Name].status)]"
        $skipped += 1
        continue
    }
    $null = Send-MarkdownFile -File $file -Token $token -TargetKnowledgeBaseId $KnowledgeBaseId
    Write-Host "已加入向量化队列：$($file.Name)"
    $uploaded += 1
}

$deadline = (Get-Date).AddMinutes($TimeoutMinutes)
$lastSummary = ""
do {
    Start-Sleep -Seconds 2
    $documentList = Invoke-Api -Method Get -Path "/documents?knowledge_base_id=$KnowledgeBaseId" -Headers $headers
    $targetDocuments = @($documentList.items | Where-Object { $_.original_filename -in $files.Name })
    $ready = @($targetDocuments | Where-Object { $_.status -eq "ready" }).Count
    $failedDocuments = @($targetDocuments | Where-Object { $_.status -eq "failed" })
    $pending = @($targetDocuments | Where-Object { $_.status -in @("queued", "processing") }).Count
    $summary = "向量化进度：ready=$ready/$($files.Count), pending=$pending, failed=$($failedDocuments.Count)"
    if ($summary -ne $lastSummary) {
        Write-Host $summary
        $lastSummary = $summary
    }
    if ($ready + $failedDocuments.Count -ge $files.Count) { break }
    if ((Get-Date) -ge $deadline) {
        throw "等待向量化超时。最后状态：$summary"
    }
} while ($true)

$analytics = Invoke-Api -Method Get -Path "/knowledge-bases/$KnowledgeBaseId/analytics" -Headers $headers
$sampleDocument = $targetDocuments | Where-Object { $_.status -eq "ready" } | Select-Object -First 1
$sampleChunkCount = 0
if ($sampleDocument) {
    $sampleChunks = Invoke-Api -Method Get -Path "/documents/$($sampleDocument.id)/chunks" -Headers $headers
    $sampleChunkCount = $sampleChunks.total
}

$result = [ordered]@{
    completed_at = (Get-Date).ToString("o")
    knowledge_base_id = $KnowledgeBaseId
    knowledge_base_name = $KnowledgeBaseName
    embedding_model = Get-DotEnvValue -Name "EMBEDDING_MODEL"
    chunk_size = $ChunkSize
    chunk_overlap = $ChunkOverlap
    expected_documents = $files.Count
    uploaded_this_run = $uploaded
    skipped_existing = $skipped
    ready_documents = $analytics.ready_count
    failed_documents = $analytics.failed_count
    chunks = $analytics.chunk_count
    products = $analytics.product_count
    sample_document_chunks = $sampleChunkCount
    failures = @($failedDocuments | ForEach-Object {
        [ordered]@{
            filename = $_.original_filename
            error = $_.error_message
        }
    })
}

$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resultFile -Encoding UTF8
Write-Host ""
Write-Host "向量知识库处理完成。"
Write-Host "knowledge_base_id=$KnowledgeBaseId"
Write-Host "文档=$($analytics.ready_count)，切片=$($analytics.chunk_count)，失败=$($analytics.failed_count)"
Write-Host "结果文件：$resultFile"

if ($failedDocuments.Count -gt 0) {
    exit 1
}




