"""Contrat du nouveau référentiel, indépendant de toute carte ou calibration.

Les témoins de l'investigation sont comparés à ±6 s et ±0,025° : ils sont
arrondis et proviennent d'un moteur non identifié. Ces bornes ne représentent
pas l'incertitude physique de 1066. La recherche numérique vise 0,01 s ; les
contraintes faisant autorité sont testées séparément, beaucoup plus finement.
"""
import csv
import json
from pathlib import Path
import subprocess
import sys

import pytest

import src.calculAstronomique as astro
from src.ReferentielSentinelles import (
    RACINE, ReferentielSentinelles, HeureMoyenneLocale,
    symetrieAzimutSolaireAstronomique,
)


ATTENDUS = {
    "S1": ("C", "heure", "09:43:00", "structurante"),
    "S2": ("D", "azimut", 107.0, "mesure_provisoire"),
    "S3": ("E", "azimut", 255.0, "mesure_provisoire"),
    "S4": ("F", "azimut", 218.0, "mesure_provisoire"),
    "S5": ("G", "heure", "12:00:00", "structurante"),
    "S6": ("A", "heure", "11:42:00", "structurante"),
    "S7": ("B", "azimut", 169.0, "reevaluee_physiquement"),
    "Joker": ("J", "heure", "10:55:00", "hypothese_de_travail"),
}


@pytest.fixture(scope="module")
def referentiel():
    return ReferentielSentinelles.charger()


def test_exactement_sept_sentinelles_et_un_axe_joker_sans_lampouy(referentiel):
    refs = list(referentiel)
    assert len(refs) == len({r.identifiant for r in refs}) == 8
    assert sum(r.nature == "sentinelle" for r in refs) == 7
    assert referentiel.get("Joker").nature == "axe_rangee"
    with pytest.raises(KeyError):
        referentiel.get("Lampouy")
    assert all(r.note != "L" for r in refs)


@pytest.mark.parametrize("identifiant", ATTENDUS)
def test_notes_autorites_valeurs_statuts_et_provenance(referentiel, identifiant):
    ref = referentiel.get(identifiant)
    assert (ref.note, ref.autorite, ref.valeur_reference, ref.statut) == ATTENDUS[identifiant]
    assert ref.origine
    # Le physique historique est une provenance distincte du solaire direct.
    with (RACINE / "data/sentinelle.csv").open(encoding="utf-8", newline="") as fichier:
        historique = {r["Nom"]: r for r in csv.DictReader(fichier)}
    assert ref.azimut_physique_initial == float(historique[identifiant]["AzimutGeant"])


def test_conventions_juliennes_UT1_et_decalage_longitude_exact(referentiel):
    contexte = referentiel.contexte
    assert contexte.lieu == "Carnac"
    assert contexte.coordonnees == pytest.approx((47 + 35 / 60 + 36 / 3600, -(3 + 4 / 60 + 47 / 3600)))
    assert contexte.date == "15/08/1066"
    assert contexte.origine_date_jd == 2110640.5
    # Skyfield interprète par défaut cette date comme grégorienne : six jours
    # de différence. Ne jamais construire ici ts.ut1(1066, 8, 15, ...).
    assert contexte.origine_date_jd - astro.ts.ut1(1066, 8, 15).ut1 == pytest.approx(6)
    assert contexte.longitude * 240 == pytest.approx(-739.1333333333333)
    heure = HeureMoyenneLocale.depuisTexte("09:43:00")
    jd = contexte.versUT1(heure)
    assert (float(jd) - contexte.origine_date_jd) * 86400 == pytest.approx(34980 + 739.1333333333333, abs=0.00005)
    assert contexte.depuisUT1(jd).secondes == pytest.approx(heure.secondes, abs=0.00005)


@pytest.mark.parametrize("identifiant", ATTENDUS)
def test_autorite_respectee_et_positions_verifiees_independamment(referentiel, identifiant):
    ref = referentiel.get(identifiant)
    if ref.autorite == "heure":
        assert ref.heure_directe.secondes == HeureMoyenneLocale.depuisTexte(ref.valeur_reference).secondes
    else:
        assert astro.distanceAngulaire(ref.azimut_direct, ref.valeur_reference) < 0.0001
    for direction in (ref.directe, ref.miroir):
        # Calcul direct Skyfield, sans employer les fonctions du nouveau moteur.
        latitude, longitude = referentiel.contexte.coordonnees
        lieu = astro.Topos(latitude_degrees=latitude, longitude_degrees=longitude)
        t = astro.ts.ut1_jd(direction.jd_ut1)
        alt, az, _ = (astro.earth + lieu).at(t).observe(astro.sun).apparent().altaz()
        assert alt.degrees > 0
        assert astro.distanceAngulaire(az.degrees, direction.azimut) < 1e-9
        assert referentiel.contexte.depuisUT1(direction.jd_ut1).secondes == pytest.approx(direction.heure_locale.secondes, abs=0.00005)


