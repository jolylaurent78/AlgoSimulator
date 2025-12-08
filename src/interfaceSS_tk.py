import tkinter as tk
from tkinter import ttk, Label
from PIL import Image, ImageTk
from tksheet import Sheet
from tkinter import filedialog

import numpy as np
import cv2
import csv

# Base de données des villes
from src.data_loader import villes_dict

# Gestion des reliquats, décodage de la supersolution et dictionnaire
from src.reliquats import Reliquats, AxeMidi
from src.DecodageSS import UniteDecodageSS
from src.DictionnaireEnigmes import DictionnaireEnigmes, SequenceCategorie
from src.ConstructionsCadrans import ObjetCadran, ConstructionsCadrans

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
        panedHorizontal = tk.PanedWindow(
            self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=5
        )
        panedHorizontal.pack(fill=tk.BOTH, expand=True)

        # Frame gauche
        self.frameGauche = tk.Frame(
            panedHorizontal, width=300, relief=tk.RIDGE, borderwidth=2
        )
        panedHorizontal.add(self.frameGauche, minsize=250)

        # PanedWindow vertical (centre)
        panedVerticalCentre = tk.PanedWindow(
            panedHorizontal, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=5
        )
        panedHorizontal.add(panedVerticalCentre, minsize=800)

        self.frameCentreHaut = tk.Frame(
            panedVerticalCentre, relief=tk.RIDGE, borderwidth=2
        )
        self.frameCentreBas = tk.Frame(
            panedVerticalCentre, relief=tk.RIDGE, borderwidth=2
        )
        panedVerticalCentre.add(self.frameCentreHaut, minsize=300)
        panedVerticalCentre.add(self.frameCentreBas, minsize=300)

        # Frame droite
        self.frameDroite = tk.Frame(
            panedHorizontal, width=400, relief=tk.RIDGE, borderwidth=2
        )
        panedHorizontal.add(self.frameDroite, minsize=250)

        # Initialisation des composants IHM
        self.ihmReliquats = ListeReliquatsIHM(self.frameGauche, self)
        self.ihmDico = DicoIHM(self.frameCentreBas)
        self.ihmAlgo = AlgorithmeSSIHM(self.frameCentreHaut, self.ihmDico)
        self.ihmAxeMidi = AxeMidiIHM(self.frameDroite, self)

        # Les 8 constructions
        self.constructionsCadrans = ConstructionsCadrans(
            "data/constructionsCadransMultiSolutions.csv"
        )

        # Le raffraichisseent de la Tree View met à jour l'IHM complet en appelant mettreAJourIHM
        self.ihmReliquats.rafraichirTreeview()

    def mettreAJourIHM(self):
        # On récupère la ligne sélectionnée dans la liste des reliquats
        ligneReliquat = self.ihmReliquats.getLigneSelectionnee()
    
        # On récupère l'axe de Midi sélectionné
        tupleAxeMidi = self.ihmAxeMidi.getSegmentMidi()

        # On creé la liste des unités de décodage pour chque segment en utilisant pour le moment l'axe midi courant
        self.listeUnitesDecodage = []
        precedent = self.ihmReliquats.getListeReliquats().getVilleInitiale()
        for source, destination in self.ihmReliquats.getListeReliquats():
            objetPrecedent = self.constructionsCadrans[precedent]
            objetSource = self.constructionsCadrans[source]
            objetDestination = self.constructionsCadrans[destination]
            self.listeUnitesDecodage.append(
                UniteDecodageSS(objetPrecedent, objetSource, objetDestination, tupleAxeMidi)
            )
            precedent = destination



        self.ihmReliquats.mettreAJourIHM(ligneReliquat)
        self.ihmAlgo.rafraichirImage(self.listeUnitesDecodage[ligneReliquat - 1])
        self.ihmAlgo.rafraichirParametres(self.listeUnitesDecodage[ligneReliquat - 1])


