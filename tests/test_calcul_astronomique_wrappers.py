from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

import src.calculAstronomique as astro
from src.calculAstronomique import MyJulianDate


def test_decalages_musicaux_et_mapping_indexes_respectent_les_cycles():
    assert astro.decalageGamme("C") == ("C", "A", "E", "F")
    assert astro.decalageGamme("B") == ("B", "G", "D", "B")
    assert astro.decalage2Notes("C", "-2") == "A"
    assert astro.decalage2Notes("D", "+2G") == "G"
    assert astro.decalage2Notes("E", "+2G") == "F"
    assert astro.genererMappingIndexes(range(7), 3, True)["C"] == [6]
    assert astro.getIndexesPourNote("C", range(7)) == [0, 6, 2, 1]
    with pytest.raises(ValueError, match="Note inconnue"):
        astro.decalage2Notes("H", "+2")


def test_decalage_de_jours_valide_les_jours_et_boucle_sur_la_semaine():
    assert astro.decalage2Jours("Lun", "-2") == "Sam"
    assert astro.decalage2Jours("Sam", "+2") == "Lun"
    with pytest.raises(ValueError):
        astro.decalage2Jours("Inconnu", "+2")


@pytest.mark.parametrize(
    ("heure", "longitude", "inverse", "attendu"),
    [
        ("12:00", 0, False, "12:00:00"),
        ("12:00:00", 3, False, "11:48:00"),
        ("12:00:00", -3, False, "12:12:00"),
        ("00:05:00", 3, False, "23:53:00"),
        ("23:55:00", -3, False, "00:07:00"),
    ],
)
def test_conversion_heure_locale_utc_gere_longitude_et_minuit(heure, longitude, inverse, attendu):
    assert astro.convertirHeureLocaleVersUTC(heure, longitude, inverse) == attendu


def test_conversion_heure_utc_locale_est_un_roundtrip_et_refuse_formats_invalides():
    utc = astro.convertirHeureLocaleVersUTC("09:17:42", 3.25)
    assert astro.convertirHeureLocaleVersUTC(utc, 3.25, inverse=True) == "09:17:42"
    for heure in ("12", "01:02:03:04", "aa:bb"):
        with pytest.raises(ValueError):
            astro.convertirHeureLocaleVersUTC(heure, 0)


@pytest.mark.parametrize(
    ("heure", "attendu"),
    [("09:43", "14:17"), ("10:00", "14:00"), ("12:00", "12:00"), ("00:01", "23:59"), ("00:00", "00:00")],
)
def test_heure_symetrique_reste_dans_le_format_hhmm(heure, attendu):
    assert astro.heureSymetrique(heure) == attendu


def test_julian_date_construction_arithmetique_et_conversion_depuis_jd():
    historique = MyJulianDate(12, 10, 1365, "00:00:00")
    moderne = MyJulianDate(1, 1, 2024, "12:00:00")

    assert historique.enTuple() == (1365, 10, 12)
    assert moderne.enTuple() == (2024, 1, 1)
    assert MyJulianDate.fromJD(float(moderne)).enTuple() == (2024, 1, 1)
    assert moderne + 2 - 2 == moderne
    assert moderne - historique == pytest.approx(float(moderne) - float(historique))
    assert historique < moderne


def test_julian_date_frontiere_1582_et_formats_arrondis():
    julienne = MyJulianDate.fromString("04/10/1582", "23:59:29")
    gregorienne = MyJulianDate.fromString("15/10/1582", "23:59:30")

    assert julienne.enTuple() == (1582, 10, 4)
    assert gregorienne.enTuple() == (1582, 10, 15)
    assert float(gregorienne) - float(julienne) == pytest.approx(1 + 1 / 86400)
    assert julienne.toString("JJ/MM/AAAA") == "04/10/1582"
    assert gregorienne.toString("HH:MM") == "00:00"
    assert gregorienne.toString("ISO").startswith("1582-10-15T23:59:30")
    assert MyJulianDate.fromString("01/01/2024", "00:00:00").toString("ISO") == "2024-01-01T00:00:00"
    with pytest.raises(ValueError, match="Format de date invalide"):
        MyJulianDate.fromString("1582-10-15")