@pytest.mark.parametrize("identifiant", ATTENDUS)
def test_comparaison_aux_temoins_affiche_les_ecarts(referentiel, identifiant):
    ref = referentiel.get(identifiant)
    ecarts = ref.ecartsTemoins()
    diagnostic = (f"{identifiant} | ecart A direct={ecarts['azimut_direct_deg']:+.6f} deg | "
                  f"ecart t direct={ecarts['heure_directe_s']:+.6f} s | "
                  f"ecart A miroir={ecarts['azimut_miroir_deg']:+.6f} deg | "
                  f"ecart t miroir={ecarts['heure_miroir_s']:+.6f} s")
    print(diagnostic)
    diagnostic += (f" ; Carnac={referentiel.contexte.coordonnees}, date julienne="
                   f"{referentiel.contexte.date}, JD origine={referentiel.contexte.origine_date_jd}, "
                   "TML=UT1+longitude×240 s, DE406, position apparente sans réfraction")
    assert abs(ecarts["azimut_direct_deg"]) < 0.025, diagnostic
    assert abs(ecarts["azimut_miroir_deg"]) < 0.025, diagnostic
    assert abs(ecarts["heure_directe_s"]) < 6.0, diagnostic
    assert abs(ecarts["heure_miroir_s"]) < 6.0, diagnostic


@pytest.mark.parametrize("identifiant,branche_directe,branche_miroir", [
    ("S1", "matin", "apres_midi"), ("S3", "apres_midi", "matin"),
    ("S4", "apres_midi", "matin"), ("S5", "matin", "apres_midi"),
    ("Joker", "matin", "apres_midi"),
])
def test_branches_reelles(referentiel, identifiant, branche_directe, branche_miroir):
    ref = referentiel.get(identifiant)
    assert (ref.directe.branche, ref.miroir.branche) == (branche_directe, branche_miroir)
    if identifiant == "Joker":
        assert ref.heure_directe.toString() == "10:55:00"
        assert ref.heure_miroir.toString("HH:MM") == "13:09"


@pytest.mark.parametrize("identifiant", ATTENDUS)
def test_symetrie_angulaire_et_involution(referentiel, identifiant):
    ref = referentiel.get(identifiant)
    assert astro.distanceAngulaire(ref.azimut_miroir, (360 - ref.azimut_direct) % 360) < 0.0001
    retour = symetrieAzimutSolaireAstronomique(ref.azimut_miroir, referentiel.moteur)
    assert astro.distanceAngulaire(retour.azimut, ref.azimut_direct) < 0.0001
    assert retour.heure_locale.secondes == pytest.approx(ref.heure_directe.secondes, abs=0.03)
    assert retour.branche == ref.directe.branche


def test_midi_solaire_vrai_et_cas_S4_distincts_de_la_symetrie_24h(referentiel):
    moteur = referentiel.moteur
    midi = moteur.directionPourAzimut(180)
    assert midi.branche == "midi_solaire"
    assert midi.heure_locale.secondes == pytest.approx(12 * 3600 + 118, abs=6)
    s5 = referentiel.get("S5")
    assert s5.heure_directe.secondes < midi.heure_locale.secondes < s5.heure_miroir.secondes
    s4 = referentiel.get("S4")
    assert astro.distanceAngulaire(s4.azimut_direct, 218) < 0.0001
    assert astro.distanceAngulaire(s4.azimut_miroir, 142) < 0.0001
    assert abs(s4.heure_miroir.secondes - (86400 - s4.heure_directe.secondes)) > 240
    assert s4.heure_miroir.toString("HH:MM") != astro.heureSymetrique(s4.heure_directe.toString("HH:MM"))


def test_secondes_non_arrondies_avant_presentation(referentiel):
    heure = referentiel.get("S2").heure_directe
    assert heure.secondes != round(heure.secondes)
    avant = heure.secondes
    assert heure.toString() == "08:14:46"
    assert heure.toString("HH:MM") == "08:15"
    assert heure.secondes == avant
    assert HeureMoyenneLocale.depuisTexte("11:30:42").secondes == 41442
    assert HeureMoyenneLocale(86399.6).toString() == "00:00:00"


