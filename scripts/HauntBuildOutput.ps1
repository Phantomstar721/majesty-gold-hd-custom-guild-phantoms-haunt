function Get-SafeHauntBuildOutputPath {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$OutputRoot
    )

    $repoRootPath = [System.IO.Path]::GetFullPath($RepoRoot)
    $distRootPath = [System.IO.Path]::GetFullPath((Join-Path $repoRootPath "dist"))
    $candidate = if ([System.IO.Path]::IsPathRooted($OutputRoot)) {
        $OutputRoot
    }
    else {
        Join-Path $repoRootPath $OutputRoot
    }
    $outputRootPath = [System.IO.Path]::GetFullPath($candidate)
    $distPrefix = $distRootPath.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar

    if (
        $outputRootPath.Equals($distRootPath, [System.StringComparison]::OrdinalIgnoreCase) -or
        -not $outputRootPath.StartsWith($distPrefix, [System.StringComparison]::OrdinalIgnoreCase)
    ) {
        throw "Unsafe Haunt build output '$OutputRoot'. Full builds and partial updates must target a package directory inside '$distRootPath'."
    }

    if (Test-Path -LiteralPath $outputRootPath -PathType Leaf) {
        throw "Haunt build output is a file, not a directory: $outputRootPath"
    }

    # Lexical containment is not enough when an existing directory in the path
    # is a junction or symbolic link to somewhere outside the repository.
    $probe = $outputRootPath
    while ($true) {
        if (Test-Path -LiteralPath $probe) {
            $item = Get-Item -LiteralPath $probe -Force
            if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Unsafe Haunt build output uses a junction or symbolic link: $probe"
            }
        }
        if ($probe.Equals($distRootPath, [System.StringComparison]::OrdinalIgnoreCase)) {
            break
        }
        $probe = Split-Path -Parent $probe
    }

    return $outputRootPath
}

function Publish-ValidatedHauntBuild {
    param(
        [Parameter(Mandatory = $true)][string]$StagedRoot,
        [Parameter(Mandatory = $true)][string]$FinalRoot,
        [Parameter(Mandatory = $true)][string]$BackupRoot
    )

    if (-not (Test-Path -LiteralPath $StagedRoot -PathType Container)) {
        throw "Validated Haunt staging directory does not exist: $StagedRoot"
    }
    if (Test-Path -LiteralPath $BackupRoot) {
        throw "Haunt build backup path already exists: $BackupRoot"
    }

    $movedPrevious = $false
    if (Test-Path -LiteralPath $FinalRoot) {
        Move-Item -LiteralPath $FinalRoot -Destination $BackupRoot
        $movedPrevious = $true
    }

    try {
        Move-Item -LiteralPath $StagedRoot -Destination $FinalRoot
    }
    catch {
        if ($movedPrevious -and -not (Test-Path -LiteralPath $FinalRoot)) {
            Move-Item -LiteralPath $BackupRoot -Destination $FinalRoot
        }
        throw
    }

    if ($movedPrevious) {
        Remove-Item -LiteralPath $BackupRoot -Recurse -Force
    }
}
