#!/usr/bin/env python3
"""
Script pour publier une nouvelle version du modpack :
- Met à jour overrides/config/bcc.json
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

def update_bcc_version(version_str):
    """Met à jour le champ modpackVersion dans bcc.json."""
    if not BCC_PATH.exists():
        print(f"❌ Fichier introuvable : {BCC_PATH}")
        sys.exit(1)

    # Retire le 'v' initial si fourni (ex: 'v2.0.4' -> '2.0.4')
    clean_version = version_str.lstrip('v')

    try:
        with open(BCC_PATH, "r+", encoding="utf-8") as f:
            data = json.load(f)
            old_version = data.get("modpackVersion", "N/A")
            data["modpackVersion"] = clean_version
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
        print(f"✅ {BCC_PATH} mis à jour : '{old_version}' ➡️ '{clean_version}'")
        return clean_version
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour de bcc.json : {e}")
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

    print(f"\n🚀 Préparation de la release {tag_name} (bcc.json: {clean_version})...\n")

    # 3. Mise à jour de bcc.json
    update_bcc_version(clean_version)

    # 4. Commit et Tag Git
    print("📦 Création du commit et du tag Git...")
    run_cmd(f'git add "{BCC_PATH}"')
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