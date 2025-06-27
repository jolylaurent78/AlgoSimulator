import pandas as pd

class Reliquats:
    def __init__(self, cheminFichier):
        self.cheminFichier = cheminFichier
        self.df = pd.read_csv(cheminFichier, skipinitialspace=True)

    # On rajoute les méthodes pour que Reliquats se comporte comme une liste classique
    def __len__(self):
        return len(self.df)

    def __getitem__(self, index):
        row = self.df.iloc[index]
        return (row["Source"], row["Destination"])

    def __iter__(self):
        for _, row in self.df.iterrows():
            yield (row["Source"], row["Destination"])

    def afficherApercu(self, lignes=5):
        print(self.df.head(lignes))

    def filtrer(self, **conditions):
        df_filtré = self.df
        for col, val in conditions.items():
            df_filtré = df_filtré[df_filtré[col] == val]
        return df_filtré

    def mettreAJour(self, index, colonne, valeur):
        if index in self.df.index and colonne in self.df.columns:
            self.df.at[index, colonne] = valeur
        else:
            print(f"Index ou colonne invalide : {index}, {colonne}")

    def monterLigne(self, index):
        if index > 1 and index < len(self.df):
            ligne_courante = self.df.loc[index -1, "Ligne"]
            ligne_au_dessus = self.df.loc[index - 2, "Ligne"]
            self.df.loc[index -1, "Ligne"], self.df.loc[index - 2, "Ligne"] = ligne_au_dessus, ligne_courante
            self.df.sort_values("Ligne", inplace=True)
            self.df.reset_index(drop=True, inplace=True)


    def descendreLigne(self, index):
        if index < len(self.df):
            ligne_courante = self.df.loc[index - 1, "Ligne"]
            ligne_en_dessous = self.df.loc[index, "Ligne"]
            self.df.loc[index -1, "Ligne"], self.df.loc[index , "Ligne"] = ligne_en_dessous, ligne_courante
            self.df.sort_values("Ligne", inplace=True)
            self.df.reset_index(drop=True, inplace=True)

    def echangerVilles(self, index):
        temp = self.df.loc[index-1, "Source"]
        self.df.loc[index-1, "Source"] = self.df.loc[index-1, "Destination"]
        self.df.loc[index-1, "Destination"] = temp

    def sauvegarder(self, chemin=None):
        chemin_sortie = chemin or self.cheminFichier
        self.df.to_csv(chemin_sortie, index=False)

    def nombreLignes(self):
        return len(self.df)

if __name__ == "__main__":
    listeReliquats = Reliquats("data/reliquats.csv")
    listeReliquats.afficherApercu()