class ListeReliquatsIHM:
    def __init__(self, parent, interface: InterfaceSS):
        # On garde le parent qui reste le dispatcher des mises à jour
        self.interface = interface
        # On charge la liste des reliquats à analyser
        self.listeReliquats = Reliquats("data/reliquats.csv")

        # On crée le Label Frame global
        self.frame = ttk.LabelFrame(
            parent, text="Liste des reliquats", style="TitreFrame.TLabelframe"
        )
        self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Zone de boutons au-dessus de la TreeView
        self.frameBoutons = tk.Frame(self.frame)
        self.frameBoutons.pack(side=tk.TOP, anchor=tk.W, pady=(8, 2))

        self.icones = {
            "reload": tk.PhotoImage(file="images/reload.png"),
            "up": tk.PhotoImage(file="images/up.png"),
            "down": tk.PhotoImage(file="images/down.png"),
            "swap": tk.PhotoImage(file="images/swap.png"),
            "save": tk.PhotoImage(file="images/save.png"),
            "reverse": tk.PhotoImage(file="images/reverse.png"),
        }

        self.boutonReload = tk.Button(
            self.frameBoutons,
            image=self.icones["reload"],
            command=self.actionReload,
            relief=tk.RAISED,
            bd=1,
        )
        self.boutonReload.pack(side=tk.LEFT, padx=2)

        self.boutonSave = tk.Button(
            self.frameBoutons,
            image=self.icones["save"],
            command=self.actionSauvegarder,
            relief=tk.RAISED,
            bd=1,
        )
        self.boutonSave.pack(side=tk.LEFT, padx=2)

        self.boutonUp = tk.Button(
            self.frameBoutons,
            image=self.icones["up"],
            command=self.actionMonter,
            relief=tk.RAISED,
            bd=1,
        )
        self.boutonUp.pack(side=tk.LEFT, padx=2)

        self.boutonDown = tk.Button(
            self.frameBoutons,
            image=self.icones["down"],
            command=self.actionDescendre,
            relief=tk.RAISED,
            bd=1,
        )
        self.boutonDown.pack(side=tk.LEFT, padx=2)

        self.boutonSwap = tk.Button(
            self.frameBoutons,
            image=self.icones["swap"],
            command=self.actionSwap,
            relief=tk.RAISED,
            bd=1,
        )
        self.boutonSwap.pack(side=tk.LEFT, padx=2)

        self.boutonReverse = tk.Button(
            self.frameBoutons,
            image=self.icones["reverse"],
            command=self.actionReverse,
            relief=tk.RAISED,
            bd=1,
        )
        self.boutonReverse.pack(side=tk.LEFT, padx=2)

        # Combo pour définir la ville initiale
        listeVilles = self.listeReliquats.getListeVillesInitialles()
        self.comboVilleInitiale = ttk.Combobox(
            self.frameBoutons, values=listeVilles, state="readonly", width=25
        )
        self.comboVilleInitiale.set(listeVilles[0])
        self.comboVilleInitiale.pack(side=tk.LEFT, padx=(10, 2))

        def onVilleInitialeChoisie(event):
            ville = self.comboVilleInitiale.get()
            self.listeReliquats.setVilleInitiale(ville)
            self.rafraichirTreeview()

        self.comboVilleInitiale.bind("<<ComboboxSelected>>", onVilleInitialeChoisie)

        # Création de la TreeView
        self.tree = ttk.Treeview(
            self.frame,
            columns=("#", "Enigme", "Indice", "Source", "Destination"),
            show="headings",
            selectmode="browse",
        )
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
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.selectionLigne())

    def getListeReliquats(self):
        return self.listeReliquats

    # On charge les données dnas la treeView lors de l'initalisation ou swap de données
    def rafraichirTreeview(self, ligneSelectionnee=None):

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
            itemId = self.tree.insert(
                "", "end", values=(ligne, enigme, indice, villeSource, villeDestination)
            )

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
        self.interface.mettreAJourIHM()

    def mettreAJourIHM(self, ligneReliquat=None):
        etat = tk.NORMAL if ligneReliquat else tk.DISABLED
        self.boutonUp.config(state=etat)
        self.boutonDown.config(state=etat)
        self.boutonSwap.config(state=etat)

    def selectionLigne(self):
        self.interface.mettreAJourIHM()

    def getLigneSelectionnee(self):
        itemSelectionne = self.tree.selection()
        ligne = int(self.tree.item(itemSelectionne)["values"][0])
        return ligne
           
    def actionReload(self):
        self.listeReliquats = Reliquats("data/reliquats.csv")
        self.rafraichirTreeview()

    # On fait remonter d'un cran le reliquat dans la liste
    def actionMonter(self):
        item = self.tree.selection()
        if item:
            ligne = int(self.tree.item(item)["values"][0])
            if ligne > 1:
                self.listeReliquats.monterLigne(ligne)
                self.rafraichirTreeview(ligne - 1)

    # On fait descendre d'un cran le reliquat dans la liste
    def actionDescendre(self):
        item = self.tree.selection()
        if item:
            ligne = int(self.tree.item(item)["values"][0])
            if ligne < self.listeReliquats.nombreLignes():
                self.listeReliquats.descendreLigne(ligne)
                self.rafraichirTreeview(ligne + 1)

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

    def actionReverse(self):
        self.listeReliquats.inverserOrdre()
        self.rafraichirTreeview()


