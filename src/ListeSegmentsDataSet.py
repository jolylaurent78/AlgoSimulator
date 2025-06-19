import csv
from collections import OrderedDict

# Moteur Algo générique
from src.AlgorithmeManager import ModuleAlgo


#
# Gestion du dataset: La lste des 7 chemins + chemin final
#
class ListeSegmentsDataSet(ModuleAlgo):
    """
    Dataset pour l'algorithme Stylet Initial basé sur un fichier CSV d'événements historiques.
    Chaque événement est indexé par son intitulé (colonne 'Evènement').
    """

    def __init__(self, chemin_csv):
        self.evenements = OrderedDict()  # { "15 Aout 778..." : {"Note": ..., "Date": ...} }

        with open(chemin_csv, newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                cle = row["Evènement"]
                self.evenements[cle] = {
                    "DateSegment": row["DateSegment"],
                    "Date": row["Date"],
                    "Stylet": row["Stylet"],
                    "LettreDecl": row["LettreDecl"],
                    "Base1": row["Base1"],
                    "Base2": row["Base2"],
                }
                if i == 0: # Première ligne pour la valeur par défaut
                    self.segment = cle
        self.date = None
        self.dateSegment = None
        self.lettreDecl = None
        self.stylet = None
        self.base1 = None
        self.base2 = None        
        super().__init__()


    def getValeursSegment(self):
        """
        Retourne la liste des événements (libellés).
        """
        return list(self.evenements.keys())

    def getValeurPourSegment(self, segment, attribut):
        """
        Retourne une valeur du dataset pour un segment donné.

        Recherche insensible à la casse sur l'attribut.
        """
        infos = self.evenements.get(segment)
        if infos is None:
            raise ValueError(f"[Dataset] Le segment '{segment}' est introuvable.")

        for cle, val in infos.items():
            if cle.lower() == attribut.lower():
                return val

        raise ValueError(f"[Dataset] L’attribut '{attribut}' est introuvable dans les données du segment '{segment}'.")

    def calculer(self):
        """
        Met à jour automatiquement les informations liées au segment sélectionné :
        - self.date ← colonne 'Date'
        - self.noteSegment ← colonne 'Note'
        """
        if self.segment not in self.evenements:
            raise ValueError(f"Le segment '{self.segment}' n'existe pas dans le dataset.")

        infos = self.evenements[self.segment]
        self.date = infos["Date"]
        self.dateSegment = infos["DateSegment"]
        self.stylet = infos["Stylet"]
        self.lettreDecl = infos["LettreDecl"]
        self.base1 = infos["Base1"]
        self.base2 = infos["Base2"]
