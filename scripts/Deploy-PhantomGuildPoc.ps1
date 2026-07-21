param(
    [string]$SourceRoot = ".\dist\PhantomGuildPoc",
    [string]$ModsRoot = "$env:USERPROFILE\Documents\My Games\MajestyHD\Mods"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$source = Join-Path $repoRoot $SourceRoot
$target = Join-Path $ModsRoot "PhantomGuildPoc"

if (-not (Test-Path $source)) {
    throw "Build output does not exist: $source"
}

New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item -Path (Join-Path (Resolve-Path $source).Path "*") -Destination $target -Recurse -Force

Write-Host "Deployed local mod package:"
Write-Host $target