class AlgorithmeSSIHM:
    def __init__(self, master, dico):
        self.dicoIHM = dico
        # Diviser en deux frames : gauche pour la carte, droite pour les paramètres
        self.frame_width = 400
        self.frame_height = 400

        self.frameCarte = tk.Frame(
            master, width=self.frame_width, height=self.frame_height
        )
        self.frameCarte.pack(side=tk.LEFT, anchor="nw")
        self.frameCarte.pack_propagate(False)

        self.frameParams = ttk.LabelFrame(
            master, text="Analyse du Segment", style="TitreFrame.TLabelframe", padding=5
        )
        self.frameParams.pack(
            side=tk.LEFT,
            anchor="nw",
            padx=(10, 10),
            pady=(5, 5),
            fill=tk.BOTH,
            expand=True,
        )  # Justifie en haut
        self.frameParams.pack_propagate(
            False
        )  # Ne pas laisser le contenu changer la taille

        # On crée l'emplacement pour l'image
        self.carteAffichee = Label(self.frameCarte)
        self.carteAffichee.pack(side=tk.LEFT, anchor="nw")

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
        origineImageDansFenetre_x = max(
            (self.frame_width - tailleImageAffichee_w) // 2, 0
        )
        origineImageDansFenetre_y = max(
            (self.frame_height - tailleImageAffichee_h) // 2, 0
        )

        # Position finale du point à l’écran
        final_x = int(rel_x * tailleImageAffichee_w + origineImageDansFenetre_x)
        final_y = int(rel_y * tailleImageAffichee_h + origineImageDansFenetre_y)

        return final_x, final_y

    def ajusterZoomEtPanSurCible(self):
        # Étape 1 : récupérer le rectangle cible
        x1Min = None
        x2Max = None
        y1Min = None
        y2Max = None

        for obj in self.listeObjetgraphiques:
            (x1, y1), (x2, y2) = obj.cadreAffichage()
            x1Min = min(x1, x2) if x1Min is None else min(x1, x2, x1Min)
            y1Min = min(y1, y2) if y1Min is None else min(y1, y2, y1Min)
            x2Max = max(x1, x2) if x2Max is None else max(x1, x2, x2Max)
            y2Max = max(y1, y2) if y2Max is None else max(y1, y2, y2Max)

        cible_w = x2Max - x1Min
        cible_h = y2Max - y1Min

        # Marge de 5% dans chaque direction
        marge_x = 0.15 * cible_w
        marge_y = 0.15 * cible_h
        cible_w += 2 * marge_x
        cible_h += 2 * marge_y

        x1Min -= marge_x
        y1Min -= marge_y
        x2Max += marge_x
        y2Max += marge_y

        # Zoom minimal pour faire entrer tout le rectangle dans la frame
        zoom_w = self.frame_width / cible_w
        zoom_h = self.frame_height / cible_h
        zoom = min(zoom_w, zoom_h)

        # Crop à faire (dans l’image) pour centrer la cible
        crop_w = self.frame_width / zoom
        crop_h = self.frame_height / zoom

        centre_x = (x1Min + x2Max) / 2
        centre_y = (y1Min + y2Max) / 2

        pan_x = centre_x - crop_w / 2
        pan_y = centre_y - crop_h / 2

        w_img, h_img = carteConfig.image_size
        pan_x = min(max(pan_x, 0), max(0, w_img - crop_w))
        pan_y = min(max(pan_y, 0), max(0, h_img - crop_h))

        self.zoom_factor = zoom
        self.pan_x = int(pan_x)
        self.pan_y = int(pan_y)

    def rafraichirImage(self, uniteDecodage: UniteDecodageSS):

        # On récupère la liste des objets graphique depuis l'unité de décodage
        self.listeObjetgraphiques = uniteDecodage.construireRepresentationCarte()

        # On calcule ensuite le pan et zoom optimal
        self.ajusterZoomEtPanSurCible()

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
        resized = cv2.resize(
            cropped, (target_w, target_h), interpolation=cv2.INTER_AREA
        )

        canvas = np.full((self.frame_height, self.frame_width, 3), 230, dtype=np.uint8)
        offset_x = max(0, (self.frame_width - target_w) // 2)
        offset_y = max(0, (self.frame_height - target_h) // 2)
        canvas[offset_y : offset_y + target_h, offset_x : offset_x + target_w] = resized

        # Affichage des objets graphiques
        for obj in self.listeObjetgraphiques:
            obj.afficher(canvas, self.transformer_affichage_pixel)

        # Mise à jour dans Tkinter
        imageRGB = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        imageTk = ImageTk.PhotoImage(Image.fromarray(imageRGB))
        self.carteAffichee.configure(image=imageTk)
        self.carteAffichee.image = imageTk

    def rafraichirParametres(self, uniteDecodage: UniteDecodageSS):
        # On nettoie les widgets précédents
        for widget in self.frameParams.winfo_children():
            widget.destroy()

        listeParametresSegment = uniteDecodage.getAttributsSegment()

        # Grouper les attributs par numéro de ligne
        lignes = dict()
        ligne = 0
        for ligne, label, valeur in listeParametresSegment:
            if ligne not in lignes:
                lignes[ligne] = []
            lignes[ligne].append((label, valeur))

        # Affichage groupé par ligne
        for row, elements in sorted(lignes.items()):
            for col, (label, valeur) in enumerate(elements):
                lbl = ttk.Label(
                    self.frameParams, text=f"{label} :", font=("Arial", 10, "bold")
                )
                val = ttk.Label(self.frameParams, text=valeur, font=("Arial", 10))

                lbl.grid(row=row, column=2 * col, sticky="w", padx=10, pady=4)
                val.grid(row=row, column=2 * col + 1, sticky="w", padx=10, pady=4)

        # On met à jour le dictionnaire
        enigme, indexMot = uniteDecodage.calculIndex()
        self.dicoIHM.selectionnerCellule(enigme, indexMot)


class DicoIHM:
    def __init__(self, master):
        # On crée le dictionnaire et une séquence
        self.listeDictionnaires = [
            ("Bons Sens / Avec code", DictionnaireEnigmes("data/livre.txt", bonSens = True)),
            ("Bon Sens / Sans code", DictionnaireEnigmes("data/livre.txt", tagExclure = "exclure", bonSens = True)),
            ("Inversé / Avec code", DictionnaireEnigmes("data/livre.txt", bonSens = False)),
            ("Inversé / Sans code", DictionnaireEnigmes("data/livre.txt", tagExclure = "exclure", bonSens = False)),
        ]

        _, self.dictionnaireEnigmes = self.listeDictionnaires[0]
        self.sequenceCategorie = SequenceCategorie(self.dictionnaireEnigmes)

        # Cadre horizontal pour les options de filtrage
        self.parent = master
        self.frameFiltrage = tk.Frame(master)
        self.frameFiltrage.pack(fill="x", pady=5)

        # Variable commune pour le mode de filtrage
        self.modeFiltrage = tk.StringVar(value="tous")

        # Boutons radio
        rbTous = tk.Radiobutton(
            self.frameFiltrage,
            text="Tous afficher",
            variable=self.modeFiltrage,
            value="tous",
            command=self.mettreAJourFiltrage,
        )
        rbTous.pack(side="left", padx=5)

        rbFiltrer = tk.Radiobutton(
            self.frameFiltrage,
            text="Filtrer par catégories",
            variable=self.modeFiltrage,
            value="categorie",
            command=self.mettreAJourFiltrage,
        )
        rbFiltrer.pack(side="left", padx=5)

        # Bouton "..." pour ouvrir la sélection des catégories
        btnCategories = tk.Button(
            self.frameFiltrage, text="...", command=self.ouvrirBoiteFiltrageCategories
        )
        btnCategories.pack(side="left", padx=5)

        # Combobox pour sélectionner le dictionnaire
        self.comboDictionnaire = ttk.Combobox(
            self.frameFiltrage,
            values=[nom for nom, _ in self.listeDictionnaires],
            state="readonly",
            width=25
        )
        self.comboDictionnaire.current(0)  # Sélection initiale
        self.comboDictionnaire.pack(side="left", padx=10)
        self.comboDictionnaire.bind("<<ComboboxSelected>>", lambda e: self.mettreAJourDictionnaire())

        # --- Création de la frame pour le tableau Excel
        self.frameTableau = ttk.Frame(master)
        self.frameTableau.pack(side="top", fill="x", pady=(5, 0))

        nb_mots = self.dictionnaireEnigmes.nbMotMax()
        headers = list(range(-nb_mots, nb_mots))

        data = []
        for i in range(len(self.dictionnaireEnigmes)):
            ligne = [self.dictionnaireEnigmes[i][j] for j in range(-nb_mots, nb_mots)]
            data.append(ligne)

        # Supprime les widgets précédents de la frame
        for widget in self.frameTableau.winfo_children():
            widget.destroy()

        # Crée la feuille
        self.sheet = Sheet(
            self.frameTableau,
            data=data,
            headers=headers,
            show_vertical_scrollbar=False,
            row_index=self.dictionnaireEnigmes.getTitres(),  # Affiche les titres comme index
            show_row_index=True,
            height=305,
            empty_vertical=0,
        )

        self.sheet.enable_bindings(
            (
                "single_select",
                "row_select",
                "column_select",
                "arrowkeys",
                "right_click_popup_menu",
                "rc_select",
                "copy",
                "paste",
                "delete",
                "undo",
                "edit_cell",
            )
        )

        # self.sheet.font(newfont=("Helvetica", 9, "normal"))
        self.sheet.disable_bindings("vertical_scroll")
        self.sheet.align_columns(columns="all", align="center")
        self.sheet.set_options(cell_align="center")
        self.sheet.pack(expand=True, fill="both")

        # On rajoute une barre de boutons pour controler la séquence
        self.frameBarreCategorie = tk.Frame(master)
        self.frameBarreCategorie.pack(side="top", fill="x")

        # Exemple de contenu : un label ou un bouton global
        self.modeIndex = tk.StringVar(value="absolu")  # valeur par défaut

        def onChangerModeIndex():
            modexIndex = True if self.modeIndex.get() == "relatif" else False
            self.sequenceCategorie.setModeIndexRelatif(modexIndex)
            self.mettreAJourChemins()

        lbl = ttk.Label(self.frameBarreCategorie, text="Mode index :")
        lbl.pack(side="left", padx=(10, 4))

        rbAbsolu = ttk.Radiobutton(
            self.frameBarreCategorie,
            text="Absolu",
            variable=self.modeIndex,
            value="absolu",
            command=onChangerModeIndex,
        )
        rbRelatif = ttk.Radiobutton(
            self.frameBarreCategorie,
            text="Relatif",
            variable=self.modeIndex,
            value="relatif",
            command=onChangerModeIndex,
        )

        rbAbsolu.pack(side="left", padx=2)
        rbRelatif.pack(side="left", padx=2)

        self.labelLongueur = ttk.Label(self.frameBarreCategorie, text="Longueur: 0")
        self.labelLongueur.pack(side="left", padx=(20, 4))
        self.labelComplexite = ttk.Label(self.frameBarreCategorie, text="Complexité: 0")
        self.labelComplexite.pack(side="left", padx=(10, 4))

        # Combobox pour afficher les chemins
        self.comboChemins = ttk.Combobox(
            self.frameBarreCategorie, width=80, state="readonly"
        )
        self.comboChemins.pack(side="left", padx=(20, 5))

        # Conteneur principal pour la séquence
        conteneurSequence = ttk.Frame(master)
        conteneurSequence.pack(side="left", fill="y")

        # Conteneur principal pour la séquence
        conteneurAnalyseIndex = ttk.Frame(master, width=200)
        conteneurAnalyseIndex.pack(side="right", fill="y")

        # Combobox pour choisir une séquence sauvegardée
        self.comboAnalyse = ttk.Combobox(
            conteneurAnalyseIndex, state="readonly", width=25
        )
        self.comboAnalyse.pack(padx=5, pady=(5, 2))

        # Treeview pour afficher les mots de la séquence
        self.treeAnalyse = ttk.Treeview(
            conteneurAnalyseIndex,
            columns=("Mot", "Pidx", "P%", "P°", "Midx", "M%", "M°"),
            show="headings",
            height=10,
        )
        self.treeAnalyse.heading("Mot", text="Mot")
        self.treeAnalyse.heading("Pidx", text="+idx")
        self.treeAnalyse.heading("P%", text="+%")
        self.treeAnalyse.heading("P°", text="+°")
        self.treeAnalyse.heading("Midx", text="-idx")
        self.treeAnalyse.heading("M%", text="-%")
        self.treeAnalyse.heading("M°", text="-°")
        self.treeAnalyse.column("Mot", width=80)
        self.treeAnalyse.column("Pidx", width=40)
        self.treeAnalyse.column("P%", width=40)
        self.treeAnalyse.column("P°", width=40)
        self.treeAnalyse.column("Midx", width=40)
        self.treeAnalyse.column("M%", width=40)
        self.treeAnalyse.column("M°", width=40)
        self.treeAnalyse.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        # Canvas pour scroll horizontal
        canvasSequence = tk.Canvas(conteneurSequence, highlightthickness=0)
        canvasSequence.pack(side="top", fill="x", expand=True)

        # Scrollbar horizontale
        scrollbarX = ttk.Scrollbar(
            conteneurSequence, orient="horizontal", command=canvasSequence.xview
        )
        scrollbarX.pack(side="bottom", fill="x")

        canvasSequence.configure(xscrollcommand=scrollbarX.set)

        # Frame réelle qui contient les colonnes
        self.frameSequence = ttk.Frame(canvasSequence)
        self.frameSequence.bind(
            "<Configure>",
            lambda e: canvasSequence.configure(scrollregion=canvasSequence.bbox("all")),
        )
        canvasSequence.create_window((0, 0), window=self.frameSequence, anchor="nw")

        self.sequenceCategorisGUI = []

        # On affiche la première colonne
        self.ajouterColonneCategorie()


    def mettreAJourDictionnaire(self):
        index = self.comboDictionnaire.current()
        _, self.dictionnaireEnigmes = self.listeDictionnaires[index]
        self.sequenceCategorie = SequenceCategorie(self.dictionnaireEnigmes)
        self.mettreAJourFiltrage()
        self.mettreAJourChemins()


    def mettreAJourChemins(self):
        # On met à jour les labels Longueur & Complexité
        longueur, complexite = self.sequenceCategorie.getComplexiteSequence()
        self.labelLongueur.config(text=f"Longueur : {longueur}")
        self.labelComplexite.config(text=f"Complexité : {complexite}")

        # On met à jour la liste des chemins
        chemins = self.sequenceCategorie.listeToutesSequencesPossibles()
        self.comboChemins["values"] = chemins
        if chemins:
            self.comboChemins.current(0)  # Sélectionne le premier chemin par défaut

            # On met à jour la combo à droite avec la sélectiondu mot dans la séquence
            valeurs = []
            for i, cat in enumerate(self.sequenceCategorie.getCategories()):
                valeurs.append(f"{i+1} - {cat}")
            self.comboAnalyse["values"] = valeurs
            if valeurs:
                self.comboAnalyse.current(0)

            def mettreAJourTreeAnalyse(event=None):
                # On récupère l'index de la catégorie sélectionnée dans la combo
                valeur = self.comboAnalyse.get()
                if not valeur or " - " not in valeur:
                    return

                indexStr, _ = valeur.split(" - ", 1)
                indexCategorie = int(indexStr.strip()) - 1  # Car affichage commence à 1

                # On récupère la liste des mots sélectionnés pour cette catégorie
                motsSelectionnes = self.sequenceCategorie.getMotsSelectionnes(
                    indexCategorie
                )
                self.treeAnalyse.delete(*self.treeAnalyse.get_children())

                for i, (enigme, indexMot) in enumerate(motsSelectionnes):
                    mot = self.dictionnaireEnigmes.getMot(enigme, indexMot)
                    enigmeIdxRel, motIdxRelPlus = (
                        self.sequenceCategorie.conversionIndexMot(indexCategorie, i)
                    )
                    indexRel = motIdxRelPlus

                    # On calcule les str si index <= 60mn
                    if indexRel <= 60:
                        indexRelStr = f"{indexRel}"
                        pourcentagePlusStr = f"{round((indexRel / 60) * 100)}%"
                        anglePlusStr = f"{round((indexRel / 60) * 360)}°"
                    else:
                        indexRelStr = ""
                        pourcentagePlusStr = ""
                        anglePlusStr = ""

                    indexRelMoins = indexRel - self.dictionnaireEnigmes.nbMotsLigne(
                        enigme
                    )
                    if indexRelMoins >= -60:
                        indexRelMoinsStr = f"{indexRelMoins}"
                        pourcentageMoinsStr = f"{round((indexRelMoins / 60) * 100)}%"
                        angleMoinsStr = f"{round((indexRelMoins / 60) * 360)}°"
                    else:
                        indexRelMoinsStr = ""
                        pourcentageMoinsStr = ""
                        angleMoinsStr = ""

                    self.treeAnalyse.insert(
                        "",
                        "end",
                        values=(
                            mot,
                            indexRelStr,
                            pourcentagePlusStr,
                            anglePlusStr,
                            indexRelMoinsStr,
                            pourcentageMoinsStr,
                            angleMoinsStr,
                        ),
                    )

            self.comboAnalyse.bind("<<ComboboxSelected>>", mettreAJourTreeAnalyse)
            mettreAJourTreeAnalyse()

    def selectionnerCellule(self, enigme: int, mot: int):

        indexLigne = enigme
        indexMot = mot + 98

        self.sheet.set_sheet_data(
            self.sheet.get_sheet_data(), reset_highlights=True, redraw=True
        )
        self.sheet.highlight_cells(
            cells=[(indexLigne, indexMot)], bg="lightblue", fg="black", redraw=True
        )
        self.sheet.see(row=indexLigne, column=indexMot)

    def mettreAJourFiltrage(self):
        mode = self.modeFiltrage.get()

        if mode == "tous":
            self.dictionnaireEnigmes.setFiltrageGlobal(False)
        elif mode == "categorie":
            self.dictionnaireEnigmes.setFiltrageGlobal(True)

        self.sheet.set_sheet_data([])
        self.sheet.headers([])  # Supprime tous les anciens entêtes

        nb_mots = self.dictionnaireEnigmes.nbMotMax()
        data = []

        nbEnigmes = len(self.dictionnaireEnigmes)
        for i in range(nbEnigmes):
            ligne = [self.dictionnaireEnigmes[i][j] for j in range(-nb_mots, nb_mots)]
            data.append(ligne)

        self.sheet.insert_rows(data)
        self.sheet.headers([str(i) for i in range(-nb_mots, nb_mots)])
        self.sheet.deselect("all")
        self.sheet.set_sheet_data(
            data, reset_col_positions=True, reset_row_positions=True
        )

    def ouvrirBoiteFiltrageCategories(self):
        # Active automatiquement le filtre par catégorie
        self.modeFiltrage.set("categorie")
        self.dictionnaireEnigmes.setFiltrageGlobal(True)

        top = tk.Toplevel(self.parent)
        top.title("Choisir les catégories")
        top.grab_set()

        # Dictionnaire temporaire pour stocker les sélections
        selections = {}

        for categorie in self.dictionnaireEnigmes.getCategories():
            var = tk.BooleanVar(
                value=categorie in self.dictionnaireEnigmes.getCategoriesSelectionnees()
            )
            cb = tk.Checkbutton(top, text=categorie.capitalize(), variable=var)
            cb.pack(anchor="w", padx=10, pady=2)
            selections[categorie] = var

        def valider():
            for cat, var in selections.items():
                self.dictionnaireEnigmes.activerCategorie(cat, var.get())
            top.destroy()
            self.mettreAJourFiltrage()

        def annuler():
            top.destroy()

        # Boutons de validation
        frameButtons = tk.Frame(top)
        frameButtons.pack(pady=10)
        tk.Button(frameButtons, text="Valider", command=valider).pack(
            side="left", padx=10
        )
        tk.Button(frameButtons, text="Annuler", command=annuler).pack(
            side="right", padx=10
        )

    def supprimerColonneCategorie(self, frameColonne):

        index = self.sequenceCategorisGUI.index(frameColonne)

        # 1. Supprimer la frameColonne (et tous ses enfants)
        frameColonne.destroy()

        # 2. Retirer le frame de la liste
        self.sequenceCategorisGUI.pop(index)

        # 3. Recaler les colonnes restantes visuellement
        for i, frame in enumerate(self.sequenceCategorisGUI):
            frame.grid_configure(column=i)

        # On retire  la catégorie de la sequence
        self.sequenceCategorie.retirerCategorie(index)

    def ajouterColonneCategorie(self, index=None):
        if index is None:
            index = len(self.sequenceCategorisGUI)

        # On crée une frame colonne
        # self.frameSequence est la grille principale horizontale
        frameColonne = tk.Frame(self.frameSequence, width=80)
        frameColonne.grid(row=0, column=index, sticky="nsw")
        frameColonne.grid_propagate(False)

        # Ligne 0 : conteneur horizontal combo + bouton
        topBar = tk.Frame(frameColonne)
        topBar.pack(side="top")

        # --- Création des widgets ---
        combo = ttk.Combobox(
            topBar,
            values=self.dictionnaireEnigmes.getCategories(),
            state="readonly",
            width=13,
        )
        combo.pack(side="left", expand=True, fill="x")

        bouton = ttk.Button(topBar, text="+", width=2)
        bouton.pack(side="left")

        tree = ttk.Treeview(
            frameColonne, columns=("mot", "pos"), show="headings", selectmode="extended"
        )
        tree.heading("mot", text="Mot")
        tree.heading("pos", text="Abs")
        tree.column("mot", width=80, stretch=False)
        tree.column("pos", width=40, stretch=False)
        # tree.pack(side="top", fill="y", expand=True)

        # --- Ajout des éléments à la structure ---
        self.sequenceCategorisGUI.insert(index, frameColonne)

        def mettreAJourListeMots(event=None):
            categorie = combo.get()
            # Protection
            if not categorie:
                return

            # On met à jour la catégorie
            indexColonne = self.sequenceCategorisGUI.index(frameColonne)
            self.sequenceCategorie.mettreAJourCategorie(indexColonne, categorie)
            self.sequenceCategorie.afficheSequence()

            # On remplit la liste des mots possible
            mots = self.dictionnaireEnigmes.getListeCategorie(categorie)
            tree.delete(*tree.get_children())
            for mot, enigmeIdx, motIdx in mots:
                posAbs = f"{enigmeIdx}/{motIdx}"
                tree.insert("", "end", values=(mot, posAbs))

        # --- Configuration du bouton ---
        def onAjouter():
            mettreAJourListeMots()

            # Si le tree n’est pas encore affiché, on l’ajoute
            if not tree.winfo_ismapped():
                tree.pack(side="top", padx=2, pady=2, fill="y", expand=True)

            bouton.configure(
                text="–", command=lambda: self.supprimerColonneCategorie(frameColonne)
            )
            self.ajouterColonneCategorie()

        # Sélection d'un mot
        def onSelectionMots(event=None):
            indexColonne = self.sequenceCategorisGUI.index(frameColonne)

            # Réinitialiser la sélection
            self.sequenceCategorie.selections[indexColonne] = []

            for item in tree.selection():
                valeurs = tree.item(item, "values")
                if len(valeurs) >= 2 and "/" in valeurs[1]:
                    enigmeIdx, motIdx = map(int, valeurs[1].split("/"))
                    self.sequenceCategorie.ajouterMotSelectionne(
                        indexColonne, enigmeIdx, motIdx
                    )
            # On met à jour la liste des chemins / longueur et complexité
            self.mettreAJourChemins()

        bouton.configure(command=onAjouter)
        combo.bind("<<ComboboxSelected>>", mettreAJourListeMots)
        tree.bind("<<TreeviewSelect>>", onSelectionMots)


class AxeMidiIHM:
    def __init__(self, parent, interface:InterfaceSS):
        self.interface = interface
        self.frame = ttk.LabelFrame(
            parent, text="Assemblage", style="TitreFrame.TLabelframe"
        )
        self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Barre de boutons en haut
        self.frameBoutons = tk.Frame(self.frame)
        self.frameBoutons.pack(side=tk.TOP, anchor=tk.W, pady=(8, 2))

        # Chargement icône
        self.iconeSave = tk.PhotoImage(file="images/save.png")

        # Bouton sauvegarder
        self.boutonSave = tk.Button(
            self.frameBoutons,
            image=self.iconeSave,
            command=self.actionSauvegarder,
            relief=tk.RAISED,
            bd=1,
        )
        self.boutonSave.pack(side=tk.LEFT, padx=2)

        # On charge la liste des axes de Midi à analyser
        self.listeAxeMidi = AxeMidi("data/segmentsMidi.csv")

        # On crée une treeview
        colonnes = self.listeAxeMidi.getColonnes()
        self.tree = ttk.Treeview(self.frame, columns=colonnes, show="headings")
        for col in colonnes:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="w", width=100)

        premierItem = None
        for i, segment in enumerate(self.listeAxeMidi):
            item = self.tree.insert("", "end", values=segment)
            if i == 0:
                premierItem = item

        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.setAxeMidi)

        # Sélection par défaut de la première ligne
        if premierItem:
            self.tree.selection_set(premierItem)
            self.tree.focus(premierItem)
            self.tree.see(premierItem)

    def getSegmentMidi(self):
        itemSelectionne = self.tree.selection()
        if not itemSelectionne:
            return None  # ou tu peux lever une exception ou retourner un tuple vide
        
        valeurs = self.tree.item(itemSelectionne[0])["values"]
        return (valeurs[1], valeurs[2])  # Debut, Fin


    def setAxeMidi(self, event=None):
        self.interface.mettreAJourIHM()

    def actionSauvegarder(self):
        print("→ Sauvegarde des segments de Midi")

        listeTriangles = []
        for uniteDecodage in self.interface.listeUnitesDecodage:
            for objet in (uniteDecodage.objetDebut, uniteDecodage.objetFin):
                if objet.typeCadran() in ("lumiere", "final"):
                    # On récupère les 3 pts graphiques du triangle
                    ptOuverture, ptBase, ptLumiere = objet.getTriangleCadran()
                    nomOuverture= ptOuverture.getNom()
                    nomBase= ptBase.getNom()
                    nomLumiere= ptLumiere.getNom()
                    # On récupère les coordonnées
                    ptOuverture_x, ptOuverture_y = ptOuverture.coordonneesPixelAbs()
                    ptBase_x, ptBase_y = ptBase.coordonneesPixelAbs()
                    ptLumiere_x, ptLumiere_y = ptLumiere.coordonneesPixelAbs()   
                    # On calcule les lignes associées
                    ligneOuvertureBase = Ligne(ptOuverture_x,ptOuverture_y, ptBase_x, ptBase_y)
                    ligneOuvertureLumiere = Ligne(ptOuverture_x, ptOuverture_y, ptLumiere_x, ptLumiere_y)
                    ligneBaseLumiere = Ligne(ptBase_x, ptBase_y, ptLumiere_x, ptLumiere_y)
                    # On calcule angles et distances entre les 3 points
                    angleOuverture = ligneOuvertureBase.angleAvec(ligneOuvertureLumiere)
                    angleBase = 180-ligneOuvertureBase.angleAvec(ligneBaseLumiere)
                    angleLumiere = ligneBaseLumiere.angleAvec(ligneOuvertureLumiere)
                    distOuvertureBase = ptOuverture.distance(ptBase)
                    distOuvertureLumiere = ptOuverture.distance(ptLumiere)
                    distLumiereBase = ptLumiere.distance(ptBase)
                    # --- Orientation (bit de sens) ---
                    # Produit vectoriel 2D au point Ouverture, corrigé du repère écran (y vers le bas)
                    s_img = (ptBase_x - ptOuverture_x) * (ptLumiere_y - ptOuverture_y) - (ptBase_y - ptOuverture_y) * (ptLumiere_x - ptOuverture_x)
                    s = -s_img  # inverse pour revenir à l’orientation mathématique habituelle
                    orientation = "CCW" if s > 0 else ("CW" if s < 0 else "COL")
                    triangle = (
                        (nomOuverture, nomBase, nomLumiere),
                        objet.typeCadran(),
                        (angleOuverture, angleBase, angleLumiere),
                        (distOuvertureBase, distOuvertureLumiere, distLumiereBase),
                        orientation,
                    )
                    print(triangle)
                    listeTriangles.append(triangle)

                         # Boîte de dialogue pour choisir le fichier
        
        cheminFichier = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Fichiers CSV", "*.csv")],
            title="Enregistrer les triangles"
        )

        if not cheminFichier:
            return  # Annulé par l'utilisateur

        with open(cheminFichier, mode="w", newline="") as fichier:
            writer = csv.writer(fichier, delimiter=";")
            writer.writerow([
                "Nom Ouverture", "Nom Base", "Nom Lumiere", "Type Cadran",
                "Angle Ouverture", "Angle Base", "Angle Lumiere",
                "Longueur Ouverture-Base", "Longueur Ouverture-Lumiere", "Longueur Lumiere-Base",
                "Orientation"
            ])
            for triangle in listeTriangles:
                noms, type, angles, longueurs, orientation = triangle
                ligne = (
                    list(noms)
                    + [type]
                    + [round(a, 2) for a in angles]
                    + [round(d, 2) for d in longueurs]
                    + [orientation]
                )
                writer.writerow(ligne)

        print(f"→ {len(listeTriangles)} triangles sauvegardés dans {cheminFichier}")
            

if __name__ == "__main__":
    app = InterfaceSS()
    app.mainloop()
