"""Projections Segment : contrats numériques, recherche et interface dynamique."""
import math
from pathlib import Path
from unittest.mock import Mock

import pytest

import src.calculAstronomique as astro
import src.AlgorithmeSegment as segment
from src.IHMAlgorithme import IHMAlgorithme


@pytest.mark.parametrize("projection", astro.PROJECTIONS_HELIOCENTRIQUES)
def test_origine_annuelle_terre_equinoxe(projection):
    equinoxe, _ = astro.trouverDatesPourDeclinaison(0, 1365)
    assert astro.azimutHeliocentrique(equinoxe, "Terre", 1365, projection) == 0


def test_ecliptique_j2000_projette_les_vecteurs_geometriques_dans_le_plan_fixe():
    # Rotation indépendante autour de X par l'obliquité J2000 (Skyfield).
    # Choisir une planète inclinée et une date éloignée de J2000 distingue
    # nettement XY équatorial, écliptique de la date et écliptique J2000.
    jd = astro.MyJulianDate(12, 10, 1365)
    equinoxe, _ = astro.trouverDatesPourDeclinaison(0, 1365)
    epsilon = math.radians(84381.448 / 3600)

    def longitude(date, planete):
        t = astro.ts.ut1_jd(float(date))
        x, y, z = (astro.ASTRES[planete] - astro.sun).at(t).position.km
        return math.degrees(math.atan2(y * math.cos(epsilon) + z * math.sin(epsilon), x))

    attendu = (longitude(jd, "Pluton") - longitude(equinoxe, "Terre")) % 360
    obtenu = astro.azimutHeliocentrique(jd, "Pluton", 1365, astro.PROJECTION_ECLIPTIQUE_J2000)
    assert obtenu == pytest.approx(attendu, abs=1e-9)
    equatorial = astro.azimutHeliocentrique(jd, "Pluton", 1365)
    assert astro.distanceAngulaire(obtenu, equatorial) > 1

    def longitude_date(date, planete):
        t = astro.ts.ut1_jd(float(date))
        return (astro.ASTRES[planete] - astro.sun).at(t).frame_latlon(astro.ecliptic_frame)[1].degrees

    de_la_date = (longitude_date(jd, "Pluton") - longitude_date(equinoxe, "Terre")) % 360
    assert astro.distanceAngulaire(obtenu, de_la_date) > 0.001


def test_equatorial_conserve_le_calcul_historique():
    jd = astro.MyJulianDate(12, 10, 1365)
    equinoxe, _ = astro.trouverDatesPourDeclinaison(0, 1365)

    def angle(date, planete):
        x, y, _ = astro.sun.at(astro.ts.ut1_jd(float(date))).observe(astro.ASTRES[planete]).position.km
        return math.degrees(math.atan2(y, x)) % 360

    attendu = (angle(jd, "Uranus") - angle(equinoxe, "Terre")) % 360
    assert astro.azimutHeliocentrique(jd, "Uranus", 1365, astro.PROJECTION_EQUATORIALE) == pytest.approx(attendu, abs=1e-12)


@pytest.mark.parametrize("cible", [0, 0.01, 359.99, 360, -0.01, 90, 180])
@pytest.mark.parametrize("projection", astro.PROJECTIONS_HELIOCENTRIQUES)
def test_recherche_date_reelle_utilise_la_projection_et_le_cercle(cible, projection):
    date = astro.trouverDatePourAzimut(cible, 1365, projection=projection, precision_heures=0.1)
    assert date.enTuple()[0] == 1365
    angle = astro.azimutHeliocentrique(date, "Terre", 1365, projection)
    assert astro.distanceAngulaire(angle, cible) < 0.005
    # L'accélération avec la date centrale doit retrouver le même passage.
    centree = astro.trouverDatePourAzimut(cible, 1365, jd_centre=date, projection=projection, precision_heures=0.1)
    assert abs(float(centree) - float(date)) < 0.1 / 24


@pytest.mark.parametrize("angle,cible,attendu", [(359, 1, 2), (1, 359, 2), (360, 0, 0), (-1, 1, 2), (0, 180, 180)])
def test_distance_angulaire_circulaire(angle, cible, attendu):
    assert astro.distanceAngulaire(angle, cible) == attendu


@pytest.mark.parametrize("projection", astro.PROJECTIONS_HELIOCENTRIQUES)
@pytest.mark.parametrize("orientation", [-1, 1])
@pytest.mark.parametrize("tolerance,accepte", [("2.5", False), ("5.0", True)])
def test_annees_transmet_projection_et_tolerance_et_affiche_erreur_circulaire(monkeypatch, projection, orientation, tolerance, accepte):
    module = segment.PlaneteAnnee()
    module.projection = projection
    module.tolerance = tolerance  # Les combos Tk transmettent des chaînes.
    module.azimutAxeterre = 10
    module.angleAnalyse = 11
    module.planetePlanete = "Uranus"
    dates = Mock(side_effect=lambda az, annee, **kw: astro.MyJulianDate(1 if az == 10 else 2, 1, annee))
    # Chaque cible est à 3°, dont l'une au passage 0°/360°.
    positions = Mock(side_effect=lambda jd, *args, **kw: ((10 if jd.enTuple()[2] == 1 else 190) + orientation * 11 + 3) % 360)
    monkeypatch.setattr(segment, "trouverDatePourAzimut", dates)
    monkeypatch.setattr(segment, "azimutHeliocentrique", positions)
    module.calculerAnnees(True)
    assert dates.call_count == 0
    module.calculerAnnees(False)
    assert dates.call_count == positions.call_count == 2
    assert [c.args[0] for c in dates.call_args_list] == [10, 190]
    assert all(c.kwargs["projection"] == projection for c in dates.call_args_list + positions.call_args_list)
    assert len(module.listeAnnees) == (2 if accepte else 0)
    if accepte:
        assert [r[2] for r in module.listeAnnees] == ["Identique", "Opposé"]
        assert all(r[-1] == "3.00°" for r in module.listeAnnees)


