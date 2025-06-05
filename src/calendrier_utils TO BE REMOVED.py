
from datetime import date
from skyfield.api import load
from convertdate import julian

ts = load.timescale()

def julien_vers_gregorien(annee, mois, jour):
    """
    Convertit une date du calendrier julien vers le calendrier grégorien.
    Retourne un objet datetime.date.
    """
    y, m, d = julian.to_gregorian(annee, mois, jour)
    return date(y, m, d)

def gregorien_vers_julien(annee, mois, jour):
    """
    Convertit une date du calendrier grégorien vers le calendrier julien.
    Retourne un objet datetime.date.
    """
    y, m, d = julian.from_gregorian(annee, mois, jour)
    return date(y, m, d)

def skyfield_from_julian(year, month, day, hour=0):
    """
    Crée un objet Skyfield Time à partir d'une date julienne.
    """
    jd = julian.to_jd(year, month, day)
    print(f"Julian Day : {jd}")
    ts = load.timescale()
    return ts.tdb(jd)
