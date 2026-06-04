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
$Entry   = ".\main.py"

# If $true: require NOTICE.txt + Licenses folder to exist or fail the build.
# If $false: bundle them only if present.
$StrictCompliance = $true
$LicensesFolderName = "Licenses"

# Build output folders
$DistDir = ".\dist_release"
$BuildDir = ".\build_release"

# Extra PyInstaller flags (optional)
# $IconPath = ".\assets\lineforge.ico"   # uncomment + set if you add an icon
# -----------------

Write-Host "`n== LineForge RELEASE build ==" -ForegroundColor Cyan
Write-Host "Project root: $PSScriptRoot`n"

if (-not (Test-Path $Entry)) { Fail "Entrypoint not found: $Entry" }

$Root = $PSScriptRoot

# Potrace support removed – no longer required for build
# $PotracePath = Join-Path $Root "bin\potrace.exe"
$NoticePath  = Join-Path $Root "NOTICE.txt"
$LicensesDir = Join-Path $Root $LicensesFolderName

# if (-not (Test-Path $PotracePath)) { Fail "Missing required file: $PotracePath" }

# if ($StrictCompliance) {
#   if (-not (Test-Path $NoticePath))  { Fail "Missing required file: $NoticePath" }
#   if (-not (Test-Path $LicensesDir)) { Fail "Missing required folder: $LicensesDir" }
# } else {
  if (-not (Test-Path $NoticePath))  { Write-Host "NOTE: NOTICE.txt not found (will not bundle)." -ForegroundColor Yellow }
  if (-not (Test-Path $LicensesDir)) { Write-Host "NOTE: $LicensesFolderName folder not found (will not bundle)." -ForegroundColor Yellow }
# }

# Potrace path resolution removed
# $PotraceAbs = (Resolve-Path $PotracePath).Path
$NoticeAbs  = $null
$LicensesAbs = $null
if (Test-Path $NoticePath)  { $NoticeAbs = (Resolve-Path $NoticePath).Path }
if (Test-Path $LicensesDir) { $LicensesAbs = (Resolve-Path $LicensesDir).Path }

Write-Host "Entrypoint: $Entry"
# Write-Host "Bundling:  $PotraceAbs"  # Potrace not bundled
if ($NoticeAbs)   { Write-Host "Bundling:  $NoticeAbs" }
if ($LicensesAbs) { Write-Host "Bundling:  $LicensesAbs" }
Write-Host ""

Write-Host "Cleaning old RELEASE build artifacts..." -ForegroundColor Cyan
Remove-IfExists $BuildDir
Remove-IfExists $DistDir
Remove-IfExists ".\$AppName.spec"

Write-Host "`nUpgrading pip + installing build deps..." -ForegroundColor Cyan
py -m pip install --upgrade pip | Out-Host
py -m pip install --upgrade pyinstaller | Out-Host
if (Test-Path ".\requirements.txt") { py -m pip install -r requirements.txt | Out-Host }

# Dynamically locate customtkinter path to bundle it
Write-Host "`nLocating customtkinter installation path..." -ForegroundColor Cyan
$CtkPath = (py -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))").Trim()
Write-Host "CustomTkinter found at: $CtkPath"

# PyInstaller args:
# - --onefile: single exe (what your README claims for release)
# - --noconsole/--windowed: GUI app, no console window
$Args = @(
  "-m","PyInstaller",
  "--noconfirm",
  "--clean",
  "--onefile",
  "--noconsole",
  "--name",$AppName,
  "--distpath",$DistDir,
  "--workpath",$BuildDir,
  "--specpath",$BuildDir,
  "--log-level","WARN"
)

# If you add an icon later, uncomment these lines:
# if (Test-Path $IconPath) {
#   $IconAbs = (Resolve-Path $IconPath).Path
#   $Args += @("--icon", $IconAbs)
# }

# Potrace bundling removed – no longer needed
# $Args += @("--add-binary", "$PotraceAbs;bin")

# Bundle customtkinter assets
$Args += @("--add-data", "$CtkPath;customtkinter")

# Bundle NOTICE + Licenses if present
if ($NoticeAbs)   { $Args += @("--add-data", "$NoticeAbs;.") }
if ($LicensesAbs) { $Args += @("--add-data", "$LicensesAbs;$LicensesFolderName") }

# Entrypoint
$Args += $Entry

Write-Host "`nRunning PyInstaller (RELEASE)..." -ForegroundColor Cyan
py @Args | Out-Host

# PyInstaller onefile output path:
$Exe = Join-Path $DistDir "$AppName.exe"
if (-not (Test-Path $Exe)) { Fail "RELEASE build finished but exe not found: $Exe" }

Write-Host "`nRELEASE Built: $Exe" -ForegroundColor Green
