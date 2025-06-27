class LigneCirculaire:
    def __init__(self, ligne, masque=None):
        self.ligne = ligne
        self.masque = masque or [True] * len(ligne)  # True = mot visible

    def __getitem__(self, index):
        n = len(self.ligne)
        if n == 0:
            raise ValueError("Ligne vide")

        index = index % n

        # S'il est masqué, on retourne None
        if not self.masque[index]:
            return ""

        return self.ligne[index]




class DictionnaireEnigmes:
    def __init__(self, cheminFichier):
        self.filtrageGlobal = False
        self.chargerFichier(cheminFichier)

    def getFiltrageGlobal(self):
        return self.filtrageGlobal
    
    def setFiltrageGlobal(self, filtrage = True):
        self.filtrageGlobal = filtrage

    def chargerFichier(self, cheminFichier):
        self.dictionnaire = []
        self.indexCategories = {
            "action": [False, []],
            "localise": [False, []],
            "pointFixe": [False, []],
            "direction": [False, []],
            "origine": [False, []],
            "ordre": [False, []],
            "nombre": [False, []],
            "pointCardinal": [False, []],
            "spatial": [False, []],
            "mesure": [False, []],
            "utilisable": [False, []]
        }
        with open(cheminFichier, "r", encoding="utf-8") as fichier:
            for numeroEnigme, ligne in enumerate(fichier.readlines()):
                mots = ligne.strip().split()
                if not mots:
                    continue  # ligne vide
                titre = mots[0]
                ligneSansTags = []
                for i, mot in enumerate(mots[1:]):  # On ignore le titre
                    if "[" in mot and mot.endswith("]"):
                        motNettoye, tag = mot.split("[")
                        tag = tag.rstrip("]")
                        ligneSansTags.append(motNettoye)
                        if tag in self.indexCategories:
                            self.indexCategories[tag][1].append((motNettoye, numeroEnigme, len(ligneSansTags) - 1))
                    else:
                        ligneSansTags.append(mot)
                self.dictionnaire.append((titre, ligneSansTags))


    def getCategories(self):
        return list(self.indexCategories.keys())

    def getIndexCategories(self):
        return self.indexCategories

    def getCategoriesSelectionnees(self):
        return [categorie for categorie, (actif, _) in self.indexCategories.items() if actif]

    def activerCategorie(self, nomCategorie, actif=True):
        if nomCategorie in self.indexCategories:
            self.indexCategories[nomCategorie][0]=actif

    def getMot(self, enigmeIndex, motIndex):
        if enigmeIndex >= len(self.dictionnaire):
            raise IndexError("Indice d'énigme hors limites")
        titre, ligne = self.dictionnaire[enigmeIndex]
        if not ligne:
            raise ValueError("Ligne vide")
        motIndex = motIndex % len(ligne)
        return ligne[motIndex]

    def __len__(self):
        return len(self.dictionnaire)

    def __getitem__(self, enigmeIndex):
        titre, ligne = self.dictionnaire[enigmeIndex]

        # Si le filtrage n'est pas actif, on renvoie la ligne complète
        if not self.filtrageGlobal:
            return LigneCirculaire(ligne)

        # Création d’un masque de visibilité
        masque = [False] * len(ligne)
        categories_actives = self.getCategoriesSelectionnees()
        for categorie in categories_actives:
            for (mot, idxEnigme, idxMot) in self.indexCategories[categorie][1]:
                if idxEnigme == enigmeIndex:
                    masque[idxMot] = True

        return LigneCirculaire(ligne, masque)

    def getTitres(self):
        return [ligne[0] if ligne else "" for ligne in self.dictionnaire]

    def getTitre(self, enigmeIndex):
        return self.dictionnaire[enigmeIndex][0]

    def nbMotMax(self):
        return max((len(ligne) for _, ligne in self.dictionnaire), default=0)


class SequenceCategorie(list):
    def __init__(self, dictionnaire):
        super().__init__()
        self.listeCategories = []
        self.dictionnaire = dictionnaire  # instance de DictionnaireEnigmes

    def ajouterCategorie(categorie):
        if categorie in self.dictionnaire.getListeCategories():
            self.listeCategories.append(categorie)   
            self.append(None) 
            return len(self.listeCategories)-1
        return None

    def retirerCategorie(self, index):
        if 0 <= index < len(self.listeCategories):
            del self.listeCategories[index]
            del self[index]



if __name__ == "__main__":
    dico = DictionnaireEnigmes("data/livre.txt")
    print(dico[5][10])
    for categorie in dico.getCategories():
        print(categorie, ":",dico.getIndexCategories()[categorie])

