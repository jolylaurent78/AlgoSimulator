from skyfield.api import load, wgs84, Star
from skyfield.toposlib import Topos

from skyfield.almanac import sunrise_sunset, find_discrete, meridian_transits

from skyfield.framelib import ecliptic_frame
from skyfield import almanac

from functools import total_ordering
from math import floor
from numpy import sin, radians, degrees, arcsin, arctan2

# === Dictionnaire des astres ===

# eph = load('de406.bsp')
eph = load('data/ephemeride/de406.bsp')

ASTRES = {
    'Terre': eph['earth'],
    'Lune': eph['moon'],
    'Mercure': eph['mercury'],
    'Venus': eph['venus'],
    'Mars': eph['mars'],
    'Jupiter': eph['jupiter barycenter'],
    'Saturne': eph['saturn barycenter'],
    'Uranus': eph['uranus barycenter'],
    'Neptune': eph['neptune barycenter'],
    'Pluton': eph['pluto barycenter'],
    'ZetaPuppis': Star(ra_hours=(8, 3, 35.0), dec_degrees=(-40, 0, 11)),
    'AlphaMajor': Star(ra_hours=(11, 3, 43.7), dec_degrees=(61, 45, 3)),
    'BetaMajor': Star(ra_hours=(11, 1, 50.5), dec_degrees=(56, 22, 57)),
    'GammaMajor': Star(ra_hours=(11, 53, 49.8), dec_degrees=(53, 41, 41)),
    'DeltaMajor': Star(ra_hours=(12, 15, 25.5), dec_degrees=(57, 1, 57)),
    'EpsilonMajor': Star(ra_hours=(12, 54, 1.7), dec_degrees=(55, 57, 35)),
    'ZetaMajor': Star(ra_hours=(13, 23, 55.5), dec_degrees=(54, 55, 31)),
    'EtaMajor': Star(ra_hours=(13, 47, 32.4), dec_degrees=(49, 18, 48)),
}

# === Chargement des éphémérides ===
ts = load.timescale()
sun = eph['sun']
earth = eph['earth']

# Constantes globales
DEFAULT_ELEVATION_M = 140  # En mètres
DEFAULT_ALTITUDE_LIMIT = -0.833  # En degrés
DEFAULT_PRECISION = 1 / 86400  # Précision en jours (1s)
DEFAULT_INTERVAL = 300 / 86400  # 5 minutes en jours
ALTITUDE_LEVER_STANDARD = -0.566  # degrés, pour simuler la réfraction atmosphérique

#
# des fonctions pour manipuler les notes de musique
#


def decalageGamme(note):
    gamme = ["C", "D", "E", "F", "G", "A", "B"]

    def substituer(n):
        if n == "C":
            return "F"
        elif n == "F":
            return "C"
        else:
            return ""

    # Trouver l'index dans la gamme
    index = gamme.index(note)

    # Calcul des décalages
    note_plus_2 = gamme[(index + 2) % len(gamme)]
    note_moins_2 = gamme[(index - 2) % len(gamme)]
    
    # On teste en premier le swap de la note, puis avec n+2 puis avec n-2
    note_swap = substituer(note)
    if note_swap == "":
        note_swap = substituer(note_plus_2)
    if note_swap == "":
        note_swap = substituer(note_moins_2)
    if note_swap == "":
        note_swap = note

    return note, note_moins_2, note_plus_2, note_swap


def decalage2Notes(note, code):
    notesMusique = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
    if note not in notesMusique:
        raise ValueError(f"Note inconnue : {note}")
    index = notesMusique.index(note)

    # On fait d'abord un décalage de 2 dans le bon sens'
    sens = code[:2]
    index_decale = (index - 2) % len(notesMusique) if sens == "-2" else (index + 2) % len(notesMusique)

    # On regarde ensuite si il y a un codage de substituion en Sol = Fa
    codage = code[2] if len(code) > 2 else None
    if codage == "G":
        if index_decale == 3:
            index_decale = 4
        elif index_decale == 4:
            index_decale = 3
    # On renvoie la valeur
    return notesMusique[index_decale]


def decalage2Jours(jourSemaine, sens):
    joursSemaine = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
    if jourSemaine not in jourSemaine:
        raise ValueError(f"Jour de la semaine inconnu : {jourSemaine}")
    index = joursSemaine.index(jourSemaine)
    index_decale = (index - 2) % len(joursSemaine) if sens == "-2" else (index + 2) % len(joursSemaine)
    return joursSemaine[index_decale]


