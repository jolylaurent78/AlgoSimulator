import tkinter as tk
from tkinter import ttk, Frame, Label, Canvas
from PIL import Image, ImageTk
import numpy as np
import cv2

# Base de données des villes
from src.data_loader import villes_dict

# Gestion des reliquats
from src.reliquats import Reliquats

# Gestion de la carte
from src.carte_config import carteConfig

# Affichage des objets graphiques
from src.affichage_objets import *

class InterfaceSS(tk.Tk):
    def __init__(self):
        super().__init__()
        style = ttk.Style()
        style.configure("TitreFrame.TLabelframe.Label", font=("Arial", 10, "bold"))

        self.title("Décodeur - Chasse au Trésor")
        self.geometry("1600x900")
        self.configure(bg="lightgray")

        # PanedWindow horizontal : Gauche / Centre / Droite
        panedHorizontal = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=5)
        panedHorizontal.pack(fill=tk.BOTH, expand=True)

        # Frame gauche
        self.frameGauche = tk.Frame(panedHorizontal, width=300, relief=tk.RIDGE, borderwidth=2)
        panedHorizontal.add(self.frameGauche, minsize=250)

        # PanedWindow vertical (centre)
        panedVerticalCentre = tk.PanedWindow(panedHorizontal, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=5)
        panedHorizontal.add(panedVerticalCentre, minsize=800)

        self.frameCentreHaut = tk.Frame(panedVerticalCentre, relief=tk.RIDGE, borderwidth=2)
        self.frameCentreBas = tk.Frame(panedVerticalCentre, relief=tk.RIDGE, borderwidth=2)
        panedVerticalCentre.add(self.frameCentreHaut, minsize=300)
        panedVerticalCentre.add(self.frameCentreBas, minsize=300)

        # Frame droite
        self.frameDroite = tk.Frame(panedHorizontal, width=400, relief=tk.RIDGE, borderwidth=2)
        panedHorizontal.add(self.frameDroite, minsize=250)


        # Initialisation des composants IHM
        self.ihmReliquats = ListeReliquatsIHM(self.frameGauche)
        self.ihmAlgo = AlgorithmeSSIHM(self.frameCentreHaut)
        self.ihmDico = DicoIHM(self.frameCentreBas)
        self.ihmSolutions = SolutionIHM(self.frameDroite)

