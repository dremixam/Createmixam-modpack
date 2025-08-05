# Createmixam Modpack

Un modpack Minecraft Fabric pour la version 1.20.1 centré sur Create et ses addons.

## 🚀 Installation

### Méthode 1: Téléchargement direct
1. Allez dans la section [Releases](../../releases) de ce repository
2. Téléchargez le fichier `.mrpack` le plus récent
3. Importez le fichier dans votre launcher Minecraft favori (Modrinth App, Prism Launcher, etc.)

### Méthode 2: Depuis les Artifacts
1. Allez dans la section [Actions](../../actions)
2. Cliquez sur le build le plus récent
3. Téléchargez l'artifact contenant le fichier `.mrpack`

## 📋 Informations du Modpack

- **Version Minecraft:** 1.20.1
- **Mod Loader:** Fabric Loader 0.16.14
- **Mods principaux:** Create, Farmer's Delight, Terralith, et bien d'autres...

## 🔧 Développement

### Structure du projet
```
├── modrinth.index.json    # Index des mods avec leurs métadonnées
├── overrides/             # Fichiers de configuration et ressources
│   ├── config/           # Configurations des mods
│   ├── mods/             # Mods personnalisés/locaux
│   └── ...
└── .github/workflows/    # Actions GitHub pour la CI/CD
```

### Build automatique
Le modpack est automatiquement construit via GitHub Actions :
- **Sur push vers `main`** : Build de développement
- **Sur tag** : Release officielle
- **Sur pull request** : Build de test

### Créer une release
1. Créez un tag avec le format `v1.0.0` :
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
2. GitHub Actions créera automatiquement une release avec le fichier `.mrpack`

## 🛠️ Modification du modpack

### Ajouter/Supprimer des mods
1. Modifiez le fichier `modrinth.index.json`
2. Ajoutez les configurations nécessaires dans `overrides/config/`
3. Commitez et poussez vos changements

### Tester localement
```bash
# Créer le mrpack manuellement
mkdir mrpack-temp
cp modrinth.index.json mrpack-temp/
cp -r overrides mrpack-temp/
cd mrpack-temp
zip -r "../Createmixam-modpack.mrpack" *
cd .. && rm -rf mrpack-temp
```

## 📝 Changelog

Voir la section [Releases](../../releases) pour l'historique des versions.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
- Signaler des bugs
- Proposer de nouveaux mods
- Améliorer les configurations
- Corriger la documentation

## 📄 Licence

Ce modpack est distribué sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.
