import pandas as pd

# Gestion des coordonnées / projection
from src.carte_config import gps_to_lambert93

# Affichage des objects graphiques
from src.affichage_objets import *



def dms_to_decimal(dms_str):
    parts = dms_str.strip().split()
    deg, min_, sec, dir_ = int(parts[0]), int(parts[1]), int(parts[2]), parts[3].upper()
    decimal = deg + min_ / 60 + sec / 3600
    return -decimal if dir_ in ['S', 'W'] else decimal



def load_villes_database(csv_path:str):
    df = pd.read_csv(csv_path)
    villes = []
    for _, row in df.iterrows():
        nom = row["Nom"]
        lat = dms_to_decimal(row["Latitude"])
        lon = dms_to_decimal(row["Longitude"])
        x_l93, y_l93 = gps_to_lambert93(lon, lat)  # conversion GPS → Lambert93
        villes.append(PointGraphique(nom, x_l93, y_l93, lat=lat, lon=lon))  # ✅ Création directe de PointGraphique
    return villes

#villes_l93 = load_villes_database("villes_database.csv")
villes_dict = {v.nom: v for v in load_villes_database("data/villes_database.csv")}