def test_centre_national_reference_la_ville_existante_sans_graphique(referentiel):
    cadran = referentiel.cadran_national
    assert cadran.centre == "Coetquidan"
    with (RACINE / "data/villes_database.csv").open(encoding="utf-8", newline="") as fichier:
        noms = {r["Nom"].strip() for r in csv.DictReader(fichier, skipinitialspace=True)}
    assert cadran.centre in noms
    assert cadran.orientation_midi == 125.371
    assert cadran.statut == "calibration_provisoire"
    assert cadran.convention == "nord_grille_lambert93_sens_horaire"
    assert cadran.repere_nord == "EPSG:2154"


@pytest.mark.parametrize("texte", ["24:00:00", "12:60:00", "12:30:60", "12:30:nan", "12:30", "-1:00:00"])
def test_heures_invalides_refusees(texte):
    with pytest.raises(ValueError):
        HeureMoyenneLocale.depuisTexte(texte)


@pytest.mark.parametrize("azimut", [0, 360, 20, float("nan"), float("inf")])
def test_azimuts_inaccessibles_ou_invalides_refuses(referentiel, azimut):
    with pytest.raises(ValueError):
        referentiel.moteur.directionPourAzimut(azimut)


@pytest.mark.parametrize("corruption", ["doublon", "note", "lampouy", "nature", "autorite", "version"])
def test_donnees_invalides_refusees_avant_calcul(tmp_path, corruption):
    donnees = json.loads((RACINE / "data/sentinelles_reference_v1.json").read_text(encoding="utf-8"))
    if corruption == "doublon":
        donnees["directions"][1] = donnees["directions"][0]
    elif corruption == "note":
        donnees["directions"][0]["note"] = "L"
    elif corruption == "lampouy":
        donnees["directions"][0]["identifiant"] = "Lampouy"
    elif corruption == "nature":
        donnees["directions"][-1]["nature"] = "sentinelle"
    elif corruption == "autorite":
        donnees["directions"][0]["autorite"] = "heure_et_azimut"
    else:
        donnees["version"] = 2
    chemin = tmp_path / "invalide.json"
    chemin.write_text(json.dumps(donnees), encoding="utf-8")
    with pytest.raises(ValueError):
        ReferentielSentinelles.charger(fichier_donnees=chemin)


def test_calendrier_gregorien_refuse(tmp_path):
    config = json.loads((RACINE / "config/cadran_national_v1.json").read_text(encoding="utf-8"))
    config["observation"]["calendrier"] = "gregorien"
    chemin = tmp_path / "invalide.json"
    chemin.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="Conventions"):
        ReferentielSentinelles.charger(fichier_configuration=chemin)


def test_temoins_et_statuts_ne_pilotent_pas_le_calcul(tmp_path, referentiel):
    donnees = json.loads((RACINE / "data/sentinelles_reference_v1.json").read_text(encoding="utf-8"))
    for definition in donnees["directions"]:
        definition["temoins"] = {"azimut_direct": 0, "heure_directe": "00:00:00",
                                 "azimut_miroir": 0, "heure_miroir": "00:00:00"}
        definition["statut"] = "temoin_documentaire_modifie_pour_le_test"
    chemin = tmp_path / "temoins_non_autoritaires.json"
    chemin.write_text(json.dumps(donnees), encoding="utf-8")
    autre = ReferentielSentinelles.charger(fichier_donnees=chemin)
    for ref in autre:
        original = referentiel.get(ref.identifiant)
        assert ref.directe == original.directe
        assert ref.miroir == original.miroir


def test_moteur_charge_sans_image_calibration_ou_interface_graphique():
    code = '''
import importlib.abc, sys
from pathlib import Path
class SansCartographie(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        interdits = ("src.carte_config", "src.affichage_objets", "src.data_loader", "src.Sentinelle", "tkinter", "cv2", "PIL")
        if any(fullname == nom or fullname.startswith(nom + ".") for nom in interdits):
            raise AssertionError("Import cartographique interdit : " + fullname)
sys.meta_path.insert(0, SansCartographie())
original = Path.open
def sans_carto(self, *args, **kwargs):
    if "carto" in self.parts:
        raise AssertionError("Accès cartographique interdit : " + str(self))
    return original(self, *args, **kwargs)
Path.open = sans_carto
from src.ReferentielSentinelles import ReferentielSentinelles
r = ReferentielSentinelles.charger()
assert r.get("S3").directe.branche == "apres_midi"
assert r.cadran_national.centre == "Coetquidan"
print("SANS_CARTE_OK")
'''
    resultat = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", code],
                              cwd=RACINE, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert resultat.returncode == 0, resultat.stdout + resultat.stderr
    assert "SANS_CARTE_OK" in resultat.stdout
