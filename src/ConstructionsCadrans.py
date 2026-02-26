import csv

# Base de données des villes
from src.data_loader import villes_dict
from src.affichage_objets import PointGraphique, SegmentEntreVilles


class ConstructionsCadrans(dict):

    def __init__(self, chemin_csv):

        super().__init__()

        # Nouveau format attendu: constructionsCadransMultiSolutions.csv
        # Colonnes: Date, TypeStylet, Stylet, HeureStylet, Lumiere, HeureLumiere
        lignesParDate = {}
        with open(chemin_csv, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            champs = reader.fieldnames or []
            if "TypeStylet" not in champs:
                raise ValueError(
                    "Format CSV invalide: colonne 'TypeStylet' absente. "
                    "Attendu: constructionsCadransMultiSolutions.csv"
                )

            for row in reader:
                date = (row.get("Date") or "").strip()
                if date == "":
                    continue
                lignesParDate.setdefault(date, []).append(row)

        # Cache pour ne pas recréer la même base quand elle apparaît plusieurs fois
        # Clé = (date, baseVille)
        baseCache = {}

        for date, lignes in lignesParDate.items():
            gnomonRow = None
            lignesBases = []

            for row in lignes:
                typeStylet = (row.get("TypeStylet") or "").strip()
                if typeStylet == "Gnomon":
                    if gnomonRow is not None:
                        raise ValueError(f"Plusieurs lignes Gnomon pour la date {date}")
                    gnomonRow = row
                elif typeStylet == "Stylet":
                    lignesBases.append(row)
                else:
                    raise ValueError(
                        f"TypeStylet inconnu '{typeStylet}' pour la date {date}"
                    )

            if gnomonRow is None:
                raise ValueError(f"Aucune ligne Gnomon pour la date {date}")

            # Ligne Gnomon = Stylet initial + Lumière
            styletVille = (gnomonRow.get("Stylet") or "").strip()
            heureStylet = (gnomonRow.get("HeureStylet") or "").strip()
            lumiereVille = (gnomonRow.get("Lumiere") or "").strip()
            heureLumiere = (gnomonRow.get("HeureLumiere") or "").strip()

            self.ajouterObjetUnique(styletVille, ObjetStylet(date, heureStylet, styletVille))
            self.ajouterObjetUnique(
                lumiereVille, ObjetLumiere(date, heureLumiere, lumiereVille, styletVille)
            )

            # Lignes Stylet = Bases + (éventuels) Finals
            for row in lignesBases:
                baseVille = (row.get("Stylet") or "").strip()
                heureBase = (row.get("HeureStylet") or "").strip()
                finalVille = (row.get("Lumiere") or "").strip()
                heureFinal = (row.get("HeureLumiere") or "").strip()

                if baseVille == "":
                    raise ValueError(f"Base (Stylet) vide pour la date {date}")

                cacheKey = (date, baseVille)
                if cacheKey in baseCache:
                    baseObj = baseCache[cacheKey]
                    if baseObj.getHeureCadran() != heureBase:
                        raise ValueError(
                            f"Incohérence: la base '{baseVille}' (date {date}) "
                            f"a des heures différentes: '{baseObj.getHeureCadran()}' vs '{heureBase}'"
                        )
                else:
                    baseObj = ObjetBase(date, heureBase, baseVille, styletVille)
                    baseCache[cacheKey] = baseObj
                    self.ajouterObjetUnique(baseVille, baseObj)

                # Certaines lignes peuvent définir une base sans point de lumière associé
                # (ex: Lumiere/HeureLumiere vides) => on ne crée pas d'ObjetFinal.
                if finalVille == "" or heureFinal == "":
                    continue

                self.ajouterObjetUnique(finalVille, ObjetFinal(date, heureFinal, finalVille, baseVille))

    def ajouterObjetUnique(self, nomVille: str, objet):
        nomVille = (nomVille or "").strip()
        if nomVille == "":
            raise ValueError("Nom de ville vide dans le CSV")
        if nomVille in self:
            raise ValueError(f"Collision: la ville '{nomVille}' est déjà définie dans ConstructionsCadrans")
        self[nomVille] = objet


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
        return SegmentEntreVilles(self.base, self.midi, couleur=couleur)

    def getBase(self, nom: str, couleur):
        point = PointGraphique(self.base, couleur=couleur, afficherNom=True, epaisseur=4)
        point.setNom(nom)
        return point

    def getLigneOmbre(self, couleur):
        return SegmentEntreVilles(self.base, self.ombre, couleur=couleur)

    def getHeure(self, nom: str, couleur):
        point = PointGraphique(self.ombre, couleur=couleur, afficherNom=True, epaisseur=4)
        point.setNom(nom)
        return point

    def getReference(self):
        return self.ombre

    def getHeureCadran(self):
        return self.heureCadran

    def typeCadran(self):
        pass

    def getTriangleCadran(self):
        pass


class ObjetStylet(ObjetCadran):
    def __init__(self, date: str, heureCadran : str, styletVille: str):
        super().__init__(date, heureCadran, styletVille, "Coetquidan", "Golfe-Juan")

    def typeCadran(self):
        return "stylet"


class ObjetLumiere(ObjetCadran):
    def __init__(self, date: str, heureCadran: str, lumiereVille: str, styletVille: str):
        super().__init__(date, heureCadran, lumiereVille, "Coetquidan", "Golfe-Juan", styletVille)

    def getTriangleCadran(self):
        ptBase = PointGraphique(self.base)
        ptOuverture = PointGraphique(self.autre)
        ptLumiere = PointGraphique(self.ombre)
        return ptOuverture, ptBase, ptLumiere

    def typeCadran(self):
        return "lumiere"


class ObjetBase(ObjetCadran):
    def __init__(self, date: str, heureCadran: str, baseVille: str, styletVille: str):
        super().__init__(date, heureCadran, styletVille, baseVille, "Bourges")

    def getReference(self):
        return self.base

    def typeCadran(self):
        return "base"


class ObjetFinal(ObjetCadran):
    def __init__(self, date: str, heureCadran: str, finalVille: str, baseVille: str):
        super().__init__(date, heureCadran, finalVille, baseVille, "Bourges")

    def typeCadran(self):
        return "final"

    def getTriangleCadran(self):
        ptBase = PointGraphique(self.base)
        ptOuverture = PointGraphique(self.midi)
        ptLumiere = PointGraphique(self.ombre)
        return ptOuverture, ptBase, ptLumiere


if __name__ == "__main__":
    constructionsCadrans = ConstructionsCadrans("data/constructionsCadransMultiSolutions.csv")
