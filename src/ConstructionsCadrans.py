import csv

# Base de données des villes
from src.data_loader import villes_dict
from src.affichage_objets import SegmentEntreVilles

class ConstructionsCadrans(dict):

    def __init__(self, chemin_csv):

        with open(chemin_csv, newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = row["Date"]
                # On rajoute le sylet initial
                stylet = ObjetStylet(date, row["Stylet"])
                self[row["Stylet"]] = stylet
                # La lumiere
                lumiere = ObjetLumiere(date, row["Lumiere"], row["Stylet"])
                self[row["Lumiere"]] = lumiere
                # Les 2 bases
                base1 = ObjetBase(date, row["Base1"], row["Stylet"])
                base2 = ObjetBase(date, row["Base2"], row["Stylet"])
                self[row["Base1"]] = base1
                self[row["Base2"]] = base2
                # Les 4 points finaux
                final1A = ObjetFinal(date, row["Final1A"], row["Base1"])
                final1B = ObjetFinal(date, row["Final1B"], row["Base1"])
                self[row["Final1A"]] = final1A
                self[row["Final1B"]] = final1B
                final2A = ObjetFinal(date, row["Final2A"], row["Base2"])
                final2B = ObjetFinal(date, row["Final2B"], row["Base2"])
                self[row["Final2A"]] = final2A
                self[row["Final2B"]] = final2B

class ObjetCadran:
    def __init__(self, date, objet : str, base : str, ouverture : str, autre : str = None):
        self.date = date
        self.objet = villes_dict[objet]
        self.ouverture = villes_dict[ouverture]
        self.base = villes_dict[base]
        if autre is not None:
            self.lumiere = villes_dict[autre]

    def getVilleObjetCadran(self):
        return self.objet
    
    def axeMidiCadran(self) : 
        return SegmentEntreVilles(self.base, self.ouverture)

    def getBase(self):
        return self.base
    
class ObjetStylet(ObjetCadran):
    def __init__(self, date, styletVille):
        super().__init__(date, styletVille, "Coetquidan", "Golfe-Juan")    


class ObjetLumiere(ObjetCadran):
    def __init__(self, date, lumiereVille,styletVille):
        super().__init__(date, lumiereVille, "Coetquidan", "Golfe-Juan", styletVille )  

    
class ObjetBase(ObjetCadran):
    def __init__(self, date, baseVille, styletVille):
        super().__init__(date, baseVille, baseVille, "Bourges", styletVille )  

    
class ObjetFinal(ObjetCadran):
    def __init__(self, date, finalVille, baseVille):
        super().__init__(date, finalVille, baseVille, "Bourges")  


if __name__ == "__main__":
    constructionsCadrans = ConstructionsCadrans("data/constructionsCadrans.csv")
