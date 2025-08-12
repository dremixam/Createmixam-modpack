#!/bin/bash

# Script de build local pour le modpack Createmixam
# Usage: ./build-local.sh [version]

set -e

# Configuration
MODPACK_NAME="Createmixam-modpack"
VERSION="${1:-dev-$(date +%Y%m%d-%H%M%S)}"
TEMP_DIR="mrpack-temp"
OUTPUT_FILE="${MODPACK_NAME}-${VERSION}.mrpack"

echo "🚀 Building $MODPACK_NAME v$VERSION"

# Vérification des fichiers requis
echo "🔍 Checking required files..."
if [ ! -f "modrinth.index.json" ]; then
    echo "❌ modrinth.index.json not found!"
    exit 1
fi

if [ ! -d "overrides" ]; then
    echo "❌ overrides directory not found!"
    exit 1
fi

echo "✅ Required files found"

# Validation JSON
echo "🔍 Validating JSON..."
if command -v jq >/dev/null 2>&1; then
    if ! jq empty modrinth.index.json 2>/dev/null; then
        echo "❌ Invalid JSON syntax in modrinth.index.json"
        exit 1
    fi
    echo "✅ JSON is valid"
    
    # Affichage des stats
    MINECRAFT_VERSION=$(jq -r '.dependencies.minecraft' modrinth.index.json)
    FABRIC_VERSION=$(jq -r '.dependencies."fabric-loader"' modrinth.index.json)
    MOD_COUNT=$(jq '.files | length' modrinth.index.json)
    
    echo "📊 Modpack info:"
    echo "  - Minecraft: $MINECRAFT_VERSION"
    echo "  - Fabric Loader: $FABRIC_VERSION"
    echo "  - Mods: $MOD_COUNT"
else
    echo "⚠️  jq not found, skipping JSON validation"
fi

# Nettoyage des fichiers précédents
echo "🧹 Cleaning up..."
rm -rf "$TEMP_DIR"
rm -f *.mrpack

# Création du répertoire temporaire
echo "📦 Creating mrpack..."
mkdir -p "$TEMP_DIR"

# Copie des fichiers
cp modrinth.index.json "$TEMP_DIR/"
cp -r overrides "$TEMP_DIR/"

# Création de l'archive
cd "$TEMP_DIR"
zip -r -0 -X "../$OUTPUT_FILE" * >/dev/null
cd ..

# Nettoyage
rm -rf "$TEMP_DIR"

# Vérification du résultat
if [ -f "$OUTPUT_FILE" ]; then
    FILE_SIZE=$(ls -lh "$OUTPUT_FILE" | awk '{print $5}')
    echo "✅ $OUTPUT_FILE created successfully ($FILE_SIZE)"
    
    # Affichage du contenu
    echo ""
    echo "📋 Archive contents:"
    unzip -l "$OUTPUT_FILE" | tail -n +4 | head -n -2 | awk '{print "  " $4}'
    
    echo ""
    echo "🎉 Build completed! You can now import $OUTPUT_FILE into your Minecraft launcher."
else
    echo "❌ Failed to create mrpack file"
    exit 1
fi
