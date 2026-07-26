#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import argparse
import sys
from pathlib import Path

def trier_fichier_json(chemin_fichier, fichier_sortie=None):
    path_obj = Path(chemin_fichier)
    
    # 1. Vérifier si le fichier existe
    if not path_obj.is_file():
        print(f"Erreur : Le fichier '{chemin_fichier}' n'existe pas.", file=sys.stderr)
        sys.exit(1)

    # 2. Charger le fichier JSON
    try:
        with open(path_obj, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Erreur lors de la lecture du JSON : {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Vérifier que la clé 'files' existe et est une liste
    if 'files' not in data or not isinstance(data['files'], list):
        print("Erreur : Le fichier JSON ne contient pas une liste sous la clé 'files'.", file=sys.stderr)
        sys.exit(1)

    # 4. Trier chaque OBJET COMPLET du tableau 'files' selon son 'path' (Ordre ASCII)
    # Les majuscules passent naturellement avant les minuscules ('A' < 'a')
    data['files'].sort(key=lambda item: item.get('path', ''))

    # 5. Déterminer le fichier de destination (écrase le fichier d'origine par défaut si non spécifié)
    destination = Path(fichier_sortie) if fichier_sortie else path_obj

    # 6. Sauvegarder le résultat
    with open(destination, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Tri terminé avec succès ! Fichier sauvegardé : {destination}")

def main():
    parser = argparse.ArgumentParser(
        description="Trie les objets d'un JSON dans la clé 'files' selon leur 'path' (ASCII : Majuscules puis minuscules)."
    )
    
    # Argument obligatoire : le fichier à trier
    parser.add_argument(
        "fichier", 
        type=str, 
        help="Chemin vers le fichier JSON à trier"
    )
    
    # Argument optionnel : un fichier de sortie si on ne veut pas écraser l'original
    parser.add_argument(
        "-o", "--output", 
        type=str, 
        default=None, 
        help="Fichier de sortie (Optionnel). Si omis, le fichier d'origine sera remplacé."
    )

    args = parser.parse_args()
    trier_fichier_json(args.fichier, args.output)

if __name__ == "__main__":
    main()