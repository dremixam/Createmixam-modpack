# Scripts de gestion des mods Modrinth

Ce dossier contient des scripts Python pour gérer les mods dans votre modpack Modrinth, créer des releases et déployer vers votre serveur.

## Installation des dépendances

### Avec environnement virtuel (recommandé)
```bash
# Créer l'environnement virtuel
python -m venv venv

# L'activer
# Sur Windows :
venv\Scripts\activate
# Sur Linux/Mac :
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

### Installation directe
```bash
pip install -r requirements.txt
```

### Installation manuelle
```bash
pip install requests paramiko python-dotenv
```

## Configuration SFTP (.env)

Créez un fichier `.env` à la racine du projet pour la connexion SFTP :

```env
SFTP_HOST=123.456.789.0
SFTP_PORT=22
SFTP_USER=mon_utilisateur
SFTP_PASSWORD=mon_mot_de_passe
SFTP_MODS_DIR=/home/container/mods
```

## 1. add_mod.py - Ajouter un mod

Ajoute automatiquement un mod au modpack depuis un lien Modrinth.

### Usage

```bash
python add_mod.py <lien_modrinth>
```

### Exemples

```bash
python add_mod.py https://modrinth.com/mod/sodium
python add_mod.py https://modrinth.com/mod/lithium
python add_mod.py sodium  # ID direct du projet
```

### Fonctionnalités

* ✅ Détecte automatiquement la version compatible avec Minecraft et Fabric
* ✅ Télécharge et calcule les hashes SHA1/SHA512
* ✅ Détermine l'environnement client/serveur automatiquement
* ✅ Vérifie si le mod est déjà présent
* ✅ Met à jour automatiquement le fichier modrinth.index.json
* ❌ Ne check pas les interdépendances entre mods en particulier au niveau des versions

## 2. check_updates.py - Vérifier les mises à jour

Vérifie et applique les mises à jour des mods déjà présents dans le modpack.

### Usage

#### Afficher les mises à jour disponibles

```bash
python check_updates.py
```

#### Mettre à jour automatiquement tous les mods

```bash
python check_updates.py --auto-update
```

#### Mode interactif (choisir quels mods mettre à jour)

```bash
python check_updates.py --interactive
```

### Fonctionnalités

* ✅ Scan tous les mods du modpack
* ✅ Vérifie les versions plus récentes compatibles
* ✅ Affiche les changements de version et dates
* ✅ Mode automatique ou interactif
* ✅ Calcule automatiquement les nouveaux hashes
* ✅ Sauvegarde automatique du fichier modifié
* ❌ Ne check pas les interdépendances entre mods en particulier au niveau des versions

## 3. release.py - Publier une nouvelle version

Prépare la publication d'une nouvelle version du modpack.

### Usage

```bash
python release.py [v2.0.4]
```

### Fonctionnalités

* ✅ Met à jour le numéro de version dans `overrides/config/bcc.json`
* ✅ Crée un commit Git dédié `Release vX.Y.Z`
* ✅ Crée et pose le Tag Git associé
* ✅ Pushe la branche et le tag sur GitHub (déclenche la CI/CD .mrpack)
* ✅ Propose d'enchaîner directement sur `generate_server.py`

## 4. generate_server.py - Générer un serveur, notes de version et SFTP

Compare l'état actuel avec le dernier tag git, génère un dossier serveur avec les mods compatibles, et propose le déploiement SFTP.

### Usage

```bash
python generate_server.py
```

### Fonctionnalités

* ✅ Compare automatiquement avec le dernier tag git
* ✅ Génère un dossier `_server/` avec les mods serveur
* ✅ Télécharge uniquement les mods compatibles côté serveur
* ✅ Crée des notes de version détaillées (PATCHNOTES.md)
* ✅ Détecte les mods ajoutés, supprimés et mis à jour
* ✅ Inclut les commits depuis le dernier tag
* ✅ Synchronise les mods `.jar` ainsi que le fichier `config/bcc.json` sur le serveur SFTP
* ✅ Conserve l'état désactivé (`.disabled`) des mods sur le serveur distant

### Contenu généré

```
_server/
├── mods/                # Mods compatibles serveur (.jar)
├── PATCHNOTES.md       # Notes de version détaillées
└── README.md           # Instructions d'installation
```

## Exemples d'utilisation

### Workflow complet de release

```bash
# 1. Ajouter ou mettre à jour des mods
python add_mod.py https://modrinth.com/mod/sodium
python check_updates.py --auto-update

# 2. Publier la nouvelle version (bcc.json, commit, tag, push)
python release.py v2.0.4

# 3. Déployer sur le serveur via generate_server.py (proposé automatiquement par release.py)
python generate_server.py
```

## Notes importantes

* Les scripts détectent automatiquement la version Minecraft depuis `modrinth.index.json`
* Le loader est assumé être Fabric
* Les hashes sont calculés en téléchargeant les fichiers
* Le déploiement SFTP met automatiquement à jour `config/bcc.json` dans le répertoire distant du serveur

## Structure du projet

```
├── modrinth.index.json  # Fichier du modpack
├── add_mod.py          # Script d'ajout de mods
├── check_updates.py    # Script de mise à jour
├── release.py          # Script de création de release Git
├── generate_server.py  # Script de génération & déploiement serveur
├── overrides/
│   └── config/
│       └── bcc.json    # Config de version du modpack
├── requirements.txt    # Dépendances Python
├── .env                # Identifiants SFTP
├── venv/               # Environnement virtuel (optionnel)
├── _server/            # Dossier généré (dans .gitignore)
│   ├── mods/           # Mods serveur
│   ├── PATCHNOTES.md   # Notes de version
│   └── README.md       # Documentation serveur
└── README_scripts.md   # Ce fichier
```

## Désactivation de l'environnement virtuel

Quand vous avez fini d'utiliser les scripts :

```bash
deactivate
```