class ListeReliquatsIHM:
    def __init__(self, parent):
        # On charge la liste des reliquats à analyser
        self.listeReliquats = Reliquats("data/reliquats.csv")

        # On crée le Label Frame global
        self.frame = ttk.LabelFrame(parent, text="Liste des reliquats", style="TitreFrame.TLabelframe")
        self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Zone de boutons au-dessus de la TreeView
        self.frameBoutons = tk.Frame(self.frame)
        self.frameBoutons.pack(side=tk.TOP, anchor=tk.W, pady=(8, 2))


        self.icones = {
            "reload": tk.PhotoImage(file="images/reload.png"),
            "up":     tk.PhotoImage(file="images/up.png"),
            "down":   tk.PhotoImage(file="images/down.png"),
            "swap":   tk.PhotoImage(file="images/swap.png"),
            "save":   tk.PhotoImage(file="images/save.png")
        }

        self.boutonReload = tk.Button(self.frameBoutons, image=self.icones["reload"], command=self.actionReload, relief=tk.RAISED, bd=1)
        self.boutonReload.pack(side=tk.LEFT, padx=2)
 
        self.boutonSave = tk.Button(self.frameBoutons, image=self.icones["save"], command=self.actionSauvegarder, relief=tk.RAISED, bd=1)
        self.boutonSave.pack(side=tk.LEFT, padx=2)

        self.boutonUp = tk.Button(self.frameBoutons, image=self.icones["up"], command=self.actionMonter, relief=tk.RAISED, bd=1)
        self.boutonUp.pack(side=tk.LEFT, padx=2)

        self.boutonDown = tk.Button(self.frameBoutons, image=self.icones["down"], command=self.actionDescendre, relief=tk.RAISED, bd=1)
        self.boutonDown.pack(side=tk.LEFT, padx=2)

        self.boutonSwap = tk.Button(self.frameBoutons, image=self.icones["swap"], command=self.actionSwap, relief=tk.RAISED, bd=1)
        self.boutonSwap.pack(side=tk.LEFT, padx=2)



        # Création de la TreeView
        self.tree = ttk.Treeview(self.frame, columns=("#","Enigme","Indice","Source", "Destination"), show="headings", selectmode="browse")
        self.tree.heading("#", text="#")
        self.tree.heading("Enigme", text="Enigme")
        self.tree.heading("Indice", text="Indice")        
        self.tree.heading("Source", text="Source")
        self.tree.heading("Destination", text="Destination")
        self.tree.column("#", width=30, anchor="center")
        self.tree.column("Enigme", width=50, anchor="center")
        self.tree.column("Indice", width=150, anchor="w")
        self.tree.column("Source", width=120, anchor="w")
        self.tree.column("Destination", width=120, anchor="w")
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.mettreAJourIHM())

        # Ajout des données dans la TreeView
        self.rafraichirTreeview()

    # On charge les données dnas la treeView lors de l'initalisation ou swap de données
    def rafraichirTreeview(self, ligneSelectionnee = None):


        for i in self.tree.get_children():
            self.tree.delete(i)

        itemASel = None
        premierItem = None
        for _, row in self.listeReliquats.df.iterrows():
            ligne = row["Ligne"]
            enigme = row["Enigme"]
            indice = row["Indice"]
            villeSource = row["Source"]
            villeDestination = row["Destination"]
            itemId = self.tree.insert("", "end", values=(ligne, enigme, indice, villeSource, villeDestination))
        
            # On garde le nouvel identifiant de la ligne précédemment sélectionnée
            if premierItem is None:
                premierItem = itemId
            if ligneSelectionnee is not None and ligne == ligneSelectionnee:
                itemASel = itemId

        # Re-sélection de la ligne si c'est celle précédemment sélectionnée
        if itemASel:
            self.tree.selection_set(itemASel)
            self.tree.see(itemASel)
        elif premierItem:
            self.tree.selection_set(premierItem)
            self.tree.see(premierItem)        
        
        # On  met à jour le reste de l'IHM
        self.mettreAJourIHM()

    def mettreAJourIHM(self):
        itemSelectionne = self.tree.selection()
        etat = tk.NORMAL if itemSelectionne else tk.DISABLED
        self.boutonUp.config(state=etat)
        self.boutonDown.config(state=etat)
        self.boutonSwap.config(state=etat)

    def actionReload(self):
        self.listeReliquats = Reliquats("data/reliquats.csv")
        self.rafraichirTreeview()        

    # On fait remonter d'un cran le reliquat dans la liste
    def actionMonter(self):
        item = self.tree.selection()
        if item:
            ligne = int(self.tree.item(item)["values"][0])
            if ligne>1:
                self.listeReliquats.monterLigne(ligne)
                self.rafraichirTreeview(ligne-1)


    # On fait descendre d'un cran le reliquat dans la liste
    def actionDescendre(self):
        item = self.tree.selection()
        if item:
            ligne = int(self.tree.item(item)["values"][0])
            if ligne<self.listeReliquats.nombreLignes():
                self.listeReliquats.descendreLigne(ligne)
                self.rafraichirTreeview(ligne+1)

    # On intervertit Source et destination
    def actionSwap(self):
        item = self.tree.selection()
        if item:
            ligne = int(self.tree.item(item)["values"][0])
            self.listeReliquats.echangerVilles(ligne)
            self.rafraichirTreeview(ligne)

    def actionSauvegarder(self):
        print("→ Sauvegarde du fichier CSV")
        # Exemple : on appelle une méthode de sauvegarde dans self.reliquats
        if hasattr(self.listeReliquats, "sauvegarderFichierCSV"):
            self.listeReliquats.sauvegarderFichierCSV()


