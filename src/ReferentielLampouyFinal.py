"""Référence solaire de Lampouy réservée au Cadran Final."""
from dataclasses import dataclass

from src.ReferentielSentinelles import (
    ContexteObservation, DirectionSolaire, HeureMoyenneLocale, MoteurSolaireSentinelles,
)
from src.data_loader import villes_dict
from src.Sentinelle import Sentinelle


CHOIX_LAMPOUY = "10:09"  # Identifiant historique des projets, pas une heure calculée.
DATE_CALIBRATION_LAMPOUY = "19/08/1152"  # Julien, indépendante de l'événement du 18 mai.


@dataclass(frozen=True)
class ReferentielLampouyFinal:
    contexte: ContexteObservation
    directe: DirectionSolaire
    miroir: DirectionSolaire
    azimut_midi: float

    @classmethod
    def charger(cls):
        # Réutiliser uniquement la lecture CSV, sans lancer les anciens calculs.
        lecture = Sentinelle.__new__(Sentinelle)
        lecture.fichierSentinelles = {}
        lecture.chargerFichier("data/sentinelle.csv")
        azimut_am = float(lecture.fichierSentinelles["Lampouy"]["Azimut"])
        azimut_pm = (360 - azimut_am) % 360
        contexte = ContexteObservation("Lampouy", *villes_dict["Lampouy"].getCoordonneesGPS(), DATE_CALIBRATION_LAMPOUY)
        moteur = MoteurSolaireSentinelles(contexte)
        return cls(contexte, moteur.directionPourAzimut(azimut_am), moteur.directionPourAzimut(azimut_pm),
                   moteur.directionPourHeure(HeureMoyenneLocale(43200)).azimut)

    def directionPourPeriode(self, periode):
        if periode not in ("AM", "PM"):
            raise ValueError(f"Période Lampouy inconnue : {periode}")
        return self.directe if periode == "AM" else self.miroir
