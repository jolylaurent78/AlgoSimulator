import math
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

import src.CadranNationalSentinelles as national_module
import src.AlgorithmeLumiereStyletInitial as lumiere
from src.CadranNationalSentinelles import SentinelleNationale, SelectionHoraire
from src.GeometrieCadran import azimutGrilleVersImage, LigneAzimutGrille
from src.ReferentielSentinelles import ReferentielSentinelles, HeureMoyenneLocale, ContexteObservation
from src.Sentinelle import Sentinelle
from src.carte_config import carteConfig, CarteConfig
from src.data_loader import villes_dict
from src.calculAstronomique import MyJulianDate, distanceAngulaire, convertirHeureLocaleVersUTC
from src.trace_export import convertir_objet_graphique


@pytest.fixture(scope="module")
def referentiel():
    return ReferentielSentinelles.charger()


@pytest.fixture
def national(referentiel):
    return SentinelleNationale(referentiel=referentiel)


@pytest.mark.parametrize("theta", [0, 45, 125.371, 270, 359.9])
@pytest.mark.parametrize("matrice", [np.diag([1, -1]), np.array([[2, .6], [-.4, -1.3]])])
def test_direction_grille_transformee_comme_deux_points_sans_offset(theta, matrice):
    carte = CarteConfig.__new__(CarteConfig)
    carte.A = matrice
    carte.offset = np.array([123456, -987654])
    origine = np.array([70, 80])
    direction = np.array([math.sin(math.radians(theta)), math.cos(math.radians(theta))])
    debut = np.array(carte.lambert93_to_pixels(*origine))
    fin = np.array(carte.lambert93_to_pixels(*(origine + 100 * direction)))
    attendu = (fin - debut) / np.linalg.norm(fin - debut)
    image = azimutGrilleVersImage(theta, carte.A)
    obtenu = [math.sin(math.radians(image)), -math.cos(math.radians(image))]
    assert obtenu == pytest.approx(attendu)
    carte.offset += 1000000
    assert azimutGrilleVersImage(theta, carte.A) == image


def test_ligne_nationale_recalcule_direction_et_centre_avec_carte_active(national, monkeypatch):
    ligne = national.afficherLigneMidi("design")
    centre = villes_dict["Coetquidan"].coordonneesLambert()
    assert (ligne.x_l93, ligne.y_l93) == centre
    assert ligne.orientation_grille == 125.371
    assert "national" in ligne.getNom()
    copie = ligne.copie()
    matrice = np.array([[.004, .0015], [-.0007, -.005]])
    monkeypatch.setattr(carteConfig, "A", matrice)
    monkeypatch.setattr(carteConfig, "A_inv", np.linalg.inv(matrice))
    monkeypatch.setattr(carteConfig, "offset", np.array([500, 45000]))
    for obj in (ligne, copie):
        obj.recalculerCoordonneesPixelAbs()
        assert obj.pointReference == pytest.approx(matrice @ centre + carteConfig.offset)
        assert obj.getAzimutCarte() == pytest.approx(azimutGrilleVersImage(125.371, matrice))
        assert obj.orientation_grille == 125.371
        assert convertir_objet_graphique(obj)["geometry"]["type"] == "line_image_azimuth"
    assert national.getOrigineStylet().coordonneesPixelAbs() == pytest.approx(ligne.pointReference)


@pytest.mark.parametrize("note", ["C", "E", "F", "G", "J"])
@pytest.mark.parametrize("branche", ["directe", "miroir"])
def test_ligne_horaire_recherche_legende_et_heure_concordent(national, note, branche):
    ref = national.par_note[note]
    direction = ref.directe if branche == "directe" else ref.miroir
    ligne = national.afficherLigneHoraire(note, branche, "design")
    angle = (125.371 + 180 - direction.azimut) % 360
    assert ligne.orientation_grille == pytest.approx(angle)
    assert ligne.getAzimutCarte() == pytest.approx(azimutGrilleVersImage(angle, carteConfig.A))
    assert branche in ligne.getNom() and direction.heure_locale.toString() in ligne.getNom()
    assert branche in ligne.getPrintLabel() and direction.heure_locale.toString() in ligne.getPrintLabel()
    assert ("après-midi" if direction.branche == "apres_midi" else "matin") in ligne.getNom()
    origine = np.array(national.getOrigineStylet().coordonneesPixelAbs())
    point = origine + 1000 * np.array(ligne.vecteur)
    resultat = national.rechercherLigneHoraire(*point)
    assert resultat.selection
    assert (resultat.note, resultat.branche) == (note, branche)
    assert resultat.heure_locale is direction.heure_locale
    assert resultat.azimut_image == pytest.approx(ligne.getAzimutCarte())
    assert resultat.distance_km == 0
    # La droite est non orientée : son autre demi-droite ne crée pas d'heure.
    oppose = national.rechercherLigneHoraire(*(2 * origine - point))
    assert (oppose.note, oppose.branche, oppose.heure_locale) == (note, branche, direction.heure_locale)


