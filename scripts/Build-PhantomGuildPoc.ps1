param(
    [string]$GamePath = "C:\Program Files (x86)\Steam\steamapps\common\Majesty HD",
    [string]$OutputRoot = ".\dist\PhantomGuildPoc",
    [string]$PortraitImage = ".\assets\source\phantom-portrait.png",
    [string]$BuildingProfileImage = ".\assets\source\phantom-guild-profile.png",
    [string]$BuildingSpriteSheet = ".\assets\source\phantom-guild-sprite-sheet-smooth.png",
    [string]$ConstructionSpriteSheet = ".\assets\source\phantom-guild-construction-proof-v1.png",
    [string]$HeroSpriteSheet = ".\assets\source\phantom-hero-sprite-source-sheet.png",
    [string]$GravestoneImage = ".\assets\source\phantom-gravestone-source.png",
    [string]$InterfacePanelImage = ".\assets\source\phantom-interface-panel-source.png",
    [string]$GplCompiler = ""
)

$ErrorActionPreference = "Stop"

function Convert-ImageToRawRgb {
    param(
        [Parameter(Mandatory = $true)][string]$InputPath,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [int]$Width = 100,
        [int]$Height = 100,
        [int]$GridColumns = 1,
        [int]$GridRows = 1,
        [int]$GridColumn = 0,
        [int]$GridRow = 0,
        [switch]$BrightenForSmallIcon
    )

    Add-Type -AssemblyName System.Drawing

    $resolvedInput = (Resolve-Path $InputPath).Path
    $source = [System.Drawing.Image]::FromFile($resolvedInput)
    $bitmap = $null
    $graphics = $null

    try {
        $cellWidth = [int]($source.Width / $GridColumns)
        $cellHeight = [int]($source.Height / $GridRows)
        $cellX = $GridColumn * $cellWidth
        $cellY = $GridRow * $cellHeight
        $side = [Math]::Min($cellWidth, $cellHeight)
        $sourceX = $cellX + [int](($cellWidth - $side) / 2)
        $sourceY = $cellY + [int](($cellHeight - $side) / 2)
        $sourceRect = New-Object System.Drawing.Rectangle $sourceX, $sourceY, $side, $side
        $destRect = New-Object System.Drawing.Rectangle 0, 0, $Width, $Height

        $bitmap = New-Object System.Drawing.Bitmap $Width, $Height, ([System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.Clear([System.Drawing.Color]::Black)
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
        $graphics.DrawImage($source, $destRect, $sourceRect, [System.Drawing.GraphicsUnit]::Pixel)

        $bytes = New-Object byte[] ($Width * $Height * 3)
        $offset = 0
        for ($y = 0; $y -lt $Height; $y++) {
            for ($x = 0; $x -lt $Width; $x++) {
                $pixel = $bitmap.GetPixel($x, $y)
                $red = $pixel.R
                $green = $pixel.G
                $blue = $pixel.B
                if ($BrightenForSmallIcon) {
                    if (($red + $green + $blue) -lt 36) {
                        $red = 30
                        $green = 64
                        $blue = 92
                    }
                    else {
                        $red = [Math]::Min(255, [int]($red * 1.18) + 18)
                        $green = [Math]::Min(255, [int]($green * 1.18) + 18)
                        $blue = [Math]::Min(255, [int]($blue * 1.28) + 28)
                    }
                }
                $bytes[$offset] = $red
                $bytes[$offset + 1] = $green
                $bytes[$offset + 2] = $blue
                $offset += 3
            }
        }

        [System.IO.File]::WriteAllBytes($OutputPath, $bytes)
    }
    finally {
        if ($graphics) { $graphics.Dispose() }
        if ($bitmap) { $bitmap.Dispose() }
        $source.Dispose()
    }
}

function Resolve-RepoPath {
    param(
        [Parameter(Mandatory = $true)][string]$PathValue
    )

    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return $PathValue
    }

    return (Join-Path $repoRoot $PathValue)
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$workspaceRoot = Split-Path -Parent $repoRoot
$toolsPython = Join-Path $workspaceRoot ".tools\python.cmd"
$builder = Join-Path $repoRoot "src\build_phantom_guild.py"
$iconGenerator = Join-Path $repoRoot "scripts\generate_phantom_icons.py"
$buildingSpriteGenerator = Join-Path $repoRoot "scripts\generate_phantom_building_sprites.py"
$heroSpriteGenerator = Join-Path $repoRoot "scripts\generate_phantom_hero_sprites.py"
$outputRootPath = Join-Path $repoRoot $OutputRoot

if (Test-Path $outputRootPath) {
    Remove-Item -LiteralPath $outputRootPath -Recurse -Force
}

$tempDir = Join-Path $repoRoot "dist\temp"
if (Test-Path $tempDir) {
    Remove-Item -LiteralPath $tempDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

$portraitRgb = Join-Path $tempDir "phantom_portrait_100.rgb"
$buildingProfileRgb = Join-Path $tempDir "phantom_guild_profile_100.rgb"
$heroIconRgb = Join-Path $tempDir "phantom_hero_icon_25.rgb"
$buildingIconRgb = Join-Path $tempDir "phantom_guild_icon_25.rgb"
$iceLanceIconRgb = Join-Path $tempDir "ice_lance_icon_29.rgb"
$iceLanceSpellIconRgb = Join-Path $tempDir "ice_lance_spell_icon_24.rgb"
$frostArmorSpellIconRgb = Join-Path $tempDir "frost_armor_spell_icon_24.rgb"
$blizzardSpellIconRgb = Join-Path $tempDir "blizzard_spell_icon_24.rgb"
$phantomCowlIconRgb = Join-Path $tempDir "phantom_cowl_icon_23.rgb"
$darkStaffSmallIconRgb = Join-Path $tempDir "dark_staff_icon_16.rgb"
$darkStaffMxIconRgb = Join-Path $tempDir "dark_staff_icon_23.rgb"
$darkStaffIconRgb = Join-Path $tempDir "dark_staff_icon_50x19.rgb"
$interfacePanelRgb = Join-Path $tempDir "phantom_interface_panel_200x245.rgb"
$buildingSpriteDir = Join-Path $tempDir "building_sprites"
$heroSpriteDir = Join-Path $tempDir "hero_sprites"

Convert-ImageToRawRgb -InputPath (Resolve-RepoPath $PortraitImage) -OutputPath $portraitRgb -Width 100 -Height 100
Convert-ImageToRawRgb -InputPath (Resolve-RepoPath $BuildingProfileImage) -OutputPath $buildingProfileRgb -Width 100 -Height 100
Convert-ImageToRawRgb -InputPath (Resolve-RepoPath $InterfacePanelImage) -OutputPath $interfacePanelRgb -Width 200 -Height 245
if (-not (Test-Path $toolsPython)) {
    throw "Shared tools Python does not exist: $toolsPython"
}
& $toolsPython $iconGenerator --out-dir $tempDir
if ($LASTEXITCODE -ne 0) {
    throw "Phantom icon generator failed with exit code $LASTEXITCODE"
}
& $toolsPython $buildingSpriteGenerator --sheet (Resolve-RepoPath $BuildingSpriteSheet) --construction-sheet (Resolve-RepoPath $ConstructionSpriteSheet) --out-dir $buildingSpriteDir
if ($LASTEXITCODE -ne 0) {
    throw "Phantom building sprite generator failed with exit code $LASTEXITCODE"
}
& $toolsPython $heroSpriteGenerator --sheet (Resolve-RepoPath $HeroSpriteSheet) --gravestone-source (Resolve-RepoPath $GravestoneImage) --out-dir $heroSpriteDir
if ($LASTEXITCODE -ne 0) {
    throw "Phantom hero sprite generator failed with exit code $LASTEXITCODE"
}

& $toolsPython $builder `
    --game-path $GamePath `
    --output-root $outputRootPath `
    --portrait-rgb $portraitRgb `
    --hero-icon-rgb $heroIconRgb `
    --building-profile-rgb $buildingProfileRgb `
    --building-icon-rgb $buildingIconRgb `
    --building-sprite-rgb-dir $buildingSpriteDir `
    --hero-sprite-png-dir $heroSpriteDir `
    --interface-panel-rgb $interfacePanelRgb `
    --building-dialog-panel-rgb $interfacePanelRgb `
    --ice-lance-icon-rgb $iceLanceIconRgb `
    --ice-lance-spell-icon-rgb $iceLanceSpellIconRgb `
    --frost-armor-spell-icon-rgb $frostArmorSpellIconRgb `
    --blizzard-spell-icon-rgb $blizzardSpellIconRgb `
    --phantom-cowl-icon-rgb $phantomCowlIconRgb `
    --dark-staff-small-icon-rgb $darkStaffSmallIconRgb `
    --dark-staff-mx-icon-rgb $darkStaffMxIconRgb `
    --dark-staff-icon-rgb $darkStaffIconRgb
if ($LASTEXITCODE -ne 0) {
    throw "Phantom CAM builder failed with exit code $LASTEXITCODE"
}

if ($GplCompiler -eq "") {
    $GplCompiler = Join-Path $GamePath "SDK\Gplbcc.exe"
}
if (-not (Test-Path $GplCompiler)) {
    throw "GPL compiler does not exist: $GplCompiler"
}

$gplDir = Join-Path $outputRootPath "GPL"
$dataDir = Join-Path $outputRootPath "Data"
$compiledPath = Join-Path $gplDir "Phantom.bcd"
Push-Location $gplDir
try {
    & $GplCompiler -in Phantom.gplproj -out Phantom.bcd -stdout
    if ($LASTEXITCODE -ne 0) {
        throw "GPL compiler failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

if (-not (Test-Path $compiledPath)) {
    throw "GPL compiler did not produce: $compiledPath"
}
Copy-Item -Path $compiledPath -Destination (Join-Path $dataDir "Phantom.bcd") -Force

Write-Host "Built local mod package:"
Write-Host $outputRootPath
