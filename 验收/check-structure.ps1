$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$required = @(
  'index.html',
  '公共资源\styles.css',
  '公共资源\home.js',
  '公共资源\subject-shell.js',
  'data\catalog.json',
  '学科\数学\index.html',
  '学科\物理\index.html',
  '学科\化学\index.html',
  '题库\数学\章节练习',
  '题库\数学\公式记忆',
  '题库\数学\二级结论记忆',
  '题库\物理\章节练习',
  '题库\物理\公式记忆',
  '题库\物理\二级结论记忆',
  '题库\化学\章节练习',
  '题库\化学\公式记忆',
  '题库\化学\二级结论记忆',
  '学习记录\数学\学习记录.template.json',
  '学习记录\物理\学习记录.template.json',
  '学习记录\化学\学习记录.template.json'
)

$missing = @($required | Where-Object { -not (Test-Path -LiteralPath (Join-Path $root $_)) })
$jsonFiles = Get-ChildItem -LiteralPath (Join-Path $root '配置') -Recurse -File -Filter '*.json'
$jsonFiles += Get-ChildItem -LiteralPath (Join-Path $root '学习记录') -Recurse -File -Filter '*.json'
$jsonFiles += Get-ChildItem -LiteralPath (Join-Path $root 'data') -Recurse -File -Filter '*.json'
$jsonErrors = @()
foreach ($file in $jsonFiles) {
  try { Get-Content -Raw -LiteralPath $file.FullName | ConvertFrom-Json | Out-Null }
  catch { $jsonErrors += $file.FullName }
}

$htmlFiles = Get-ChildItem -LiteralPath $root -Recurse -File -Filter '*.html'
$externalRefs = @()
$unexpectedExternalRefs = @()
foreach ($file in $htmlFiles) {
  $text = Get-Content -Raw -LiteralPath $file.FullName
  $urls = @([regex]::Matches($text, 'https?://[^\s"''`<>]+') | ForEach-Object Value | Sort-Object -Unique)
  if ($urls.Count) {
    $externalRefs += [ordered]@{ file = $file.FullName; urls = $urls }
    $unexpected = @($urls | Where-Object { $_ -notlike 'https://api.github.com/*' })
    if ($unexpected.Count) { $unexpectedExternalRefs += [ordered]@{ file = $file.FullName; urls = $unexpected } }
  }
}

$result = [ordered]@{
  checked_at = (Get-Date).ToString('o')
  root = $root
  required_count = $required.Count
  missing = $missing
  json_file_count = $jsonFiles.Count
  invalid_json = $jsonErrors
  html_file_count = $htmlFiles.Count
  approved_external_urls = $externalRefs
  unexpected_external_urls = $unexpectedExternalRefs
  passed = ($missing.Count -eq 0 -and $jsonErrors.Count -eq 0 -and $unexpectedExternalRefs.Count -eq 0)
}
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'structure-validation.json') -Encoding UTF8
$result | ConvertTo-Json -Depth 8
if (-not $result.passed) { exit 1 }