@pytest.mark.parametrize(
    ("date", "bissextile"),
    [("01/01/1364", True), ("01/01/1900", False), ("01/01/2000", True), ("01/01/2024", True)],
)
def test_jours_semaine_bissextiles_et_lettres_dominicales(date, bissextile):
    assert MyJulianDate.fromString(date).estBissextile() is bissextile


def test_jour_semaine_et_lettre_dominicale_suivent_la_convention_du_projet():
    assert MyJulianDate.fromString("01/01/2024").jourSemaine() == "Lun"
    assert MyJulianDate.fromString("12/10/1365").jourSemaine() == "Dim"
    assert MyJulianDate.fromString("28/02/2024").lettreDominicale() == "C"
    assert MyJulianDate.fromString("01/03/2024").lettreDominicale() == "D"


@pytest.mark.parametrize(
    ("date", "opposee"),
    [("01/01/2023", "03/07/2023"), ("03/07/2023", "02/01/2023"), ("01/01/2024", "02/07/2024")],
)
def test_date_six_mois_suit_le_decalage_182_183_jours_implemente(date, opposee):
    assert MyJulianDate.fromString(date).date6Mois().toString("JJ/MM/AAAA") == opposee


def test_coords_proches_respecte_la_tolerance_inclusive():
    origine = (48.0, 2.0)
    tolerance = astro.COORD_TOLERANCE_DEG
    assert astro.coordsProches(origine, origine)
    assert astro.coordsProches(origine, (48.0 + tolerance / 2, 2.0))
    assert astro.coordsProches(origine, (48.0 + tolerance, 2.0))
    assert not astro.coordsProches(origine, (48.0 + 2 * tolerance, 2.0))


class FauxAngle:
    def __init__(self, degrees):
        self.degrees = degrees


class FauxAstrometrique:
    def __init__(self, altitude=12.5, azimut=210.25):
        self.altitude = altitude
        self.azimut = azimut

    def apparent(self):
        return self

    def altaz(self):
        return FauxAngle(self.altitude), FauxAngle(self.azimut), None


class FauxObservateur:
    def __init__(self, journal, astrometrique):
        self.journal = journal
        self.astrometrique = astrometrique

    def at(self, instant):
        self.journal.append(("at", instant))
        return self

    def observe(self, astre):
        self.journal.append(("observe", astre))
        return self.astrometrique


class FauxTerre:
    def __init__(self, journal, astrometrique):
        self.observateur = FauxObservateur(journal, astrometrique)

    def __add__(self, lieu):
        self.observateur.journal.append(("lieu", lieu))
        return self.observateur


class FauxTs:
    def __init__(self):
        self.ut1 = []

    def ut1_jd(self, jd):
        self.ut1.append(jd)
        return jd


class FauxJD:
    def __init__(self, valeur, date="01/01/2000", annee=2000):
        self.valeur = valeur
        self.date = date
        self.annee = annee

    def __float__(self):
        return float(self.valeur)

    def toString(self, _format):
        return self.date

    def enTuple(self):
        return self.annee, 1, 1


def installer_position_factice(monkeypatch, altitude=12.5, azimut=210.25):
    journal = []
    ts = FauxTs()
    monkeypatch.setattr(astro, "ts", ts)
    monkeypatch.setattr(astro, "Topos", lambda **kwargs: kwargs)
    monkeypatch.setattr(astro, "earth", FauxTerre(journal, FauxAstrometrique(altitude, azimut)))
    return journal, ts


def test_position_soleil_et_astre_transmettent_coordonnees_jd_et_astre(monkeypatch):
    journal, ts = installer_position_factice(monkeypatch)
    jd = FauxJD(123.5)
    astre = object()

    assert astro.positionSoleil((48.1, 2.2), jd) == (12.5, 210.25)
    assert astro.positionAstre((48.1, 2.2), jd, astre) == (12.5, 210.25)
    assert ts.ut1 == [123.5, 123.5]
    assert journal[0] == ("lieu", {"latitude_degrees": 48.1, "longitude_degrees": 2.2})
    assert ("observe", astro.sun) in journal
    assert ("observe", astre) in journal


