
from src.data_loader import villes_dict
from src.affichage_objets import SegmentEntreVilles, PointGraphique, LigneEntreVilles
from src.ConstructionsCadrans import ObjetCadran

class UniteDecodageSS:
    def __init__(self, objetSource: ObjetCadran, objetMilieu: ObjetCadran, objetDestination: ObjetCadran):
        self.objetSource = objetSource
        self.objetMilieu = objetMilieu
        self.objetDestination = objetDestination
        
        self.segmentA = SegmentEntreVilles(objetSource.getVilleObjetCadran(), objetMilieu.getVilleObjetCadran())
        self.segmentB = SegmentEntreVilles(objetMilieu.getVilleObjetCadran(), objetDestination.getVilleObjetCadran())        
        self.azimutSegmentA = self.segmentA.getAzimutCarte()
        self.azimutSegmentB = self.segmentB.getAzimutCarte()
        self.distanceSegment = self.segmentA.distanceSegment()+self.segmentB.distanceSegment()

    def construireRepresentationCarte(self):
        """
        Retourne la liste des objets graphiques à afficher pour visualiser ce segment.
        """
        
        # On rajoute d'abord les points Source, Milieu et Destination
        pointS = PointGraphique(self.objetSource.getVilleObjetCadran(), afficherNom = True)
        pointM = PointGraphique(self.objetMilieu.getVilleObjetCadran(), afficherNom = True)
        pointD = PointGraphique(self.objetDestination.getVilleObjetCadran(), afficherNom = True)
        pointS.setNom("S")
        pointM.setNom("M")
        pointD.setNom("D")   

        # On rajoute l'axe du cadran solaire associé
        segmentAxeCadranMilieu = self.objetMilieu.axeMidiCadran()
        segmentAxeCadranMilieu.setCouleur((255, 145, 34))
        ligneAxeCadranMilieu = LigneEntreVilles(segmentAxeCadranMilieu.ville1, segmentAxeCadranMilieu.ville2, couleur = (255, 145, 34))
        pointBaseMilieu = PointGraphique(self.objetMilieu.getBase(), afficherNom = True)
        pointBaseMilieu.setNom("Base M") 
        self.azimutBaseM = ligneAxeCadranMilieu.getAzimutCarte()

        segmentAxeCadranDestination = self.objetDestination.axeMidiCadran()
        segmentAxeCadranDestination.setCouleur((255, 145, 34))
        ligneAxeCadranDestination = LigneEntreVilles(segmentAxeCadranDestination.ville1, segmentAxeCadranDestination.ville2, couleur = (255, 145, 34))
        pointBaseDestination = PointGraphique(self.objetDestination.getBase(), afficherNom = True)
        pointBaseDestination.setNom("Base D")    
        self.azimutBaseD = ligneAxeCadranDestination.getAzimutCarte()

        return [pointS, pointM, pointD, 
                self.segmentA, self.segmentB, 
                pointBaseMilieu, segmentAxeCadranMilieu, ligneAxeCadranMilieu, 
                pointBaseDestination, segmentAxeCadranDestination, ligneAxeCadranDestination]

    def getAttributsSegment(self):
        """
        Retourne les caractéristiques géométriques du segment :
        - longueur en kilomètres
        - azimut (degrés, 0 = nord, sens horaire)
        """
        distSM = self.segmentA.distanceSegment()
        distMD = self.segmentB.distanceSegment()

        # On calcule et affiche d'abord les azimuts des cadrans (en direct et en opposé) A = SM B =MD
        azA = self.azimutSegmentA
        azOppA = (azA + 180) % 360
        azB = self.azimutSegmentB
        azOppB = (azB + 180) % 360

        # On calcule le delta entre les deux segments
        delta = (azOppA - azB) % 360
        deltaOpp = (360 - delta) % 360

        # On calcule l'azimut de la base du cadran associé de la base vers le stylet
        baseM = self.azimutBaseM
        baseOppM = (baseM + 180 ) % 360

        baseD = self.azimutBaseD
        baseOppD = (baseD + 180) % 360

        # On calcule l'azimut MS et MD par rapport à l'axe des stylets respetifs M et D
        azMSCadran = azOppA - baseM
        azMDCadran = azB - baseD

        return [
            (0, "Longueur SM", f"{distSM:.02f}km"),
            (0, "Longueur MD", f"{distMD:.02f}km"),
            (1, f"Azimut SM", f"{azA:.02f}° - {azOppA:.02f}°"),
            (1, f"Azimut MD", f"{azB:.02f}° - {azOppB:.02f}°"),
            (2, f"Delta", f"{delta:.02f}° - {deltaOpp:.02f}°"),
            (3, f"Azimut Base M", f"{baseM:.02f}° - {baseOppM:.02f}°"),
            (3, f"Azimut Base D", f"{baseD:.02f}° - {baseOppD:.02f}°"),
            (4, f"Azimut MS % Cadran", f"{azMSCadran:.02f}°"),
            (4, f"Azimut MD % Cadran", f"{azMDCadran:.02f}°"),
        ]

    def calculIndex(self):
        """
        Exemple d’algorithme de décodage.
        Convertit l’azimut en colonne, et la longueur en ligne.
        - Azimut ∈ [0, 360] → 12 segments → index colonne = azimut // 30
        - Longueur ∈ [0, 120 km] → 12 intervalles → index ligne = longueur // 10
        """
        indexMot = int(self.azimutSegmentA / 24)
        enigme = int(self.distanceSegment / 91.5)

        return (enigme, indexMot)
