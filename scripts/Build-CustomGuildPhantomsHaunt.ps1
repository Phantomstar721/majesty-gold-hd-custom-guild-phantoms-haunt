param(
    [string]$GamePath = "C:\Program Files (x86)\Steam\steamapps\common\Majesty HD",
    [string]$OutputRoot = ".\dist\CustomGuildPhantomsHaunt",
    [string]$PortraitImage = ".\assets\source\hero\portrait.png",
    [string]$BuildingProfileImage = ".\assets\source\buildings\haunt\level-1\profile.png",
    [string]$BuildingSpriteSheet = ".\assets\source\buildings\haunt\level-1\sprite-sheet.png",
    [string]$ConstructionSpriteSheet = ".\assets\source\buildings\haunt\level-1\construction-sheet.png",
    [string]$DamagedBSample = ".\assets\source\buildings\haunt\level-1\damaged-b.png",
    [string]$CollapsedIntermediateSample = ".\assets\source\buildings\haunt\level-1\collapsed.png",
    [string]$Level2ActiveSource = ".\assets\source\buildings\haunt\level-2\active.png",
    [string]$Level2DamagedSource = ".\assets\source\buildings\haunt\level-2\damaged.png",
    [string]$Level2DamagedBSource = ".\assets\source\buildings\haunt\level-2\damaged-b.png",
    [string]$Level2CollapsedSource = ".\assets\source\buildings\haunt\level-2\collapsed.png",
    [string]$Level2DestroyedSource = ".\assets\source\buildings\haunt\level-2\destroyed.png",
    [string]$Level2ConstructionEarlySource = ".\assets\source\buildings\haunt\level-2\upgrade-early.png",
    [string]$Level2ConstructionLateSource = ".\assets\source\buildings\haunt\level-2\upgrade-late.png",
    [string]$Level3ActiveSource = ".\assets\source\buildings\haunt\level-3\active.png",
    [string]$Level3DamagedSource = ".\assets\source\buildings\haunt\level-3\damaged.png",
    [string]$Level3DamagedBSource = ".\assets\source\buildings\haunt\level-3\damaged-b.png",
    [string]$Level3CollapsedSource = ".\assets\source\buildings\haunt\level-3\collapsed.png",
    [string]$Level3DestroyedSource = ".\assets\source\buildings\haunt\level-3\destroyed.png",
    [string]$Level3ConstructionEarlySource = ".\assets\source\buildings\haunt\level-3\upgrade-early.png",
    [string]$Level3ConstructionLateSource = ".\assets\source\buildings\haunt\level-3\upgrade-late.png",
    [string]$HeroSpriteSheet = ".\assets\source\hero\sprite-actions.png",
    [string]$HeroDirection03 = ".\assets\source\hero\direction-03.png",
    [string]$HeroDirection04 = ".\assets\source\hero\direction-04.png",
    [string]$HeroDirection05 = ".\assets\source\hero\direction-05.png",
    [string]$HeroDeathConcept = ".\assets\source\hero\death-concept.png",
    [string]$HeroDeathDirectionals = ".\assets\source\hero\death-directionals.png",
    [string]$HeroCastGlow = ".\assets\source\hero\cast-staff-glow.png",
    [string]$IceLanceProjectileSource = ".\assets\source\spells\ice-lance\projectile.png",
    [string]$IcyTouchImpactSource = ".\assets\source\spells\icy-touch\impact-skull.png",
    [string]$FrostArmorCrystalSource = ".\assets\source\spells\frost-armor\crystal.png",
    [string]$FrostArmorFrozenCasingSource = ".\assets\source\spells\frost-armor\frozen-casing.png",
    [string]$CallToGravePortalSource = ".\assets\source\spells\call-to-grave\portal.png",
    [string]$EternalSoulFlameSource = ".\assets\source\spells\eternal-soul\flame.png",
    [string]$EndlessWinterVortexSource = ".\assets\source\spells\endless-winter\vortex-sheet.png",
    [string]$EndlessWinterHitSource = ".\assets\source\spells\endless-winter\hit-tornado.png",
    [string]$EndlessWinterMissileSource = ".\assets\source\spells\endless-winter\missile-sheet.png",
    [string]$InterfacePanelImage = ".\assets\source\interface\panel.png",
    [string]$AudioRoot = ".\assets\audio",
    [switch]$AudioOnly,
    [switch]$GplOnly,
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
$validator = Join-Path $repoRoot "src\validate_phantom_build.py"
$iconGenerator = Join-Path $repoRoot "scripts\generate_phantom_icons.py"
$buildingSpriteGenerator = Join-Path $repoRoot "scripts\generate_phantom_building_sprites.py"
$heroSpriteGenerator = Join-Path $repoRoot "scripts\generate_phantom_hero_sprites.py"
$outputRootPath = Join-Path $repoRoot $OutputRoot

if ($AudioOnly -and $GplOnly) {
    throw "-AudioOnly and -GplOnly are mutually exclusive."
}

if ($GplOnly) {
    if (-not (Test-Path $outputRootPath)) {
        throw "GPL-only build requires an existing validated package: $outputRootPath. Run a full build first."
    }
    if (-not (Test-Path $toolsPython)) {
        throw "Shared tools Python does not exist: $toolsPython"
    }

    & $toolsPython $builder `
        --game-path $GamePath `
        --output-root $outputRootPath `
        --gpl-only
    if ($LASTEXITCODE -ne 0) {
        throw "Phantom GPL source generation failed with exit code $LASTEXITCODE"
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

    & $toolsPython $validator --output-root $outputRootPath
    if ($LASTEXITCODE -ne 0) {
        throw "Phantom package verification failed with exit code $LASTEXITCODE"
    }

    Write-Host "Updated GPL in existing validated mod package:"
    Write-Host $outputRootPath
    return
}

if ($AudioOnly) {
    if (-not (Test-Path $outputRootPath)) {
        throw "Audio-only build requires an existing validated package: $outputRootPath. Run a full build first."
    }
    if (-not (Test-Path $toolsPython)) {
        throw "Shared tools Python does not exist: $toolsPython"
    }

    $audioRootPath = Resolve-RepoPath $AudioRoot

    & $toolsPython $builder `
        --game-path $GamePath `
        --output-root $outputRootPath `
        --voices-only `
        --voice-dir $audioRootPath
    if ($LASTEXITCODE -ne 0) {
        throw "Phantom voice CAM builder failed with exit code $LASTEXITCODE"
    }

    & $toolsPython $validator --output-root $outputRootPath
    if ($LASTEXITCODE -ne 0) {
        throw "Phantom package verification failed with exit code $LASTEXITCODE"
    }

    Write-Host "Updated audio in existing validated mod package:"
    Write-Host $outputRootPath
    return
}

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
$callToGraveSpellIconRgb = Join-Path $tempDir "call_to_grave_spell_icon_24.rgb"
$phantomCowlIconRgb = Join-Path $tempDir "phantom_cowl_icon_23.rgb"
$darkStaffSmallIconRgb = Join-Path $tempDir "dark_staff_icon_16.rgb"
$darkStaffMxIconRgb = Join-Path $tempDir "dark_staff_icon_23.rgb"
$darkStaffIconRgb = Join-Path $tempDir "dark_staff_icon_50x19.rgb"
$interfacePanelRgb = Join-Path $tempDir "phantom_interface_panel_200x245.rgb"
$buildingSpriteDir = Join-Path $tempDir "building_sprites"
$buildingLevel2SpriteDir = Join-Path $tempDir "building_level_2_sprites"
$buildingLevel3SpriteDir = Join-Path $tempDir "building_level_3_sprites"
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
& $toolsPython $buildingSpriteGenerator `
    --sheet (Resolve-RepoPath $BuildingSpriteSheet) `
    --construction-sheet (Resolve-RepoPath $ConstructionSpriteSheet) `
    --damaged-b-sample (Resolve-RepoPath $DamagedBSample) `
    --collapsed-intermediate-sample (Resolve-RepoPath $CollapsedIntermediateSample) `
    --out-dir $buildingSpriteDir
if ($LASTEXITCODE -ne 0) {
    throw "Phantom building sprite generator failed with exit code $LASTEXITCODE"
}
& $toolsPython $buildingSpriteGenerator `
    --sheet (Resolve-RepoPath $BuildingSpriteSheet) `
    --level 2 `
    --active-source (Resolve-RepoPath $Level2ActiveSource) `
    --damaged-source (Resolve-RepoPath $Level2DamagedSource) `
    --destroyed-source (Resolve-RepoPath $Level2DestroyedSource) `
    --construction-early-source (Resolve-RepoPath $Level2ConstructionEarlySource) `
    --construction-late-source (Resolve-RepoPath $Level2ConstructionLateSource) `
    --damaged-b-sample (Resolve-RepoPath $Level2DamagedBSource) `
    --collapsed-intermediate-sample (Resolve-RepoPath $Level2CollapsedSource) `
    --out-dir $buildingLevel2SpriteDir
if ($LASTEXITCODE -ne 0) {
    throw "Phantom level 2 building sprite generator failed with exit code $LASTEXITCODE"
}
& $toolsPython $buildingSpriteGenerator `
    --sheet (Resolve-RepoPath $BuildingSpriteSheet) `
    --level 3 `
    --active-source (Resolve-RepoPath $Level3ActiveSource) `
    --damaged-source (Resolve-RepoPath $Level3DamagedSource) `
    --destroyed-source (Resolve-RepoPath $Level3DestroyedSource) `
    --construction-early-source (Resolve-RepoPath $Level3ConstructionEarlySource) `
    --construction-late-source (Resolve-RepoPath $Level3ConstructionLateSource) `
    --damaged-b-sample (Resolve-RepoPath $Level3DamagedBSource) `
    --collapsed-intermediate-sample (Resolve-RepoPath $Level3CollapsedSource) `
    --out-dir $buildingLevel3SpriteDir
if ($LASTEXITCODE -ne 0) {
    throw "Phantom level 3 building sprite generator failed with exit code $LASTEXITCODE"
}
& $toolsPython $heroSpriteGenerator `
    --sheet (Resolve-RepoPath $HeroSpriteSheet) `
    --direction-03 (Resolve-RepoPath $HeroDirection03) `
    --direction-04 (Resolve-RepoPath $HeroDirection04) `
    --direction-05 (Resolve-RepoPath $HeroDirection05) `
    --death-concept (Resolve-RepoPath $HeroDeathConcept) `
    --death-directionals (Resolve-RepoPath $HeroDeathDirectionals) `
    --cast-glow (Resolve-RepoPath $HeroCastGlow) `
    --out-dir $heroSpriteDir
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
    --building-level-2-sprite-rgb-dir $buildingLevel2SpriteDir `
    --building-level-3-sprite-rgb-dir $buildingLevel3SpriteDir `
    --hero-sprite-png-dir $heroSpriteDir `
    --interface-panel-rgb $interfacePanelRgb `
    --building-dialog-panel-rgb $interfacePanelRgb `
    --ice-lance-icon-rgb $iceLanceIconRgb `
    --ice-lance-projectile-source-png (Resolve-RepoPath $IceLanceProjectileSource) `
    --icy-touch-impact-source-png (Resolve-RepoPath $IcyTouchImpactSource) `
    --frost-armor-crystal-source-png (Resolve-RepoPath $FrostArmorCrystalSource) `
    --frost-armor-frozen-casing-source-png (Resolve-RepoPath $FrostArmorFrozenCasingSource) `
    --call-to-grave-portal-source-png (Resolve-RepoPath $CallToGravePortalSource) `
    --eternal-soul-flame-source-png (Resolve-RepoPath $EternalSoulFlameSource) `
    --endless-winter-vortex-source-png (Resolve-RepoPath $EndlessWinterVortexSource) `
    --endless-winter-hit-source-png (Resolve-RepoPath $EndlessWinterHitSource) `
    --endless-winter-missile-source-png (Resolve-RepoPath $EndlessWinterMissileSource) `
    --ice-lance-spell-icon-rgb $iceLanceSpellIconRgb `
    --frost-armor-spell-icon-rgb $frostArmorSpellIconRgb `
    --blizzard-spell-icon-rgb $blizzardSpellIconRgb `
    --call-to-grave-spell-icon-rgb $callToGraveSpellIconRgb `
    --phantom-cowl-icon-rgb $phantomCowlIconRgb `
    --dark-staff-small-icon-rgb $darkStaffSmallIconRgb `
    --dark-staff-mx-icon-rgb $darkStaffMxIconRgb `
    --dark-staff-icon-rgb $darkStaffIconRgb `
    --voice-dir (Resolve-RepoPath $AudioRoot)
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

& $toolsPython $validator --output-root $outputRootPath
if ($LASTEXITCODE -ne 0) {
    throw "Phantom package verification failed with exit code $LASTEXITCODE"
}

Write-Host "Built local mod package:"
Write-Host $outputRootPath