@pytest.mark.parametrize(
    ("coordonnees", "date", "astre_pluton", "attendu_hack"),
    [
        ((49 + 55 / 60 + 21 / 3600 + 5e-10, 1 + 4 / 60 + 42 / 3600 - 5e-10), "12/10/1365", True, True),
        ((49 + 55 / 60 + 21 / 3600 + 2e-9, 1 + 4 / 60 + 42 / 3600), "12/10/1365", True, False),
        ((49 + 55 / 60 + 21 / 3600, 1 + 4 / 60 + 42 / 3600), "12/10/1365", False, False),
        ((49 + 55 / 60 + 21 / 3600, 1 + 4 / 60 + 42 / 3600), "11/10/1365", True, False),
    ],
)
def test_hack_pluton_dieppe_est_limite_coordonnees_astre_et_date(monkeypatch, coordonnees, date, astre_pluton, attendu_hack):
    installer_position_factice(monkeypatch, altitude=1, azimut=2)
    pluton = object()
    monkeypatch.setattr(astro, "ASTRES", {"Pluton": pluton})
    astre = pluton if astre_pluton else object()

    resultat = astro.positionAstre(coordonnees, FauxJD(1, date), astre)

    assert resultat == ((46 + 46 / 60 + 54 / 3600, 106 + 34 / 60 + 37 / 3600) if attendu_hack else (1.0, 2.0))


class FauxTempsEvenement:
    def __init__(self, ut1):
        self.ut1 = ut1


def test_wrappers_lever_coucher_zenith_respectent_fenetres_et_evenements(monkeypatch):
    ts = FauxTs()
    latlon = Mock(return_value="observateur")
    monkeypatch.setattr(astro, "ts", ts)
    monkeypatch.setattr(astro, "wgs84", SimpleNamespace(latlon=latlon))
    monkeypatch.setattr(astro, "sunrise_sunset", Mock(return_value="soleil"))
    monkeypatch.setattr(astro, "meridian_transits", Mock(return_value="transit"))
    appels = []

    def find(t0, t1, evenement):
        appels.append((t0, t1, evenement))
        valeurs = {"soleil": ([FauxTempsEvenement(9.6), FauxTempsEvenement(10.2)], [1, 0]), "transit": ([FauxTempsEvenement(10.1)], [1])}
        return valeurs[evenement]

    monkeypatch.setattr(astro, "find_discrete", find)
    jd = FauxJD(10)

    assert float(astro.calculLeverSoleil((48, 2), jd)) == 9.6
    assert float(astro.calculCoucherSoleil((48, 2), jd)) == 10.2
    assert float(astro.calculZenithSoleil((48, 2), jd)) == 10.1
    assert appels == [(9.5, 10, "soleil"), (10, 10.5, "soleil"), (9.5, 10.5, "transit")]
    assert latlon.call_args_list == [call(48, 2), call(48, 2), call(48, 2)]


@pytest.mark.parametrize("fonction", [astro.calculLeverSoleil, astro.calculCoucherSoleil, astro.calculZenithSoleil])
def test_wrappers_evenements_signalent_labsence_devenement(monkeypatch, fonction):
    monkeypatch.setattr(astro, "ts", FauxTs())
    monkeypatch.setattr(astro, "wgs84", SimpleNamespace(latlon=lambda *_args: "observateur"))
    monkeypatch.setattr(astro, "sunrise_sunset", lambda *_args: "soleil")
    monkeypatch.setattr(astro, "meridian_transits", lambda *_args: "transit")
    monkeypatch.setattr(astro, "find_discrete", lambda *_args: ([], []))

    with pytest.raises(RuntimeError):
        fonction((48, 2), FauxJD(10))


class FauxTerreAltitude:
    def __init__(self, hauteur, azimut=None):
        self.hauteur = hauteur
        self.azimut = azimut

    def __add__(self, _lieu):
        return self

    def at(self, instant):
        self.instant = instant
        return self

    def observe(self, _astre):
        return self

    def apparent(self):
        return self

    def altaz(self):
        azimut = self.azimut(self.instant) if self.azimut else 0
        return FauxAngle(self.hauteur(self.instant)), FauxAngle(azimut), None


