param(
    [string]$SourceRoot = ".\dist\PhantomGuildPoc",
    [string]$SdkModsRoot = "C:\Program Files (x86)\Steam\steamapps\common\Majesty HD\SDK\Mods",
    [string]$WorkshopProject = ".\assets\source\phantom guild.mswproj"
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
$workshopProjectPath = Join-Path $repoRoot $WorkshopProject
$target = Join-Path $SdkModsRoot "PhantomGuildPoc"

if (-not (Test-Path $source)) {
    throw "Build output does not exist: $source"
}
if (-not (Test-Path $workshopProjectPath)) {
    throw "Workshop project metadata does not exist: $workshopProjectPath"
}

if (Test-Path $target) {
    Remove-Item -LiteralPath $target -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item -Path (Join-Path (Resolve-Path $source).Path "*") -Destination $target -Recurse -Force

$fileCount = Test-ExactCopy -SourceRoot (Resolve-Path $source).Path -TargetRoot (Resolve-Path $target).Path
Copy-Item -LiteralPath $workshopProjectPath -Destination (Join-Path $target "PhantomGuildPoc.mswproj") -Force

Write-Host "Deployed SDK upload package:"
Write-Host $target
Write-Host "Deploy verification matched $fileCount files."
Write-Host "Copied Workshop metadata:"
Write-Host (Join-Path $target "PhantomGuildPoc.mswproj")
