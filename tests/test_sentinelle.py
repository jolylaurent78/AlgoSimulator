from types import SimpleNamespace

import pytest

import src.Sentinelle as sentinelle_module
from src.Sentinelle import LieuxObservation, Sentinelle


class DateFictive:
    def __init__(self, valeur):
        self.valeur = valeur

    def toString(self, _format):
        return "10:10:29"


class VilleFictive:
    def __init__(self, nom, coordonnees, pixels=(0, 0), metres_par_pixel=10_000):
        self.nom = nom
        self._coordonnees = coordonnees
        self._pixels = pixels
        self._metres_par_pixel = metres_par_pixel

    def getCoordonneesGPS(self):
        return self._coordonnees

    def coordonneesPixelAbs(self):
        return self._pixels

    def pixelsVersMetres(self):
        return self._metres_par_pixel


class LigneCalibrationFictive:
    def __init__(self, *_coordonnees):
        pass

    def azimut(self):
        return 100.0

    def angleAvec(self, _autre):
        return 30.0


def installer_frontieres_sentinelle(monkeypatch, heures="10:10:29"):
    villes = {
        "Coetquidan": VilleFictive("Coetquidan", (47.0, -2.0), (0, 0)),
        "Golfe-Juan": VilleFictive("Golfe-Juan", (43.0, 7.0), (10, 0)),
        "Carnac": VilleFictive("Carnac", (47.0, -3.0)),
        "Lampouy": VilleFictive("Lampouy", (48.0, -2.0)),
    }

    monkeypatch.setattr(sentinelle_module, "villes_dict", villes)
    monkeypatch.setattr(sentinelle_module, "PointGraphique", lambda ville: ville)
    monkeypatch.setattr(sentinelle_module, "Ligne", LigneCalibrationFictive)
    monkeypatch.setattr(
        sentinelle_module,
        "MyJulianDate",
        SimpleNamespace(fromString=lambda valeur: DateFictive(valeur)),
    )
    monkeypatch.setattr(
        sentinelle_module,
        "calculHeurePourAzimutSoleil",
        lambda *_args, **_kwargs: SimpleNamespace(toString=lambda _format: heures),
    )
    monkeypatch.setattr(
        sentinelle_module,
        "convertirHeureLocaleVersUTC",
        lambda heure, _longitude, inverse: heure,
    )
    return villes


def ecrire_csv(tmp_path, contenu):
    chemin = tmp_path / "sentinelle.csv"
    chemin.write_text(contenu, encoding="utf-8")
    return chemin


def test_charge_csv_synthetique_et_construit_les_notes(tmp_path, monkeypatch):
    installer_frontieres_sentinelle(monkeypatch)
    chemin = ecrire_csv(
        tmp_path,
        "Nom,Note,Azimut,AzimutGeant,Ville\nS1,C,128.5,308.5,\nS2,F,142,218,Lampouy\n",
    )

    sentinelle = Sentinelle(chemin)

    assert list(sentinelle.fichierSentinelles) == ["S1", "S2"]
    assert sentinelle.fichierSentinelles["S1"]["Azimut"] == "128.5"
    assert sentinelle["C"] == {
        "HeureLocale": "10:10",
        "AzimutCalibre": 128.5,
        "AzimutGeant": 308.5,
    }
    assert sentinelle["F"]["AzimutCalibre"] == 150.0
    assert sentinelle["F"]["AzimutGeant"] == 218.0


def test_csv_azimut_non_numerique_est_refuse_lors_de_la_calibration(tmp_path, monkeypatch):
    installer_frontieres_sentinelle(monkeypatch)
    chemin = ecrire_csv(tmp_path, "Nom,Note,Azimut,AzimutGeant,Ville\nS1,C,invalide,308.5,\n")

    with pytest.raises(ValueError):
        Sentinelle(chemin)


def test_acces_aux_notes_et_recherche_par_heure(tmp_path, monkeypatch):
    installer_frontieres_sentinelle(monkeypatch)
    chemin = ecrire_csv(tmp_path, "Nom,Note,Azimut,AzimutGeant,Ville\nS1,C,100,200,\n")
    sentinelle = Sentinelle(chemin)

    assert sentinelle["C"]["AzimutCalibre"] == 100.0
    assert sentinelle.getAzimut("10:10") == 100.0
    assert sentinelle.getAzimut("00:00") is None
    with pytest.raises(KeyError):
        _ = sentinelle["Inconnue"]


def test_calculer_heure_arrondit_et_gere_le_depassement_de_minuit(tmp_path, monkeypatch):
    installer_frontieres_sentinelle(monkeypatch, heures="23:59:30")
    chemin = ecrire_csv(tmp_path, "Nom,Note,Azimut,AzimutGeant,Ville\nS1,C,100,200,\n")

    sentinelle = Sentinelle(chemin)

    assert sentinelle["C"]["HeureLocale"] == "00:00"