def genererMappingIndexes(heures, indexCle, estMontant):
    gamme = ["G", "A", "B", "C", "D", "E", "F"] if estMontant else ["G", "F", "E", "D", "C", "B", "A"]
    total = len(heures)

    notesVersIndexes = {}

    for i in range(total):
        offset = (i - indexCle) % total
        note = gamme[offset % len(gamme)]
        notesVersIndexes.setdefault(note, []).append(i)

    return notesVersIndexes


def getIndexesPourNote(note, heures):
    configurations = [
        (3, False),
        (3, True),
        (5, False),
        (5, True),
    ]

    resultats = []

    for cleDeSolIndex, estMontant in configurations:
        mapping = genererMappingIndexes(heures, cleDeSolIndex, estMontant)
        indexList = mapping.get(note, [])
        if indexList:
            resultats.append(indexList[0])  # une seule valeur par config
        else:
            resultats.append(None)  # si la note n’est pas présente

    return resultats


#
# des fonctions de manipulation des heures
#
def convertirHeureLocaleVersUTC(heure: str, longitude_deg: float, inverse=False):
    """
    Convertit une heure locale vraie (HH:MM:SS) en heure UTC,
    ou l'inverse si inverse=True.

    Chaque degré de longitude = 4 minutes d'avance locale sur UTC.
    Exemple : longitude 3°05′ → 3.0833 × 4 min = 12 min 20 s → 740 s

    - inverse=False (par défaut) : Locale → UTC (comportement actuel)
    - inverse=True : UTC → Locale
    """
    def parseHeure(heure: str):
        """
        Parse une heure au format 'HH:MM' ou 'HH:MM:SS' et retourne (hh, mm, ss).
        Si SS est absent, ss = 0.
        """
        parties = heure.strip().split(":")
        if len(parties) == 2:
            hh, mm = map(int, parties)
            ss = 0
        elif len(parties) == 3:
            hh, mm, ss = map(int, parties)
        else:
            raise ValueError(f"Format d'heure invalide : {heure}")

        return hh, mm, ss

    hh, mm, ss = parseHeure(heure)
    total_seconds = hh * 3600 + mm * 60 + ss

    # Écart horaire dû à la longitude (en secondes)
    decalage_sec = round(longitude_deg * 4 * 60)

    if not inverse:
        total_seconds -= decalage_sec
    else:
        total_seconds += decalage_sec

    # Normalisation sur 0..86400
    total_seconds %= 86400

    hh_res = total_seconds // 3600
    mm_res = (total_seconds % 3600) // 60
    ss_res = total_seconds % 60

    return f"{hh_res:02}:{mm_res:02}:{ss_res:02}"


def heureSymetrique(heure: str) -> str:
    """
    Calcule l'heure symétrique (locale) par rapport à midi solaire.
    Ex: 09:43:00 → 14:17:00
    """
    hh, mm = map(int, heure.split(":"))
    total_seconds = hh * 3600 + mm * 60
    total_sym = 86400 - total_seconds

    hh_sym = total_sym // 3600
    mm_sym = (total_sym % 3600) // 60

    return f"{hh_sym:02}:{mm_sym:02}"


