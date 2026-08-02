param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$deployScript = Join-Path $repoRoot "scripts\Deploy-CustomGuildPhantomsHaunt.ps1"
. (Join-Path $repoRoot "scripts\HauntDeployment.ps1")

function Assert-ThrowsLike {
    param(
        [Parameter(Mandatory = $true)][scriptblock]$Action,
        [Parameter(Mandatory = $true)][string]$Pattern
    )

    try {
        & $Action
    } catch {
        if ($_ -notmatch $Pattern) {
            throw "Expected error matching '$Pattern', got: $_"
        }
        return
    }
    throw "Expected an error matching '$Pattern'."
}

$testRoot = Join-Path $PSScriptRoot (".tmp-haunt-deployment-{0}-{1}" -f $PID, [guid]::NewGuid().ToString("N"))
$source = Join-Path $testRoot "source"
$modsRoot = Join-Path $testRoot "Documents\My Games\MajestyHD\Mods"
$target = Join-Path $modsRoot "CustomGuildPhantomsHaunt"
$junction = $null

try {
    New-Item -ItemType Directory -Path (Join-Path $source "Data") -Force | Out-Null
    New-Item -ItemType Directory -Path $modsRoot -Force | Out-Null
    [IO.File]::WriteAllBytes((Join-Path $source "Data\payload.bin"), [byte[]]@(1, 2, 3, 4))
    [IO.File]::WriteAllText((Join-Path $source "README.txt"), "deployment fixture")

    & $deployScript -SourceRoot $source -ModsRoot $modsRoot
    $matched = Assert-HauntDeploymentMatches -SourceRoot $source -TargetRoot $target
    if ($matched -ne 2) {
        throw "Expected two files in the valid deployment, got $matched."
    }

    [IO.File]::WriteAllBytes((Join-Path $target "Data\payload.bin"), [byte[]]@(4, 3, 2, 1))
    Assert-ThrowsLike {
        Assert-HauntDeploymentMatches -SourceRoot $source -TargetRoot $target
    } "SHA-256 mismatch"

    & $deployScript -SourceRoot $source -ModsRoot $modsRoot
    Remove-Item -LiteralPath (Join-Path $target "README.txt")
    Assert-ThrowsLike {
        Assert-HauntDeploymentMatches -SourceRoot $source -TargetRoot $target
    } "missing file"

    & $deployScript -SourceRoot $source -ModsRoot $modsRoot
    [IO.File]::WriteAllText((Join-Path $target "extra.txt"), "unexpected")
    Assert-ThrowsLike {
        Assert-HauntDeploymentMatches -SourceRoot $source -TargetRoot $target
    } "extra file"

    Assert-ThrowsLike {
        Get-SafeHauntDeploymentPaths (Join-Path $testRoot "not-the-mods-folder")
    } "Expected a MajestyHD\\Mods directory"

    & $deployScript -SourceRoot $source -ModsRoot $modsRoot
    Remove-Item -LiteralPath $target -Recurse -Force
    $junctionTarget = Join-Path $testRoot "junction-target"
    New-Item -ItemType Directory -Path $junctionTarget | Out-Null
    $junction = New-Item -ItemType Junction -Path $target -Target $junctionTarget
    Assert-ThrowsLike {
        Get-SafeHauntDeploymentPaths $modsRoot
    } "reparse point"
    Remove-Item -LiteralPath $target -Force
    $junction = $null
    if (-not (Test-Path -LiteralPath $junctionTarget -PathType Container)) {
        throw "Reparse-point rejection damaged the junction target."
    }

    [IO.File]::WriteAllText((Join-Path $modsRoot "MajestyHD.exe"), "fixture")
    Assert-ThrowsLike {
        Get-SafeHauntDeploymentPaths $modsRoot
    } "appears to be the game directory"

    Write-Host "Haunt deployment safety and integrity tests passed."
} finally {
    if ($null -ne $junction -and (Test-Path -LiteralPath $target)) {
        Remove-Item -LiteralPath $target -Force
    }
    $testRootPath = [IO.Path]::GetFullPath($testRoot)
    $testsRootPath = [IO.Path]::GetFullPath($PSScriptRoot)
    if (Test-Path -LiteralPath $testRootPath) {
        if (-not $testRootPath.StartsWith(
            $testsRootPath + [IO.Path]::DirectorySeparatorChar,
            [StringComparison]::OrdinalIgnoreCase
        )) {
            throw "Refusing to remove temporary path outside the tests directory: $testRootPath"
        }
        Remove-Item -LiteralPath $testRootPath -Recurse -Force
    }
}