class AlgorithmeSSIHM:
    def __init__(self, master):
        self.frame = ttk.LabelFrame(master, text="Analyse du Segment", padding=5)
        self.frame.pack(expand=True, fill=tk.BOTH)

        # Diviser en deux frames : gauche pour la carte, droite pour les paramètres
        self.frame_width = 600
        self.frame_height = 600
        self.zoom_factor = 1/16
        self.pan_x = 0
        self.pan_y =0

        self.frameCarte = tk.Frame(self.frame, width=self.frame_width, height=self.frame_height, bg="gray")
        self.frameCarte.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        self.frameCarte.pack_propagate(False)
                                       
        self.frameParams = tk.Frame(self.frame, bg="lightgray", width=300)
        self.frameParams.pack(side=tk.RIGHT, fill=tk.Y)

        # La liste des objets graphiques à afficher
        self.listeObjetgraphiques = []
        self.creerSegmentGraphique("Bourges", "Roncevaux")

        # On crée l'emplacement pour l'image
        self.labelImage = Label(self.frameCarte)
        self.labelImage.pack(expand=True, fill=tk.BOTH)

        # Chargement de la carte depuis CarteConfig
        self.rafraichirImage()

    def creerSegmentGraphique(self, source:str, destination:str):
        pointSource = villes_dict[source]
        pointDestination = villes_dict[destination]
        ligne1 = SegmentEntreVilles(pointSource, pointDestination)
        cercle = CercleGraphique(pointSource, 200)
        self.listeObjetgraphiques.append(ligne1)
        self.listeObjetgraphiques.append(cercle)

    def transformer_affichage_pixel(self, px, py):
        """
        Transforme les coordonnées (px, py) d’un point en pixels image absolus
        en coordonnées (x, y) en pixels écran (dans la fenêtre d’affichage),
        en tenant compte du zoom, du pan, du centrage (bord gris éventuel),
        et du ratio d’aspect.
        """

        (w_img, h_img) = carteConfig.image_size
        # Taille de l’image affichée en pixels image (après zoom, mais limitée à l’image réelle)
        souhaiteAfficher_w = self.frame_width / self.zoom_factor
        souhaiteAfficher_h = self.frame_height / self.zoom_factor

        tailleImageRelative_w = min(w_img, souhaiteAfficher_w)
        tailleImageRelative_h = min(h_img, souhaiteAfficher_h)

        # Position absolue (image) du coin haut gauche de la portion affichée
        x0 = min(max(0, self.pan_x), max(0, w_img - tailleImageRelative_w))
        y0 = min(max(0, self.pan_y), max(0, h_img - tailleImageRelative_h))

        # Position relative du point dans la zone affichée
        rel_x = (px - x0) / tailleImageRelative_w
        rel_y = (py - y0) / tailleImageRelative_h

        # Taille réelle de l’image affichée dans la fenêtre (en pixels écran)
        tailleImageAffichee_w = int(tailleImageRelative_w * self.zoom_factor)
        tailleImageAffichee_h = int(tailleImageRelative_h * self.zoom_factor)

        # Décalage (centrage éventuel) dans la fenêtre
        origineImageDansFenetre_x = max((self.frame_width - tailleImageAffichee_w) // 2, 0)
        origineImageDansFenetre_y = max((self.frame_height - tailleImageAffichee_h) // 2, 0)

        # Position finale du point à l’écran
        final_x = int(rel_x * tailleImageAffichee_w + origineImageDansFenetre_x)
        final_y = int(rel_y * tailleImageAffichee_h + origineImageDansFenetre_y)

        return final_x, final_y
    
    def calculerBordEcran(self):
        # On prend la liste des objets
        x1Min = None
        x2Max = None
        y1Min = None
        y2Max = None

        for obj in self.listeObjetgraphiques:
            (x1, y1) , (x2, y2) =obj.cadreAffichage()
            x1Min = x1 if x1Min is None else min(x1, x1Min)
            y1Min = y1 if y1Min is None else min(y1, y1Min)
            x2Max = x2 if x2Max is None else max(x2, x2Max)
            y2Max = y2 if y2Max is None else max(y2, y2Max)
        return (x1Min, y1Min), (x2Max, y2Max)
    
    
    def rafraichirImage(self):
        w_img, h_img = carteConfig.image_size
        crop_w = int(self.frame_width / self.zoom_factor)
        crop_h = int(self.frame_height / self.zoom_factor)

        self.pan_x = min(max(self.pan_x, 0), max(0, w_img - crop_w))
        self.pan_y = min(max(self.pan_y, 0), max(0, h_img - crop_h))

        x1 = max(0, self.pan_x)
        y1 = max(0, self.pan_y)
        x2 = min(self.pan_x + crop_w, w_img)
        y2 = min(self.pan_y + crop_h, h_img)

        # Découpage et resize
        cropped = carteConfig.img[y1:y2, x1:x2]
        target_w = int((x2 - x1) * self.zoom_factor)
        target_h = int((y2 - y1) * self.zoom_factor)
        resized = cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_AREA)

        canvas = np.full((self.frame_height, self.frame_width, 3), 230, dtype=np.uint8)
        offset_x = max(0, (self.frame_width - target_w) // 2)
        offset_y = max(0, (self.frame_height - target_h) // 2)
        canvas[offset_y:offset_y + target_h, offset_x:offset_x + target_w] = resized

        # Affichage des objets graphiques
        for obj in self.listeObjetgraphiques:
            obj.afficher(canvas, self.transformer_affichage_pixel)

        # Mise à jour dans Tkinter
        self.afficherCarte(canvas)


    def afficherCarte(self,img):
        imageRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        imageTk = ImageTk.PhotoImage(Image.fromarray(imageRGB))
        self.labelImage.configure(image=imageTk)
        self.labelImage.image = imageTk


class DicoIHM:
    def __init__(self, parent):
        self.frame = ttk.LabelFrame(parent, text="Dictionnaire visuel", style="TitreFrame.TLabelframe")
        self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

class SolutionIHM:
    def __init__(self, parent):
        self.frame = ttk.LabelFrame(parent, text="Solutions générées", style="TitreFrame.TLabelframe")
        self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

if __name__ == "__main__":
    app = InterfaceSS()
    app.mainloop()
