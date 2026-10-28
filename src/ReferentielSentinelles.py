"""Lot 1 : référentiel solaire autonome, sans consommation par les anciens algorithmes.

Les heures sont des secondes de temps moyen local ; les dates astronomiques
sont des JD UT1. Aucun chargement de carte, de villes graphiques ou de Tk.
"""
from dataclasses import dataclass
import json
from math import copysign, isfinite
from pathlib import Path

from src.calculAstronomique import (
    MyJulianDate, positionSoleil, calculLeverSoleil, calculCoucherSoleil,
    ecartAngulaire,
)


RACINE = Path(__file__).resolve().parent.parent
CORRESPONDANCES = dict(zip(("S1", "S2", "S3", "S4", "S5", "S6", "S7", "Joker"), "CDEFGABJ"))


@dataclass(frozen=True)
class HeureMoyenneLocale:
    secondes: float

    def __post_init__(self):
        if not isfinite(self.secondes) or not 0 <= self.secondes < 86400:
            raise ValueError("Heure moyenne locale hors de la journée")

    @classmethod
    def depuisTexte(cls, texte):
        parties = texte.split(":")
        if len(parties) != 3:
            raise ValueError("Heure attendue au format HH:MM:SS")
        h, m = map(int, parties[:2])
        s = float(parties[2])
        if not (0 <= h < 24 and 0 <= m < 60 and 0 <= s < 60):
            raise ValueError("Heure moyenne locale invalide")
        return cls(h * 3600 + m * 60 + s)

    def toString(self, format="HH:MM:SS"):
        """Arrondi de présentation seulement ; ne modifie jamais les secondes."""
        if format not in ("HH:MM:SS", "HH:MM"):
            raise ValueError(f"Format d'heure inconnu : {format}")
        unite = 60 if format == "HH:MM" else 1
        secondes = int(self.secondes / unite + 0.5) * unite % 86400
        h, reste = divmod(secondes, 3600)
        m, s = divmod(reste, 60)
        return f"{h:02d}:{m:02d}" if unite == 60 else f"{h:02d}:{m:02d}:{s:02d}"


@dataclass(frozen=True)
class ContexteObservation:
    lieu: str
    latitude: float
    longitude: float
    date: str

    @property
    def coordonnees(self):
        return self.latitude, self.longitude

    @property
    def origine_date_jd(self):
        # Origine numérique de la date à 00:00, avant correction de longitude.
        # 1066 est bien interprété en calendrier julien par MyJulianDate.
        return float(MyJulianDate.fromString(self.date, "00:00:00"))

    def versUT1(self, heure: HeureMoyenneLocale):
        # TML = UT1 + longitude_est × 240 s/°. Ne pas arrondir le décalage.
        return MyJulianDate.fromJD(self.origine_date_jd + (heure.secondes - self.longitude * 240) / 86400)

    def depuisUT1(self, jd):
        secondes = (float(jd) - self.origine_date_jd) * 86400 + self.longitude * 240
        return HeureMoyenneLocale(secondes)


@dataclass(frozen=True)
class DirectionSolaire:
    azimut: float
    heure_locale: HeureMoyenneLocale
    jd_ut1: float
    branche: str


class MoteurSolaireSentinelles:
    """Recherche diurne au site de référence, où l'azimut croît du lever au coucher.

    La position apparente topocentrique sans réfraction est celle de
    positionSoleil(). La précision numérique de recherche est de 0,01 seconde.
    """
    PRECISION_SECONDES = 0.01

    def __init__(self, contexte: ContexteObservation):
        self.contexte = contexte
        date = MyJulianDate.fromString(contexte.date)
        self.lever = float(calculLeverSoleil(contexte.coordonnees, date))
        self.coucher = float(calculCoucherSoleil(contexte.coordonnees, date))
        self.azimut_lever = self._position(self.lever)[1]
        self.azimut_coucher = self._position(self.coucher)[1]
        if not self.azimut_lever < 180 < self.azimut_coucher:
            raise ValueError("Ce moteur requiert un arc solaire diurne croissant passant par le sud")
        self.midi_solaire_jd = self._datePourAzimut(180)
        self.heure_midi_solaire = contexte.depuisUT1(self.midi_solaire_jd)

    def _position(self, jd):
        return positionSoleil(self.contexte.coordonnees, MyJulianDate.fromJD(jd))

    def _datePourAzimut(self, azimut):
        if not isfinite(azimut):
            raise ValueError("Azimut non fini")
        cible = azimut % 360
        if not self.azimut_lever <= cible <= self.azimut_coucher:
            raise ValueError(f"Azimut {cible}° inaccessible sur l'arc solaire diurne de référence")
        # Comparaison sur l'arc diurne déroulé : ne pas confondre cible et
        # direction opposée au passage de la discontinuité d'un écart modulo.
        avant, apres = self.lever, self.coucher
        while (apres - avant) * 86400 > self.PRECISION_SECONDES:
            milieu = (avant + apres) / 2
            if self._position(milieu)[1] < cible:
                avant = milieu
            else:
                apres = milieu
        return (avant + apres) / 2

    def _direction(self, jd, heure=None):
        altitude, azimut = self._position(jd)
        if altitude < 0:
            raise ValueError("La direction solaire doit être au-dessus de l'horizon")
        ecart_secondes = (jd - self.midi_solaire_jd) * 86400
        branche = ("midi_solaire" if abs(ecart_secondes) <= self.PRECISION_SECONDES
                   else "matin" if ecart_secondes < 0 else "apres_midi")
        return DirectionSolaire(azimut, heure if heure is not None else self.contexte.depuisUT1(jd), jd, branche)

    def directionPourHeure(self, heure: HeureMoyenneLocale):
        return self._direction(float(self.contexte.versUT1(heure)), heure)

    def directionPourAzimut(self, azimut):
        return self._direction(self._datePourAzimut(azimut))


