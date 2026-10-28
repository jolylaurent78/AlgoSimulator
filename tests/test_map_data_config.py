import json
import math
from pathlib import Path

import numpy as np
import pytest

import src.carte_config as carte_config
import src.data_loader as data_loader
from src.carte_config import CarteConfig
from src.configGlobale import ConfigGlobale


class PointFictif:
    def __init__(self, nom, x_l93, y_l93):
        self.nom = nom
        self.x_l93 = x_l93
        self.y_l93 = y_l93

    def coordonneesLambert(self):
        return self.x_l93, self.y_l93


class ProjectionFictive:
    def gps_to_lambert93(self, lon, lat):
        return lon * 1000, lat * 1000


@pytest.mark.parametrize(
    ("dms", "attendu"),
    [
        ("47 30 00 N", 47.5),
        ("2 15 00 E", 2.25),
        ("12 30 00 S", -12.5),
        ("1 30 00 W", -1.5),
    ],
)
def test_dms_to_decimal_convertit_les_quatre_directions(dms, attendu):
    assert data_loader.VillesDict.dms_to_decimal(dms) == pytest.approx(attendu)


def test_villes_dict_charge_un_csv_dms_et_projette_les_coordonnees(tmp_path, monkeypatch):
    csv_path = tmp_path / "villes.csv"
    csv_path.write_text(
        "Nom,Latitude,Longitude,Icone\n"
        "Ville Nord,47 30 00 N,2 15 00 E,inconnue.png\n"
        "Ville Sud,12 30 00 S,1 30 00 W,inconnue.png\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(data_loader, "PointGraphique", PointFictif)
    monkeypatch.setattr(data_loader, "carteConfig", ProjectionFictive())

    villes = data_loader.VillesDict(csv_path)

    assert set(villes) == {"Ville Nord", "Ville Sud"}
    assert villes["Ville Nord"].coordonneesLambert() == pytest.approx((2250, 47500))
    assert villes["Ville Sud"].coordonneesLambert() == pytest.approx((-1500, -12500))


def test_recharger_remplace_le_contenu_au_lieu_de_l_accumuler(tmp_path, monkeypatch):
    csv_path = tmp_path / "villes.csv"
    csv_path.write_text(
        "Nom,Latitude,Longitude,Icone\nAncienne,47 00 00 N,2 00 00 E,map.png\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(data_loader, "PointGraphique", PointFictif)
    monkeypatch.setattr(data_loader, "carteConfig", ProjectionFictive())
    villes = data_loader.VillesDict(csv_path)

    csv_path.write_text(
        "Nom,Latitude,Longitude,Icone\nNouvelle,48 00 00 N,3 00 00 E,map.png\n",
        encoding="utf-8",
    )
    villes.recharger()

    assert set(villes) == {"Nouvelle"}


def test_villes_reelles_requises_sont_chargees_avec_des_coordonnees_lambert_plausibles():
    for nom in ("Carnac", "Bourges", "Roncevaux", "Lampouy", "Beaufort-en-Vallée"):
        x_l93, y_l93 = data_loader.villes_dict[nom].coordonneesLambert()

        assert math.isfinite(x_l93)
        assert math.isfinite(y_l93)
        assert 0 < x_l93 < 1_500_000
        assert 6_000_000 < y_l93 < 7_500_000


def configuration_affine_vide():
    return CarteConfig.__new__(CarteConfig)


def test_transformation_affine_avec_termes_croises_est_inversible():
    configuration = configuration_affine_vide()
    configuration.A = np.array([[2.0, 0.5], [-1.25, 3.0]])
    configuration.offset = np.array([10.0, -4.0])
    configuration.A_inv = np.linalg.inv(configuration.A)

    pixels = configuration.lambert93_to_pixels(4.0, -2.0)

    assert pixels == pytest.approx((17.0, -15.0))
    assert configuration.pixels_to_lambert93(*pixels) == pytest.approx((4.0, -2.0))


def test_calibrer_retrouve_matrice_affine_et_offset_avec_termes_croises():
    configuration = configuration_affine_vide()
    matrice = np.array([[1.5, -0.25], [0.75, 2.0]])
    offset = np.array([12.0, -8.0])
    points_lambert = [(0, 0), (4, 0), (0, 3), (-2, 5)]
    points_pixels = [tuple(matrice @ point + offset) for point in points_lambert]

    configuration.calibrer(points_lambert, points_pixels)

    assert configuration.A == pytest.approx(matrice)
    assert configuration.offset == pytest.approx(offset)
    assert configuration.pixels_to_lambert93(*points_pixels[-1]) == pytest.approx(points_lambert[-1])


def test_calibrer_exige_au_moins_trois_points():
    with pytest.raises(AssertionError, match="Au moins 3 points"):
        configuration_affine_vide().calibrer([(0, 0), (1, 1)], [(0, 0), (1, 1)])


def test_carte_config_charge_un_json_synthetique_et_son_image_associee(tmp_path, monkeypatch):
    json_path = tmp_path / "carte.json"
    json_path.write_text(
        json.dumps(
            {
                "projection": "lambert93",
                "A": [[2, 0], [0, -3]],
                "offset": [10, 20],
                "image_file": "fond.png",
                "description": "Carte de test",
                "calibration_villes": ["Carnac"],
            }
        ),
        encoding="utf-8",
    )
    chemins_lus = []

    def lire_image(chemin):
        chemins_lus.append(chemin)
        return np.zeros((3, 7, 3), dtype=np.uint8)

    monkeypatch.setattr(carte_config.cv2, "imread", lire_image)

    configuration = CarteConfig(json_path)

    assert chemins_lus == [str(tmp_path / "fond.png")]
    assert configuration.image_size == (7, 3)
    assert configuration.description == "Carte de test"
    assert configuration.calibration_villes == ["Carnac"]


def test_carte_config_refuse_une_projection_non_supportee(tmp_path):
    json_path = tmp_path / "carte.json"
    json_path.write_text(json.dumps({"projection": "mercator"}), encoding="utf-8")

    with pytest.raises(ValueError, match="lambert93"):
        CarteConfig(json_path)


def test_carte_config_signale_l_image_associee_absente(tmp_path, monkeypatch):
    json_path = tmp_path / "carte.json"
    json_path.write_text(
        json.dumps(
            {
                "projection": "lambert93",
                "A": [[1, 0], [0, 1]],
                "offset": [0, 0],
                "image_file": "absente.png",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(carte_config.cv2, "imread", lambda _chemin: None)

    with pytest.raises(FileNotFoundError, match="absente.png"):
        CarteConfig(json_path)


def test_config_globale_persiste_et_restitue_la_derniere_carte(tmp_path):
    chemin = tmp_path / "simulateur.ini"
    configuration = ConfigGlobale(chemin)

    assert configuration.get("Carte", "lastCarte", "data/carto/899.json") == "data/carto/899.json"
    configuration.set("Carte", "lastCarte", "data/carto/carte test.json")
    configuration.save()

    assert ConfigGlobale(chemin).get("Carte", "lastCarte") == "data/carto/carte test.json"


def test_configuration_carto_reelle_reference_une_image_existante():
    json_path = Path("data/carto/899 - extended v2 corse_calibree.json")
    with open(json_path, encoding="utf-8") as fichier:
        configuration = json.load(fichier)

    assert configuration["projection"] == "lambert93"
    assert len(configuration["A"]) == 2
    assert (json_path.parent / configuration["image_file"]).is_file()
