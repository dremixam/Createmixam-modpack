#!/usr/bin/env python3
"""
Script pour générer un dossier serveur et des notes de version
Usage: python generate_server.py
"""

import json
import os
import subprocess
import sys
import requests
import hashlib
import re
import shutil
from pathlib import Path
from datetime import datetime

def run_git_command(command, silent_errors=False):
    """Exécute une commande git et retourne le résultat"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if not silent_errors:
            print(f"Erreur git: {e}")
        return None

def get_latest_tag():
    """Récupère le dernier tag git"""
    return run_git_command('git describe --tags --abbrev=0')

def get_commits_since_tag(tag):
    """Récupère les commits depuis le dernier tag"""
    if not tag:
        return run_git_command('git log --oneline')
    return run_git_command(f'git log {tag}..HEAD --oneline')

def load_modpack_from_commit(commit_hash=None):
    """Charge modrinth.index.json depuis un commit spécifique"""
    try:
        if commit_hash:
            content = run_git_command(f'git show {commit_hash}:modrinth.index.json')
        else:
            content = run_git_command('git show HEAD:modrinth.index.json')
        
        if content:
            return json.loads(content)
    except Exception as e:
        print(f"Erreur lors du chargement du modpack depuis git: {e}")
    
    return None

def load_current_modpack():
    """Charge le fichier modrinth.index.json actuel"""
    try:
        with open('modrinth.index.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erreur lors du chargement du modpack actuel: {e}")
        return None

def extract_project_id_from_url(url):
    """Extrait l'ID du projet depuis l'URL de téléchargement Modrinth"""
    pattern = r'cdn\.modrinth\.com/data/([^/]+)/versions'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

def get_project_info(project_id):
    """Récupère les infos du projet depuis l'API Modrinth"""
    url = f"https://api.modrinth.com/v2/project/{project_id}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

def is_server_compatible(file_entry):
    """Vérifie si un mod est compatible serveur"""
    env = file_entry.get('env', {})
    server_side = env.get('server', 'optional')
    return server_side in ['required', 'optional']

def download_file(url, destination):
    """Télécharge un fichier"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        with open(destination, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"Erreur lors du téléchargement de {url}: {e}")
        return False

def verify_file_hash(file_path, expected_sha1):
    """Vérifie le hash SHA1 d'un fichier"""
    try:
        sha1_hash = hashlib.sha1()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha1_hash.update(chunk)
        return sha1_hash.hexdigest() == expected_sha1
    except Exception:
        return False

def compare_modpacks(old_modpack, new_modpack):
    """Compare deux versions du modpack et retourne les changements"""
    changes = {
        'added': [],
        'removed': [],
        'updated': []
    }
    
    if not old_modpack or not new_modpack:
        return changes
    
    # Créer des dictionnaires par URL/projet pour faciliter la comparaison
    old_files = {}
    new_files = {}
    
    for file_entry in old_modpack.get('files', []):
        if file_entry.get('downloads'):
            url = file_entry['downloads'][0]
            project_id = extract_project_id_from_url(url)
            if project_id:
                old_files[project_id] = file_entry
    
    for file_entry in new_modpack.get('files', []):
        if file_entry.get('downloads'):
            url = file_entry['downloads'][0]
            project_id = extract_project_id_from_url(url)
            if project_id:
                new_files[project_id] = file_entry
    
    # Trouver les changements
    for project_id, file_entry in new_files.items():
        if project_id not in old_files:
            changes['added'].append((project_id, file_entry))
        elif old_files[project_id]['downloads'][0] != file_entry['downloads'][0]:
            changes['updated'].append((project_id, old_files[project_id], file_entry))
    
    for project_id, file_entry in old_files.items():
        if project_id not in new_files:
            changes['removed'].append((project_id, file_entry))
    
    return changes

def get_filename_from_path(path):
    """Extrait le nom de fichier depuis le path"""
    return os.path.basename(path)

