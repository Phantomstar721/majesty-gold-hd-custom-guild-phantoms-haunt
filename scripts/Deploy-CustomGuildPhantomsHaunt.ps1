param(
    [string]$SourceRoot = ".\dist\CustomGuildPhantomsHaunt",
    [string]$ModsRoot = "$env:USERPROFILE\Documents\My Games\MajestyHD\Mods"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$source = Join-Path $repoRoot $SourceRoot
$target = Join-Path $ModsRoot "CustomGuildPhantomsHaunt"

if (-not (Test-Path $source)) {
    throw "Build output does not exist: $source"
}

if (Test-Path $target) {
    Remove-Item -LiteralPath $target -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item -Path (Join-Path (Resolve-Path $source).Path "*") -Destination $target -Recurse -Force

$sourceRoot = (Resolve-Path $source).Path
$targetRoot = (Resolve-Path $target).Path
$sourceFiles = @{}
$targetFiles = @{}

Get-ChildItem -LiteralPath $sourceRoot -Recurse -File | ForEach-Object {
    $relative = $_.FullName.Substring($sourceRoot.Length).TrimStart('\')
    $sourceFiles[$relative] = $_.Length
}

Get-ChildItem -LiteralPath $targetRoot -Recurse -File | ForEach-Object {
    $relative = $_.FullName.Substring($targetRoot.Length).TrimStart('\')
    $targetFiles[$relative] = $_.Length
}

foreach ($relative in $sourceFiles.Keys) {
    if (-not $targetFiles.ContainsKey($relative)) {
        throw "Deploy verification failed, missing file in target: $relative"
    }
    if ($targetFiles[$relative] -ne $sourceFiles[$relative]) {
        throw "Deploy verification failed, size mismatch: $relative"
    }
}

foreach ($relative in $targetFiles.Keys) {
    if (-not $sourceFiles.ContainsKey($relative)) {
        throw "Deploy verification failed, extra file in target: $relative"
    }
}

Write-Host "Deployed local mod package:"
Write-Host $target
Write-Host "Deploy verification matched $($sourceFiles.Count) files."