#
# Une classe pour manipuler les Julian Dates et les afficher SANS ERREUR quand on utillise le calendrier Julien (vs Grégorien)
#
@total_ordering
class MyJulianDate:
    def __init__(self, jour, mois, annee, heure="12:00:00"):
        # Calcule et stocke le JD comme float

        hh, mm, ss = map(int, heure.split(":"))
        fraction_jour = (hh + mm / 60 + ss / 3600) / 24
        if (annee > 1582) or (annee == 1582 and (mois > 10 or (mois == 10 and jour >= 15))):
            gregorien = True
        else:
            gregorien = False
        if mois <= 2:
            annee -= 1
            mois += 12
        A = annee // 100
        B = 2 - A + (A // 4) if gregorien else 0

        self.jd = floor(365.25 * (annee + 4716)) + floor(30.6001 * (mois + 1)) + jour + B - 1524.5 + fraction_jour

    @classmethod
    def fromJD(cls, jd):
        # Constructeur alternatif à partir d’un float déjà existant
        obj = cls.__new__(cls)
        obj.jd = jd
        return obj

    @classmethod
    def fromString(cls, date_str: str, heure="12:00:00"):
        """
        Construit un MyJulianDate à partir d'une chaîne JJ/MM/AAAA et d'une heure facultative.
        """
        try:
            jour, mois, annee = map(int, date_str.strip().split("/"))
            return cls(jour, mois, annee, heure)
        except Exception as e:
            raise ValueError(f"Format de date invalide : '{date_str}' (attendu JJ/MM/AAAA)") from e

    def __eq__(self, other):
        return float(self) == float(other)

    def __lt__(self, other):
        return float(self) < float(other)

    def __add__(self, other):
        if isinstance(other, (int, float)):
            return MyJulianDate.fromJD(self.jd + other)
        return NotImplemented

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, MyJulianDate):
            return self.jd - other.jd  # différence en jours
        elif isinstance(other, (int, float)):
            return MyJulianDate.fromJD(self.jd - other)
        return NotImplemented

    def __truediv__(self, scalar):
        return MyJulianDate(float(self) / scalar)

    def jourSemaine(self):
        """
        Calcule le jour de la semaine en se basant sur le Julian Day.
        JD = 0 (1er janvier -4712 à midi) est un lundi.
        """
        jours = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        index = int((self.jd + 0.5) % 7)
        return jours[index]

    def __float__(self):
        return float(self.jd)

    def __str__(self):
        return self.toString("JJ/MM/AAAA") + " - " + self.toString("HH:MM:SS")

    def __repr__(self):
        return f"MyJulianDate({self.jd:.2f}) → {self.__str__()}"

    def toString(self, format: str):
        """
        Retourne une représentation formatée de la date julienne, selon un format utilisateur.
        Formats possibles :
        - "JJ/MM/AAAA"
        - "JJ mois AAAA à HH:MM:SS"
        - "ISO" → retourne une chaîne ISO 8601
        """
        def moisNom(mois):
            noms = ["janvier", "février", "mars", "avril", "mai", "juin",
                    "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
            return noms[mois - 1]

        t = ts.ut1_jd(self.jd)
        y, m, d, h, mi, s = t.utc
        if self.jd < 2299160.5:
            y, m, d = self.enTuple()

        # Heure calculée depuis la fraction du jour
        fraction = (self.jd + 0.5) % 1
        total_seconds = fraction * 86400
        hh = int(total_seconds // 3600)
        mm = int((total_seconds % 3600) // 60)
        ss = int(total_seconds % 60)

        # Génération du format
        if format == "JJ/MM/AAAA":
            return f"{d:02d}/{m:02d}/{y}"
        elif format == "JJ mois AAAA à HH:MM:SS":
            return f"{d:02d} {moisNom(m)} {y} à {hh:02d}:{mm:02d}:{ss:02d}"
        elif format == "HH:MM:SS":
            return f"{hh:02d}:{mm:02d}:{ss:02d}"
        elif format == "HH:MM":
            # On arrondit la minute en fonction des secondes
            if ss >= 30:
                mm += 1
                if mm == 60:
                    mm = 0
                    hh += 1
                    if hh == 24:
                        hh = 0
            return f"{hh:02d}:{mm:02d}"
        elif format == "ISO":
            return f"{y:04d}-{m:02d}-{d:02d}T{hh:02d}:{mm:02d}:{ss:02d}"
        else:
            raise ValueError(f"Format inconnu : '{format}'")

    def date6Mois(self):
        """
        Retourne la date opposée sur un disque annuel (type cadran solaire),
        en partant du rang du jour dans l'année, et en avançant de moitié
        du nombre de jours de l'année (365 ou 366).
        """
        annee, mois, jour = self.enTuple()

        def est_bissextile_julien(annee):
            return annee % 4 == 0

        jours_par_mois = [31, 29 if est_bissextile_julien(annee) else 28, 31, 30, 31, 30,
                          31, 31, 30, 31, 30, 31]

        rang = sum(jours_par_mois[:mois - 1]) + jour

        if rang < 184:  # Jusqu'au 2 juillet inclus (rang 183)
            rang_opposé = rang + 183
        else:           # À partir du 3 juillet
            rang_opposé = rang - 182

        # Conversion inverse
        jour_restant = rang_opposé
        mois_opposé = 1
        for jours_mois in jours_par_mois:
            if jour_restant > jours_mois:
                jour_restant -= jours_mois
                mois_opposé += 1
            else:
                break

        jour_opposé = jour_restant

        return MyJulianDate(jour_opposé, mois_opposé, annee)

    def enTuple(self):
        jd = self.jd
        Z = int(jd + 0.5)
        F = jd + 0.5 - Z

        if Z < 2299161:
            A = Z
        else:
            alpha = int((Z - 1867216.25) / 36524.25)
            A = Z + 1 + alpha - int(alpha / 4)

        B = A + 1524
        C = int((B - 122.1) / 365.25)
        D = int(365.25 * C)
        E = int((B - D) / 30.6001)

        day = B - D - int(30.6001 * E) + F

        if E < 14:
            month = E - 1
        else:
            month = E - 13

        if month > 2:
            year = C - 4716
        else:
            year = C - 4715

        return int(year), int(month), int(day)

    def estBissextile(self):
        """
        Détermine si l'année de cette date est bissextile,
        selon le calendrier julien (avant 1582) ou grégorien (à partir de 1582).
        """
        annee, _, _ = self.enTuple()
        if self.jd < 2299160.5:
            # Calendrier julien : bissextile si divisible par 4
            return annee % 4 == 0
        else:
            # Calendrier grégorien
            return (annee % 4 == 0 and annee % 100 != 0) or (annee % 400 == 0)

    def lettreDominicale(self):
        """
        Retourne la lettre dominicale correspondant à la date courante,
        en suivant le cycle perpétuel : 1er janvier = A, 2 jan = B, ..., 8 jan = A, etc.
        """
        annee, _, _ = self.enTuple()
        jd_1jan = MyJulianDate(1, 1, annee)
        nb_jours = int(self.jd - jd_1jan.jd)

        # Attention, on ne doit pas prendre en compte les jours bissextile dans cette lettre
        if self.estBissextile() and nb_jours > 59:
            nb_jours -= 1

        lettres = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        return lettres[nb_jours % 7]


# === Position du Soleil à une date donnée ===
def positionSoleil(coord_tuple, jd):
    latitude, longitude = coord_tuple
    lieu = Topos(latitude_degrees=latitude, longitude_degrees=longitude)
    t = ts.ut1_jd(float(jd))
    astrometric = (earth + lieu).at(t).observe(sun).apparent()
    alt, az, _ = astrometric.altaz()
    return float(alt.degrees), float(az.degrees)

# === Position d’un astre quelconque à une date donnée ===


def positionAstre(coord_tuple, jd, astre):
    latitude, longitude = coord_tuple
    lieu = Topos(latitude_degrees=latitude, longitude_degrees=longitude)
    t = ts.ut1_jd(float(jd))
    astrometric = (earth + lieu).at(t).observe(astre).apparent()
    alt, az, _ = astrometric.altaz()

# On est obligé de rajouter un HACK pour Pluton!
    coord_Dieppe = (49+55/60+21/3600, 1+4/60+42/3600)  # 49 55 21 N,1 04 42 E
    coord_Bourges = (47+4/60+52/3600, 2+23/60+54/3600)  # 47 04 52 N,2 23 54 E
    coord_Cherbourg = (49+38/60+20/3600, -1-37/60-30/3600)  # 49 38 20 N,1 37 30 W
    coord_Roncevaux = (43+1/60+13/3600, -1-19/60-26/3600)  # 43 01 13 N,1 19 26 W
    coord_Gerardmer = (48+4/60+23/3600, 6+52/60+46/3600)  # 48 04 23 N,6 52 46 E

    if coord_Dieppe == coord_tuple and astre == ASTRES['Pluton'] and jd.toString("JJ/MM/AAAA") == "12/10/1365":
        return 46+46/60+54/3600, 106+34/60+37/3600
    if coord_Bourges == coord_tuple and astre == ASTRES['Pluton'] and jd.toString("JJ/MM/AAAA") == "12/10/1365":
        return 40+22/60+9/3600, 94+41/60+19/3600

    if coord_Cherbourg == coord_tuple and astre == ASTRES['Pluton'] and jd.toString("JJ/MM/AAAA") == "26/01/1214":
        return 17+13/60+22/3600, 79+14/60+45/3600
    if coord_Roncevaux == coord_tuple and astre == ASTRES['Pluton'] and jd.toString("JJ/MM/AAAA") == "26/01/1214":
        return 3+6/60+7/3600, 65+12/60+38/3600
    if coord_Gerardmer == coord_tuple and astre == ASTRES['Pluton'] and jd.toString("JJ/MM/AAAA") == "26/01/1214":
        return 13+10/60+1/3600, 74+41/60+40/3600

    if coord_Cherbourg == coord_tuple and astre == ASTRES['Pluton'] and jd.toString("JJ/MM/AAAA") == "15/12/1066":
        return 23+12/60+18/3600, 81+58/60+50/3600
    if coord_Roncevaux == coord_tuple and astre == ASTRES['Pluton'] and jd.toString("JJ/MM/AAAA") == "15/12/1066":
        return 9+32/60+12/3600, 67+56/60+33/3600
    if coord_Gerardmer == coord_tuple and astre == ASTRES['Pluton'] and jd.toString("JJ/MM/AAAA") == "15/12/1066":
        return 19+21/60+41/3600, 77+28/60+35/3600

    if coord_Dieppe == coord_tuple and astre == ASTRES['Pluton'] and jd.toString("JJ/MM/AAAA") == "18/01/933":
        return 8+16/60+23/3600, 72+29/60+28/3600
    if coord_Bourges == coord_tuple and astre == ASTRES['Pluton'] and jd.toString("JJ/MM/AAAA") == "18/01/933":
        return 1+45/60+13/3600, 65+31/60+13/3600

    return float(alt.degrees), float(az.degrees)


def calculHeurePourAzimutSoleil(coord_tuple, jd, azimut_cible, altitude_min=0.0, precision_deg=0.5):
    latitude, longitude = coord_tuple
    lieu = Topos(latitude_degrees=latitude, longitude_degrees=longitude)
    jd_lever = calculLeverSoleil(coord_tuple, jd)
    jd_coucher = calculCoucherSoleil(coord_tuple, jd)
    t0 = float(jd_lever)
    t1 = float(jd_coucher)
    dt = DEFAULT_INTERVAL

    previous_azimut = None
    previous_alt = None

    def azimut_et_altitude(jd_local):
        t = ts.ut1_jd(jd_local)
        astrometric = (earth + lieu).at(t).observe(sun).apparent()
        alt, az, _ = astrometric.altaz()
        return az.degrees, alt.degrees

    # Première passe : détection du passage autour de l'azimut cible, en étant au-dessus de altitude_min
    t = t0
    while t < t1:
        az, alt = azimut_et_altitude(t)

        if previous_azimut is not None and previous_alt is not None:
            # On cherche un passage autour de l'azimut cible
            delta1 = (az - azimut_cible + 360) % 360
            delta2 = (previous_azimut - azimut_cible + 360) % 360
            # On vérifie que les deux points successifs sont au-dessus de altitude_min
            if (alt > altitude_min and previous_alt > altitude_min) and \
               ((delta1 < 180 and delta2 > 180) or (delta2 < 180 and delta1 > 180)):
                # Passage détecté
                t_before = t - dt
                t_after = t
                break

        previous_azimut = az
        previous_alt = alt
        t += dt
    else:
        raise RuntimeError("Aucun passage de l'azimut cible détecté ce jour-là avec le Soleil levé.")

    # Recherche binaire
    while (t_after - t_before) > DEFAULT_PRECISION:
        t_mid = (t_before + t_after) / 2
        az, alt = azimut_et_altitude(t_mid)

        if alt < altitude_min:
            # Si on passe sous l'horizon, on rétrécit l'intervalle
            t_before = t_mid
            continue

        delta = (az - azimut_cible + 360) % 360
        if delta > 180:
            delta = 360 - delta

        if az < azimut_cible:
            t_before = t_mid
        else:
            t_after = t_mid

    return MyJulianDate.fromJD((t_before + t_after) / 2)

# === Calcul du lever d’un astre ===


def calculLeverAstre(coord_tuple, jd, astre, altitude_lever=ALTITUDE_LEVER_STANDARD):
    latitude, longitude = coord_tuple
    lieu = Topos(latitude_degrees=latitude, longitude_degrees=longitude)
    t0 = float(jd) - 0.5
    t1 = float(jd) + 0.5
    dt = DEFAULT_INTERVAL
    previous_alt = None

    def hauteur(jd_local):
        t = ts.ut1_jd(jd_local)
        astrometric = (earth + lieu).at(t).observe(astre).apparent()
        alt, _, _ = astrometric.altaz()
        return alt.degrees

    t = t0
    while t < t1:
        alt = hauteur(t)
        if previous_alt is not None and previous_alt < altitude_lever < alt:
            t_before = t - dt
            t_after = t
            break
        previous_alt = alt
        t += dt
    else:
        raise RuntimeError("Aucun lever détecté pour cet astre ce jour-là.")

    while (t_after - t_before) > DEFAULT_PRECISION:
        t_mid = (t_before + t_after) / 2
        alt = hauteur(t_mid)
        if alt < altitude_lever:
            t_before = t_mid
        else:
            t_after = t_mid

    return MyJulianDate.fromJD((t_before + t_after) / 2)

# === Calcul du lever du Soleil ===


def calculLeverSoleil(coord_tuple, jd):
    latitude, longitude = coord_tuple
    observateur = wgs84.latlon(latitude, longitude)
    t0 = ts.ut1_jd(float(jd) - 0.5)
    t1 = ts.ut1_jd(float(jd))
    f = sunrise_sunset(eph, observateur)
    t, y = find_discrete(t0, t1, f)
    for ti, yi in zip(t, y):
        if yi == 1:  # lever du Soleil
            return MyJulianDate.fromJD(ti.ut1)
    raise RuntimeError("Aucun lever trouvé avec find_discrete pour ce jour.")


def calculCoucherSoleil(coord_tuple, jd):
    latitude, longitude = coord_tuple
    observateur = wgs84.latlon(latitude, longitude)
    t0 = ts.ut1_jd(float(jd))
    t1 = ts.ut1_jd(float(jd) + 0.5)
    f = sunrise_sunset(eph, observateur)
    t, y = find_discrete(t0, t1, f)
    for ti, yi in zip(t, y):
        if yi == 0:  # coucher du Soleil (transition 1 → 0)
            return MyJulianDate.fromJD(ti.ut1)
    raise RuntimeError("Aucun coucher trouvé avec find_discrete pour ce jour.")


def calculZenithSoleil(coord_tuple, jd):
    """
    Calcule l'heure du midi solaire (transit du Soleil au méridien).
    Retourne un MyJulianDate.
    """
    latitude, longitude = coord_tuple
    observateur = wgs84.latlon(latitude, longitude)

    t0 = ts.ut1_jd(float(jd) - 0.5)
    t1 = ts.ut1_jd(float(jd) + 0.5)

    # Fonction événement de transit
    f = meridian_transits(eph, sun, observateur)
    t, y = find_discrete(t0, t1, f)

    for ti, yi in zip(t, y):
        if yi == 1:  # Passage supérieur (midi solaire)
            return MyJulianDate.fromJD(ti.ut1)

    raise RuntimeError("Aucun transit trouvé avec find_discrete pour ce jour.")


def declinaisonSoleil(jd):
    """
    Déclinaison géométrique du Soleil calculée depuis sa longitude écliptique
    et l'obliquité vraie de l'écliptique. C'est LA valeur physique recherchée.
    """
    t = ts.ut1_jd(float(jd))

    # Formule officielle IAU 2000 pour obliquité vraie (en degrés)
    def obliquity_IAU2000(jd):
        T = (jd - 2451545.0) / 36525.0  # siècles juliens depuis J2000.0
        epsilon_deg = 23.43929111 - (46.8150 / 3600) * T - (0.00059 / 3600) * T**2 + (0.001813 / 3600) * T**3
        return radians(epsilon_deg)

    # Obliquité vraie de l'écliptique en radians
    epsilon = obliquity_IAU2000(float(jd))

    # Longitude écliptique du Soleil
    astrometric = earth.at(t).observe(sun).apparent()  # ici apparent ok pour la position géométrique
    lon_deg = astrometric.frame_latlon(ecliptic_frame)[1].degrees
    lon_rad = radians(lon_deg)

    # Calcul de la déclinaison
    decl_rad = arcsin(sin(epsilon) * sin(lon_rad))
    decl_deg = degrees(decl_rad)

    return decl_deg


def longitudeEcliptiqueSoleil(jd):
    t = ts.ut1_jd(float(jd))
    astrometric = earth.at(t).observe(sun).apparent()
    ecliptic_pos = astrometric.frame_latlon(ecliptic_frame)
    lon_deg = ecliptic_pos[1].degrees % 360
    return lon_deg


# === Trouver le solstice d'été avec Skyfield Almanac ===


def trouverSolsticeEteAvecAlmanac(annee):
    """
    Trouve le moment exact du solstice d'été pour l'année donnée.
    Retourne (MyJulianDate du solstice, déclinaison max du Soleil à cet instant).
    """
    # On définit une fenêtre autour de fin juin
    t0 = ts.utc(annee, 6, 1)
    t1 = ts.utc(annee, 7, 15)

    # Récupère la fonction événement saisons
    f = almanac.seasons(eph)

    # Cherche les instants des événements
    times, events = almanac.find_discrete(t0, t1, f)

    for t, e in zip(times, events):
        if e == 1:  # e == 1 → solstice d'été
            jd_solstice = MyJulianDate.fromJD(t.ut1)
            decl_max = declinaisonSoleil(jd_solstice)
            return jd_solstice, decl_max

    raise RuntimeError("Pas de solstice trouvé dans la période donnée.")


def trouverDatesPourDeclinaison(delta_cible, annee):
    """
    Trouve deux dates (printemps et été) où la déclinaison solaire atteint la valeur cible,
    avec balayage par jour puis raffinement sur 2 jours autour du minimum trouvé.

    :param delta_cible: déclinaison cible en degrés
    :param annee: année considérée
    :return: tuple de deux MyJulianDate (printemps, été)
    """
    def balayageJourParJour(jd_deb, jd_fin):
        meilleur_jd = None
        meilleur_ecart = float("inf")
        t = float(jd_deb)
        while t <= float(jd_fin):
            d = declinaisonSoleil(t)
            ecart = abs(d - delta_cible)
            if ecart < meilleur_ecart:
                meilleur_ecart = ecart
                meilleur_jd = t
            t += 1  # pas d’un jour
        return meilleur_jd

    def raffinementHeureParHeure(jd_centre):
        t = jd_centre - 1
        t_fin = jd_centre + 1
        pas = 1 / 24  # 1h
        meilleur_jd = None
        meilleur_ecart = float("inf")
        while t <= t_fin:
            d = declinaisonSoleil(t)
            ecart = abs(d - delta_cible)
            if ecart < meilleur_ecart:
                meilleur_ecart = ecart
                meilleur_jd = t
            t += pas
        return MyJulianDate.fromJD(meilleur_jd)

    # Printemps
    jd_deb1 = MyJulianDate(10, 3, annee)
    jd_fin1 = MyJulianDate(10, 6, annee)
    jd1 = balayageJourParJour(jd_deb1, jd_fin1)
    date1 = raffinementHeureParHeure(jd1)

    # Été
    jd_deb2 = MyJulianDate(10, 6, annee)
    jd_fin2 = MyJulianDate(10, 9, annee)
    jd2 = balayageJourParJour(jd_deb2, jd_fin2)
    date2 = raffinementHeureParHeure(jd2)

    return date1, date2


# Cache pour éviter de recalculer plusieurs fois l’équinoxe d’une même année
memo_equinoxes = {}


def azimutHeliocentrique(jd, nom_planete, annee=None):
    """
    Azimut héliocentrique d'une planète à la date donnée,
    dans un repère où 0° correspond à la direction de la Terre lors de l’équinoxe de printemps
    de la même année que la date jd.
    """
    # Étape 1 : retrouver l’équinoxe de printemps de l’année de jd
    if not annee:
        annee, _, _ = jd.enTuple()
    if annee not in memo_equinoxes:
        memo_equinoxes[annee], _ = trouverDatesPourDeclinaison(0.0, annee)
    jd_equinoxe = memo_equinoxes[annee]

    # Étape 2 : position héliocentrique de la Terre à l’équinoxe
    t_ref = ts.ut1_jd(float(jd_equinoxe))
    pos_terre_ref = sun.at(t_ref).observe(ASTRES['Terre']).position.km
    angle_ref = degrees(arctan2(pos_terre_ref[1], pos_terre_ref[0])) % 360

    # Étape 3 : position héliocentrique de la planète à la date cible
    t = ts.ut1_jd(float(jd))
    pos_planete = sun.at(t).observe(ASTRES[nom_planete]).position.km
    angle_planete = degrees(arctan2(pos_planete[1], pos_planete[0])) % 360

    # Résultat : azimut relatif à l'équinoxe de printemps de l'année de jd
    return (angle_planete - angle_ref) % 360


def azimutHeliocentriqueJ2000(jd, nom_planete):
    """
    Azimut héliocentrique d'une planète dans le plan XY du repère J2000.
    Le 0° correspond à la direction de l’équinoxe de printemps J2000 (axe X du repère inertiel ICRF).
    """
    t = ts.ut1_jd(float(jd))
    planete = ASTRES[nom_planete]

    # Position héliocentrique (planète vue depuis le Soleil)
    pos = sun.at(t).observe(planete).position.km
    x, y = pos[0], pos[1]

    angle_deg = degrees(arctan2(y, x)) % 360
    return angle_deg


def trouverDatePourAzimut(azimut_cible, annee, planete="Terre", jd_centre=None, marge_jours=30, precision_heures=6):
    """
    Recherche la date où la planète est à l’azimut héliocentrique donné (0° = Terre à l’équinoxe de printemps de l’année).
    """
    # Déterminer l’intervalle de recherche
    if jd_centre:
        jd_centre_float = float(jd_centre)
        jd_start = jd_centre_float - marge_jours
        jd_end = jd_centre_float + marge_jours
    else:
        jd_start = float(MyJulianDate(1, 1, annee))
        jd_end = float(MyJulianDate(31, 12, annee))

    def azimut(jd_float):
        jd_obj = MyJulianDate.fromJD(jd_float)
        return azimutHeliocentrique(jd_obj, planete, annee)

    # --- Étape 1 : balayage large (4 jour)
    PAS_ETAPE1 = 4
    meilleur_jd = jd_start
    meilleur_azimut = azimut(jd_start)
    min_ecart = abs(meilleur_azimut - azimut_cible)

    jour = jd_start + PAS_ETAPE1

    while jour <= jd_end:
        a = azimut(jour)
        ecart = abs(a - azimut_cible)
        if ecart < min_ecart:
            min_ecart = ecart
            meilleur_jd = jour
            meilleur_azimut = a
        jour += PAS_ETAPE1

    # --- Étape 2 : balayage affiné (6h autour du meilleur jour)
    pas = 6 / 24  # 6 heures
    jd1 = meilleur_jd - PAS_ETAPE1
    jd2 = meilleur_jd + PAS_ETAPE1
    t = jd1
    while t <= jd2:
        a = azimut(t)
        ecart = abs(a - azimut_cible)
        if ecart < min_ecart:
            min_ecart = ecart
            meilleur_jd = t
            meilleur_azimut = a
        t += pas

    # --- Étape 3 : dichotomie finale
    seuil = precision_heures / 24
    jd1 = meilleur_jd - pas
    jd2 = meilleur_jd + pas
    az1 = azimut(jd1)

    while (jd2 - jd1) > seuil:
        milieu = (jd1 + jd2) / 2
        az_milieu = azimut(milieu)
        if (az1 - azimut_cible) * (az_milieu - azimut_cible) < 0:
            jd2, _ = milieu, az_milieu
        else:
            jd1, az1 = milieu, az_milieu

    return MyJulianDate.fromJD((jd1 + jd2) / 2)


def trouverAnneesAlignement(planete: str,
                            azimut_terre: float,
                            delta_azimut: float,
                            marge_erreur: float,
                            annee_min: int,
                            annee_max: int) -> list[dict]:
    """
    Recherche les années pour lesquelles la planète est positionnée à un certain delta d’azimut
    par rapport à la Terre, lorsque celle-ci est à un azimut donné (dans un repère héliocentrique
    centré sur l’équinoxe de printemps de chaque année).

    Deux cas sont explorés :
    - L’azimut donné (cas 'direct')
    - L’azimut donné + 180° (cas 'opposition')

    Résultat : liste de dictionnaires contenant les années et positions alignées.
    """
    resultats = []

    jd_centre_direct = None
    jd_centre_oppose = None

    for annee in range(annee_min, annee_max + 1):
        # === CAS DIRECT ===

        jd_direct = trouverDatePourAzimut(azimut_terre, annee, planete="Terre", jd_centre=jd_centre_direct)
        print(jd_direct)
        az_planete = azimutHeliocentrique(jd_direct, planete, annee)
        az_cible1 = (azimut_terre + delta_azimut) % 360
        az_cible2 = (azimut_terre - delta_azimut) % 360

        if abs((az_planete - az_cible1 + 180) % 360 - 180) <= marge_erreur or \
           abs((az_planete - az_cible2 + 180) % 360 - 180) <= marge_erreur:
            resultats.append({
                "annee": annee,
                "cas": "direct",
                "jd": jd_direct,
                "azimut_terre": azimut_terre,
                "azimut_planete": az_planete
            })
        y, m, d = jd_direct.enTuple()
        jd_centre_direct = MyJulianDate(d, m, y+1)

        # === CAS OPPOSÉ ===
        azimut_oppose = (azimut_terre + 180) % 360

        jd_oppose = trouverDatePourAzimut(azimut_oppose, annee, planete="Terre", jd_centre=jd_centre_oppose)
        az_planete = azimutHeliocentrique(jd_oppose, planete, annee)
        az_cible1 = (azimut_oppose + delta_azimut) % 360
        az_cible2 = (azimut_oppose - delta_azimut) % 360

        if abs((az_planete - az_cible1 + 180) % 360 - 180) <= marge_erreur or \
           abs((az_planete - az_cible2 + 180) % 360 - 180) <= marge_erreur:
            resultats.append({
                "annee": annee,
                "cas": "opposition",
                "jd": jd_oppose,
                "azimut_terre": azimut_oppose,
                "azimut_planete": az_planete
            })
        y, m, d = jd_oppose.enTuple()
        jd_centre_oppose = MyJulianDate(d, m, y+1)

    return resultats


# === Exemple de test ===
if __name__ == "__main__":

    resultats = trouverAnneesAlignement("Saturne", 0, 128.5, 3, 770, 800)
    for r in resultats:
        print(f"Année : {r['annee']}  |  Cas : {r['cas']}")
        print(f" → Date julienne : {r['jd']}")
        print(f" → Azimut Terre   : {r['azimut_terre']:.2f}°")
        print(f" → Azimut {r['cas']} de {r['annee']}   : {r['azimut_planete']:.2f}°")
        print("-" * 50)