def generate_patch_notes(changes, old_modpack, new_modpack, latest_tag, commits):
    """Génère les notes de version"""
    notes = []
    
    # En-tête
    current_version = run_git_command('git describe --tags --exact-match HEAD 2>/dev/null', silent_errors=True) or "Unreleased"
    notes.append(f"# Patch Notes - {current_version}")
    notes.append(f"*Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}*")
    notes.append("")
    
    # Informations sur les versions
    if old_modpack and new_modpack:
        old_mc = old_modpack.get('dependencies', {}).get('minecraft', 'N/A')
        new_mc = new_modpack.get('dependencies', {}).get('minecraft', 'N/A')
        old_loader = old_modpack.get('dependencies', {}).get('fabric-loader', 'N/A')
        new_loader = new_modpack.get('dependencies', {}).get('fabric-loader', 'N/A')
        
        notes.append("## Informations techniques")
        if old_mc != new_mc:
            notes.append(f"- **Minecraft:** {old_mc} → {new_mc}")
        else:
            notes.append(f"- **Minecraft:** {new_mc}")
            
        if old_loader != new_loader:
            notes.append(f"- **Fabric Loader:** {old_loader} → {new_loader}")
        else:
            notes.append(f"- **Fabric Loader:** {new_loader}")
        
        old_count = len(old_modpack.get('files', []))
        new_count = len(new_modpack.get('files', []))
        diff = new_count - old_count
        if diff > 0:
            notes.append(f"- **Nombre de mods:** {old_count} → {new_count} (+{diff})")
        elif diff < 0:
            notes.append(f"- **Nombre de mods:** {old_count} → {new_count} ({diff})")
        else:
            notes.append(f"- **Nombre de mods:** {new_count}")
        notes.append("")
    
    # Changements depuis le dernier tag
    if latest_tag:
        notes.append(f"## Changements depuis {latest_tag}")
    else:
        notes.append("## Changements")
    notes.append("")
    
    # Mods ajoutés
    if changes['added']:
        notes.append("### ➕ Mods ajoutés")
        for project_id, file_entry in changes['added']:
            project_info = get_project_info(project_id)
            if project_info:
                name = project_info['title']
                slug = project_info['slug']
                description = project_info.get('description', '')
                if description and len(description) > 100:
                    description = description[:100] + "..."
                notes.append(f"- **[{name}](https://modrinth.com/mod/{slug})** - {description}")
            else:
                filename = get_filename_from_path(file_entry.get('path', ''))
                notes.append(f"- {filename}")
        notes.append("")
    
    # Mods supprimés
    if changes['removed']:
        notes.append("### ➖ Mods supprimés")
        for project_id, file_entry in changes['removed']:
            project_info = get_project_info(project_id)
            if project_info:
                name = project_info['title']
                slug = project_info['slug']
                notes.append(f"- **[{name}](https://modrinth.com/mod/{slug})**")
            else:
                filename = get_filename_from_path(file_entry.get('path', ''))
                notes.append(f"- {filename}")
        notes.append("")
    
    # Mods mis à jour
    if changes['updated']:
        notes.append("### 🔄 Mods mis à jour")
        for project_id, old_file, new_file in changes['updated']:
            project_info = get_project_info(project_id)
            if project_info:
                name = project_info['title']
                slug = project_info['slug']
                old_filename = get_filename_from_path(old_file.get('path', ''))
                new_filename = get_filename_from_path(new_file.get('path', ''))
                
                # Essayer d'extraire les versions des noms de fichiers
                old_version = extract_version_from_filename(old_filename)
                new_version = extract_version_from_filename(new_filename)
                
                if old_version and new_version and old_version != new_version:
                    notes.append(f"- **[{name}](https://modrinth.com/mod/{slug})** {old_version} → {new_version}")
                else:
                    notes.append(f"- **[{name}](https://modrinth.com/mod/{slug})** (mise à jour)")
            else:
                old_filename = get_filename_from_path(old_file.get('path', ''))
                new_filename = get_filename_from_path(new_file.get('path', ''))
                notes.append(f"- {old_filename} → {new_filename}")
        notes.append("")
    
    # Commits
    if commits:
        notes.append("### 📝 Commits")
        for commit in commits.split('\n'):
            if commit.strip():
                notes.append(f"- {commit}")
        notes.append("")
    
    # Pied de page
    if not changes['added'] and not changes['removed'] and not changes['updated']:
        notes.append("*Aucun changement de mods depuis le dernier tag.*")
        notes.append("")
    
    notes.append("---")
    notes.append("*Notes générées automatiquement par generate_server.py*")
    
    return '\n'.join(notes)