def symetrieAzimutSolaireAstronomique(azimut_direct, moteur: MoteurSolaireSentinelles):
    """Miroir angulaire, puis recherche solaire réelle : azimut, heure et branche.

    Aucun appel à heureSymetrique(), ni symétrie des heures autour de 12:00.
    """
    return moteur.directionPourAzimut((360 - azimut_direct) % 360)


@dataclass(frozen=True)
class CadranNational:
    centre: str
    designation_centre: str
    orientation_midi: float
    unite: str
    convention: str
    repere_nord: str
    statut: str
    fonction: str


@dataclass(frozen=True)
class ReferenceSentinelle:
    identifiant: str
    note: str
    nature: str
    azimut_physique_initial: float | None
    autorite: str
    valeur_reference: str | float
    origine: str
    statut: str
    temoins: dict
    directe: DirectionSolaire
    miroir: DirectionSolaire

    @property
    def azimut_direct(self):
        return self.directe.azimut

    @property
    def heure_directe(self):
        return self.directe.heure_locale

    @property
    def azimut_miroir(self):
        return self.miroir.azimut

    @property
    def heure_miroir(self):
        return self.miroir.heure_locale

    def ecartsTemoins(self):
        """Écarts calcul − témoin ; angles circulaires en degrés, temps en secondes."""
        return {
            "azimut_direct_deg": ecartAngulaire(self.azimut_direct, self.temoins["azimut_direct"]),
            "heure_directe_s": self.heure_directe.secondes - HeureMoyenneLocale.depuisTexte(self.temoins["heure_directe"]).secondes,
            "azimut_miroir_deg": ecartAngulaire(self.azimut_miroir, self.temoins["azimut_miroir"]),
            "heure_miroir_s": self.heure_miroir.secondes - HeureMoyenneLocale.depuisTexte(self.temoins["heure_miroir"]).secondes,
        }


class ReferentielSentinelles:
    def __init__(self, moteur, cadran_national, references):
        self.moteur = moteur
        self.contexte = moteur.contexte
        self.cadran_national = cadran_national
        self._references = {r.identifiant: r for r in references}

    def get(self, identifiant):
        return self._references[identifiant]

    def __iter__(self):
        return iter(self._references.values())

    @classmethod
    def charger(cls, fichier_donnees=None, fichier_configuration=None):
        donnees = json.loads(Path(fichier_donnees or RACINE / "data/sentinelles_reference_v1.json").read_text(encoding="utf-8"))
        config = json.loads(Path(fichier_configuration or RACINE / "config/cadran_national_v1.json").read_text(encoding="utf-8"))
        if donnees["version"] != 1 or config["version"] != 1:
            raise ValueError("Version du référentiel non supportée")
        obs = config["observation"]
        if (obs["calendrier"], obs["heure_locale"], obs["temps_interne"], obs["azimut"]) != (
                "julien", "moyenne", "UT1", "nord_geographique_sens_horaire"):
            raise ValueError("Conventions astronomiques incompatibles avec le lot 1")
        # MyJulianDate emploie le calendrier julien uniquement avant sa réforme.
        if MyJulianDate.fromString(obs["date"]).jd >= 2299160.5:
            raise ValueError("Ce référentiel julien utilise une date antérieure au 15/10/1582")

        def dms(valeur):
            degres, minutes, secondes = valeur
            return degres + copysign(minutes / 60 + secondes / 3600, degres)

        contexte = ContexteObservation(obs["lieu"], dms(obs["latitude_dms"]), dms(obs["longitude_dms"]), obs["date"])
        definitions = donnees["directions"]
        if len(definitions) != 8 or {r["identifiant"]: r["note"] for r in definitions} != CORRESPONDANCES:
            raise ValueError("Il faut exactement S1–S7 et Joker avec leurs notes distinctes")
        for definition in definitions:
            nature = "axe_rangee" if definition["identifiant"] == "Joker" else "sentinelle"
            if definition["nature"] != nature or definition["autorite"] not in ("heure", "azimut"):
                raise ValueError("Nature ou autorité de référence invalide")
        moteur = MoteurSolaireSentinelles(contexte)
        references = []
        for definition in definitions:
            if definition["autorite"] == "heure":
                directe = moteur.directionPourHeure(HeureMoyenneLocale.depuisTexte(definition["valeur_reference"]))
            else:
                directe = moteur.directionPourAzimut(float(definition["valeur_reference"]))
            miroir = symetrieAzimutSolaireAstronomique(directe.azimut, moteur)
            references.append(ReferenceSentinelle(**definition, directe=directe, miroir=miroir))
        return cls(moteur, CadranNational(**config["cadran_national"]), references)
