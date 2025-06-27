from itertools import product

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

    def getListeCategorie(self, categorie):
        return self.indexCategories[categorie][1]
    
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


class SequenceCategorie:
    def __init__(self, dictionnaire):
        super().__init__()
        self.listeCategories = []           # liste des catégories de la séquence
        self.selections = []                # liste des mots sélectionnés pour chaque catégorie
        self.dictionnaire = dictionnaire    # instance de DictionnaireEnigmes
        self.modeIndexRelatif = False       # Par défaut, on travaille en Index absolu

    def setModeIndexRelatif(self, modeIndex):
        self.modeIndexRelatif = modeIndex

    def ajouterCategorie(self, categorie):
        if categorie in self.dictionnaire.getCategories():
            self.listeCategories.append(categorie)   
            self.selections.append([])              # aucune sélection au départ
            return len(self.listeCategories)-1
        return None

    def retirerCategorie(self, index):
        if 0 <= index < len(self.listeCategories):
            del self.listeCategories[index]
            del self.selections[index]

    
    def mettreAJourCategorie(self, index, nouvelleCategorie):
        if nouvelleCategorie not in self.dictionnaire.getCategories():
            return False  # Catégorie inconnue

        if 0 <= index < len(self.listeCategories):
            self.listeCategories[index] = nouvelleCategorie
            self.selections[index] = []  # Réinitialiser les sélections
            return True
        elif index == len(self.listeCategories):
            self.ajouterCategorie(nouvelleCategorie)
            return True
        return False


    def ajouterMotSelectionne(self, indexCategorie, indexEnigme, indexMot):
        if 0 <= indexCategorie < len(self.selections):
            if (indexEnigme, indexMot) not in self.selections[indexCategorie]:
                self.selections[indexCategorie].append((indexEnigme, indexMot))

    def retirerMotSelectionne(self, indexCategorie, indexEnigme, indexMot):
        if 0 <= indexCategorie < len(self.selections):
            if (indexEnigme, indexMot) in self.selections[indexCategorie]:
                self.selections[indexCategorie].remove((indexEnigme, indexMot))

    def getMotsSelectionnes(self, indexCategorie):
        if 0 <= indexCategorie < len(self.selections):
            return self.selections[indexCategorie]
        return []

    def getCategorie(self, indexCategorie):
        if 0 <= indexCategorie < len(self.listeCategories):
            return self.listeCategories[indexCategorie]
        return None

    def afficheSequence(self):
        listeStr = ""
        for c in self.listeCategories:
            listeStr+=f"{c} : "
        print(listeStr)


    def getComplexiteSequence(self):
        i =0
        complexite = 1
        for index in range(len(self.listeCategories)):
            if len(self.selections[index])>0:
                i+=1
                complexite*=len(self.selections[index])
            else:
                break
        if i ==0:
            return 0, 0
        else:
            return i, complexite 


    def listeToutesSequencesPossibles(self):
        if not self.selections or any(len(sel) == 0 for sel in self.selections):
            return []

        # Produit cartésien de toutes les sélections
        toutesCombinaisons = product(*self.selections)
        resultats = []

        for combinaison in toutesCombinaisons:
            if self.modeIndexRelatif:
                # On part de (0,0) et on calcule les deltas
                chemin = []
                prev = combinaison[0]
                chemin = [f"({prev[0]}, {prev[1]})"]
                for curr in combinaison[1:]:
                    dx = curr[0] - prev[0]
                    dy = curr[1] - prev[1]
                    chemin.append(f"(+{dx}, +{dy})" if dx >= 0 and dy >= 0 else f"({dx}, {dy})")
                    prev = curr
            else:
                # Coordonnées absolues
                chemin = [f"({e},{m})" for (e, m) in combinaison]

            resultats.append(" → ".join(chemin))

        return resultats


if __name__ == "__main__":
    dico = DictionnaireEnigmes("data/livre.txt")
    print(dico[5][10])
    for categorie in dico.getCategories():
        print(categorie, ":",dico.getIndexCategories()[categorie])

