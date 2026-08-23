[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$releaseId = Get-Date -Format 'yyyyMMdd-HHmmss'
$releaseRoot = Join-Path $projectRoot "dist\releases\$releaseId"
$workRoot = Join-Path $projectRoot "build\release-$releaseId"
$specPath = Join-Path $projectRoot 'KeyMimic.spec'

Write-Host "Building KeyMimic release $releaseId..."
& python -m PyInstaller --noconfirm --clean --distpath $releaseRoot --workpath $workRoot $specPath
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$executable = Join-Path $releaseRoot 'KeyMimic\KeyMimic.exe'
if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw "Build completed without the expected executable: $executable"
}

Write-Host 'Running packaged smoke test...'
& $executable --smoke-test
if ($LASTEXITCODE -ne 0) {
    throw "Packaged smoke test failed with exit code $LASTEXITCODE"
}

$relativeExecutable = "dist\releases\$releaseId\KeyMimic\KeyMimic.exe"
$pointerPath = Join-Path $projectRoot 'dist\current.txt'
$temporaryPointer = Join-Path $projectRoot 'dist\current.txt.tmp'
[System.IO.File]::WriteAllText($temporaryPointer, "$relativeExecutable`r`n")
Move-Item -LiteralPath $temporaryPointer -Destination $pointerPath -Force

$files = Get-ChildItem -LiteralPath (Join-Path $releaseRoot 'KeyMimic') -Recurse -File
$sizeMb = [math]::Round((($files | Measure-Object Length -Sum).Sum / 1MB), 1)
Write-Host "Build verified: $executable"
Write-Host "Package size: $sizeMb MB in $($files.Count) files"
