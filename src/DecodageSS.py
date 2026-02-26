
from src.data_loader import villes_dict
from src.affichage_objets import LigneEntreVilles
from src.ConstructionsCadrans import ObjetCadran


class UniteDecodageSS:

    COULEUR_AXEMIDI = (255, 145, 34)

    def __init__(self, objetPrecedent, objetDebut: ObjetCadran, objetFin: ObjetCadran, axeMidi: (str, str)):
        # On sauvegarde les objets
        self.objetPrecedent = objetPrecedent
        self.objetDebut = objetDebut
        self.objetFin = objetFin

        # Axe Midi
        (self.debutAxeMidi, self.finAxeMidi) = axeMidi
        axeMidiNonCentre = LigneEntreVilles(villes_dict[self.debutAxeMidi], villes_dict[self.finAxeMidi])
        self.azimutMidi = axeMidiNonCentre.getAzimutCarte()

        # Axe Ombre
        self.segmentLumiereDebut = self.objetDebut.getLigneOmbre((0, 0, 0))
        self.distanceLumiereDebut = self.segmentLumiereDebut.distanceSegment()
        self.azimutLumiereDebut = self.segmentLumiereDebut.getAzimutCarte()
        self.segmentLumiereFin = self.objetFin.getLigneOmbre((0, 0, 0))
        self.distanceLumiereFin = self.segmentLumiereFin.distanceSegment()
        self.azimutLumiereFin = self.segmentLumiereFin.getAzimutCarte()

        # AxeBase
        self.segmentBaseDebut = self.objetDebut.axeMidiCadran(UniteDecodageSS.COULEUR_AXEMIDI)
        self.segmentBaseFin = self.objetFin.axeMidiCadran(UniteDecodageSS.COULEUR_AXEMIDI)
        self.angleSegmentMidiDebut = self.azimutLumiereDebut - self.segmentBaseDebut.getAzimutCarte()
        self.angleSegmentMidiFin = self.azimutLumiereFin - self.segmentBaseFin.getAzimutCarte()

    def construireRepresentationCarte(self):
        """
        Retourne la liste des objets graphiques à afficher pour visualiser ce segment.
        """
        # On affiche le point précédent
        # pointPrecedent = PointGraphique(self.objetPrecedent.getReference(), epaisseur = 4, couleur = (0, 0, 0))
        # On affiche le cadran du premier point

        pointBaseDebut = self.objetDebut.getBase("Base Deb", UniteDecodageSS.COULEUR_AXEMIDI)
        pointLumiereDebut = self.objetDebut.getHeure("Debut", (0, 0, 0))

        # On affiche le cadran du deuième point

        pointBaseFin = self.objetFin.getBase("Base Fin", UniteDecodageSS.COULEUR_AXEMIDI)
        pointLumiereFin = self.objetFin.getHeure("Fin", (0, 0, 0))

        return [self.segmentBaseDebut, pointBaseDebut, self.segmentLumiereDebut, pointLumiereDebut,
                self.segmentBaseFin, pointBaseFin, self.segmentLumiereFin, pointLumiereFin,
                ]

    def getAttributsSegment(self):
        """
        Retourne les caractéristiques géométriques du segment :
        - longueur en kilomètres
        - azimut (degrés, 0 = nord, sens horaire)
        """

        def minutesDepuisMidi(horaire: str) -> int:
            """Retourne le nombre de minutes depuis midi à partir d'une heure au format 'HH:MM'."""
            heures, minutes = map(int, horaire.split(":"))
            total_minutes = heures * 60 + minutes
            minutes_midi = 12 * 60
            return abs(total_minutes - minutes_midi)

        # Heure Cadran pour chacun des segment
        heureCadranA = self.objetDebut.getHeureCadran()
        heureCadranB = self.objetFin.getHeureCadran()
        minuteCadranA = minutesDepuisMidi(heureCadranA)
        minuteCadranB = minutesDepuisMidi(heureCadranB)

        azA = self.azimutLumiereDebut
        azOppA = (azA + 180) % 360
        azB = self.azimutLumiereFin
        azOppB = (azB + 180) % 360

        indexA = azA / 6
        indexOppA = azOppA / 6
        indexB = azB / 6
        indexOppB = azOppB / 6

        # Angle entre la base et le segment
        angleMidiA = self.angleSegmentMidiDebut
        angleMidiB = self.angleSegmentMidiFin

        # Azimu et Index autour de l'axe de Midi
        azMidi = self.azimutMidi
        azOppMidi = (azMidi + 180) % 360
        indexMidi = azMidi / 6

        return [
            (0, "Heure Cadran Debut", f"{heureCadranA} - {minuteCadranA}mn"),
            (0, "Heure Cadran Fin", f"{heureCadranB} - {minuteCadranB}mn"),
            (1, "Distance Debut", f"{self.distanceLumiereDebut:.02f}km"),
            (1, "Distance Fin", f"{self.distanceLumiereFin:.02f}km"),
            (2, "Azimut Debut", f"{azA:.02f}° - {azOppA:.02f}°"),
            (2, "Azimut Fin", f"{azB:.02f}° - {azOppB:.02f}°"),
            (3, "Azimut Debut Base 60", f"{indexA:.02f} - {indexOppA:.02f}"),
            (3, "Azimut Debut Base 60", f"{indexB:.02f} - {indexOppB:.02f}"),
            (4, "Angle Debut % Base", f"{angleMidiA:.02f}°"),
            (4, "Angle Fin % Base", f"{angleMidiB:.02f}°"),
            (5, "Azimut Midi", f"{azMidi:.02f}° - {azOppMidi:.02f}°"),
            (5, "Index Midi", f"{indexMidi:.02f}"),
                ]

    def calculIndex(self):
        """
        Exemple d’algorithme de décodage.
        Convertit l’azimut en colonne, et la longueur en ligne.
        - Azimut ∈ [0, 360] → 12 segments → index colonne = azimut // 30
        - Longueur ∈ [0, 120 km] → 12 intervalles → index ligne = longueur // 10
        """
        indexMot = 1
        enigme = 1

        return (enigme, indexMot)
