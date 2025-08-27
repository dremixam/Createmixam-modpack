# Scripts de gestion des mods Modrinth

Ce dossier contient deux scripts Python pour gérer les mods dans votre modpack Modrinth.

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
pip install requests
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
- ✅ Détecte automatiquement la version compatible avec Minecraft et Fabric
- ✅ Télécharge et calcule les hashes SHA1/SHA512
- ✅ Détermine l'environnement client/serveur automatiquement
- ✅ Vérifie si le mod est déjà présent
- ✅ Met à jour automatiquement le fichier modrinth.index.json

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
- ✅ Scan tous les mods du modpack
- ✅ Vérifie les versions plus récentes compatibles
- ✅ Affiche les changements de version et dates
- ✅ Mode automatique ou interactif
- ✅ Calcule automatiquement les nouveaux hashes
- ✅ Sauvegarde automatique du fichier modifié

## Exemples d'utilisation

### Ajouter plusieurs mods
```bash
python add_mod.py https://modrinth.com/mod/sodium
python add_mod.py https://modrinth.com/mod/lithium  
python add_mod.py https://modrinth.com/mod/phosphor
```

### Vérifier et mettre à jour
```bash
# Voir ce qui peut être mis à jour
python check_updates.py

# Tout mettre à jour d'un coup
python check_updates.py --auto-update

# Choisir interactivement
python check_updates.py --interactive
```

## Notes importantes

- Les scripts détectent automatiquement la version Minecraft depuis `modrinth.index.json`
- Le loader est assumé être Fabric (modifiable dans le code si besoin)
- Les hashes sont calculés en téléchargeant les fichiers
- Sauvegarde automatique avec formatage JSON propre
- Gestion d'erreur pour les mods non compatibles ou introuvables

## Structure du projet

```
├── modrinth.index.json  # Fichier du modpack
├── add_mod.py          # Script d'ajout de mods
├── check_updates.py    # Script de mise à jour
├── requirements.txt    # Dépendances Python
├── venv/               # Environnement virtuel (optionnel)
└── README_scripts.md   # Ce fichier
```

## Désactivation de l'environnement virtuel

Quand vous avez fini d'utiliser les scripts :
```bash
deactivate
```
