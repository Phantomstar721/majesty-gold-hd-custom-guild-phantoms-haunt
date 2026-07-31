param(
    [string]$GamePath = "C:\Program Files (x86)\Steam\steamapps\common\Majesty HD",
    [string]$OutputRoot = ".\dist\PhantomGuildPoc",
    [string]$AudioRoot = ".\assets\audio",
    [string]$RecruitmentVoiceClean = ".\assets\audio\phantom-recruitment-clean.wav",
    [string]$RecruitmentVoice = ".\assets\audio\phantom-recruitment-game.wav"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$buildScript = Join-Path $PSScriptRoot "Build-PhantomGuildPoc.ps1"
$deployScript = Join-Path $PSScriptRoot "Deploy-PhantomGuildPocRegisteredWorkshop.ps1"

& $buildScript `
    -GamePath $GamePath `
    -OutputRoot $OutputRoot `
    -AudioRoot $AudioRoot `
    -RecruitmentVoiceClean $RecruitmentVoiceClean `
    -RecruitmentVoice $RecruitmentVoice `
    -AudioOnly
if ($LASTEXITCODE -ne 0) {
    throw "Incremental Phantom audio build failed with exit code $LASTEXITCODE"
}

& $deployScript -SourceRoot $OutputRoot
if ($LASTEXITCODE -ne 0) {
    throw "Registered Workshop audio deploy failed with exit code $LASTEXITCODE"
}

Write-Host "Released incremental Phantom audio update from:"
Write-Host (Join-Path $repoRoot $OutputRoot)