def test_projection_inconnue_et_precision_invalide():
    jd = astro.MyJulianDate(1, 1, 1365)
    with pytest.raises(ValueError, match="Projection"):
        astro.azimutHeliocentrique(jd, "Terre", projection="inconnue")
    with pytest.raises(ValueError, match="précision"):
        astro.trouverDatePourAzimut(0, 1365, precision_heures=0)


def test_interface_propose_les_nouveaux_choix_sans_lancer_de_recherche(monkeypatch):
    import tkinter as tk
    import src.IHMAlgorithme as ihm_module

    module = segment.PlaneteAnnee()
    recherche = Mock()
    monkeypatch.setattr(module, "calculerAnnees", recherche)
    # Construire les vrais combos Tk depuis la configuration, vérifier leurs
    # valeurs initiales et exercer les callbacks avec un interpréteur Tk caché.
    root = tk.Tk()
    root.withdraw()
    try:
        ihm = IHMAlgorithme.__new__(IHMAlgorithme)
        ihm.parametres_widgets = {}
        ihm.attributsModulesAffichés = []
        ihm.moteurAlgo = Mock()
        ihm.moteurAlgo.getParametre.side_effect = lambda m, a: module.getParametre(a)
        ihm.moteurAlgo.getValeursParametre.side_effect = lambda m, a: module.getValeursParametre(a)
        ihm.updateModuleEtInterface = Mock(side_effect=lambda m, a, v: module.setParametre(a, v))
        lignes = ihm.parser_csv(str(Path("config/AlgorithmeSegment.csv")))
        choix = [r for r in lignes if r.get("Module") == "annee" and r.get("Widget") == "combo"]
        assert len(choix) == 4
        assert all(r["Section"] == "Recherche de l'année" and r["Widget"] == "combo" for r in choix)
        champs = {c["Attribut"]: c for c in choix}
        assert champs["borneMin"]["Ligne"] == champs["periode"]["Ligne"] == "8"
        assert champs["projection"]["Ligne"] == champs["tolerance"]["Ligne"] == "9"
        for numero in ("8", "9"):
            frame = ihm_module.ttk.Frame(root)
            frame.pack(anchor="w")
            ihm.ajouter_ligne_widgets(frame, [c for c in choix if c["Ligne"] == numero])
        root.update_idletasks()
        assert all(f.winfo_reqwidth() <= 530 for f in root.winfo_children())
        assert ihm.parametres_widgets["annee.projection"].get() == astro.PROJECTION_ECLIPTIQUE_J2000
        assert float(ihm.parametres_widgets["annee.tolerance"].get()) == 2.5
        combos = [w for f in root.winfo_children() for c in f.winfo_children()
                  for w in c.winfo_children() if isinstance(w, ihm_module.ttk.Combobox)]
        assert [int(c["width"]) for c in combos] == [5, 5, 18, 5]
        assert all(str(c["state"]) == "readonly" for c in combos)
        assert tuple(map(int, combos[0]["values"])) == tuple(module.getValeursBorneMin())
        assert tuple(map(int, combos[1]["values"])) == tuple(module.getValeursPeriode())
        assert tuple(combos[2]["values"]) == astro.PROJECTIONS_HELIOCENTRIQUES
        assert tuple(map(float, combos[3]["values"])) == (2.5, 5)
        # Exercer la sélection des quatre listes et leurs callbacks réels Tk.
        for combo, valeur in zip(combos, (1300, 200, astro.PROJECTION_EQUATORIALE, 5.0)):
            valeurs = tuple(map(str, combo["values"]))
            combo.current(valeurs.index(str(valeur)))
        assert int(module.borneMin) == 1300
        assert int(module.periode) == 200
        assert module.projection == astro.PROJECTION_EQUATORIALE
        assert float(module.tolerance) == 5
        assert ihm.updateModuleEtInterface.call_count == 4
        recherche.assert_not_called()
    finally:
        root.destroy()


@pytest.mark.parametrize("field_type,largeur", [("shorttext", 15), ("longtext", 40), ("int", 5)])
def test_combo_sans_largeur_specifique_conserve_la_largeur_historique(field_type, largeur):
    import tkinter as tk
    import src.IHMAlgorithme as ihm_module

    root = tk.Tk()
    root.withdraw()
    try:
        ihm = IHMAlgorithme.__new__(IHMAlgorithme)
        ihm.parametres_widgets = {}
        ihm.moteurAlgo = Mock()
        ihm.moteurAlgo.getParametre.return_value = "A"
        ihm.moteurAlgo.getValeursParametre.return_value = ("A", "B")
        ihm.updateModuleEtInterface = Mock()
        ihm.ajouter_ligne_widgets(root, [{"Widget": "combo", "FieldType": field_type,
                                        "Module": "autre", "Attribut": "choix"}])
        combo = next(w for c in root.winfo_children() for w in c.winfo_children()
                     if isinstance(w, ihm_module.ttk.Combobox))
        assert int(combo["width"]) == largeur
        assert tuple(combo["values"]) == ("A", "B")
        combo.current(1)
        ihm.updateModuleEtInterface.assert_called_once_with("autre", "choix", "B")
    finally:
        root.destroy()
