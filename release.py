#!/usr/bin/env python3
"""
Script pour publier une nouvelle version du modpack :
- Met à jour overrides/config/bcc.json
- Met à jour modrinth.index.json
- Crée le commit de version
- Pose le tag Git
- Pushe le tout sur GitHub (déclenche le workflow .mrpack)
- Optionnellement, lance generate_server.py pour le serveur
Usage: python release.py [v2.0.4]
"""

import json
import os
import subprocess
import sys
from pathlib import Path

BCC_PATH = Path("overrides/config/bcc.json")
MODRINTH_PATH = Path("modrinth.index.json")

def run_cmd(command, check=True):
    """Exécute une commande shell et gère les erreurs."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=check)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'exécution : {command}")
        print(f"   Détails : {e.stderr.strip()}")
        if check:
            sys.exit(1)
        return None

def update_json_file(file_path, key_name, version_str):
    """Met à jour une clé spécifique dans un fichier JSON."""
    if not file_path.exists():
        print(f"⚠️ Fichier introuvable (ignoré) : {file_path}")
        return False

    try:
        with open(file_path, "r+", encoding="utf-8") as f:
            data = json.load(f)
            old_version = data.get(key_name, "N/A")
            data[key_name] = version_str
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
        print(f"✅ {file_path} mis à jour : '{old_version}' ➡️ '{version_str}'")
        return True
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour de {file_path} : {e}")
        sys.exit(1)

def main():
    # 1. Vérification de l'état Git
    status = run_cmd("git status --porcelain")
    if status:
        print("⚠️ Attention : Vous avez des modifications non commitées dans le dépôt.")
        print(status)
        answer = input("\nVoulez-vous quand même continuer ? (o/N) : ")
        if answer.lower() not in ['o', 'oui', 'y', 'yes']:
            print("Annulé.")
            sys.exit(0)

    # 2. Récupération du numéro de version
    if len(sys.argv) > 1:
        version_input = sys.argv[1]
    else:
        version_input = input("📌 Entrez le numéro de la nouvelle version (ex: v2.0.4) : ").strip()

    if not version_input:
        print("❌ Aucune version spécifiée.")
        sys.exit(1)

    tag_name = version_input if version_input.startswith('v') else f"v{version_input}"
    clean_version = version_input.lstrip('v')

    print(f"\n🚀 Préparation de la release {tag_name} (version: {clean_version})...\n")

    # 3. Mise à jour des fichiers de configuration
    files_to_stage = []
    
    # bcc.json utilise la clé 'modpackVersion'
    if update_json_file(BCC_PATH, "modpackVersion", clean_version):
        files_to_stage.append(str(BCC_PATH))
        
    # modrinth.index.json utilise la clé 'versionId'
    if update_json_file(MODRINTH_PATH, "versionId", clean_version):
        files_to_stage.append(str(MODRINTH_PATH))

    if not files_to_stage:
        print("❌ Aucun fichier n'a pu être mis à jour.")
        sys.exit(1)

    # 4. Commit et Tag Git
    print("\n📦 Création du commit et du tag Git...")
    for file in files_to_stage:
        run_cmd(f'git add "{file}"')
        
    run_cmd(f'git commit -m "Release {tag_name}"')
    run_cmd(f'git tag -a {tag_name} -m "Release {tag_name}"')

    # 5. Push vers GitHub
    print("📤 Push vers GitHub (déclenche le build .mrpack)...")
    run_cmd("git push origin main")
    run_cmd(f"git push origin {tag_name}")

    print(f"\n🎉 Release {tag_name} publiée avec succès sur GitHub !")

    # 6. Proposition de générer la version serveur
    print("\n" + "="*50)
    answer = input("🚀 Souhaitez-vous exécuter generate_server.py maintenant ? (o/N) : ")
    if answer.lower() in ['o', 'oui', 'y', 'yes']:
        subprocess.run([sys.executable, "generate_server.py"])

if __name__ == "__main__":
    main()