@pytest.mark.parametrize("distance,selection,km", [(19.999, True, 19), (20, False, 20), (20.999, False, 20)])
def test_distance_historique_tronquee_puis_comparaison_stricte(national, monkeypatch, distance, selection, km):
    national.pointCoetquidan = SimpleNamespace(coordonneesPixelAbs=lambda: (0, 0),
                                             pixelsVersMetres=lambda: 1000,
                                             recalculerCoordonneesPixelAbs=lambda: None)
    monkeypatch.setattr(national_module, "Ligne", SimpleNamespace(
        depuisPointEtAzimut=lambda *_args: SimpleNamespace(distanceAuPoint=lambda *_point: distance)))
    resultat = national.rechercherLigneHoraire(0, 0)
    assert resultat.distance_km == km
    assert resultat.selection is selection
    assert resultat.repere == "S1" and resultat.branche == "directe"  # égalités : premier candidat


def test_lampouy_isole_reutilise_ses_heures_et_sa_geometrie_historiques(national, monkeypatch):
    historique = Sentinelle("data/sentinelle.csv")
    methode = Sentinelle.calculerHeureSentinelle
    appels = []
    def calcul_lampouy(obj):
        appels.append(list(obj.fichierSentinelles))
        return methode(obj)
    monkeypatch.setattr(Sentinelle, "calculerHeureSentinelle", calcul_lampouy)
    assert set(national) == set("CDEFGABJ") and "L" not in national
    assert national["L"] == historique["L"]
    assert appels == [["Lampouy"]]
    for ampm in ("AM", "PM"):
        attendu = historique.afficherLigneHoraire("L", ampm, "design")
        obtenu = national.afficherLigneHoraire("L", ampm, "design")
        assert obtenu.getAzimutCarte() == pytest.approx(attendu.getAzimutCarte())
    # Mettre le candidat exactement sur la droite Lampouy : inclusion explicite.
    ligne = national.afficherLigneHoraire("L", "AM", "design")
    point = np.array(ligne.pointReference) + 1000 * np.array(ligne.vecteur)
    resultat = national.rechercherLigneHoraire(*point, inclureLampouy=True)
    assert resultat.repere == "Lampouy" and resultat.historique_lampouy
    assert national.rechercherLigneHoraire(*point).repere != "Lampouy"


def test_consommateurs_cadrans_migres_et_segment_historique():
    import src.AlgorithmeBaseCadran as base
    import src.AlgorithmeCadranFinal as final
    import src.AlgorithmeSegment as segment
    assert base.Sentinelle is final.Sentinelle is SentinelleNationale
    assert segment.Sentinelle is Sentinelle


@pytest.mark.parametrize("calendrier,lettre,notes", [
    ("Standard", "C", {"=": "C", "+2": "E", "-2": "A", "Clef": "F", "11:00": "J"}),
    ("Déclinaison", "F", {"=": "F", "+2": "A", "-2": "D", "Clef": "C", "11:00": "J"}),
])
@pytest.mark.parametrize("choix", ["=", "+2", "-2", "Clef", "11:00"])
@pytest.mark.parametrize("ampm", ["AM", "PM"])
def test_choix_manuels_calendriers_et_substitutions(national, monkeypatch, calendrier, lettre, notes, choix, ampm):
    monkeypatch.setattr(lumiere, "Sentinelle", lambda _chemin: national)
    module = lumiere.HeureDateObservation()
    module.lettreDomObservation, module.lettreDeclDataset = "C", "F"
    module.choixCalendrier, module.choixHeure, module.heureAMPM = calendrier, choix, ampm
    module.calculer()
    ref = national.par_note[notes[choix]]
    attendu = next(d for d in (ref.directe, ref.miroir) if d.branche == ("matin" if ampm == "AM" else "apres_midi"))
    assert module.lettreChoix == lettre
    assert module.heureLocaleSecondes == attendu.heure_locale.secondes
    assert module.heureLocale == attendu.heure_locale.toString()


def selection(national, note, branche, valide=True):
    direction = national.directionPourNote(note, branche)
    return SelectionHoraire(valide, national.par_note[note].identifiant, note, branche, direction.branche,
                            direction.heure_locale, direction.azimut, national.orientationGrille(direction.azimut),
                            azimutGrilleVersImage(national.orientationGrille(direction.azimut), carteConfig.A), 1)


