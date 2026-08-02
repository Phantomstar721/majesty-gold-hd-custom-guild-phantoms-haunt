param(
    [string]$SourceRoot = ".\dist\CustomGuildPhantomsHaunt",
    [string]$ModsRoot = "$env:USERPROFILE\Documents\My Games\MajestyHD\Mods"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "HauntDeployment.ps1")

$repoRoot = Split-Path -Parent $PSScriptRoot
$source = if ([IO.Path]::IsPathRooted($SourceRoot)) {
    Get-HauntCanonicalPath $SourceRoot
} else {
    Get-HauntCanonicalPath (Join-Path $repoRoot $SourceRoot)
}
$deploymentPaths = Get-SafeHauntDeploymentPaths $ModsRoot
$target = $deploymentPaths.Target

if (-not (Test-Path -LiteralPath $source -PathType Container)) {
    throw "Build output does not exist: $source"
}
$sourcePrefix = $source + [IO.Path]::DirectorySeparatorChar
$targetPrefix = $target + [IO.Path]::DirectorySeparatorChar
if ($source.Equals($target, [StringComparison]::OrdinalIgnoreCase) -or
    $source.StartsWith($targetPrefix, [StringComparison]::OrdinalIgnoreCase) -or
    $target.StartsWith($sourcePrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Unsafe Haunt deployment: source and target directories overlap."
}
$sourceManifest = Get-HauntDeploymentManifest $source
if ($sourceManifest.Count -eq 0) {
    throw "Refusing to replace the installed Haunt with an empty source package: $source"
}

if (Test-Path -LiteralPath $target) {
    Remove-Item -LiteralPath $target -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $target | Out-Null
Get-ChildItem -LiteralPath $source -Force | Copy-Item -Destination $target -Recurse -Force
$matchedFileCount = Assert-HauntDeploymentMatches -SourceRoot $source -TargetRoot $target

Write-Host "Deployed local mod package:"
Write-Host $target
Write-Host "Deploy verification matched $matchedFileCount files by size and SHA-256."
