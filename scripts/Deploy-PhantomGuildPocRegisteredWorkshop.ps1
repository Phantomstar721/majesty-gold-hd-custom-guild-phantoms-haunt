param(
    [string]$SourceRoot = ".\dist\PhantomGuildPoc",
    [string]$WorkshopContentRoot = "C:\Program Files (x86)\Steam\steamapps\workshop\content\73230",
    [string]$WorkshopId = "3769947406",
    [string]$ModsRoot = "$env:USERPROFILE\Documents\My Games\MajestyHD\Mods"
)

$ErrorActionPreference = "Stop"

function Test-ExactCopy {
    param(
        [Parameter(Mandatory = $true)][string]$SourceRoot,
        [Parameter(Mandatory = $true)][string]$TargetRoot
    )

    $sourceFiles = @{}
    $targetFiles = @{}

    Get-ChildItem -LiteralPath $SourceRoot -Recurse -File | ForEach-Object {
        $relative = $_.FullName.Substring($SourceRoot.Length).TrimStart('\')
        $sourceFiles[$relative] = $_.Length
    }

    Get-ChildItem -LiteralPath $TargetRoot -Recurse -File | ForEach-Object {
        $relative = $_.FullName.Substring($TargetRoot.Length).TrimStart('\')
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

    return $sourceFiles.Count
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$source = Join-Path $repoRoot $SourceRoot
$target = Join-Path $WorkshopContentRoot $WorkshopId
$localLooseTarget = Join-Path $ModsRoot "PhantomGuildPoc"

if (-not (Test-Path $source)) {
    throw "Build output does not exist: $source"
}
if (-not (Test-Path $target)) {
    throw "Registered Workshop folder does not exist yet: $target. Subscribe to the private item, or update it through RGSeditor from the SDK package first."
}

if (Test-Path $localLooseTarget) {
    Remove-Item -LiteralPath $localLooseTarget -Recurse -Force
}

Remove-Item -LiteralPath $target -Recurse -Force
New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item -Path (Join-Path (Resolve-Path $source).Path "*") -Destination $target -Recurse -Force

$fileCount = Test-ExactCopy -SourceRoot (Resolve-Path $source).Path -TargetRoot (Resolve-Path $target).Path

Write-Host "Removed loose local mod package:"
Write-Host $localLooseTarget
Write-Host "Deployed registered private Workshop package:"
Write-Host $target
Write-Host "Workshop ID:"
Write-Host $WorkshopId
Write-Host "Deploy verification matched $fileCount files."
