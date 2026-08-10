#!/usr/bin/env python3
"""
Script pour générer un dossier serveur, des notes de version et déployer via SFTP
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
import paramiko
from dotenv import load_dotenv

load_dotenv()

SFTP_HOST = os.getenv("SFTP_HOST", "")
SFTP_PORT = int(os.getenv("SFTP_PORT", "22"))
SFTP_USER = os.getenv("SFTP_USER", "")
SFTP_PASSWORD = os.getenv("SFTP_PASSWORD", "")
SFTP_MODS_DIR = os.getenv("SFTP_MODS_DIR", "/home/container/mods")

def run_git_command(command, silent_errors=False):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if not silent_errors:
            print(f"Erreur git: {e}")
        return None

def get_current_tag():
    return run_git_command('git describe --tags --exact-match HEAD', silent_errors=True)

def get_previous_tag():
    current_tag = get_current_tag()
    if current_tag:
        return run_git_command('git describe --tags --abbrev=0 HEAD~1', silent_errors=True)
    return run_git_command('git describe --tags --abbrev=0', silent_errors=True)

def debug_git_state():
    print("\n" + "="*50)
    print("🔍 DIAGNOSTIC GIT DETAILLE")
    print("="*50)
    
    current_commit = run_git_command('git rev-parse HEAD')
    current_tag = get_current_tag()
    previous_tag = get_previous_tag()
    
    print(f"📌 Commit actuel (HEAD)     : {current_commit}")
    print(f"📌 Tag sur HEAD (actuel)     : {current_tag or 'Aucun (Pas de tag sur ce commit exact)'}")
    print(f"📌 Tag trouvé via HEAD~1     : {run_git_command('git describe --tags --abbrev=0 HEAD~1', silent_errors=True)}")
    print(f"📌 Tag retourné comme 'prev' : {previous_tag}")
    
    print("\n📋 5 derniers tags créés dans l'historique :")
    tags_list = run_git_command('git tag --sort=-creatordate')
    if tags_list:
        for t in tags_list.split('\n')[:5]:
            t_commit = run_git_command(f'git rev-parse {t}')
            print(f"  - {t} (commit: {t_commit})")
            
    print("\n📜 5 derniers commits (avec leurs tags associés) :")
    commits_log = run_git_command('git log --oneline --decorate -n 5')
    if commits_log:
        for line in commits_log.split('\n'):
            print(f"  {line}")
            
    print("="*50 + "\n")

def get_commits_since_tag(tag):
    if not tag:
        return run_git_command('git log --oneline')
    return run_git_command(f'git log {tag}..HEAD --oneline')

def load_modpack_from_commit(commit_hash=None):
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
    try:
        with open('modrinth.index.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erreur lors du chargement du modpack actuel: {e}")
        return None

def extract_project_id_from_url(url):
    pattern = r'cdn\.modrinth\.com/data/([^/]+)/versions'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

def get_project_info(project_id):
    url = f"https://api.modrinth.com/v2/project/{project_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

def is_server_compatible(file_entry):
    env = file_entry.get('env', {})
    server_side = env.get('server', 'optional')
    return server_side in ['required', 'optional']

def download_file(url, destination):
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
    try:
        sha1_hash = hashlib.sha1()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha1_hash.update(chunk)
        return sha1_hash.hexdigest() == expected_sha1
    except Exception:
        return False

def compare_modpacks(old_modpack, new_modpack):
    changes = {'added': [], 'removed': [], 'updated': []}
    if not old_modpack or not new_modpack:
        return changes
    
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
    return os.path.basename(path)

def extract_version_from_filename(filename):
    patterns = [
        r'(\d+\.\d+\.\d+(?:\.\d+)?)',
        r'v(\d+\.\d+\.\d+)',
        r'-(\d+\.\d+\.\d+)',
        r'_(\d+\.\d+\.\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            return match.group(1)
    return None

def normalize_mod_name(filename):
    name = filename.replace('.disabled', '').replace('.jar', '').lower()
    name = re.sub(r'[-_](fabric|forge|neoforge|quilt|mc\d+[\d\.]*|1\.\d+[\d\.]*)', '', name)
    match = re.match(r'^([a-z0-9]+(?:[-_][a-z]+)*)', name)
    if match:
        clean = match.group(1).strip('-_')
        clean = re.sub(r'[-_](fabric|forge|neoforge|quilt)$', '', clean)
        return clean
    return name

def generate_patch_notes(changes, old_modpack, new_modpack, current_tag, previous_tag, commits):
    notes = []
    version_display = current_tag or "Unreleased"
    notes.append(f"# Patch Notes - {version_display}")
    notes.append(f"*Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}*")
    notes.append("")
    
    if old_modpack and new_modpack:
        old_mc = old_modpack.get('dependencies', {}).get('minecraft', 'N/A')
        new_mc = new_modpack.get('dependencies', {}).get('minecraft', 'N/A')
        old_loader = old_modpack.get('dependencies', {}).get('fabric-loader', 'N/A')
        new_loader = new_modpack.get('dependencies', {}).get('fabric-loader', 'N/A')
        
        notes.append("## Informations techniques")
        notes.append(f"- **Minecraft:** {new_mc if old_mc == new_mc else f'{old_mc} → {new_mc}'}")
        notes.append(f"- **Fabric Loader:** {new_loader if old_loader == new_loader else f'{old_loader} → {new_loader}'}")
        
        old_count = len(old_modpack.get('files', []))
        new_count = len(new_modpack.get('files', []))
        diff = new_count - old_count
        notes.append(f"- **Nombre de mods:** {old_count} → {new_count} ({'+' if diff > 0 else ''}{diff})")
        notes.append("")
    
    notes.append(f"## Changements{' depuis ' + previous_tag if previous_tag else ''}\n")
    
    if changes['added']:
        notes.append("### ➕ Mods ajoutés")
        for project_id, file_entry in changes['added']:
            project_info = get_project_info(project_id)
            if project_info:
                name, slug = project_info['title'], project_info['slug']
                desc = (project_info.get('description', '')[:100] + "...") if len(project_info.get('description', '')) > 100 else project_info.get('description', '')
                notes.append(f"- **[{name}](https://modrinth.com/mod/{slug})** - {desc}")
            else:
                notes.append(f"- {get_filename_from_path(file_entry.get('path', ''))}")
        notes.append("")
    
    if changes['removed']:
        notes.append("### ➖ Mods supprimés")
        for project_id, file_entry in changes['removed']:
            project_info = get_project_info(project_id)
            if project_info:
                notes.append(f"- **[{project_info['title']}](https://modrinth.com/mod/{project_info['slug']})**")
            else:
                notes.append(f"- {get_filename_from_path(file_entry.get('path', ''))}")
        notes.append("")
    
    if changes['updated']:
        notes.append("### 🔄 Mods mis à jour")
        for project_id, old_file, new_file in changes['updated']:
            project_info = get_project_info(project_id)
            old_fn = get_filename_from_path(old_file.get('path', ''))
            new_fn = get_filename_from_path(new_file.get('path', ''))
            old_v, new_v = extract_version_from_filename(old_fn), extract_version_from_filename(new_fn)
            
            if project_info:
                notes.append(f"- **[{project_info['title']}](https://modrinth.com/mod/{project_info['slug']})** {f'{old_v} → {new_v}' if old_v and new_v else '(mise à jour)'}")
            else:
                notes.append(f"- {old_fn} → {new_fn}")
        notes.append("")
    
    if commits:
        notes.append("### 📝 Commits")
        for commit in commits.split('\n'):
            if commit.strip():
                notes.append(f"- {commit}")
        notes.append("")
    
    notes.append("---\n*Notes générées automatiquement par generate_server.py*")
    return '\n'.join(notes)

def get_mod_slug_or_base(project_id, filename):
    if project_id:
        info = get_project_info(project_id)
        if info and 'slug' in info:
            return info['slug'].replace('-', '').replace('_', '').lower()
    
    clean = filename.replace('.disabled', '').replace('.jar', '').lower()
    return clean.split('-')[0].split('_')[0]

def deploy_to_sftp(changes, mods_dir):
    import getpass
    print("\n🌐 Connexion au serveur SFTP...")
    
    host = SFTP_HOST or input("Hôte SFTP: ")
    user = SFTP_USER or input("Utilisateur SFTP: ")
    port = SFTP_PORT
    password = SFTP_PASSWORD or getpass.getpass("Mot de passe SFTP: ")
    remote_mods_dir = SFTP_MODS_DIR or input("Dossier mods distant: ")

    try:
        transport = paramiko.Transport((host, port))
        transport.connect(username=user, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        print("✅ Connecté au serveur avec succès !")
    except Exception as e:
        print(f"❌ Échec de la connexion SFTP: {e}")
        return

    # Synchronisation unique du fichier bcc.json
    local_bcc = Path("overrides/config/bcc.json")
    if not local_bcc.exists():
        local_bcc = Path("config/bcc.json")

    if local_bcc.exists():
        remote_base = os.path.dirname(remote_mods_dir.rstrip('/'))
        remote_bcc_path = f"{remote_base}/config/bcc.json"
        
        try:
            sftp.mkdir(f"{remote_base}/config")
        except IOError:
            pass
        
        print(f"📄 Upload de {local_bcc} vers {remote_bcc_path}...")
        try:
            sftp.put(str(local_bcc), remote_bcc_path)
            print("✅ Fichier bcc.json mis à jour sur le serveur !")
        except Exception as e:
            print(f"⚠️ Erreur lors de l'upload de bcc.json: {e}")
    else:
        print("⚠️ Aucun fichier bcc.json trouvé localement (overrides/config/bcc.json ou config/bcc.json).")

    try:
        remote_files = sftp.listdir(remote_mods_dir)
    except Exception as e:
        print(f"❌ Impossible de lire le dossier distant {remote_mods_dir}: {e}")
        sftp.close()
        transport.close()
        return

    warnings = []

    for project_id, file_entry in changes['removed']:
        filename = get_filename_from_path(file_entry.get('path', ''))
        slug = get_mod_slug_or_base(project_id, filename)
        
        found = False
        for r_file in remote_files:
            clean_r = r_file.replace('-', '').replace('_', '').lower()
            if slug in clean_r:
                print(f"🗑️ [SFTP] Suppression du mod retiré : {r_file}")
                sftp.remove(f"{remote_mods_dir}/{r_file}")
                found = True
        
        if not found:
            warnings.append(f"Mod retiré du modpack mais introuvable sur le SFTP : '{filename}'")

    remote_files = sftp.listdir(remote_mods_dir)
    updated_project_ids = {project_id: old_file for project_id, old_file, new_file in changes['updated']}

    local_mods = list(mods_dir.glob('*.jar'))
    print(f"📤 Synchronisation de {len(local_mods)} mods vers le serveur...")

    current_pack = load_current_modpack() or {}
    file_to_project = {}
    for f in current_pack.get('files', []):
        if f.get('downloads'):
            pid = extract_project_id_from_url(f['downloads'][0])
            fn = get_filename_from_path(f.get('path', ''))
            if pid and fn:
                file_to_project[fn] = pid

    for local_mod in local_mods:
        project_id = file_to_project.get(local_mod.name)
        slug = get_mod_slug_or_base(project_id, local_mod.name)
        
        is_disabled = False
        matching_remote_files = []

        for r_file in remote_files:
            clean_r = r_file.replace('-', '').replace('_', '').lower()
            if slug in clean_r:
                matching_remote_files.append(r_file)
                if r_file.endswith('.disabled'):
                    is_disabled = True

        if project_id in updated_project_ids and not matching_remote_files:
            old_fn = get_filename_from_path(updated_project_ids[project_id].get('path', ''))
            warnings.append(f"Mod mis à jour ({local_mod.name}) mais l'ancienne version ('{old_fn}') est introuvable sur le serveur SFTP.")

        for r_file in matching_remote_files:
            print(f"🧹 Suppression de l'ancienne version distante : {r_file}")
            sftp.remove(f"{remote_mods_dir}/{r_file}")

        target_name = f"{local_mod.name}.disabled" if is_disabled else local_mod.name
        remote_path = f"{remote_mods_dir}/{target_name}"

        status_str = "🔒 (.disabled)" if is_disabled else "⚡ (actif)"
        print(f"  ➡️ Upload: {target_name} {status_str}")
        sftp.put(str(local_mod), remote_path)

    sftp.close()
    transport.close()
    print("🎉 Synchronisation SFTP terminée avec succès !")

    if warnings:
        print("\n" + "⚠️ " * 15)
        print("ALERTES DE SYNCHRONISATION (Action requise) :")
        for warn in warnings:
            print(f"  - {warn}")
        print("⚠️ " * 15)

def generate_server_folder():
    print("🔍 Génération du dossier serveur...")
    
    debug_git_state()

    server_dir = Path('_server')
    if server_dir.exists():
        shutil.rmtree(server_dir)
    
    server_dir.mkdir(exist_ok=True)
    mods_dir = server_dir / 'mods'
    mods_dir.mkdir(exist_ok=True)
    
    current_modpack = load_current_modpack()
    if not current_modpack:
        return False
    
    current_tag = get_current_tag()
    previous_tag = get_previous_tag()
    
    ref_to_load = previous_tag or "HEAD~1"
    print(f"🔎 Chargement de l'ancien modpack depuis le tag/commit : '{ref_to_load}'")
    old_modpack = load_modpack_from_commit(ref_to_load)
    
    if old_modpack is None and previous_tag:
        print(f"⚠️ ATTENTION : Impossible de lire 'modrinth.index.json' au commit/tag '{previous_tag}' !")
    
    changes = compare_modpacks(old_modpack, current_modpack)
    print(f"📊 Changements détectés : {len(changes['added'])} ajoutés, {len(changes['removed'])} supprimés, {len(changes['updated'])} mis à jour")

    commits = get_commits_since_tag(previous_tag)
    
    patch_notes = generate_patch_notes(
        changes, 
        old_modpack, 
        current_modpack, 
        current_tag, 
        previous_tag, 
        commits
    )
    
    with open(server_dir / 'PATCHNOTES.md', 'w', encoding='utf-8') as f:
        f.write(patch_notes)
    
    changed_mods = []
    for project_id, file_entry in changes['added']:
        if is_server_compatible(file_entry):
            changed_mods.append(file_entry)
    for project_id, old_file, new_file in changes['updated']:
        if is_server_compatible(new_file):
            changed_mods.append(new_file)
            
    if not changed_mods:
        print("✅ Tous les mods serveur sont déjà à jour !")
    else:
        for i, file_entry in enumerate(changed_mods, 1):
            if not file_entry.get('downloads'): 
                continue
            filename = get_filename_from_path(file_entry.get('path', ''))
            destination = mods_dir / filename
            print(f"📥 [{i}/{len(changed_mods)}] {filename}")
            download_file(file_entry['downloads'][0], destination)

    if os.path.exists("config"):
        print("📁 Copie du dossier config...")
        shutil.copytree("config", server_dir / "config", dirs_exist_ok=True)

    answer = input("\n🚀 Veux-tu déployer les changements directement sur le serveur via SFTP ? (o/N) : ")
    if answer.lower() in ['o', 'oui', 'y', 'yes']:
        deploy_to_sftp(changes, mods_dir)

    return True

def main():
    if not os.path.exists('.git') or not os.path.exists('modrinth.index.json'):
        print("❌ Dépôt Git ou modrinth.index.json introuvable.")
        sys.exit(1)
    
    generate_server_folder()

if __name__ == "__main__":
    main()