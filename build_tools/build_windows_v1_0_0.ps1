param([string]$ProjectRoot = "")
$ErrorActionPreference = "Stop"
function Step([string]$m) { Write-Host ""; Write-Host "=== $m ===" -ForegroundColor Cyan }
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) { $ProjectRoot=(Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path } else { $ProjectRoot=(Resolve-Path $ProjectRoot).Path }
$corePath=Join-Path $ProjectRoot "PaedDeadSpace-Core"
$uiPath=Join-Path $ProjectRoot "PaedDeadSpace-UI"
if (!(Test-Path (Join-Path $corePath "pyproject.toml"))) { throw "Expected sibling repository not found: $corePath" }
if (!(Test-Path (Join-Path $uiPath "app.py"))) { throw "Expected sibling repository not found: $uiPath" }
$buildRoot=Join-Path $ProjectRoot "WINDOWS_BUILD_v1_0_0"
$staging=Join-Path $buildRoot "staging"
$venv=Join-Path $buildRoot ".venv_build"
Step "Preparing clean workspace"
if (Test-Path $buildRoot) { Remove-Item $buildRoot -Recurse -Force }
New-Item -ItemType Directory -Path (Join-Path $staging "ui") -Force | Out-Null
Copy-Item (Join-Path $PSScriptRoot "launcher.py") $staging
Copy-Item (Join-Path $PSScriptRoot "PaedDeadSpace.spec") $staging
Copy-Item (Join-Path $uiPath "app.py") (Join-Path $staging "ui")
Copy-Item (Join-Path $uiPath "ui_logic.py") (Join-Path $staging "ui")
Step "Creating Python 3.13 build environment"
$pycmd = Get-Command py -ErrorAction SilentlyContinue
if ($pycmd) { & py -3.13 -m venv $venv } else { python -m venv $venv }
$python=Join-Path $venv "Scripts\python.exe"
$ver=& $python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($ver -notin @('3.11','3.12','3.13')) { throw "Windows v1.0.0 build requires Python 3.11-3.13; found $ver" }
& $python -m pip install --upgrade pip
& $python -m pip install "$corePath"
& $python -m pip install -r (Join-Path $PSScriptRoot "requirements-build.txt")
Step "Running Core tests"
Push-Location $corePath; try { & $python -m pytest -q tests; if ($LASTEXITCODE -ne 0) { throw 'Core tests failed' }; $env:PYTHONPATH="$corePath;$corePath\src"; & $python -m pytest -q validation_tests; if ($LASTEXITCODE -ne 0) { throw 'Validation tests failed' } } finally { Pop-Location; Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue }
Step "Running UI tests"
Push-Location $uiPath; try { $env:PYTHONPATH="$corePath\src;$uiPath"; & $python -m pytest -q tests; if ($LASTEXITCODE -ne 0) { throw 'UI tests failed' } } finally { Pop-Location; Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue }
& $python --version | Out-File (Join-Path $staging "PYTHON_VERSION.txt") -Encoding utf8
& $python -m pip freeze | Out-File (Join-Path $staging "BUILD_ENVIRONMENT.txt") -Encoding utf8
@"
PaedDeadSpace Windows v1.0.0
Build source date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz")
Scientific core: paeddeadspace 1.0.0
UI: PaedDeadSpace UI v1.0.0
Runtime: local Streamlit; usage statistics disabled by launcher.
"@ | Out-File (Join-Path $staging "RELEASE_INFO.txt") -Encoding utf8
Step "Building executable"
Push-Location $staging; try { & $python -m PyInstaller --clean --noconfirm ".\PaedDeadSpace.spec"; if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' } } finally { Pop-Location }
$dist=Join-Path $staging "dist\PaedDeadSpace"; $exe=Join-Path $dist "PaedDeadSpace.exe"
if (!(Test-Path $exe)) { throw "Expected executable not found: $exe" }
Copy-Item (Join-Path $PSScriptRoot "README_PORTABLE.txt") (Join-Path $dist "README.txt")
Copy-Item (Join-Path $ProjectRoot "PaedDeadSpace-Windows\LICENSE") (Join-Path $dist "LICENSE")
Copy-Item (Join-Path $staging "RELEASE_INFO.txt") $dist
Copy-Item (Join-Path $staging "PYTHON_VERSION.txt") $dist
Copy-Item (Join-Path $staging "BUILD_ENVIRONMENT.txt") $dist
$exeHash=(Get-FileHash $exe -Algorithm SHA256).Hash.ToLower()
"$exeHash  PaedDeadSpace.exe" | Out-File (Join-Path $dist "SHA256SUMS.txt") -Encoding ascii
$out=Join-Path $buildRoot "PaedDeadSpace-Windows-v1.0.0-x86_64-portable.zip"
Compress-Archive -Path (Join-Path $dist "*") -DestinationPath $out -Force
$zipHash=(Get-FileHash $out -Algorithm SHA256).Hash.ToLower()
Step "BUILD COMPLETE - manual golden-case validation still required"
Write-Host "Portable ZIP: $out" -ForegroundColor Green
Write-Host "ZIP SHA-256: $zipHash" -ForegroundColor Green
Write-Host "EXE SHA-256: $exeHash" -ForegroundColor Green
Write-Host "Run the Pearsall golden case before publishing the asset."