def test_lampouy_utilise_ses_coordonnees_et_sa_date_dediee(tmp_path, monkeypatch):
    villes = installer_frontieres_sentinelle(monkeypatch)
    appels = []
    monkeypatch.setattr(
        sentinelle_module,
        "calculHeurePourAzimutSoleil",
        lambda coord, date, azimut, precision_deg: appels.append((coord, date.valeur, azimut, precision_deg))
        or SimpleNamespace(toString=lambda _format: "10:10:29"),
    )
    chemin = ecrire_csv(
        tmp_path,
        "Nom,Note,Azimut,AzimutGeant,Ville\nS1,C,100,200,\nLampouy,L,138.5,139,\n",
    )

    Sentinelle(chemin)

    assert appels == [
        (villes["Carnac"].getCoordonneesGPS(), "15/08/1066", 100.0, 0.2),
        (villes["Lampouy"].getCoordonneesGPS(), "20/08/1152", 138.5, 0.2),
    ]


class LigneDistanceFictive:
    distances = {}

    def __init__(self, azimut):
        self.azimut = azimut

    @classmethod
    def depuisPointEtAzimut(cls, _point, azimut):
        return cls(azimut)

    def distanceAuPoint(self, _px, _py):
        return self.distances[self.azimut]


def sentinelle_pour_lignes(distances, valeurs, inclure_lampouy=False):
    sentinelle = Sentinelle.__new__(Sentinelle)
    dict.__init__(sentinelle, valeurs)
    sentinelle.azimutMidi = 100.0
    sentinelle.pointCoetquidan = VilleFictive("Coetquidan", (0, 0), metres_par_pixel=10_000)
    LigneDistanceFictive.distances = distances
    return sentinelle.surLigneHoraire(0, 0, inclure_lampouy)


def test_sur_ligne_horaire_recherche_le_candidat_am_le_plus_proche(monkeypatch):
    monkeypatch.setattr(sentinelle_module, "Ligne", LigneDistanceFictive)
    valeurs = {
        "C": {"HeureLocale": "09:42", "AzimutCalibre": 150.0},
        "F": {"HeureLocale": "10:25", "AzimutCalibre": 160.0},
    }

    resultat = sentinelle_pour_lignes(
        {130.0: 4.0, 70.0: 5.0, 120.0: 1.9, 80.0: 6.0}, valeurs
    )

    assert resultat == (True, "10:25", "AM", 19, 120.0)


def test_sur_ligne_horaire_reconnait_pm_et_rejette_le_seuil_20_km(monkeypatch):
    monkeypatch.setattr(sentinelle_module, "Ligne", LigneDistanceFictive)
    valeurs = {"C": {"HeureLocale": "09:42", "AzimutCalibre": 150.0}}

    resultat_pm = sentinelle_pour_lignes({130.0: 3.0, 70.0: 1.9}, valeurs)
    resultat_seuil = sentinelle_pour_lignes({130.0: 2.0, 70.0: 3.0}, valeurs)

    assert resultat_pm == (True, "09:42", "PM", 19, 70.0)
    assert resultat_seuil == (False, "09:42", "AM", 20, 130.0)


def test_sur_ligne_horaire_exclut_lampouy_sauf_demande(monkeypatch):
    monkeypatch.setattr(sentinelle_module, "Ligne", LigneDistanceFictive)
    valeurs = {
        "C": {"HeureLocale": "09:42", "AzimutCalibre": 150.0},
        "L": {"HeureLocale": "08:12", "AzimutCalibre": 140.0},
    }
    distances = {130.0: 4.0, 70.0: 5.0, 140.0: 1.0, 60.0: 6.0}

    sans_lampouy = sentinelle_pour_lignes(distances, valeurs)
    avec_lampouy = sentinelle_pour_lignes(distances, valeurs, inclure_lampouy=True)

    assert sans_lampouy == (False, "09:42", "AM", 40, 130.0)
    assert avec_lampouy == (True, "08:12", "AM", 10, 140.0)


def test_lieux_observation_expose_les_options_speciales():
    assert LieuxObservation.getListeLieuxObservation("C") == ["Roncevaux", "Cherbourg", "Gérardmer"]
    assert LieuxObservation.getListeLieuxObservation("F", "18/05/1152") == ["Bourges", "Dieppe", "Lampouy"]
    assert LieuxObservation.getDefautLieuObservation("C") == "Roncevaux"
    assert LieuxObservation.getDefautLieuObservation("?") == "-"


@pytest.mark.integration
def test_csv_reel_garde_les_notes_references(monkeypatch):
    monkeypatch.setattr(
        sentinelle_module,
        "calculHeurePourAzimutSoleil",
        lambda *_args, **_kwargs: SimpleNamespace(toString=lambda _format: "10:10:29"),
    )
    monkeypatch.setattr(
        sentinelle_module,
        "convertirHeureLocaleVersUTC",
        lambda heure, _longitude, inverse: heure,
    )

    sentinelle = Sentinelle("data/sentinelle.csv")

    assert set(("C", "F", "J", "L")) <= set(sentinelle)
    assert sentinelle["J"]["AzimutGeant"] == 153.0
    assert sentinelle["L"]["HeureLocale"] == "10:10"
