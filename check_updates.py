#!/usr/bin/env python3
"""
Script pour vérifier les mises à jour des mods dans modrinth.index.json
Usage: python check_updates.py [--auto-update]
"""

import json
import sys
import requests
import hashlib
import re
from urllib.parse import urlparse
from datetime import datetime

def load_modpack_index():
    """Charge le fichier modrinth.index.json"""
    try:
        with open('modrinth.index.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Fichier modrinth.index.json non trouvé")
        return None
    except json.JSONDecodeError:
        print("Erreur de format JSON dans modrinth.index.json")
        return None

def save_modpack_index(data):
    """Sauvegarde le fichier modrinth.index.json"""
    try:
        with open('modrinth.index.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Erreur lors de la sauvegarde: {e}")
        return False

def extract_project_id_from_url(url):
    """Extrait l'ID du projet depuis l'URL de téléchargement Modrinth"""
    # URL format: https://cdn.modrinth.com/data/PROJECT_ID/versions/VERSION_ID/filename.jar
    pattern = r'cdn\.modrinth\.com/data/([^/]+)/versions'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

def get_project_versions(project_id, minecraft_version, loader):
    """Récupère toutes les versions compatibles d'un projet"""
    url = f"https://api.modrinth.com/v2/project/{project_id}/version"
    params = {
        'game_versions': f'["{minecraft_version}"]',
        'loaders': f'["{loader}"]'
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la récupération des versions pour {project_id}: {e}")
        return []

def get_project_info(project_id):
    """Récupère les infos du projet depuis l'API Modrinth"""
    url = f"https://api.modrinth.com/v2/project/{project_id}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la récupération du projet {project_id}: {e}")
        return None

def get_version_from_url(versions, current_url):
    """Trouve la version actuelle basée sur l'URL"""
    for version in versions:
        for file in version['files']:
            if file['url'] == current_url:
                return version
    return None

def download_file_hash(url):
    """Télécharge un fichier et calcule ses hashes"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        sha1_hash = hashlib.sha1()
        sha512_hash = hashlib.sha512()
        file_size = 0
        
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                sha1_hash.update(chunk)
                sha512_hash.update(chunk)
                file_size += len(chunk)
        
        return {
            'sha1': sha1_hash.hexdigest(),
            'sha512': sha512_hash.hexdigest(),
            'size': file_size
        }
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors du téléchargement: {e}")
        return None

def compare_versions(current_version, latest_version):
    """Compare deux versions pour voir si une mise à jour est disponible"""
    if not current_version or not latest_version:
        return False
    
    current_date = datetime.fromisoformat(current_version['date_published'].replace('Z', '+00:00'))
    latest_date = datetime.fromisoformat(latest_version['date_published'].replace('Z', '+00:00'))
    
    return latest_date > current_date

def update_file_entry(file_entry, new_version, project_info):
    """Met à jour une entrée de fichier avec la nouvelle version"""
    primary_file = new_version['files'][0]
    
    print(f"Téléchargement et calcul des hashes pour {primary_file['filename']}...")
    hash_data = download_file_hash(primary_file['url'])
    
    if not hash_data:
        return False
    
    # Préserver l'environnement existant mais s'assurer que client est toujours 'required'
    if 'env' not in file_entry:
        file_entry['env'] = {}
    
    # Toujours marquer comme required côté client
    file_entry['env']['client'] = 'required'
    
    # Mettre à jour l'entrée
    file_entry['downloads'] = [primary_file['url']]
    file_entry['fileSize'] = hash_data['size']
    file_entry['hashes']['sha1'] = hash_data['sha1']
    file_entry['hashes']['sha512'] = hash_data['sha512']
    file_entry['path'] = f"mods/{primary_file['filename']}"
    
    return True

def check_updates(auto_update=False):
    """Vérifie les mises à jour disponibles"""
    modpack_data = load_modpack_index()
    if not modpack_data:
        return
    
    minecraft_version = modpack_data['dependencies']['minecraft']
    loader = 'fabric'
    
    print(f"🔍 Vérification des mises à jour pour Minecraft {minecraft_version} avec {loader}")
    print("=" * 60)
    
    updates_available = []
    updates_applied = []
    
    for i, file_entry in enumerate(modpack_data['files']):
        if not file_entry.get('downloads'):
            continue
            
        current_url = file_entry['downloads'][0]
        project_id = extract_project_id_from_url(current_url)
        
        if not project_id:
            continue
        
        # Récupérer les infos du projet
        project_info = get_project_info(project_id)
        if not project_info:
            continue
        
        project_name = project_info['title']
        print(f"📦 Vérification de {project_name}...")
        
        # Récupérer toutes les versions compatibles
        versions = get_project_versions(project_id, minecraft_version, loader)
        if not versions:
            print(f"   ⚠️  Aucune version compatible trouvée")
            continue
        
        # Trouver la version actuelle
        current_version = get_version_from_url(versions, current_url)
        latest_version = versions[0]  # La première est la plus récente
        
        if not current_version:
            print(f"   ❓ Version actuelle non trouvée dans les versions compatibles")
            continue
        
        # Comparer les versions
        if compare_versions(current_version, latest_version):
            update_info = {
                'index': i,
                'project_name': project_name,
                'current_version': current_version['version_number'],
                'latest_version': latest_version['version_number'],
                'current_date': current_version['date_published'][:10],
                'latest_date': latest_version['date_published'][:10],
                'file_entry': file_entry,
                'new_version': latest_version,
                'project_info': project_info
            }
            updates_available.append(update_info)
            
            print(f"   🆕 Mise à jour disponible!")
            print(f"      Actuelle: {current_version['version_number']} ({current_version['date_published'][:10]})")
            print(f"      Nouvelle: {latest_version['version_number']} ({latest_version['date_published'][:10]})")
            
            if auto_update:
                print(f"   🔄 Mise à jour automatique en cours...")
                if update_file_entry(file_entry, latest_version, project_info):
                    updates_applied.append(update_info)
                    print(f"   ✅ Mise à jour appliquée!")
                else:
                    print(f"   ❌ Échec de la mise à jour")
        else:
            print(f"   ✅ À jour ({current_version['version_number']})")
    
    print("=" * 60)
    
    if updates_available:
        print(f"📊 Résumé: {len(updates_available)} mise(s) à jour disponible(s)")
        
        if auto_update:
            if updates_applied:
                # Trier les fichiers par path (ordre ASCII : majuscules avant minuscules)
                modpack_data['files'].sort(key=lambda x: x.get('path', ''))
                
                if save_modpack_index(modpack_data):
                    print(f"💾 {len(updates_applied)} mise(s) à jour appliquée(s) et sauvegardée(s)")
                else:
                    print("❌ Erreur lors de la sauvegarde")
            else:
                print("❌ Aucune mise à jour n'a pu être appliquée")
        else:
            print("\n🔧 Pour appliquer les mises à jour, relancez avec --auto-update")
            print("   Ou mettez à jour manuellement:")
            for update in updates_available:
                print(f"   - {update['project_name']}: {update['current_version']} → {update['latest_version']}")
    else:
        print("✅ Tous les mods sont à jour!")

def interactive_update():
    """Mode interactif pour choisir quelles mises à jour appliquer"""
    modpack_data = load_modpack_index()
    if not modpack_data:
        return
    
    minecraft_version = modpack_data['dependencies']['minecraft']
    loader = 'fabric'
    
    print(f"🔍 Vérification des mises à jour pour Minecraft {minecraft_version} avec {loader}")
    print("=" * 60)
    
    updates_available = []
    
    for i, file_entry in enumerate(modpack_data['files']):
        if not file_entry.get('downloads'):
            continue
            
        current_url = file_entry['downloads'][0]
        project_id = extract_project_id_from_url(current_url)
        
        if not project_id:
            continue
        
        project_info = get_project_info(project_id)
        if not project_info:
            continue
        
        project_name = project_info['title']
        print(f"📦 Vérification de {project_name}...")
        
        versions = get_project_versions(project_id, minecraft_version, loader)
        if not versions:
            print(f"   ⚠️  Aucune version compatible trouvée")
            continue
        
        current_version = get_version_from_url(versions, current_url)
        latest_version = versions[0]
        
        if not current_version:
            print(f"   ❓ Version actuelle non trouvée dans les versions compatibles")
            continue
        
        if compare_versions(current_version, latest_version):
            update_info = {
                'index': i,
                'project_name': project_name,
                'current_version': current_version['version_number'],
                'latest_version': latest_version['version_number'],
                'current_date': current_version['date_published'][:10],
                'latest_date': latest_version['date_published'][:10],
                'file_entry': file_entry,
                'new_version': latest_version,
                'project_info': project_info
            }
            updates_available.append(update_info)
            print(f"   🆕 Mise à jour disponible: {current_version['version_number']} → {latest_version['version_number']}")
        else:
            print(f"   ✅ À jour ({current_version['version_number']})")
    
    print("=" * 60)
    
    if not updates_available:
        print("✅ Tous les mods sont à jour!")
        return
    
    print(f"📊 {len(updates_available)} mise(s) à jour disponible(s):")
    print()
    
    for i, update in enumerate(updates_available):
        print(f"{i+1:2d}. {update['project_name']}")
        print(f"    {update['current_version']} ({update['current_date']}) → {update['latest_version']} ({update['latest_date']})")
    
    print()
    print("Options:")
    print("  a) Tout mettre à jour")
    print("  s) Sélectionner individuellement")
    print("  q) Quitter")
    
    choice = input("\nVotre choix: ").strip().lower()
    
    updates_to_apply = []
    
    if choice == 'a':
        updates_to_apply = updates_available
    elif choice == 's':
        print("\nSélectionnez les mods à mettre à jour (séparez par des espaces, ex: 1 3 5):")
        try:
            indices = input("Numéros: ").strip().split()
            for idx in indices:
                i = int(idx) - 1
                if 0 <= i < len(updates_available):
                    updates_to_apply.append(updates_available[i])
        except ValueError:
            print("❌ Format invalide")
            return
    elif choice == 'q':
        return
    else:
        print("❌ Choix invalide")
        return
    
    if not updates_to_apply:
        print("Aucune mise à jour sélectionnée")
        return
    
    print(f"\n🔄 Application de {len(updates_to_apply)} mise(s) à jour...")
    
    success_count = 0
    for update in updates_to_apply:
        print(f"   📦 {update['project_name']}...")
        if update_file_entry(update['file_entry'], update['new_version'], update['project_info']):
            success_count += 1
            print(f"   ✅ {update['project_name']} mis à jour!")
        else:
            print(f"   ❌ Échec pour {update['project_name']}")
    
    if success_count > 0:
        # Trier les fichiers par path (ordre ASCII : majuscules avant minuscules)
        modpack_data['files'].sort(key=lambda x: x.get('path', ''))
        
        if save_modpack_index(modpack_data):
            print(f"\n💾 {success_count} mise(s) à jour appliquée(s) et sauvegardée(s)!")
        else:
            print("\n❌ Erreur lors de la sauvegarde")
    else:
        print("\n❌ Aucune mise à jour n'a pu être appliquée")

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == '--auto-update':
            check_updates(auto_update=True)
        elif sys.argv[1] == '--interactive' or sys.argv[1] == '-i':
            interactive_update()
        else:
            print("Usage: python check_updates.py [--auto-update | --interactive]")
            print("  --auto-update : Met à jour automatiquement tous les mods")
            print("  --interactive : Mode interactif pour choisir les mises à jour")
            print("  (sans argument) : Affiche seulement les mises à jour disponibles")
    else:
        check_updates(auto_update=False)

if __name__ == "__main__":
    main()
