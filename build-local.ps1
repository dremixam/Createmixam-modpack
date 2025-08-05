# Script de build local pour le modpack Createmixam (PowerShell)
# Usage: .\build-local.ps1 [version]

param(
    [string]$Version = "dev-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
)

# Configuration
$ModpackName = "Createmixam-modpack"
$TempDir = "mrpack-temp"
$OutputFile = "$ModpackName-$Version.mrpack"

Write-Host "🚀 Building $ModpackName v$Version" -ForegroundColor Green

# Vérification des fichiers requis
Write-Host "🔍 Checking required files..." -ForegroundColor Cyan
if (-not (Test-Path "modrinth.index.json")) {
    Write-Host "❌ modrinth.index.json not found!" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "overrides" -PathType Container)) {
    Write-Host "❌ overrides directory not found!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Required files found" -ForegroundColor Green

# Validation JSON (si jq est disponible)
Write-Host "🔍 Validating JSON..." -ForegroundColor Cyan
try {
    $jsonContent = Get-Content "modrinth.index.json" | ConvertFrom-Json
    Write-Host "✅ JSON is valid" -ForegroundColor Green
    
    # Affichage des stats
    $minecraftVersion = $jsonContent.dependencies.minecraft
    $fabricVersion = $jsonContent.dependencies.'fabric-loader'
    $modCount = $jsonContent.files.Count
    
    Write-Host "📊 Modpack info:" -ForegroundColor Yellow
    Write-Host "  - Minecraft: $minecraftVersion"
    Write-Host "  - Fabric Loader: $fabricVersion"
    Write-Host "  - Mods: $modCount"
}
catch {
    Write-Host "❌ Invalid JSON syntax in modrinth.index.json" -ForegroundColor Red
    exit 1
}

# Nettoyage des fichiers précédents
Write-Host "🧹 Cleaning up..." -ForegroundColor Cyan
if (Test-Path $TempDir) {
    Remove-Item $TempDir -Recurse -Force
}
Get-ChildItem "*.mrpack" | Remove-Item -Force -ErrorAction SilentlyContinue

# Création du répertoire temporaire
Write-Host "📦 Creating mrpack..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

# Copie des fichiers
Copy-Item "modrinth.index.json" $TempDir
Copy-Item "overrides" $TempDir -Recurse

# Création de l'archive
try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory((Get-Item $TempDir).FullName, (Join-Path $PWD $OutputFile))
}
catch {
    Write-Host "❌ Failed to create ZIP archive: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Nettoyage
Remove-Item $TempDir -Recurse -Force

# Vérification du résultat
if (Test-Path $OutputFile) {
    $fileSize = [math]::Round((Get-Item $OutputFile).Length / 1MB, 2)
    Write-Host "✅ $OutputFile created successfully ($fileSize MB)" -ForegroundColor Green
    
    # Affichage du contenu
    Write-Host ""
    Write-Host "📋 Archive contents:" -ForegroundColor Yellow
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead((Get-Item $OutputFile).FullName)
    $zip.Entries | ForEach-Object { Write-Host "  $($_.FullName)" }
    $zip.Dispose()
    
    Write-Host ""
    Write-Host "🎉 Build completed! You can now import $OutputFile into your Minecraft launcher." -ForegroundColor Green
}
else {
    Write-Host "❌ Failed to create mrpack file" -ForegroundColor Red
    exit 1
}
