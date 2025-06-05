# AlgoSimulator

Simulation algorithmique interactive avec interface graphique, destinée à l'exploration, la visualisation et le test de modules algorithmiques sur données géographiques ou historiques.

## 🧩 Fonctionnalités

- Interface utilisateur interactive (Tkinter)
- Gestion modulaire des algorithmes
- Chargement de fichiers de configuration (INI, CSV)
- Base de données de villes intégrée
- Affichage cartographique avec OpenCV
- Débogage visuel et traçage des scénarios

## 📁 Arborescence recommandée

```
AlgoSimulator/
├── src/                      # Code source Python (modules, IHM, logique)
├── config/                   # Fichiers de configuration INI
├── dataset/                  # Données d'entrée CSV (ex : villes)
├── images/                   # Éléments graphiques (icônes, cartes, etc.)
├── projets/                  # Scénarios ou sauvegardes utilisateur
├── Synthese Word/            # Rapports ou documents liés
├── README.md                 # Ce fichier
├── requirements.txt          # Dépendances Python
└── .gitignore                # Fichiers à exclure de Git
```

## 🚀 Lancer l’application

Assurez-vous d’avoir Python ≥ 3.10 installé.

```bash
cd AlgoSimulator
python src/interface_tk.py
```

## 🧪 Débogage

Le projet est compatible avec VS Code :
- Profils `launch.json` personnalisés
- Points d'arrêt à la volée
- Exécution d’un scénario ou d’un module individuel

## 📦 Dépendances

Installez les bibliothèques nécessaires :

```bash
pip install -r requirements.txt
```

Les bibliothèques typiques incluent :
- `opencv-python`
- `tkinter`
- `numpy`
- `pandas`

## 📚 Auteurs

Développé par Laurent Joly  
Projet personnel pour la visualisation algorithmique et la manipulation de données géographiques.
