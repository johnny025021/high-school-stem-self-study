[CmdletBinding()]
param(
    [string]$SiteRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem

$site = [IO.Path]::GetFullPath($SiteRoot)
$questionBankRoot = Join-Path $site '题库\数学'
$outputDirectory = Join-Path $site 'data'
$outputPath = Join-Path $outputDirectory 'catalog.json'

if (-not (Test-Path -LiteralPath $questionBankRoot -PathType Container)) {
    throw "Mathematics question-bank root not found: $questionBankRoot"
}

$packages = foreach ($zipFile in Get-ChildItem -LiteralPath $questionBankRoot -Recurse -File -Filter '*.zip') {
    $archive = [IO.Compression.ZipFile]::OpenRead($zipFile.FullName)
    try {
        $entry = $archive.Entries |
            Where-Object { $_.FullName -match '(^|/)manifest\.json$' } |
            Select-Object -First 1
        if (-not $entry) {
            throw "manifest.json not found in $($zipFile.Name)"
        }

        $reader = [IO.StreamReader]::new($entry.Open(), [Text.Encoding]::UTF8)
        try {
            $manifest = $reader.ReadToEnd() | ConvertFrom-Json
        }
        finally {
            $reader.Dispose()
        }

        $isMother = [int]($manifest.mother_question_count ?? 0) -gt 0
        $relativePath = [IO.Path]::GetRelativePath($site, $zipFile.FullName).Replace('\', '/')
        [ordered]@{
            package_id = [string]$manifest.package_id
            subject_id = 'math'
            version = [string]($manifest.package_version ?? '1.0')
            package_name = if ($manifest.package_name) { [string]$manifest.package_name } elseif ($isMother) { "$($manifest.chapter_name) 核心母题" } else { [string]$manifest.chapter_name }
            book_id = [string]$manifest.book_id
            book_name = [string]$manifest.book_name
            chapter_id = [string]$manifest.chapter_id
            chapter_name = [string]$manifest.chapter_name
            question_count = [int]$manifest.question_count
            module_id = if ($isMother) { 'mother_question' } else { 'chapter_practice' }
            mother_question_count = if ($isMother) { [int]$manifest.mother_question_count } else { 0 }
            file_name = $zipFile.Name
            file_size = [long]$zipFile.Length
            path = $relativePath
            published = $true
        }
    }
    finally {
        $archive.Dispose()
    }
}

$packages = @($packages | Sort-Object @{ Expression = { if ($_.book_id -eq 'MATH_YKYL2026_U1') { 0 } else { 1 } } }, chapter_id)
$catalog = [ordered]@{
    schema_version = '1.0'
    app_id = 'general_learning_question_bank'
    catalog_id = 'STEMBANK_GITHUB_CATALOG_V1'
    generated_at = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
    delivery_mode = 'github_pages_on_demand'
    package_count = $packages.Count
    packages = $packages
}

[IO.Directory]::CreateDirectory($outputDirectory) | Out-Null
[IO.File]::WriteAllText($outputPath, ($catalog | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
Write-Host "Wrote $($packages.Count) catalog entries: $outputPath"
