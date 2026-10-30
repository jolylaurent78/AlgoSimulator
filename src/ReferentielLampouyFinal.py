"""Référence solaire de Lampouy réservée au Cadran Final."""
from dataclasses import dataclass

from src.ReferentielSentinelles import (
    ContexteObservation, DirectionSolaire, HeureMoyenneLocale, MoteurSolaireSentinelles,
)
from src.data_loader import villes_dict


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
        contexte = ContexteObservation("Lampouy", *villes_dict["Lampouy"].getCoordonneesGPS(), DATE_CALIBRATION_LAMPOUY)
        moteur = MoteurSolaireSentinelles(contexte)
        return cls(contexte, moteur.directionPourAzimut(138.5), moteur.directionPourAzimut(221.5),
                   moteur.directionPourHeure(HeureMoyenneLocale(43200)).azimut)

    def directionPourPeriode(self, periode):
        if periode not in ("AM", "PM"):
            raise ValueError(f"Période Lampouy inconnue : {periode}")
        return self.directe if periode == "AM" else self.miroir