def test_recherches_lever_astre_et_heure_azimut_raffinent_un_passage(monkeypatch):
    monkeypatch.setattr(astro, "Topos", lambda **kwargs: kwargs)
    monkeypatch.setattr(astro, "ts", FauxTs())
    monkeypatch.setattr(astro, "DEFAULT_PRECISION", 1e-6)
    monkeypatch.setattr(astro, "earth", FauxTerreAltitude(lambda t: t - 10))

    lever = astro.calculLeverAstre((48, 2), FauxJD(10), object(), altitude_lever=0)

    monkeypatch.setattr(astro, "calculLeverSoleil", lambda *_args: MyJulianDate.fromJD(0))
    monkeypatch.setattr(astro, "calculCoucherSoleil", lambda *_args: MyJulianDate.fromJD(1))
    monkeypatch.setattr(astro, "earth", FauxTerreAltitude(lambda _t: 10, azimut=lambda t: t * 360))
    heure = astro.calculHeurePourAzimutSoleil((48, 2), FauxJD(0), 90, altitude_min=0)

    assert float(lever) == pytest.approx(10, abs=1e-5)
    assert float(heure) == pytest.approx(0.25, abs=1e-5)


def test_recherches_lever_astre_et_heure_azimut_signalent_labsence_de_passage(monkeypatch):
    monkeypatch.setattr(astro, "Topos", lambda **kwargs: kwargs)
    monkeypatch.setattr(astro, "ts", FauxTs())
    monkeypatch.setattr(astro, "earth", FauxTerreAltitude(lambda _t: -5, azimut=lambda _t: 0))
    monkeypatch.setattr(astro, "calculLeverSoleil", lambda *_args: MyJulianDate.fromJD(0))
    monkeypatch.setattr(astro, "calculCoucherSoleil", lambda *_args: MyJulianDate.fromJD(0.02))

    with pytest.raises(RuntimeError):
        astro.calculLeverAstre((48, 2), FauxJD(0), object(), altitude_lever=0)
    with pytest.raises(RuntimeError):
        astro.calculHeurePourAzimutSoleil((48, 2), FauxJD(0), 90, altitude_min=0)


class FauxAstrometriqueEcliptique:
    def __init__(self, longitude):
        self.longitude = longitude

    def apparent(self):
        return self

    def frame_latlon(self, _frame):
        return None, FauxAngle(self.longitude), None


class FauxTerreEcliptique:
    def __init__(self, longitude):
        self.astrometrique = FauxAstrometriqueEcliptique(longitude)

    def at(self, _instant):
        return self

    def observe(self, _astre):
        return self.astrometrique


def test_declinaison_et_longitude_ecliptique_sont_des_wrappers_normalises(monkeypatch):
    monkeypatch.setattr(astro, "ts", FauxTs())
    monkeypatch.setattr(astro, "earth", FauxTerreEcliptique(-90))

    assert astro.declinaisonSoleil(FauxJD(2451545.0)) == pytest.approx(-23.43929111)
    assert astro.longitudeEcliptiqueSoleil(FauxJD(2451545.0)) == pytest.approx(270)


def test_solstice_almanac_selectionne_levenement_ete_et_propage_declinaison(monkeypatch):
    utc = Mock(side_effect=lambda *args: args)
    instant = FauxTempsEvenement(2459000.25)
    declinaison = Mock(return_value=23.4)
    monkeypatch.setattr(astro, "ts", SimpleNamespace(utc=utc))
    monkeypatch.setattr(astro, "almanac", SimpleNamespace(seasons=lambda _eph: "saisons", find_discrete=lambda *_args: ([instant], [1])))
    monkeypatch.setattr(astro, "declinaisonSoleil", declinaison)

    date, valeur = astro.trouverSolsticeEteAvecAlmanac(2024)

    assert float(date) == 2459000.25
    assert valeur == 23.4
    assert utc.call_args_list == [call(2024, 6, 1), call(2024, 7, 15)]
    declinaison.assert_called_once_with(date)


def test_solstice_almanac_sans_evenement_echoue_explicitement(monkeypatch):
    monkeypatch.setattr(astro, "ts", SimpleNamespace(utc=lambda *args: args))
    monkeypatch.setattr(astro, "almanac", SimpleNamespace(seasons=lambda _eph: "saisons", find_discrete=lambda *_args: ([], [])))

    with pytest.raises(RuntimeError, match="Pas de solstice"):
        astro.trouverSolsticeEteAvecAlmanac(2024)