def extract_version_from_filename(filename):
    """Essaie d'extraire le numéro de version depuis un nom de fichier"""
    # Patterns communs pour les versions
    patterns = [
        r'(\d+\.\d+\.\d+(?:\.\d+)?)',  # x.y.z ou x.y.z.w
        r'v(\d+\.\d+\.\d+)',           # vx.y.z
        r'-(\d+\.\d+\.\d+)',           # -x.y.z
        r'_(\d+\.\d+\.\d+)',           # _x.y.z
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            return match.group(1)
    
    return None

def generate_server_folder():
    """Génère le dossier serveur avec les mods compatibles"""
    print("🔍 Génération du dossier serveur...")
    
    # Créer/nettoyer le dossier _server
    server_dir = Path('_server')
    if server_dir.exists():
        print("🧹 Nettoyage du dossier _server existant...")
        shutil.rmtree(server_dir)
    
    server_dir.mkdir(exist_ok=True)
    mods_dir = server_dir / 'mods'
    mods_dir.mkdir(exist_ok=True)
    
    # Charger le modpack actuel
    current_modpack = load_current_modpack()
    if not current_modpack:
        print("❌ Impossible de charger le modpack actuel")
        return False
    
    # Obtenir le dernier tag
    latest_tag = get_latest_tag()
    print(f"📍 Dernier tag: {latest_tag or 'Aucun'}")
    
    # Charger l'ancien modpack si un tag existe
    old_modpack = None
    if latest_tag:
        old_modpack = load_modpack_from_commit(latest_tag)
    
    # Comparer les modpacks
    changes = compare_modpacks(old_modpack, current_modpack)
    
    # Obtenir les commits depuis le dernier tag
    commits = get_commits_since_tag(latest_tag)
    
    # Générer les notes de version
    print("📝 Génération des notes de version...")
    patch_notes = generate_patch_notes(changes, old_modpack, current_modpack, latest_tag, commits)
    
    # Sauvegarder les notes
    with open(server_dir / 'PATCHNOTES.md', 'w', encoding='utf-8') as f:
        f.write(patch_notes)
    
    print(f"✅ Notes de version sauvegardées dans {server_dir / 'PATCHNOTES.md'}")
    
    # Déterminer quels mods télécharger (seulement ceux qui ont changé)
    print("📦 Analyse des mods à télécharger...")
    
    server_mods = []
    skipped_mods = []
    changed_mods = []  # Mods ajoutés ou mis à jour
    
    # Classifier tous les mods
    for file_entry in current_modpack.get('files', []):
        if is_server_compatible(file_entry):
            server_mods.append(file_entry)
        else:
            skipped_mods.append(file_entry)
    
    # Identifier les mods qui ont changé
    changed_project_ids = set()
    
    # Ajouter les mods ajoutés
    for project_id, file_entry in changes['added']:
        if is_server_compatible(file_entry):
            changed_project_ids.add(project_id)
            changed_mods.append(file_entry)
    
    # Ajouter les mods mis à jour
    for project_id, old_file, new_file in changes['updated']:
        if is_server_compatible(new_file):
            changed_project_ids.add(project_id)
            changed_mods.append(new_file)
    
    print(f"📊 {len(server_mods)} mods compatibles serveur, {len(skipped_mods)} mods client uniquement")
    print(f"🔄 {len(changed_mods)} mods à télécharger (changés depuis le dernier tag)")
    
    if not changed_mods:
        print("✅ Aucun mod à télécharger, tous les mods serveur sont à jour!")
        success_count = len(server_mods)
        total_size = sum(file_entry.get('fileSize', 0) for file_entry in server_mods)
    else:
        success_count = 0
        total_size = 0
        
        for i, file_entry in enumerate(changed_mods, 1):
            if not file_entry.get('downloads'):
                continue
            
            url = file_entry['downloads'][0]
            filename = get_filename_from_path(file_entry.get('path', ''))
            destination = mods_dir / filename
            
            print(f"📥 [{i}/{len(changed_mods)}] {filename}")
            
            # Vérifier si le fichier existe déjà et a le bon hash
            if destination.exists():
                expected_sha1 = file_entry.get('hashes', {}).get('sha1')
                if expected_sha1 and verify_file_hash(destination, expected_sha1):
                    print(f"   ✅ Déjà présent et vérifié")
                    success_count += 1
                    total_size += file_entry.get('fileSize', 0)
                    continue
            
            # Télécharger le fichier
            if download_file(url, destination):
                # Vérifier le hash
                expected_sha1 = file_entry.get('hashes', {}).get('sha1')
                if expected_sha1 and verify_file_hash(destination, expected_sha1):
                    print(f"   ✅ Téléchargé et vérifié")
                    success_count += 1
                    total_size += file_entry.get('fileSize', 0)
                else:
                    print(f"   ⚠️  Téléchargé mais hash incorrect")
                    success_count += 1  # On compte quand même
                    total_size += file_entry.get('fileSize', 0)
            else:
                print(f"   ❌ Échec du téléchargement")
        
        # Compter la taille totale de tous les mods serveur (pas seulement les téléchargés)
        total_server_size = sum(file_entry.get('fileSize', 0) for file_entry in server_mods)
    
    print("=" * 60)
    print(f"✅ Dossier serveur généré dans {server_dir}")
    if changed_mods:
        print(f"� {success_count}/{len(changed_mods)} mods changés téléchargés")
        print(f"💾 Taille téléchargée: {total_size / 1024 / 1024:.1f} MB")
    else:
        print(f"📦 Aucun téléchargement nécessaire (tous les mods à jour)")
    
    print(f"🔢 {len(server_mods)} mods serveur au total")
    print(f"📝 Notes de version: {server_dir / 'PATCHNOTES.md'}")
    
    # Résumé des changements
    if changes['added'] or changes['removed'] or changes['updated']:
        print(f"🔄 Changements depuis {latest_tag or 'le début'}:")
        if changes['added']:
            print(f"   ➕ {len(changes['added'])} mods ajoutés")
        if changes['removed']:
            print(f"   ➖ {len(changes['removed'])} mods supprimés")
        if changes['updated']:
            print(f"   🔄 {len(changes['updated'])} mods mis à jour")
    else:
        print("📋 Aucun changement de mods détecté")
    
    return True

def main():
    # Vérifier qu'on est dans un dépôt git
    if not os.path.exists('.git'):
        print("❌ Ce script doit être exécuté dans un dépôt git")
        sys.exit(1)
    
    # Vérifier que modrinth.index.json existe
    if not os.path.exists('modrinth.index.json'):
        print("❌ modrinth.index.json non trouvé")
        sys.exit(1)
    
    print("🚀 Génération du serveur et des notes de version...")
    print("=" * 60)
    
    if generate_server_folder():
        print("=" * 60)
        print("🎉 Génération terminée avec succès!")
    else:
        print("❌ Erreur lors de la génération")
        sys.exit(1)

if __name__ == "__main__":
    main()