def soleil_pret(national, monkeypatch, resultat):
    monkeypatch.setattr(lumiere, "Sentinelle", lambda _chemin: national)
    monkeypatch.setattr(national, "rechercherLigneHoraire", Mock(return_value=resultat))
    module = lumiere.Soleil()
    module.dateDataset = "15/08/778"
    module.stylet = "Roncevaux"
    module.lieuObservationObservation = "Roncevaux"
    module.sourceHeure = "Stylet"
    module._sourceHeureInitiale = False
    return module


@pytest.mark.parametrize("note", list("CDEFGABJ"))
@pytest.mark.parametrize("branche", ["directe", "miroir"])
@pytest.mark.parametrize("choix", ["Même heure", "Symétrique"])
def test_lumiere_meme_heure_ou_autre_branche_sans_double_symetrie(national, monkeypatch, note, branche, choix):
    resultat = selection(national, note, branche)
    module = soleil_pret(national, monkeypatch, resultat)
    module.choixHeure = choix
    module.calculer()
    autre = "miroir" if branche == "directe" else "directe"
    attendu = national.heurePourNote(note, branche if choix == "Même heure" else autre)
    assert module.heureObservationSecondes == attendu.secondes
    assert module.heureObservation == attendu.toString()
    assert module.ampmStylet == resultat.ampm
    assert module.heureAMPM == (resultat.ampm if choix == "Même heure" else ("PM" if resultat.ampm == "AM" else "AM"))
    lat, lon = villes_dict["Roncevaux"].getCoordonneesGPS()
    jd = ContexteObservation("Roncevaux", lat, lon, "15/08/778").versUT1(attendu)
    assert module.dateObservationUT1 == jd
    assert module.dateObservationUT1.enTuple() == (778, 8, 15)


def test_secondes_fractionnaires_transmises_au_calcul_solaire_du_lieu_reel(national, monkeypatch):
    module = soleil_pret(national, monkeypatch, selection(national, "E", "directe"))
    module.lieuObservationObservation = "Bourges"
    module.choixHeure = "Même heure"
    module.calculer()
    assert module.heureObservationSecondes != round(module.heureObservationSecondes)
    stylet = lumiere.Stylet()
    stylet.setup()
    stylet.dateDataset = module.dateDataset
    stylet.styletSoleil = module.stylet
    stylet.lettreDomObservation = "C"
    stylet.lieuObservationObservation = "Bourges"
    stylet.rotationCarteObservation = 10
    stylet.heureUTCSoleil = module.heureUTC
    stylet.dateObservationUT1Soleil = module.dateObservationUT1
    calcul = Mock(return_value=(45, 120))
    monkeypatch.setattr(lumiere, "positionSoleil", calcul)
    stylet.calculer()
    assert calcul.call_args.args[0] == villes_dict["Bourges"].getCoordonneesGPS()
    assert calcul.call_args.args[1] is module.dateObservationUT1
    depuis_presentation = MyJulianDate.fromString(module.dateDataset, module.heureUTC)
    assert abs(float(depuis_presentation) - float(module.dateObservationUT1)) * 86400 > 0.1


def test_source_manuelle_survit_a_un_stylet_refuse_sans_changer_calendrier(national, monkeypatch):
    module = soleil_pret(national, monkeypatch, selection(national, "E", "directe", valide=False))
    module.sourceHeure = "Manuel"
    heure = national.heurePourNote("F", "AM")
    module.heureLocaleHeuredate = heure.toString()
    module.heureLocaleSecondesHeuredate = heure.secondes
    module.calculer()
    assert module.validite == "Unvalide"
    assert module.heureSentinelle is None
    assert module.heureObservationSecondes == heure.secondes


@pytest.mark.parametrize("miroir", [False, True])
def test_options_lampouy_et_conversion_historique_preservees(national, monkeypatch, miroir):
    module = soleil_pret(national, monkeypatch, selection(national, "C", "directe"))
    module.dateDataset = "18/05/1152"
    options = module.getValeursChoixHeure()
    assert options[:2] == ["Même heure", "Symétrique"]
    module.choixHeure = options[3 if miroir else 2]
    module.calculer()
    lon = villes_dict[module.lieuObservationObservation].getCoordonneesGPS()[1]
    attendu = convertirHeureLocaleVersUTC(module.choixHeure + ":00", lon)
    assert module.heureUTC == attendu
    assert module.dateObservationUT1 == MyJulianDate.fromString(module.dateDataset, attendu)
