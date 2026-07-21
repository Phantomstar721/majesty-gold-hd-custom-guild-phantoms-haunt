param(
    [string]$GamePath = "C:\Program Files (x86)\Steam\steamapps\common\Majesty HD",
    [string]$OutputRoot = ".\dist\PhantomGuildPoc",
    [string]$GplCompiler = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$builder = Join-Path $repoRoot "src\build_phantom_guild.py"
$outputRootPath = Join-Path $repoRoot $OutputRoot

python $builder --game-path $GamePath --output-root $outputRootPath

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
