"""Activation explicite du lot 2. Le Sentinelle historique reste inchangé par défaut."""
from collections import OrderedDict
from dataclasses import dataclass

from src.Sentinelle import Sentinelle
from src.ReferentielSentinelles import ReferentielSentinelles, HeureMoyenneLocale
from src.calculAstronomique import heureSymetrique
from src.affichage_objets import PointGraphique, Ligne
from src.carte_config import carteConfig
from src.data_loader import villes_dict
from src.GeometrieCadran import LigneAzimutGrille, azimutGrilleVersImage


@dataclass(frozen=True)
class SelectionHoraire:
    selection: bool
    repere: str
    note: str
    branche: str
    branche_solaire: str
    heure_locale: HeureMoyenneLocale
    azimut_solaire: float | None
    orientation_grille: float | None
    azimut_image: float
    distance_km: int
    historique_lampouy: bool = False

    @property
    def ampm(self):
        return "AM" if self.branche_solaire == "matin" else "PM"


class SentinelleNationale(dict):
    def __init__(self, chemin_csv="data/sentinelle.csv", referentiel=None):
        self.referentiel = referentiel or ReferentielSentinelles.charger()
        self.par_note = {r.note: r for r in self.referentiel}
        self.pointCoetquidan = PointGraphique(villes_dict[self.referentiel.cadran_national.centre])
        self.chemin_csv = chemin_csv
        self._lampouy = None
        super().__init__({r.note: {"HeureLocale": r.heure_directe.toString(),
                                  "AzimutCalibre": r.azimut_direct,
                                  "AzimutGeant": r.azimut_physique_initial} for r in self.referentiel})

    @property
    def lampouy(self):
        if self._lampouy is None:
            # Réemployer exclusivement les méthodes historiques sur la seule
            # ligne Lampouy ; ne recalculer aucune des huit références via le CSV.
            ancien = Sentinelle.__new__(Sentinelle)
            ancien.fichierSentinelles = OrderedDict()
            ancien.chargerFichier(self.chemin_csv)
            ancien.fichierSentinelles = OrderedDict(Lampouy=ancien.fichierSentinelles["Lampouy"])
            ancien.pointCoetquidan = self.pointCoetquidan
            ancien.pointGolfeJuan = PointGraphique(villes_dict["Golfe-Juan"])
            ancien.azimutMidi = ancien.completerAzimutPrecis()
            ancien.calculerHeureSentinelle()
            ancien.creerDictSentinelles()
            self._lampouy = ancien
        return self._lampouy

    def __getitem__(self, note):
        return self.lampouy["L"] if note == "L" else super().__getitem__(note)

    @property
    def azimutMidi(self):
        return azimutGrilleVersImage(self.referentiel.cadran_national.orientation_midi, carteConfig.A)

    def getOrigineStylet(self):
        self.pointCoetquidan.recalculerCoordonneesPixelAbs()
        return self.pointCoetquidan

    def orientationGrille(self, azimut_solaire):
        return (self.referentiel.cadran_national.orientation_midi + 180 - azimut_solaire) % 360

    def directionPourNote(self, note, branche):
        ref = self.par_note[note]
        if branche in ("AM", "PM"):
            solaire = "matin" if branche == "AM" else "apres_midi"
            return next(d for d in (ref.directe, ref.miroir) if d.branche == solaire)
        if branche not in ("directe", "miroir"):
            raise ValueError(f"Branche inconnue : {branche}")
        return ref.directe if branche == "directe" else ref.miroir

    def heurePourNote(self, note, branche):
        if note == "L":
            heure = self.lampouy["L"]["HeureLocale"]
            if branche in ("PM", "miroir"):
                heure = heureSymetrique(heure)
            return HeureMoyenneLocale.depuisTexte(heure + ":00")
        return self.directionPourNote(note, branche).heure_locale

    def autreHeure(self, resultat):
        return self.heurePourNote(resultat.note, "miroir" if resultat.branche == "directe" else "directe")

    def getAzimut(self, heureLocale):
        for ref in self.referentiel:
            for direction in (ref.directe, ref.miroir):
                if heureLocale in (direction.heure_locale.toString(), direction.heure_locale.toString("HH:MM")):
                    return direction.azimut
        return self.lampouy.getAzimut(heureLocale)

    def afficherLigneMidi(self, tagLevel):
        ligne = LigneAzimutGrille(
            self.pointCoetquidan, self.referentiel.cadran_national.orientation_midi,
            nom="Axe national de midi (125,371° Lambert-93)",
            couleur=Sentinelle.COULEUR_TRAIT_MIDI, epaisseur=1, tags={"level": tagLevel},
        )
        ligne.setPrintLabel("Midi national 125,371 L93")
        return ligne

    def afficherLigneHoraire(self, note, am_pm, tagLevel, selectionne=False):
        if note == "L":
            return self.lampouy.afficherLigneHoraire(note, am_pm, tagLevel, selectionne)
        direction = self.directionPourNote(note, am_pm)
        ref = self.par_note[note]
        branche = "directe" if direction is ref.directe else "miroir"
        moment = "matin" if direction.branche == "matin" else "après-midi"
        ligne = LigneAzimutGrille(
            self.pointCoetquidan, self.orientationGrille(direction.azimut),
            nom=f"{ref.identifiant}/{note} {branche} {direction.heure_locale.toString()} ({moment})",
            couleur=Sentinelle.COULEUR_TRAIT_CANDIDAT if selectionne else Sentinelle.COULEUR_TRAIT_HEURE,
            epaisseur=1,
            tooltips=[f"Soleil : {direction.azimut:.6f}°", f"Branche : {branche}, {moment}"],
            tags={"level": tagLevel},
        )
        ligne.setPrintLabel(f"{ref.identifiant}/{note} {branche} {direction.heure_locale.toString()}")
        return ligne

    def rechercherLigneHoraire(self, px, py, inclureLampouy=False):
        candidats = []
        for ref in self.referentiel:
            for branche, direction in (("directe", ref.directe), ("miroir", ref.miroir)):
                grille = self.orientationGrille(direction.azimut)
                image = azimutGrilleVersImage(grille, carteConfig.A)
                candidats.append((ref.identifiant, ref.note, branche, direction.branche,
                                  direction.heure_locale, direction.azimut, grille, image, False))
        if inclureLampouy:
            a = self.lampouy["L"]["AzimutCalibre"]
            for branche, ampm, signe in (("directe", "AM", 1), ("miroir", "PM", -1)):
                image = (self.lampouy.azimutMidi + signe * ((180 - a) % 360)) % 360
                candidats.append(("Lampouy", "L", branche, "matin" if ampm == "AM" else "apres_midi",
                                  self.heurePourNote("L", ampm), None, None, image, True))
        origine = self.getOrigineStylet().coordonneesPixelAbs()
        meilleur = None
        distance_min = float("inf")
        for candidat in candidats:
            distance = Ligne.depuisPointEtAzimut(origine, candidat[7]).distanceAuPoint(px, py)
            if distance < distance_min:  # comparaison stricte, premier en cas d'égalité
                meilleur, distance_min = candidat, distance
        repere, note, branche, solaire, heure, azimut, grille, image, historique = meilleur
        # Contrat historique : métrique image, facteur horizontal au centre,
        # troncature en km puis sélection strictement sous 20 km.
        distance_km = int(self.pointCoetquidan.pixelsVersMetres() * distance_min / 1000)
        return SelectionHoraire(distance_km < 20, repere, note, branche, solaire,
                                heure, azimut, grille, image, distance_km, historique)

    def surLigneHoraire(self, px, py, inclureLampouy=False):
        resultat = self.rechercherLigneHoraire(px, py, inclureLampouy)
        return (resultat.selection, resultat.heure_locale.toString(), resultat.ampm,
                resultat.distance_km, resultat.azimut_image)
