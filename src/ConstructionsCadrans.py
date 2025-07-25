import csv

# Base de données des villes
from src.data_loader import villes_dict
from src.affichage_objets import PointGraphique, SegmentEntreVilles

class ConstructionsCadrans(dict):

    def __init__(self, chemin_csv):

        with open(chemin_csv, newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = row["Date"]
                # On rajoute le sylet initial
                stylet = ObjetStylet(date, row["HeureStylet"], row["Stylet"])
                self[row["Stylet"]] = stylet
                # La lumiere
                lumiere = ObjetLumiere(date, row["HeureLumiere"], row["Lumiere"], row["Stylet"])
                self[row["Lumiere"]] = lumiere
                # Les 2 bases
                base1 = ObjetBase(date, row["HeureBase1"], row["Base1"], row["Stylet"])
                base2 = ObjetBase(date, row["HeureBase2"], row["Base2"], row["Stylet"])
                self[row["Base1"]] = base1
                self[row["Base2"]] = base2
                # Les 4 points finaux
                final1A = ObjetFinal(date, row["HeureFinal1A"], row["Final1A"], row["Base1"])
                final1B = ObjetFinal(date, row["HeureFinal1B"], row["Final1B"], row["Base1"])
                self[row["Final1A"]] = final1A
                self[row["Final1B"]] = final1B
                final2A = ObjetFinal(date, row["HeureFinal2A"], row["Final2A"], row["Base2"])
                final2B = ObjetFinal(date, row["HeureFinal2B"],row["Final2B"], row["Base2"])
                self[row["Final2A"]] = final2A
                self[row["Final2B"]] = final2B

class ObjetCadran:
    def __init__(self, date, heureCadran: str, ombre : str, base : str, midi : str, autre : str = None):
        self.date = date
        self.heureCadran = heureCadran
        self.ombre = villes_dict[ombre]
        self.midi = villes_dict[midi]
        self.base = villes_dict[base]
        if autre is not None:
            self.autre = villes_dict[autre]

    def getVilleObjetCadran(self):
        return self.ombre
    
    def axeMidiCadran(self, couleur) : 
        return SegmentEntreVilles(self.base, self.midi, couleur = couleur)

    def getBase(self, nom: str, couleur):
        point = PointGraphique(self.base, couleur = couleur, afficherNom = True, epaisseur = 4)
        point.setNom(nom)
        return point

    def getLigneOmbre(self, couleur):
        return SegmentEntreVilles(self.base, self.ombre, couleur = couleur)
            
    def getHeure(self, nom: str, couleur):
        point = PointGraphique(self.ombre, couleur = couleur, afficherNom = True, epaisseur = 4)
        point.setNom(nom)
        return point
    
    def getReference(self):
        return self.ombre

    def getHeureCadran(self):
        return self.heureCadran
    
class ObjetStylet(ObjetCadran):
    def __init__(self, date: str, heureCadran : str, styletVille: str):
        super().__init__(date, heureCadran, styletVille, "Coetquidan", "Golfe-Juan")    

    
class ObjetLumiere(ObjetCadran):
    def __init__(self, date: str, heureCadran: str, lumiereVille: str, styletVille: str):
        super().__init__(date, heureCadran, lumiereVille, "Coetquidan", "Golfe-Juan", styletVille )  

    
class ObjetBase(ObjetCadran):
    def __init__(self, date: str, heureCadran: str, baseVille: str, styletVille: str):
        super().__init__(date, heureCadran, styletVille, baseVille, "Bourges")  

    def getReference(self):
        return self.base
    
class ObjetFinal(ObjetCadran):
    def __init__(self, date: str, heureCadran: str, finalVille: str, baseVille: str):
        super().__init__(date, heureCadran, finalVille, baseVille, "Bourges")  



if __name__ == "__main__":
    constructionsCadrans = ConstructionsCadrans("data/constructionsCadrans.csv")