def test_recherche_dates_declinaison_renvoie_les_deux_minima_synthetiques(monkeypatch):
    printemps = float(MyJulianDate(20, 4, 2024))
    ete = float(MyJulianDate(20, 8, 2024))
    monkeypatch.setattr(
        astro,
        "declinaisonSoleil",
        lambda jd: min(abs(float(jd) - printemps), abs(float(jd) - ete)),
    )

    date_printemps, date_ete = astro.trouverDatesPourDeclinaison(0.0, 2024)

    assert float(date_printemps) == pytest.approx(printemps, abs=1 / 24)
    assert float(date_ete) == pytest.approx(ete, abs=1 / 24)
    assert date_printemps < date_ete


class FauxPosition:
    def __init__(self, vecteur):
        self.position = SimpleNamespace(km=vecteur)


class FauxSoleilPositions:
    def __init__(self, vecteurs):
        self.vecteurs = vecteurs
        self.instants = []

    def at(self, instant):
        self.instants.append(instant)
        return self

    def observe(self, astre):
        return FauxPosition(self.vecteurs[astre])


def test_azimut_heliocentrique_utilise_le_cache_equinoxe_et_normalise(monkeypatch):
    terre = object()
    mars = object()
    soleil = FauxSoleilPositions({terre: (1, 0, 0), mars: (0, -1, 0)})
    recherche = Mock(return_value=(FauxJD(100, annee=2024), None))
    monkeypatch.setattr(astro, "ASTRES", {"Terre": terre, "Mars": mars})
    monkeypatch.setattr(astro, "sun", soleil)
    monkeypatch.setattr(astro, "ts", FauxTs())
    monkeypatch.setattr(astro, "memo_equinoxes", {})
    monkeypatch.setattr(astro, "trouverDatesPourDeclinaison", recherche)

    assert astro.azimutHeliocentrique(FauxJD(110, annee=2024), "Mars") == pytest.approx(270)
    assert astro.azimutHeliocentrique(FauxJD(111, annee=2024), "Mars", annee=2024) == pytest.approx(270)
    recherche.assert_called_once_with(0.0, 2024)


@pytest.mark.parametrize(
    ("vecteur", "attendu"),
    [((1, 0, 0), 0), ((0, 1, 0), 90), ((-1, -1, 0), 225)],
)
def test_azimut_heliocentrique_j2000_normalise_les_quadrants(monkeypatch, vecteur, attendu):
    planete = object()
    monkeypatch.setattr(astro, "ASTRES", {"Mars": planete})
    monkeypatch.setattr(astro, "sun", FauxSoleilPositions({planete: vecteur}))
    monkeypatch.setattr(astro, "ts", FauxTs())

    assert astro.azimutHeliocentriqueJ2000(FauxJD(10), "Mars") == pytest.approx(attendu)


def test_recherche_date_pour_azimut_balaye_et_raffine_autour_du_centre(monkeypatch):
    monkeypatch.setattr(astro, "azimutHeliocentrique", lambda jd, *_args: float(jd) - 100)

    resultat = astro.trouverDatePourAzimut(10, 2024, jd_centre=FauxJD(100), marge_jours=20, precision_heures=0.1)

    assert float(resultat) == pytest.approx(110, abs=0.1 / 24)


def test_recherche_alignements_couvre_cas_direct_et_oppose(monkeypatch):
    appels = []

    def trouver_date(azimut, annee, planete, jd_centre=None):
        appels.append((azimut, annee, planete, jd_centre))
        return MyJulianDate(1 if azimut < 180 else 2, 1, annee)

    def azimut_planete(jd, _planete, _annee):
        return 15 if jd.enTuple()[2] == 1 else 195

    monkeypatch.setattr(astro, "trouverDatePourAzimut", trouver_date)
    monkeypatch.setattr(astro, "azimutHeliocentrique", azimut_planete)

    resultats = astro.trouverAnneesAlignement("Mars", 10, 5, 0.01, 2024, 2025)

    assert [(resultat["annee"], resultat["cas"]) for resultat in resultats] == [
        (2024, "direct"), (2024, "opposition"), (2025, "direct"), (2025, "opposition")
    ]
    assert appels[0][3] is None and appels[1][3] is None
    assert appels[2][3] is not None and appels[3][3] is not None
