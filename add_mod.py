#!/usr/bin/env python3
"""
Script pour ajouter un mod à modrinth.index.json depuis un lien Modrinth
Usage: python add_mod.py <lien_modrinth>
Exemple: python add_mod.py https://modrinth.com/mod/sodium
"""

import json
import sys
import requests
import hashlib
import re
from urllib.parse import urlparse

def get_project_id_from_url(url):
    """Extrait l'ID du projet depuis l'URL Modrinth"""
    # Patterns possibles:
    # https://modrinth.com/mod/sodium
    # https://modrinth.com/datapack/terralith
    # https://modrinth.com/project/create
    
    pattern = r'modrinth\.com/(?:mod|datapack|project)/([^/?]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    
    # Si pas de match, essayer avec l'ID direct
    if '/' in url:
        return url.split('/')[-1]
    
    return url

def get_project_info(project_id):
    """Récupère les infos du projet depuis l'API Modrinth"""
    url = f"https://api.modrinth.com/v2/project/{project_id}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la récupération du projet: {e}")
        return None

def get_compatible_version(project_id, minecraft_version, loader):
    """Trouve une version compatible avec MC et le loader"""
    url = f"https://api.modrinth.com/v2/project/{project_id}/version"
    params = {
        'game_versions': f'["{minecraft_version}"]',
        'loaders': f'["{loader}"]'
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        versions = response.json()
        
        if not versions:
            return None
            
        # Prendre la version la plus récente
        return versions[0]
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la récupération des versions: {e}")
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

def is_mod_already_added(modpack_data, project_id):
    """Vérifie si le mod est déjà dans le modpack"""
    for file_entry in modpack_data.get('files', []):
        if any(project_id in url for url in file_entry.get('downloads', [])):
            return True
    return False

def create_file_entry(version_data, project_info):
    """Crée l'entrée de fichier pour modrinth.index.json"""
    primary_file = version_data['files'][0]  # Premier fichier (principal)
    
    # Déterminer l'environnement basé sur le type de projet
    project_type = project_info.get('project_type', 'mod')
    server_side = project_info.get('server_side', 'optional')
    client_side = project_info.get('client_side', 'optional')
    
    env = {}
    if client_side == 'required':
        env['client'] = 'required'
    elif client_side == 'optional':
        env['client'] = 'optional'
    else:
        env['client'] = 'unsupported'
        
    if server_side == 'required':
        env['server'] = 'required'
    elif server_side == 'optional':
        env['server'] = 'optional'
    else:
        env['server'] = 'unsupported'
    
    # Calculer les hashes
    print(f"Téléchargement et calcul des hashes pour {primary_file['filename']}...")
    hash_data = download_file_hash(primary_file['url'])
    
    if not hash_data:
        return None
    
    return {
        'downloads': [primary_file['url']],
        'env': env,
        'fileSize': hash_data['size'],
        'hashes': {
            'sha1': hash_data['sha1'],
            'sha512': hash_data['sha512']
        },
        'path': f"mods/{primary_file['filename']}"
    }

def main():
    if len(sys.argv) != 2:
        print("Usage: python add_mod.py <lien_modrinth>")
        print("Exemple: python add_mod.py https://modrinth.com/mod/sodium")
        sys.exit(1)
    
    mod_url = sys.argv[1]
    
    # Charger le modpack
    modpack_data = load_modpack_index()
    if not modpack_data:
        sys.exit(1)
    
    minecraft_version = modpack_data['dependencies']['minecraft']
    loader = 'fabric'  # Assume fabric basé sur le modpack
    
    print(f"Modpack: Minecraft {minecraft_version}, Loader: {loader}")
    
    # Extraire l'ID du projet
    project_id = get_project_id_from_url(mod_url)
    print(f"ID du projet: {project_id}")
    
    # Vérifier si déjà ajouté
    if is_mod_already_added(modpack_data, project_id):
        print(f"Le mod {project_id} est déjà dans le modpack!")
        sys.exit(0)
    
    # Récupérer les infos du projet
    print("Récupération des informations du projet...")
    project_info = get_project_info(project_id)
    if not project_info:
        sys.exit(1)
    
    print(f"Projet trouvé: {project_info['title']}")
    print(f"Description: {project_info.get('description', 'N/A')}")
    
    # Trouver une version compatible
    print(f"Recherche d'une version compatible...")
    version = get_compatible_version(project_id, minecraft_version, loader)
    if not version:
        print(f"Aucune version compatible trouvée pour Minecraft {minecraft_version} avec {loader}")
        sys.exit(1)
    
    print(f"Version trouvée: {version['version_number']} ({version['name']})")
    
    # Créer l'entrée de fichier
    file_entry = create_file_entry(version, project_info)
    if not file_entry:
        print("Erreur lors de la création de l'entrée de fichier")
        sys.exit(1)
    
    # Ajouter au modpack
    modpack_data['files'].append(file_entry)
    
    # Trier les fichiers par path (ordre ASCII : majuscules avant minuscules)
    modpack_data['files'].sort(key=lambda x: x.get('path', ''))
    
    # Sauvegarder
    if save_modpack_index(modpack_data):
        print(f"✅ Mod {project_info['title']} ajouté avec succès!")
        print(f"Fichier: {file_entry['path']}")
    else:
        print("❌ Erreur lors de la sauvegarde")
        sys.exit(1)

if __name__ == "__main__":
    main()
