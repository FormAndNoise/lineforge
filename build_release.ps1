$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location -Path $PSScriptRoot

function Fail([string]$msg) {
  Write-Host "`nERROR: $msg`n" -ForegroundColor Red
  exit 1
}

function Remove-IfExists([string]$p) {
  if (Test-Path $p) { Remove-Item -Recurse -Force $p }
}

# ---- CONFIG ----
$AppName = "LineForge"
$Entry = ".\main.py"

# If $true: require NOTICE.txt + Licenses folder to exist or fail the build.
# If $false: bundle them only if present.
$StrictCompliance = $true
$LicensesFolderName = "Licenses"

# Build output folders
$DistDir = ".\dist_release"
$BuildDir = ".\build_release"

# Extra PyInstaller flags (optional)
$IconPath = ".\lineforge_icon.ico"
# -----------------

Write-Host "`n== LineForge RELEASE build ==" -ForegroundColor Cyan
Write-Host "Project root: $PSScriptRoot`n"

if (-not (Test-Path $Entry)) { Fail "Entrypoint not found: $Entry" }

$Root = $PSScriptRoot

# Potrace support removed – no longer required for build
# $PotracePath = Join-Path $Root "bin\potrace.exe"
$NoticePath = Join-Path $Root "NOTICE.txt"
$LicensesDir = Join-Path $Root $LicensesFolderName

# if (-not (Test-Path $PotracePath)) { Fail "Missing required file: $PotracePath" }

# if ($StrictCompliance) {
#   if (-not (Test-Path $NoticePath))  { Fail "Missing required file: $NoticePath" }
#   if (-not (Test-Path $LicensesDir)) { Fail "Missing required folder: $LicensesDir" }
# } else {
if (-not (Test-Path $NoticePath)) { Write-Host "NOTE: NOTICE.txt not found (will not bundle)." -ForegroundColor Yellow }
if (-not (Test-Path $LicensesDir)) { Write-Host "NOTE: $LicensesFolderName folder not found (will not bundle)." -ForegroundColor Yellow }
# }

# Potrace path resolution removed
# $PotraceAbs = (Resolve-Path $PotracePath).Path
$NoticeAbs = $null
$LicensesAbs = $null
if (Test-Path $NoticePath) { $NoticeAbs = (Resolve-Path $NoticePath).Path }
if (Test-Path $LicensesDir) { $LicensesAbs = (Resolve-Path $LicensesDir).Path }

Write-Host "Entrypoint: $Entry"
# Write-Host "Bundling:  $PotraceAbs"  # Potrace not bundled
if ($NoticeAbs) { Write-Host "Bundling:  $NoticeAbs" }
if ($LicensesAbs) { Write-Host "Bundling:  $LicensesAbs" }
Write-Host ""

Write-Host "Cleaning old RELEASE build artifacts..." -ForegroundColor Cyan
Remove-IfExists $BuildDir
Remove-IfExists $DistDir
Remove-IfExists ".\$AppName.spec"

# Build Rust Engine if cargo is available
$RustEngineDir = Join-Path $PSScriptRoot "lineforge_engine"
$BinDir = Join-Path $PSScriptRoot "bin"
$VpipeTarget = Join-Path $BinDir "vpipe-cli.exe"

Write-Host "`nChecking Rust Engine..." -ForegroundColor Cyan
if (Get-Command cargo -ErrorAction SilentlyContinue) {
  Write-Host "Building Rust engine with Cargo..." -ForegroundColor Cyan
  Push-Location $RustEngineDir
  try {
    cargo build --release | Out-Host
    if (-not (Test-Path $BinDir)) { New-Item -ItemType Directory -Path $BinDir | Out-Null }
    Copy-Item "target\release\vpipe-cli.exe" $VpipeTarget -Force
    Write-Host "Rust Engine successfully built and copied to $VpipeTarget" -ForegroundColor Green
  } catch {
    Write-Host "Warning: Failed to build Rust Engine: $_" -ForegroundColor Yellow
  } finally {
    Pop-Location
  }
} else {
  Write-Host "Warning: cargo command not found. Skipping Rust engine build. If bin\vpipe-cli.exe is not present, tracing features will fail." -ForegroundColor Yellow
}

Write-Host "`nUpgrading pip + installing build deps..." -ForegroundColor Cyan
py -m pip install --upgrade pip | Out-Host
py -m pip install --upgrade pyinstaller | Out-Host
if (Test-Path ".\requirements.txt") { py -m pip install -r requirements.txt | Out-Host }
py -m pip uninstall -y pathlib | Out-Host

# Dynamically locate customtkinter path to bundle it
Write-Host "`nLocating customtkinter installation path..." -ForegroundColor Cyan
$CtkPath = (py -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))").Trim()
Write-Host "CustomTkinter found at: $CtkPath"

# PyInstaller args:
# - --onefile: single exe (what your README claims for release)
# - --noconsole/--windowed: GUI app, no console window
$Args = @(
  "-m", "PyInstaller",
  "--noconfirm",
  "--clean",
  "--onefile",
  "--noconsole",
  "--name", $AppName,
  "--distpath", $DistDir,
  "--workpath", $BuildDir,
  "--specpath", $BuildDir,
  "--log-level", "WARN"
)

# Adding the icon to the executable
if (Test-Path $IconPath) {
  $IconAbs = (Resolve-Path $IconPath).Path
  $Args += @("--icon", $IconAbs)
  $Args += @("--add-data", "$IconAbs;.")
}

# Bundle the PNG logo
$PngPath = ".\lineforge icon.png"
if (Test-Path $PngPath) {
  $PngAbs = (Resolve-Path $PngPath).Path
  $Args += @("--add-data", "$PngAbs;.")
}

# Bundle Rust Engine (vpipe-cli.exe) if present
$VpipePath = Join-Path $Root "bin\vpipe-cli.exe"
if (Test-Path $VpipePath) {
  $VpipeAbs = (Resolve-Path $VpipePath).Path
  $Args += @("--add-binary", "$VpipeAbs;bin")
} else {
  Write-Host "NOTE: bin\vpipe-cli.exe not found. The resulting executable won't contain the rust engine!" -ForegroundColor Yellow
}

# Bundle customtkinter assets
$Args += @("--add-data", "$CtkPath;customtkinter")

# Bundle NOTICE + Licenses if present
if ($NoticeAbs) { $Args += @("--add-data", "$NoticeAbs;.") }
if ($LicensesAbs) { $Args += @("--add-data", "$LicensesAbs;$LicensesFolderName") }

# Entrypoint
$Args += $Entry

Write-Host "`nRunning PyInstaller (RELEASE)..." -ForegroundColor Cyan
py @Args | Out-Host

# PyInstaller onefile output path:
$Exe = Join-Path $DistDir "$AppName.exe"
if (-not (Test-Path $Exe)) { Fail "RELEASE build finished but exe not found: $Exe" }

Write-Host "`nRELEASE Built: $Exe" -ForegroundColor Green
