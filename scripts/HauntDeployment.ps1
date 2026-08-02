$HauntDeploymentPackageName = "CustomGuildPhantomsHaunt"

function Get-HauntCanonicalPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    return [IO.Path]::GetFullPath($Path).TrimEnd(
        [IO.Path]::DirectorySeparatorChar,
        [IO.Path]::AltDirectorySeparatorChar
    )
}

function Test-HauntReparsePoint {
    param([Parameter(Mandatory = $true)][string]$Path)

    $item = Get-Item -LiteralPath $Path -Force
    return (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)
}

function Get-SafeHauntDeploymentPaths {
    param([Parameter(Mandatory = $true)][string]$ModsRoot)

    if ([string]::IsNullOrWhiteSpace($ModsRoot)) {
        throw "Unsafe Haunt deployment path: the Mods root is empty."
    }

    $modsRootPath = Get-HauntCanonicalPath $ModsRoot
    if ((Split-Path -Leaf $modsRootPath) -ine "Mods" -or
        (Split-Path -Leaf (Split-Path -Parent $modsRootPath)) -ine "MajestyHD") {
        throw "Unsafe Haunt deployment path '$modsRootPath'. Expected a MajestyHD\Mods directory."
    }
    if (-not (Test-Path -LiteralPath $modsRootPath -PathType Container)) {
        throw "MajestyHD Mods directory does not exist: $modsRootPath"
    }
    if (Test-HauntReparsePoint $modsRootPath) {
        throw "Unsafe Haunt deployment path: the Mods directory is a reparse point: $modsRootPath"
    }
    if (Test-Path -LiteralPath (Join-Path $modsRootPath "MajestyHD.exe")) {
        throw "Unsafe Haunt deployment path: the selected Mods root appears to be the game directory: $modsRootPath"
    }

    $targetPath = Get-HauntCanonicalPath (Join-Path $modsRootPath $HauntDeploymentPackageName)
    $targetParent = Get-HauntCanonicalPath (Split-Path -Parent $targetPath)
    if (-not $targetParent.Equals($modsRootPath, [StringComparison]::OrdinalIgnoreCase) -or
        (Split-Path -Leaf $targetPath) -cne $HauntDeploymentPackageName -or
        $targetPath.Equals($modsRootPath, [StringComparison]::OrdinalIgnoreCase) -or
        -not $targetPath.StartsWith(
            $modsRootPath + [IO.Path]::DirectorySeparatorChar,
            [StringComparison]::OrdinalIgnoreCase
        )) {
        throw "Unsafe Haunt deployment target: $targetPath"
    }

    if (Test-Path -LiteralPath $targetPath) {
        if (-not (Test-Path -LiteralPath $targetPath -PathType Container)) {
            throw "Unsafe Haunt deployment target is not a directory: $targetPath"
        }
        if (Test-HauntReparsePoint $targetPath) {
            throw "Unsafe Haunt deployment target contains a reparse point: $targetPath"
        }

        $pending = New-Object "Collections.Generic.Stack[string]"
        $pending.Push($targetPath)
        while ($pending.Count -gt 0) {
            $directory = $pending.Pop()
            foreach ($item in @(Get-ChildItem -LiteralPath $directory -Force)) {
                if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                    throw "Unsafe Haunt deployment target contains a reparse point: $($item.FullName)"
                }
                if ($item.PSIsContainer) {
                    $pending.Push($item.FullName)
                }
            }
        }
    }

    return [pscustomobject]@{
        ModsRoot = $modsRootPath
        Target = $targetPath
    }
}

function Get-HauntDeploymentManifest {
    param([Parameter(Mandatory = $true)][string]$Root)

    $rootPath = Get-HauntCanonicalPath $Root
    if (-not (Test-Path -LiteralPath $rootPath -PathType Container)) {
        throw "Cannot create deployment manifest; directory does not exist: $rootPath"
    }

    $manifest = @{}
    Get-ChildItem -LiteralPath $rootPath -Recurse -File -Force | ForEach-Object {
        $relative = $_.FullName.Substring($rootPath.Length).TrimStart('\', '/')
        $manifest[$relative] = [pscustomobject]@{
            Length = $_.Length
            Sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash
        }
    }
    return $manifest
}

function Assert-HauntDeploymentMatches {
    param(
        [Parameter(Mandatory = $true)][string]$SourceRoot,
        [Parameter(Mandatory = $true)][string]$TargetRoot
    )

    $sourceFiles = Get-HauntDeploymentManifest $SourceRoot
    $targetFiles = Get-HauntDeploymentManifest $TargetRoot
    if ($sourceFiles.Count -eq 0) {
        throw "Deploy verification failed: source package contains no files."
    }

    foreach ($relative in $sourceFiles.Keys) {
        if (-not $targetFiles.ContainsKey($relative)) {
            throw "Deploy verification failed, missing file in target: $relative"
        }
        if ($targetFiles[$relative].Length -ne $sourceFiles[$relative].Length) {
            throw "Deploy verification failed, size mismatch: $relative"
        }
        if ($targetFiles[$relative].Sha256 -ne $sourceFiles[$relative].Sha256) {
            throw "Deploy verification failed, SHA-256 mismatch: $relative"
        }
    }

    foreach ($relative in $targetFiles.Keys) {
        if (-not $sourceFiles.ContainsKey($relative)) {
            throw "Deploy verification failed, extra file in target: $relative"
        }
    }

    return $sourceFiles.Count
}
