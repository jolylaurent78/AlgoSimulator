import tkinter as tk

from tkinter import ttk, PanedWindow, colorchooser, filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import os
import pickle
import json
import sqlite3
from collections import defaultdict
import csv
import pandas as pd
import webbrowser

# Base de données des villes
from src.data_loader import villes_dict

# Affichage de la carte interractive
from src.affichage_fenetre import display, img, transformer_pixel_affichage_vers_image, selectionVille, selectionObjet, sauvegarder_carte_complete
from src.affichage_fenetre import ListePOIs
from src.affichage_fenetre import pan_x, pan_y, zoom_factor, frame_width, frame_height, set_globals, canvasDisplay

# Gestion des coordonnées / projection
from src.carte_config import lambert93_to_pixels, pixels_to_lambert93, image_size, lambert93_to_gps, charger_icone, hexVersBGR, bgrVersHex

# Affichage des objects graphiques
from src.affichage_objets import *

# Affichge de l'IHM pour l'algorithme'
from src.IHMAlgorithme import IHMAlgorithme

# Gestion de l'algo
from src.AlgorithmeStyletInitial import AlgorithmeStyletInitial
from src.AlgorithmeLumiereStyletInitial import AlgorithmeLumiereStyletInitial
from src.AlgorithmeManager import TypeScenario

# Gestion des layers graphiques
from src.layerManager import LayerManager



class InterfaceCarte(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simulateur d'algorithmes de la Chouette d'Or")
        self.geometry("1600x1000")
        self.chemin_bd = "../shared-db/WikiCarto.db"
        # On initialise les répertoires de travail
        self.dossiers = {
            "projets": os.path.join(os.getcwd(), "projets"),
            "images": os.path.join(os.getcwd(), "images"),
            "exports": os.path.join(os.getcwd(), "exports")
        }

        # Création automatique si nécessaire
        for dossier in self.dossiers.values():
            os.makedirs(dossier, exist_ok=True)

        # On crée le layer Manager
        self.layerManager = LayerManager()

        self.moteurAlgo = AlgorithmeLumiereStyletInitial(self.layerManager)
        largeur, hauteur = self.moteurAlgo.getLargeurHauteurIHM()


        # Initialisation des attributs pour l'affichage des segment'
        self.varSegmentAffiche = None
        self.comboSegmentAffiche = None
        self.pointReferenceMesureDistance = None
        
        # Variable d'affichage pour la gestion des POIs
        self.varPOIVisible = tk.BooleanVar(value=False)
        self.varPOIPertinence = tk.StringVar(value="Elevée")
        self.varPOICategorie = tk.StringVar(value="Standard")
        self.varPOISujet = tk.StringVar()

        self._setup_main_split(largeur, hauteur )
        self._setup_menu()

        # Création de la liste dynamique des POIs Wikipédia et paramètres d'affichage des POIs
        self.listePOIs = ListePOIs(self.canvas_image, self.chemin_bd, self)
        self.listePOIs.layer.setVisible(False)


        # Le nom du fichier de description de l'IHM porte le même nom de la classe Métier'
        nom_fichier_csv = "config/"+type(self.moteurAlgo).__name__ + ".csv"
        self.ihm_algo = IHMAlgorithme(
            self.frameIHMAlgo,
            nom_fichier_csv,
            self.moteurAlgo,
            self.layerManager,
            callbackRefreshLayers=lambda nomScenario=None: self.creerLayerControle(self.frameLayers, nomScenario),
            callbackRedessinerCarte=self._refresh_images,
            callbackMiseAJourMenu=None
            )
        self.ihm_algo.pack(fill="both", expand=True)

        self._refresh_images()


    def sauvegarderEtatComplet(self, chemin: str):
        with open(chemin, "wb") as f:

            # 1. Écrire les métadonnées au début (encodées en JSON + taille fixe)
            metadata = {
                "algo_type": type(self.moteurAlgo).__name__,
                "version": "1.0",
            }
            metadata_bytes = json.dumps(metadata).encode("utf-8")
            taille = len(metadata_bytes)
            f.write(taille.to_bytes(4, byteorder="big"))
            f.write(metadata_bytes)

            # 2. Écrire ensuite le contenu pickle
            pickle.dump({
                "layers": self.layerManager,
                "moteur": self.moteurAlgo
            }, f)


    def lireMetaDonneesProjet(self,chemin: str) -> dict:
        with open(chemin, "rb") as f:
            taille = int.from_bytes(f.read(4), byteorder="big")
            metadata_bytes = f.read(taille)
            metadata = json.loads(metadata_bytes.decode("utf-8"))
            return metadata

    def chargerEtatComplet(self, chemin: str):

        with open(chemin, "rb") as f:
            taille = int.from_bytes(f.read(4), byteorder="big")
            f.read(taille)  # on ignore les métadonnées
            data = pickle.load(f)

        self.appliquerEtat(data["layers"], data["moteur"])


    def appliquerEtat(self, layerManager: LayerManager, moteurAlgo):
        """Applique le nouvel état (layers et moteur) à l'interface."""
        self.layerManager = layerManager
        self.moteurAlgo = moteurAlgo

        # Synchroniser les attributs principaux
        segment_actif = self.moteurAlgo.segment_actif
        if not self.varSegmentAffiche:
            self.varSegmentAffiche = tk.StringVar()
        self.varSegmentAffiche.set(segment_actif)
        self.layerManager.segmentActif = segment_actif

        # MAJ de la combo des segments
        if hasattr(self, "frameSegment") and self.frameSegment:
            for widget in self.frameSegment.winfo_children():
                widget.destroy()
            self.creerSelectionSegments(self.frameSegment)

        # Détruire l'IHM existante si elle existe
        if hasattr(self, "ihm_algo") and self.ihm_algo:
            self.ihm_algo.destroy()

        # Recréer une nouvelle IHM liée au bon moteur
        nom_fichier_csv = "config/" + type(self.moteurAlgo).__name__ + ".csv"
        self.ihm_algo = IHMAlgorithme(
            self.frameIHMAlgo,
            nom_fichier_csv,
            self.moteurAlgo,
            self.layerManager,
            callbackRefreshLayers=lambda nomScenario=None: self.creerLayerControle(self.frameLayers, nomScenario),
            callbackRedessinerCarte=self._refresh_images,
            callbackMiseAJourMenu=None,
        )
        self.ihm_algo.pack(fill="both", expand=True)

        # Rafraîchir les layers et la carte
        self.creerLayerControle(self.frameLayers)
        self._refresh_images()



### Mise en place des panels, menu, mini-carte

    def _setup_menu(self):
        menubar = tk.Menu(self)

        #
        # Menu Fichier
        menu_fichier = tk.Menu(menubar, tearoff=0)

        menu_nouveau = tk.Menu(menu_fichier, tearoff=0)
        menu_nouveau.add_command(
            label="AlgorithmeStyletInitial",
            command=lambda: self.actionNouveauProjet(AlgorithmeStyletInitial),
        )
        menu_nouveau.add_command(
            label="AlgorithmeLumiereStyletInitial",
            command=lambda: self.actionNouveauProjet(AlgorithmeLumiereStyletInitial),
        )
        menu_fichier.add_cascade(label="🆕 Nouveau", menu=menu_nouveau)
        menu_fichier.add_command(label="💾 Sauvegarder un projet...", command=self.actionSauvegarderProjet)
        menu_fichier.add_command(label="📂 Charger un projet", command=self.actionChargerProjet)
        menu_fichier.add_separator()

        # Chargement dynamique des projets enregistrés avec métadonnées
        projets_dir = self.dossiers["projets"]
        if os.path.exists(projets_dir):
            for file in sorted(os.listdir(projets_dir)):
                if file.endswith(".pkl"):
                    chemin_fichier = os.path.join(projets_dir, file)
                    try:
                        metadata = self.lireMetaDonneesProjet(chemin_fichier)
                        algo = metadata.get("algo_type", "Inconnu")
                        label = f"{algo} : {file}"
                        menu_fichier.add_command(
                            label=label,
                            command=lambda f=chemin_fichier: self.chargerEtatComplet(f)
                        )
                    except Exception as e:
                        print(f"[⚠️] Erreur de lecture de métadonnées pour {file} : {e}")



        menu_fichier.add_separator()
        menu_fichier.add_command(label="Sauvegarder carte", command=self.sauvegarder_carte)
        menu_fichier.add_separator()
        menu_fichier.add_command(label="Quitter", command=self.quitter_application)
        menubar.add_cascade(label="Fichier", menu=menu_fichier)

        # Menu Algorithme
        menu_algo = tk.Menu(menubar, tearoff=0)
        menu_algo.add_command(label="Gérer les règles...", command=self.gerer_regles_algo)
        menu_algo.add_command(label="Créer scénarios automatiques", command=self.creer_scenarios_automatiques)
        menu_algo.add_separator()
        menu_algo.add_command(label="Générer un rapport...", command=self.demanderGenerationRapport)
        menubar.add_cascade(label="Algorithme", menu=menu_algo)

        # Menu Wikipedia
        menu_wiki = tk.Menu(menubar, tearoff=0)
        menu_wiki.add_command(label="Filtrage des catégories...", command=self.afficherFiltrageCategories)
        menu_wiki.add_separator()
        menu_wiki.add_command(label="Extraire les TAG P31", command=self.extraireTagsP31)
        menu_wiki.add_command(label="Importer un fichier P31...", command=self.importerFichierP31)

        menubar.add_cascade(label="Wikipedia", menu=menu_wiki)

        self.config(menu=menubar)

    def _setup_main_split(self, width, height):
        self.main_pane = PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        self._setup_side_panel()
        self._setup_canvas()

        self.main_pane.add(self.sidePanel, minsize=width)
        self.main_pane.add(self.canvas_image)

    def _setup_side_panel(self):
        # Le style pour afficher le texte des frames
        style = ttk.Style()
        style.configure("TitreFrame.TLabelframe.Label", font=("TkDefaultFont", 9, "bold"))

        # On crée le side panel
        self.sidePanel  = tk.Frame(self)
        self.sidePanel .pack(side="left", fill="y", padx=10, pady=10)

        # On crée une frame pour la gestion des segments
        self.frameSegment = ttk.LabelFrame(self.sidePanel, text="Sélection de la date", style="TitreFrame.TLabelframe")
        self.frameSegment.pack(side="top", fill="x", padx=0, pady=5)
        self.creerSelectionSegments(self.frameSegment)

        self.paneGauche = tk.PanedWindow(self.sidePanel, orient=tk.VERTICAL)
        self.paneGauche.pack(fill="both", expand=True)

        # Frame du haut : gestion des layers
        self.frameLayers = ttk.LabelFrame(self.paneGauche, text="Calques / Layers", style="TitreFrame.TLabelframe")
        self.frameLayers.config(height=100)
        self.paneGauche.add(self.frameLayers, minsize=100)
        self.paneGauche.paneconfig(self.frameLayers, height=200)

        self.creerLayerControle(self.frameLayers)

        # Frame du bas : panneau de contrôle
        self.frameIHMAlgo = ttk.LabelFrame(self.paneGauche, text="Algorithme", style="TitreFrame.TLabelframe")
        self.paneGauche.add(self.frameIHMAlgo, minsize=400)
        self.frameIHMAlgo.update_idletasks()  # force le layout
        label = self.moteurAlgo.getScenario().getDescriptionLisible()
        self.frameIHMAlgo.config(text=f"Scénario : {label}")


    def creerSelectionSegments(self, parent):
        segments = self.moteurAlgo.getListeSegments()

        if not self.varSegmentAffiche:
            self.varSegmentAffiche = tk.StringVar()

        if segments and not self.varSegmentAffiche.get():
            self.varSegmentAffiche.set(segments[0])

        comboSegment = ttk.Combobox(
            parent,
            values=segments,
            textvariable=self.varSegmentAffiche,
            state="readonly"
        )
        comboSegment.pack(fill="x", padx=5, pady=5)
        self.comboSegmentAffiche = comboSegment

        def onSegmentChange(event=None):
            segment = self.varSegmentAffiche.get()
            self.layerManager.segmentActif = segment             # 🎯 Synchronise l'affichage
            self.moteurAlgo.setSegment(segment, self.layerManager)             # 🔁 Changement logique
#            self.ihm_algo.reconstruire_interface()          # 🔁 Rafraîchit l'IHM centrale
            self.creerLayerControle(self.frameLayers)       # 🔁 Rafraîchit les layers visibles

        comboSegment.bind("<<ComboboxSelected>>", onSegmentChange)

### On gère le controle des layers
    def getNomScenarioSelectionne(self) -> str:
        selection = self.treeLayers.selection()
        if not selection:
            return None

        nom_scenario = selection[0]
        # Ignore les groupes (grp_user / grp_auto)
        if nom_scenario in ("grp_user", "grp_auto"):
            self.treeLayers.selection_remove(nom_scenario)
            return

        return nom_scenario # L'IHM utilise le nom lisible comme identifiant


    def cocherTousLesModules(self):
        """
        Coche tous les modules (cases associées) et met à jour le filtrage.
        """
        for var in self.varModulesFiltres.values():
            var.set(1)
        self.mettreAJourFiltrageModules()

    def reinitialiserComboFiltrageLevel(self):
        """
        Réinitialise la combo de niveau à 'Tous' et applique le filtrage associé.
        """
        self.comboFiltrageNiveau.set("Tous")
        self.onChangementNiveau()  # ou autre nom selon ta méthode liée


    def mettreAJourCheckboxGlobale(self):
        etats = [var.get() for var in self.checkVarsLayers.values()]
        if all(etats):
            self.var_select_all.set(1)
        elif not any(etats):
            self.var_select_all.set(0)
        else:
            self.var_select_all.set(-1)  # état mixte visuel

    def mettreAJourFiltrageModules(self):
        modules_visibles = [
            module for module, var in self.varModulesFiltres.items()
            if var.get()
        ]

        if not modules_visibles:
            self.layerManager.setFiltreTag("module", None)  # désactive tout
        else:
            self.layerManager.setFiltreTag("module", modules_visibles)

        self._refresh_images()

    def onChangementNiveau(self, event=None):
        valeur = self.comboFiltrageNiveau.get()
        self.layerManager.setFiltreTag("level", valeur.lower())
        self._refresh_images()


    def selectionnerUniquementScenarioActif(self, nom_scenario_lisible: str):
        """
        Rend visible uniquement le scénario correspondant au nom donné.
        Utilise directement le nom affiché dans la Treeview (description lisible).
        """
        segment = self.moteurAlgo.segment_actif
        for nomLayer in self.layerManager.getNomsLayers(segment):
            layer = self.layerManager.getLayer(nomLayer, segment)
            visible = (nomLayer == nom_scenario_lisible)
            if layer:
                layer.setVisible(visible)

        # Met à jour l'affichage avec ce scénario sélectionné
        self.creerLayerControle(self.frameLayers, scenario_a_selectionner=nom_scenario_lisible)
        self.updaterScenarioActif()



    def updaterScenarioActif(self, event = None):

        nom_scenario = self.getNomScenarioSelectionne()
        if nom_scenario is None:
            return

        # Appel logique d’application de scénario
        self.moteurAlgo.appliquerScenario(nom_scenario)
        if hasattr(self, "frameIHMAlgo") and self.frameIHMAlgo:
            self.frameIHMAlgo.config(text=f"Scénario : {nom_scenario}")
        if hasattr(self, "ihm_algo") and self.ihm_algo:
            self.ihm_algo.reconstruire_interface(nom_scenario)

        # On met à jour les boutons Action
        self.mettreAJourEtatBoutonsScenario()


    def mettreAJourEtatBoutonsScenario(self):
        """
        Active ou désactive les boutons Dupliquer, Éditer et Supprimer
        en fonction du type du scénario identifié par son label lisible.
        """
        nom_scenario_lisible = self.getNomScenarioSelectionne()
        if nom_scenario_lisible is None:
            self.boutonToggleVisibilite.configure(state="disabled")
            self.boutonDupliquer.config(state="disabled")
            self.boutonEditer.config(state="disabled")
            self.boutonSupprimer.config(state="disabled")
            return

        scenario = self.moteurAlgo.getScenarioNomLisible(nom_scenario_lisible)
        type_scenario = scenario.getTypeScenario()
        layer = self.layerManager.getLayer(nom_scenario_lisible)

        # On set la visibilité de l'icone "Afficher/Cacher"en fonction de la visibilté du layer'
        icone = self.icone_visible if layer.estVisible() else self.icone_invisible
        self.boutonToggleVisibilite.configure(image=icone, state="normal")


        # On peut dupliquer n'importe quel type de scénario'
        self.boutonDupliquer.config(state="normal")

        # on ne peut éditer que les scnéario utilisateurs et défaut
        if type_scenario in (TypeScenario.DEFAULT, TypeScenario.UTILISATEUR):
            self.boutonEditer.config(state="normal")
        else:
            self.boutonEditer.config(state="disabled")

        # Règle : on ne peut supprimer que si au moins 1 scénario (DEFAULT ou UTILISATEUR) resterait
        nb_editables = (
            len(self.moteurAlgo.getListeScenarios(type_scenario=TypeScenario.DEFAULT)) +
            len(self.moteurAlgo.getListeScenarios(type_scenario=TypeScenario.UTILISATEUR))
        )

        if nb_editables >= 2:
            self.boutonSupprimer.config(state="normal")
        else:
            self.boutonSupprimer.config(state="disabled")



    def creerLayerControle(self, parent, scenario_a_selectionner=None):

        # 🧹 Nettoyage avant recréation
        for widget in parent.winfo_children():
            widget.destroy()

        # === Frame principale de filtrage ===
        frame_filtrage = ttk.Frame(parent)
        frame_filtrage.pack(fill="x", padx=5, pady=5)

        # === Ligne de configuration des POIs ===
        ligne_poi = ttk.Frame(frame_filtrage)
        ligne_poi.pack(fill="x", pady=(0, 2))

        def togglePOIVisible():
            """Active ou désactive l'affichage des POIs."""
            self.listePOIs.layer.setVisible(self.varPOIVisible.get())
            self._refresh_images()

        ttk.Label(ligne_poi, text="POI").pack(side="left", padx=(0, 2))
        tk.Checkbutton(
            ligne_poi,
            variable=self.varPOIVisible,
            command=togglePOIVisible
        ).pack(side="left", padx=(0, 2))

        ttk.Label(ligne_poi, text="Pertinence:").pack(side="left", padx=(0, 4))
        self.comboPOIPertinence = ttk.Combobox(
            ligne_poi,
            values=["Elevée", "Moyenne", "Faible"],
            textvariable=self.varPOIPertinence,
            state="readonly",
            width=8,
       )
        self.varPOIPertinence.trace_add("write", lambda *args: self._refresh_images())
        self.comboPOIPertinence.pack(side="left", padx=(0, 4))

        ttk.Label(ligne_poi, text="Catégories:").pack(side="left", padx=(0, 4))
        self.comboPOICategorie = ttk.Combobox(
            ligne_poi,
            values=["Filtrées", "Toutes"],
            textvariable=self.varPOICategorie,
            state="readonly",
            width=8,
        )
        self.varPOICategorie.trace_add("write", lambda *args: self._refresh_images())
        self.comboPOICategorie.pack(side="left", padx=(0, 4))

        ttk.Label(ligne_poi, text="Sujet:").pack(side="left", padx=(0, 4))
        try:
            with sqlite3.connect(self.chemin_bd) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT source_backlink FROM SourceBacklink ORDER BY source_backlink"
                )
                sujets = ["Tous"] + [row[0] for row in cursor.fetchall()]
        except Exception:
            sujets = []
        self.comboPOISujet = ttk.Combobox(
            ligne_poi,
            values=sujets,
            textvariable=self.varPOISujet,
            state="readonly",
            width=15
        )   
        if sujets and not self.varPOISujet.get():
            self.varPOISujet.set(sujets[0])
        self.varPOISujet.trace_add("write", lambda *args: self._refresh_images())
        self.comboPOISujet.pack(side="left")
#
# 2ème ligne avec filtrage pr TAG
#



        # === Ligne de filtrage des layers ===
        ligne_niveau_module = ttk.Frame(frame_filtrage)
        ligne_niveau_module.pack(fill="x", pady=(0, 2))

        ttk.Label(ligne_niveau_module, text="Tracé:").pack(side="left", padx=(0, 4))
        self.comboFiltrageNiveau = ttk.Combobox(ligne_niveau_module, values=["Tous", "Construction", "Design"], state="readonly", width=15)
        self.comboFiltrageNiveau.set("Tous")
        self.comboFiltrageNiveau.pack(side="left", padx=(0, 10))
        self.comboFiltrageNiveau.bind("<<ComboboxSelected>>", self.onChangementNiveau)

        self.varModulesFiltres = {}  # dict[module_id: tk.IntVar]
        modules = self.moteurAlgo.getModulesAvecAffichage()
        for module_id in modules:
            var = tk.IntVar(value=1)  # 1 = visible par défaut
            self.varModulesFiltres[module_id] = var
            cb = tk.Checkbutton(
                ligne_niveau_module,
                text=module_id.capitalize(),
                variable=var,
                command=self.mettreAJourFiltrageModules
            )
            cb.pack(side="left", padx=(2, 2))





#
# Filtrae des layers par attributs
#
        # === Ligne 2 : Filtrage des layers en eux même ===
        ligne_checkbox = ttk.Frame(frame_filtrage)
        ligne_checkbox.pack(fill="x", pady=(2, 0))


        def ouvrir_fenetre_filtrage_scenarios_auto():
            segment = self.moteurAlgo.segment_actif

            scenarioAutoExistant = self.moteurAlgo.aDesScenarioAutomatiques(segment)
            if not scenarioAutoExistant:
                print("Aucun scénario automatique n’existe pour ce segment.")
                return

            parametresScenario = self.moteurAlgo.getListeParametresScenarioAutomatique(segment)
            if not parametresScenario:
                print("Aucun paramètre automatique trouvé.")
                return

            # Préparer la popup
            popup = tk.Toplevel(self)
            popup.title("Filtrer les scénarios automatiques")
            popup.transient(self)
            popup.grab_set()

            frame_principal = ttk.Frame(popup)
            frame_principal.pack(fill="both", expand=True, padx=10, pady=10)

            zone_gauche = ttk.Frame(frame_principal)
            zone_gauche.grid(row=0, column=0, sticky="nsew")
            colonne_boutons = ttk.Frame(frame_principal)
            colonne_boutons.grid(row=0, column=1, sticky="ns", padx=(20, 0))

            frame_principal.columnconfigure(0, weight=1)

            # Préparer les variables de filtres
            self.filtres_vars = {}  # clef = (module, attribut), valeur = {valeur: BooleanVar}

            for col_index, (module, attribut) in enumerate(parametresScenario):


                valeurs_possibles = self.moteurAlgo.getValeursParametre(module, attribut)
                if not valeurs_possibles:
                    continue

                cadre = ttk.LabelFrame(zone_gauche, text=attribut+module.capitalize())
                cadre.grid(row=0, column=col_index, padx=5, pady=5, sticky="n")

                self.filtres_vars[(module, attribut)] = {}

                for val in valeurs_possibles:
                    var = tk.BooleanVar(value=True)
                    cb = tk.Checkbutton(cadre, text=val, variable=var)
                    cb.pack(anchor="w")
                    self.filtres_vars[(module, attribut)][val] = var

            # === FONCTIONS BOUTONS ===
            def tout_selectionner():
                for d in self.filtres_vars.values():
                    for var in d.values():
                        var.set(True)

            def tout_deselectionner():
                for d in self.filtres_vars.values():
                    for var in d.values():
                        var.set(False)

            def appliquer():
                def appliquer_filtre(scenario, filtre: dict[tuple[str, str], set[str]]) -> bool:
                    """
                    Détermine si un scénario respecte le filtre actif.

                    :param scenario: objet Scenario
                    :param filtre: dict {(module, attribut): set(valeurs acceptées)}
                    :return: True si le scénario doit être visible, False sinon
                    """
                    for module, attribut, short, valeur in scenario.parametres:
                        cle = (module, attribut)
                        if cle in filtre:
                            if valeur not in filtre[cle]:
                                return False  # Ce paramètre ne respecte pas le filtre
                    return True  # Tous les paramètres sont conformes au filtre

                # 1. Construire le filtre actif à partir des cases cochées
                filtre = {}
                for (module, attribut), dict_valeurs in self.filtres_vars.items():
                    valeurs_conservees = [val for val, var in dict_valeurs.items() if var.get()]
                    if valeurs_conservees:
                        filtre[(module, attribut)] = set(valeurs_conservees)

                # 2. Appliquer le filtre aux scénarios automatiques
                dict_scenarios = self.moteurAlgo.getScenariosDict(type_scenario=TypeScenario.AUTOMATIQUE)

                for nom, scenario in dict_scenarios.items():
                    visible = appliquer_filtre(scenario, filtre)
                    layer = self.layerManager.getLayer(scenario.getDescriptionLisible())
                    layer.setVisible(visible)

                # 3. Rafraîchir la carte / IHM
                self.creerLayerControle(self.frameLayers)

                popup.destroy()

            def annuler():
                popup.destroy()

            # === BOUTONS ACTIONS ===
            ttk.Button(colonne_boutons, text="Tout sélectionner", command=tout_selectionner).pack(fill="x", pady=2)
            ttk.Button(colonne_boutons, text="Tout désélectionner", command=tout_deselectionner).pack(fill="x", pady=2)
            ttk.Button(colonne_boutons, text="Appliquer", command=appliquer).pack(fill="x", pady=(20, 2))
            ttk.Button(colonne_boutons, text="Annuler", command=annuler).pack(fill="x", pady=2)

            popup.update_idletasks()



        # Checkbox "Tout sélectionner"
        def on_toggle_select_all():
            etat = self.var_select_all.get()

            for nom_scenario in self.treeLayers.get_children("grp_user") + self.treeLayers.get_children("grp_auto"):
                layer = self.layerManager.getLayer(nom_scenario)
                if not layer:
                    continue

                # Selon l’état du bouton à 3 états, on agit :
                if etat == 1:  # ✓ Tout afficher
                    layer.setVisible(True)
                    self.treeLayers.set(nom_scenario, column="vis", value="✓")
                elif etat == 0:  # ✗ Tout masquer
                    layer.setVisible(False)
                    self.treeLayers.set(nom_scenario, column="vis", value="")
                else:  # État "indéterminé" : on ignore
                    pass


            self._refresh_images()

        # Label "Select"
        label_select = ttk.Label(ligne_checkbox, text="Selection:")
        label_select.pack(side="left", padx=(0, 0))

        # Checkbox à 3 états
        self.var_select_all = tk.IntVar(value=-1)  # -1 = état mixte

        check_select = tk.Checkbutton(
            ligne_checkbox,
            variable=self.var_select_all,
            tristatevalue=-1,
            onvalue=1,
            offvalue=0,
            text="",  # pas de texte pour compacité
            width=2,
            command=on_toggle_select_all
        )
        check_select.pack(side="left", padx=(0, 0))

        # Bouton "..."
        label_filtrageauto = ttk.Label(ligne_checkbox, text="Scénario auto:")
        label_filtrageauto.pack(side="left", padx=(0, 0))
        btn_menu = ttk.Button(
            ligne_checkbox,
            text="…",
            width=2,
            command=ouvrir_fenetre_filtrage_scenarios_auto
        )
        btn_menu.pack(side="left")


        def ouvrirFenetreEditionScenario(nomscenario, nouveau=False):
            #On récupère le scénario et le layer pour l'initialisation des données et la sauvegarde
            scenario = self.moteurAlgo.getScenarioNomLisible(nomscenario)
            layer = self.layerManager.getLayer(scenario.getDescriptionLisible(), segment=scenario.segment)

            top = tk.Toplevel(self)
            top.title(f"Édition – {scenario.getDescriptionLisible()}")
            top.transient(self)
            top.grab_set()


            # === Nom ===
            var_nom = tk.StringVar(value=scenario.nom)
            ttk.Label(top, text="Nom du scénario :").pack(anchor="w", padx=10, pady=(10, 2))
            entry_nom = ttk.Entry(top, textvariable=var_nom, width=30)
            entry_nom.pack(padx=10, fill="x")

            # === Couleur + Épaisseur ===
            couleur =  "#000000" if nouveau else layer.getCouleur()
            var_couleur = tk.StringVar(value="#000000")
            epaisseur = 1 if nouveau else layer.getEpaisseur()
            var_epaisseur = tk.IntVar(value=1)

            frame_style = ttk.Frame(top)
            frame_style.pack(fill="x", padx=10, pady=(10, 0))

            ttk.Label(frame_style, text="Couleur :").pack(side="left", padx=(0, 5))

            # --- Couleur (canvas cliquable) ---
            def choisirCouleur():
                couleur = colorchooser.askcolor(initialcolor=var_couleur.get())[1]
                if couleur:
                    var_couleur.set(couleur)
                    canvas_couleur.config(bg=couleur)

            canvas_couleur = tk.Canvas(
                frame_style, width=20, height=20, bg=var_couleur.get(), highlightthickness=1, relief="solid"
            )
            canvas_couleur.pack(side="left", padx=(0, 15))
            canvas_couleur.bind("<Button-1>", lambda e: choisirCouleur())

            ttk.Label(frame_style, text="Épaisseur :").pack(side="left", padx=(0, 5))
            spin_epaisseur = ttk.Spinbox(frame_style, from_=1, to=10, textvariable=var_epaisseur, width=5)
            spin_epaisseur.pack(side="left")


            # === Scénario solution ===
            solutionActive = scenario.getSolution()
            var_solution = tk.BooleanVar(value=solutionActive)
            ttk.Checkbutton(top, text="Ce scénario est une solution", variable=var_solution).pack(anchor="w", padx=10, pady=(10, 2))



            # === Bouton Sauvegarder ===
            def sauvegarder():
                ancien_nom = scenario.nom
                ancien_nom_lisible = scenario.getDescriptionLisible()
                nouveau_nom = var_nom.get()
                self.moteurAlgo.renommerScenario(ancien_nom, nouveau_nom)
                self.layerManager.renommerLayer(ancien_nom_lisible, nouveau_nom)

                # Couleur / épaisseur → layer graphique
                if layer:
                    couleur_bgr = hexVersBGR(var_couleur.get())
                    layer.setCouleur(couleur_bgr)
                    layer.setEpaisseur(var_epaisseur.get())

                # Si c'est une solution'
                scenario.setSolution(var_solution.get())

                # 3. Rafraîchir la carte / IHM
                self.creerLayerControle(self.frameLayers)
                top.destroy()

            ttk.Button(top, text="Enregistrer", command=sauvegarder).pack(pady=15)

            top.mainloop()


        def actionDupliquerScenario():
            """
            Crée un nouveau scénario utilisateur basé sur celui sélectionné,
            puis ouvre immédiatement la fenêtre d’édition.
            """
            nom_scenario_lisible = self.getNomScenarioSelectionne()
            if nom_scenario_lisible == None:
                return
            base = self.moteurAlgo.getScenarioNomLisible(nom_scenario_lisible)

            # Générer un nom unique
            base_name = base.nom or "copie"
            i = 0
            i_str = ""
            nouveaux_noms = set(self.moteurAlgo.getScenariosDict(base.segment).keys())
            while f"{base_name} - Copie{i_str}" in nouveaux_noms:
                i += 1
                i_str = str(i)
            nouveau_nom = f"{base_name} - Copie{i_str}"

            # Créer le nouveau scénario
            scenario = self.moteurAlgo.creerScenarioUtilisateur(nouveau_nom, base, self.layerManager, couleur=(0, 0, 0))  # noir par défaut

            # Sélectionner visuellement le nouveau layer
            label = scenario.getDescriptionLisible()
            self.creerLayerControle(self.frameLayers, scenario_a_selectionner=label)

            # Ouvrir la fenêtre d’édition en lui disant que l'objet est nouveau'
            ouvrirFenetreEditionScenario(label, True)


        def actionEditerScenario():
            nom_scenario_lisible = self.getNomScenarioSelectionne()
            if nom_scenario_lisible == None:
                return
            ouvrirFenetreEditionScenario(nom_scenario_lisible)

        def actionSupprimerScenario():
            nom_scenario_lisible = self.getNomScenarioSelectionne()
            if not nom_scenario_lisible:
                return

            from tkinter import messagebox
            reponse = messagebox.askyesno(
                "Confirmation de suppression",
                f"Voulez-vous vraiment supprimer le scénario :\n\n{nom_scenario_lisible} ?"
            )

            if not reponse:
                return

            # Supprimer du moteur et du layer manager (la fonction supprimer fait les deux))
            self.moteurAlgo.supprimerScenarioNomLisible(nom_scenario_lisible, self.layerManager)

            # Rafraîchir l'affichage
            self.creerLayerControle(self.frameLayers)

        def toggleVisibiliteLayer():
            nom_scenario = self.getNomScenarioSelectionne()
            if not nom_scenario:
                return

            layer = self.layerManager.getLayer(nom_scenario)
            if not layer:
                return

            nouveau_statut = not layer.estVisible()
            layer.setVisible(nouveau_statut)
            self.creerLayerControle(self.frameLayers, scenario_a_selectionner=nom_scenario)

        # === Boutons Actions alignés à droite sur la même ligne ===
        actions_frame = ttk.Frame(ligne_checkbox)
        actions_frame.pack(side="right")

        ttk.Label(actions_frame, text="Actions :").pack(side="left", padx=(0, 5))

        self.icone_visible = charger_icone("images/icone_oeil_ouvert.png")
        self.icone_invisible = charger_icone("images/icone_oeil_barre.png")
        self.icone_dupliquer = charger_icone("images/save.png")
        self.icone_editer = charger_icone("images/edit.png")
        self.icone_supprimer = charger_icone("images/delete.png")

        self.boutonToggleVisibilite = ttk.Button(
            actions_frame,
            image=self.icone_visible,
            command=toggleVisibiliteLayer
        )
        self.boutonToggleVisibilite.pack(side="left", padx=2)

        self.boutonDupliquer = ttk.Button(
            actions_frame, image=self.icone_dupliquer, command=actionDupliquerScenario
        )
        self.boutonDupliquer.pack(side="left", padx=(2, 2))

        self.boutonEditer = ttk.Button(
            actions_frame, image=self.icone_editer, command=actionEditerScenario
        )
        self.boutonEditer.pack(side="left", padx=(2, 2))

        self.boutonSupprimer = ttk.Button(
            actions_frame, image=self.icone_supprimer, command=actionSupprimerScenario
        )
        self.boutonSupprimer.pack(side="left", padx=(2, 2))





#
# Affichage des layers
#


        # on crée une troisième ligne dans laquelle on affichera la Tree View + liste de boutons  de commande
        frameLigneLayer = ttk.Frame(parent)
        frameLigneLayer.pack(fill="x", padx=5, pady=2)


        def onDoubleClickLayer(event):
            item_id = self.treeLayers.identify_row(event.y)

            if item_id in ("grp_user", "grp_auto", "", None):
                return  # On ignore les groupes

            self.selectionnerUniquementScenarioActif(item_id)


        self.treeLayers = ttk.Treeview(
            frameLigneLayer,
            columns=("vis", "solution"),
            show="tree headings",
            selectmode="extended",
            height=12
        )
        frameLigneLayer.grid_columnconfigure(0, weight=1)
        self.treeLayers.grid(row=0, column=0, sticky="nsew")
        self.treeLayers.bind("<Double-1>", onDoubleClickLayer)

        # Scrollbar verticale
        scrollbar_y = ttk.Scrollbar(frameLigneLayer, orient="vertical", command=self.treeLayers.yview)
        self.treeLayers.configure(yscrollcommand=scrollbar_y.set)

        # Placement côte à côte
        self.treeLayers.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")

        # Expand la colonne 0 (Treeview) pour qu'elle prenne l'espace restant
        frameLigneLayer.grid_columnconfigure(0, weight=1)
        frameLigneLayer.grid_rowconfigure(0, weight=1)



        # Colonne #0 = texte principal (nom + carré)
        self.treeLayers.column("#0", width=400, anchor = "w", stretch=True)
        self.treeLayers.heading("#0", text="Scénario", anchor = "w")

        # Colonne visibilité
        self.treeLayers.column("vis", width=30, anchor="center", stretch=False)
        self.treeLayers.heading("vis", text="👁", anchor="center")

        # Colonne solution
        self.treeLayers.column("solution", width=30, anchor="center", stretch=False)
        self.treeLayers.heading("solution", text="🥇", anchor="center")



        # Groupes visibles dans colonne #0
        grp_user = self.treeLayers.insert("", "end", iid="grp_user", text="📘 Scénarios personnalisés", open=True)
        grp_auto = self.treeLayers.insert("", "end", iid="grp_auto", text="⚙️ Scénarios automatiques", open=False)

        # Récupération des scénarios existants
        scenarios_dict = self.moteurAlgo.getScenariosDict()

        for nom_scenario, scenario in scenarios_dict.items():
            # On récupère le nom et le type du scnéario puis sa visibilité et sa couleur à partir du layer
            desc = scenario.getDescriptionLisible()
            type_scenario = scenario.getTypeScenario()
            layer = self.layerManager.getLayer(desc)
            visible = layer.estVisible()
            couleur_bgr = layer.getCouleur()

            # Couleur texte
            hex_color = bgrVersHex(couleur_bgr)
            tag_name = f"tag_{nom_scenario}"

            style = ttk.Style()
            style.configure(f"{tag_name}.Treeview", foreground=hex_color)
            self.treeLayers.tag_configure(tag_name, foreground=hex_color)

            # Groupe cible
            if type_scenario == TypeScenario.AUTOMATIQUE:
                parent = grp_auto
            else:
                parent = grp_user

            vis = "✓" if visible else "✗"
            label = f"■ {desc}"
            symbole_solution = "✅" if scenario.getSolution() else ""

            self.treeLayers.insert(
                parent,
                "end",
                iid=desc,
                text=label,  # carré + nom
                values=(vis, symbole_solution),  # desc peut être ajouté si utile
                tags=(tag_name,)
            )
            self.treeLayers.bind("<<TreeviewSelect>>", self.updaterScenarioActif)


        # Sélectionne le scénario actif si précisé
        if scenario_a_selectionner:
            self.treeLayers.selection_set(scenario_a_selectionner)
            self.treeLayers.see(scenario_a_selectionner)

        # Si rien de précisé mais un scénario est actif, on le sélectionne
        else:
            nom_actif = self.moteurAlgo.getScenario().getDescriptionLisible()
            if nom_actif in self.treeLayers.get_children("grp_user") + self.treeLayers.get_children("grp_auto"):
                self.treeLayers.selection_set(nom_actif)
                self.treeLayers.see(nom_actif)
                # Et on applique explicitement
                self.updaterScenarioActif()

        self._refresh_images()



### Gestion des évènements utilisatuer sur l'image'
    def _setup_canvas(self):  # ajout des événements souris
        self.canvas_image = tk.Canvas(self, bg="gray")
        self.canvas_image.bind("<Configure>", self._on_canvas_resize)
        self.canvas_image.bind("<ButtonPress-1>", self._on_mouse_press)
        self.canvas_image.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas_image.bind("<MouseWheel>", self._on_mouse_wheel)
        self.last_mouse_pos = None
        self.menu_contextuel = tk.Menu(self, tearoff=0)
        self.canvas_image.bind("<Button-3>", self._on_right_click)
        self.canvas_image.bind("<Motion>", self._on_mouse_move_global)

        # Pour la gestion de l'affichage des distance
        self.bind("<Escape>", self.desactiverMesureDistance)

    def _on_canvas_resize(self, event):
        import src.affichage_fenetre as af

        (w_img, h_img) = image_size
        if event.width <= 1 or event.height <= 1:
            return

        af.frame_width = event.width
        af.frame_height = event.height

        scale_x = af.frame_width / w_img
        scale_y = af.frame_height / h_img
        af.zoom_factor = min(scale_x, scale_y)

        af.pan_x = 0
        af.pan_y = 0

        # Affichage de la fenetre des distances
        if hasattr(self, "overlay"):
            self.overlay.place(x=10, y=self.canvas_image.winfo_height() - 10, anchor="sw")

        self._refresh_images()

    def _refresh_images(self, afficherPOIsUniquement = False):

        if not hasattr(self, "canvas_image"):
            return  # L'objet n'est pas encore prêt

        (w_img, h_img) = image_size
        canvas = display(self.layerManager, self.listePOIs, retourner_image=True, afficherPOIsUniquement = afficherPOIsUniquement)

        image_rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        image_pil = Image.fromarray(image_rgb)
        image_pil = image_pil.resize((self.canvas_image.winfo_width() or 800, self.canvas_image.winfo_height() or 800))
        self.tk_image = ImageTk.PhotoImage(image_pil)
        self.canvas_image.delete("all")
        self.canvas_image.create_image(0, 0, anchor="nw", image=self.tk_image)

        minimap_height = int(250 * 2 / 3)
        minimap_ratio = w_img / h_img
        minimap_width = int(minimap_ratio * minimap_height)
        from src.affichage_fenetre import img as full_img
        minimap = cv2.resize(full_img, (minimap_width, minimap_height))
        minimap_rgb = cv2.cvtColor(minimap, cv2.COLOR_BGR2RGB)
        minimap_pil = Image.fromarray(minimap_rgb)
        self.tk_minimap = ImageTk.PhotoImage(minimap_pil)

        x_offset = self.tk_image.width() - self.tk_minimap.width() - 10
        y_offset = self.tk_image.height() - self.tk_minimap.height() - 10

        self.canvas_image.create_rectangle(
            x_offset - 2, y_offset - 2,
            x_offset + self.tk_minimap.width() + 2,
            y_offset + self.tk_minimap.height() + 2,
            fill="black"
        )

        self.canvas_image.create_image(x_offset, y_offset, anchor='nw', image=self.tk_minimap)

        # Dessiner le cadre de la vue actuelle sur la mini-carte
        import src.affichage_fenetre as af
        ratio_x = self.tk_minimap.width() / w_img
        ratio_y = self.tk_minimap.height() / h_img

        vue_x = af.pan_x * ratio_x
        vue_y = af.pan_y * ratio_y
        vue_w = af.frame_width * ratio_x / af.zoom_factor
        vue_h = af.frame_height * ratio_y / af.zoom_factor

        self.canvas_image.create_rectangle(
            x_offset + vue_x, y_offset + vue_y,
            x_offset + vue_x + vue_w, y_offset + vue_y + vue_h,
            outline="red", width=2
        )



### Gesion des évènements souris

    def _on_mouse_move_global(self, event):

        px, py = transformer_pixel_affichage_vers_image(event.x, event.y)
        if px is None or py is None:
            return

        # On gère d'abord les tooltips'
        obj = selectionObjet(px, py, self.layerManager, layerPOIs = self.listePOIs.layer)
        texte = None
        if obj is not None:
            lignes = obj.getTooltipComplet() if hasattr(obj, "getTooltipComplet") else []
            texte = "\n".join(lignes)

        if not hasattr(self, "tooltip_overlay"):
            self.tooltip_overlay = self.tooltip_overlay = tk.Label(
                self.canvas_image,
                text="",
                background="white",
                relief="solid",
                borderwidth=1,
                font=("TkDefaultFont", 9),
                justify="left",
                wraplength=200  # largeur max en pixels
            )

        if texte:
            self.tooltip_overlay.config(text=texte)
            self.tooltip_overlay.place(x=event.x + 10, y=event.y + 10)
        else:
            self.tooltip_overlay.place_forget()

        #On gère la mesure de la distance
        if not self.pointReferenceMesureDistance:
            return

        x_ref, y_ref = self.pointReferenceMesureDistance
        x, y = pixels_to_lambert93(px, py)

        dx = x - x_ref
        dy = y - y_ref
        distance_km = (dx ** 2 + dy ** 2) ** 0.5 / 1000

        texte = f"Distance depuis {self.nomReferenceMesureDistance} : {distance_km:.2f} km"

        # Efface le contenu précédent
        self.overlay.delete("all")

        # Dessine un fond gris clair (simulant la transparence)
        self.overlay.create_rectangle(0, 0, 300, 30, fill="#f0f0f0", outline="gray")

        # Texte noir par-dessus
        self.overlay.create_text(10, 15, text=texte, anchor="w", fill="black", font=("TkDefaultFont", 10))




    def _on_mouse_press(self, event):

        import src.affichage_fenetre as af
        (w_img, h_img) = image_size
        minimap_height = int(250 * 2 / 3)
        minimap_ratio = w_img / h_img
        minimap_width = int(minimap_ratio * minimap_height)

        x_offset = self.tk_image.width() - minimap_width - 10
        y_offset = self.tk_image.height() - minimap_height - 10

        if x_offset <= event.x <= x_offset + minimap_width and y_offset <= event.y <= y_offset + minimap_height:
            rel_x = (event.x - x_offset) / minimap_width
            rel_y = (event.y - y_offset) / minimap_height
            af.pan_x = int(rel_x * w_img - af.frame_width / (2 * af.zoom_factor))
            af.pan_y = int(rel_y * h_img - af.frame_height / (2 * af.zoom_factor))
            af.pan_x = int(max(0, min(af.pan_x, w_img - af.frame_width / af.zoom_factor)))
            af.pan_y = int(max(0, min(af.pan_y, h_img - af.frame_height / af.zoom_factor)))
            self._refresh_images()
        else:
            # 🎯 Clic sur l'image principale → tentative de sélection
            px, py = transformer_pixel_affichage_vers_image(event.x, event.y)
            if px is not None and py is not None:
                obj = selectionObjet(px, py, self.layerManager)
                if obj:
                    if not obj.estSelectionne():
                        for o in self.layerManager.getListeObjetsGraphiquesVisible():
                            o.setSelection(False)
                        obj.setSelection(True)


                else:
                    # Clic dans le vide : tout désélectionner
                    for o in self.layerManager.getListeObjetsGraphiquesVisible():
                        o.setSelection(False)
                self._refresh_images()  # ✅ Affiche les changements

            self.last_mouse_pos = (event.x, event.y)

    def _on_right_click(self, event):

        # 1. Conversion coordonnées écran → pixels image
        px, py = transformer_pixel_affichage_vers_image(event.x, event.y)
        if px is None or py is None:
            return

        self.menu_contextuel.delete(0, tk.END)
        self.menu_contextuel.add_command(
            label="Centrer la carte",
            command=lambda: self.centrerCarte(px, py))


        # Gestion de l'outil de distance
        # 1. Conversion coordonnées pixels image → Lambert93
        x_l93, y_l93 = pixels_to_lambert93(px, py)


        # 2. Chercher d'abord une ville
        ville = selectionVille(px, py)

        # 3. Si pas de ville, chercher un objet graphique
        point = None
        if not ville:
            obj = selectionObjet(px, py, self.layerManager, layerPOIs = self.listePOIs.layer)
            if isinstance(obj, PointGraphique) and obj.estVisible():
                point = obj

        # 4. Déterminer le texte et les coordonnées de référence
        if ville:
            nom = ville.getNom()
            texte = f"Mesurer depuis {nom}"
            x_ref, y_ref = ville.coordonneesLambert()
        elif point:
            nom = point.getNom()
            texte = f"Mesurer depuis \"{nom}\""
            x_ref, y_ref = point.coordonneesLambert()
        else:
            lat, lon = lambert93_to_gps(x_l93, y_l93)
            nom = f"({lat:.4f}, {lon:.4f})"
            texte = f"Mesurer depuis {nom}"
            x_ref, y_ref = x_l93, y_l93

        # 5. Créer le menu contextuel
        self.menu_contextuel.add_command(
            label=texte,
            command=lambda: self.definirPointReferenceMesure(x_ref, y_ref, nom)
        )

        # Si c'est un POIs'
        if isinstance(point, SymboleWiki):
            self.menu_contextuel.add_command(label=f"Ouvrir le lien « {point.url} »", command=lambda: webbrowser.open(point.url))


        #
        # Analyse en détail d'un scénario'
        #
        if obj:
            layer = obj.getLayer()
            if layer:
                nom_scenario_lisible = layer.nom
                self.menu_contextuel.add_separator()
                self.menu_contextuel.add_command(
                    label=f"Analyser ce scénario : {nom_scenario_lisible}",
                    command=lambda: self.analyserScenarioDepuisCarte(nom_scenario_lisible)
                )
        #
        # On met à jour le menu
        #
        self.menu_contextuel.tk_popup(event.x_root, event.y_root)
        self.menu_contextuel.grab_release()



    def cacher_objet_selectionne(self):
        if hasattr(self, 'objet_selectionne') and self.objet_selectionne:
            self.objet_selectionne.setVisible(False)
            self._refresh_images()
            print("👁️ Objet rendu invisible.")

    def _on_mouse_drag(self, event):
        if self.last_mouse_pos is None:
            return
        dx = event.x - self.last_mouse_pos[0]
        dy = event.y - self.last_mouse_pos[1]
        import src.affichage_fenetre as af
        af.pan_x = max(0, af.pan_x - int(dx / af.zoom_factor))
        af.pan_y = max(0, af.pan_y - int(dy / af.zoom_factor))
        self.last_mouse_pos = (event.x, event.y)
        self._refresh_images()


    def _on_mouse_wheel(self, event):
        import src.affichage_fenetre as af
        old_zoom = af.zoom_factor
        af.zoom_factor *= 0.9 if event.delta > 0 else 1.1
        af.zoom_factor = max(af.zoom_factor, 0.1)
        canvas_x = event.x
        canvas_y = event.y
        rel_x = canvas_x / af.frame_width
        rel_y = canvas_y / af.frame_height
        af.pan_x += int((rel_x) * af.frame_width * (1 / old_zoom - 1 / af.zoom_factor))
        af.pan_y += int((rel_y) * af.frame_height * (1 / old_zoom - 1 / af.zoom_factor))
        self._refresh_images()

### Gestion de l'outil Distance

    def definirPointReferenceMesure(self, x_l93: float, y_l93: float, nom: str):
        """
        Enregistre un point de référence pour la mesure de distance.
        Ce point est défini en coordonnées Lambert93, avec un nom affiché.
        """
        self.pointReferenceMesureDistance = (x_l93, y_l93)
        self.nomReferenceMesureDistance = nom

        print(f"📏 Point de mesure défini : {nom} ({x_l93:.1f}, {y_l93:.1f})")

        # Crée dynamiquement l’overlay s’il n’existe pas
        if not hasattr(self, "overlay") or self.overlay is None:
            self.overlay = tk.Canvas(self.canvas_image, width=300, height=30, highlightthickness=0, bg="#f0f0f0")
            self.overlay.place(x=10, y=self.canvas_image.winfo_height() - 30, anchor="sw")

    def desactiverMesureDistance(self, event=None):
        """
        Désactive le mode de mesure de distance :
        - Supprime le point de référence
        - Efface l'affichage de la distance
        - Supprime le suivi de la souris
        """
        self.pointReferenceMesureDistance = None
        self.nomReferenceMesureDistance = ""

        if hasattr(self, "overlay") and self.overlay:
            self.overlay.destroy()
            self.overlay = None
        print("❌ Mode mesure désactivé (touche Échap)")


### Centrage de la carte


    def centrerCarte(self, px, py, zoom_max=2.5):
        from affichage_fenetre import frame_width, frame_height, image_size
        w_img, h_img = image_size

        # Zoom auto si nécessaire
        facteur_zoom = zoom_factor
        while True:
            crop_w = frame_width / facteur_zoom
            crop_h = frame_height / facteur_zoom
            cadre_sort = (
                px - crop_w / 2 < 0 or
                px + crop_w / 2 > w_img or
                py - crop_h / 2 > h_img or
                py - crop_h / 2 < 0
            )
            if not cadre_sort or facteur_zoom >= zoom_max:
                break
            facteur_zoom *= 1.1

        crop_w = frame_width / facteur_zoom
        crop_h = frame_height / facteur_zoom

        # Calcule l'offset pour tenir compte du centrage dans la fenêtre
        offset_x = max(0, (frame_width - crop_w) / 2)
        offset_y = max(0, (frame_height - crop_h) / 2)

        # Centrage corrigé
        nouveau_pan_x = int(px - (frame_width - offset_x * 2) / (2 * facteur_zoom))
        nouveau_pan_y = int(py - (frame_height - offset_y * 2) / (2 * facteur_zoom))

        # Clamp pour rester dans les limites
        nouveau_pan_x = max(0, min(nouveau_pan_x, w_img - crop_w))
        nouveau_pan_y = max(0, min(nouveau_pan_y, h_img - crop_h))

        set_globals(pan_x_val=nouveau_pan_x, pan_y_val=nouveau_pan_y, zoom_factor_val=facteur_zoom)
        self._refresh_images()


### Analyse d'un scnéario'

    def analyserScenarioDepuisCarte(self, nom_scenario_lisible: str):
        scenario = self.moteurAlgo.getScenarioNomLisible(nom_scenario_lisible)

         # 1. Réinitialise les modules visibles (coche tous)
        self.cocherTousLesModules()

        # 2. Remet le niveau de filtrage à "Tous"
        self.reinitialiserComboFiltrageLevel()

        # 3. Masque tous les autres layers
        self.selectionnerUniquementScenarioActif(nom_scenario_lisible)

        # 4. Applique le scénario dans l’IHM

        self._refresh_images()
        return

### Menu Wikipedia'

    def extraireTagsP31(self):
        """
        Extrait la liste des P31 avec leur catégorie, statut, et les occurrences dans EntreeHistorique.
        """

        requete = """
        SELECT
            p31c.p31,
            p31c.label,
            p31c.categorie,
            p31c.statut,
            COUNT(e.qid) AS total,
            SUM(CASE WHEN e.crossReference = 1 THEN 1 ELSE 0 END) AS nb_cross_ref
        FROM P31Classification p31c
        LEFT JOIN EntreeHistorique e ON e.p31 = p31c.p31
        GROUP BY p31c.p31, p31c.label, p31c.categorie, p31c.statut
        ORDER BY total DESC;
        """

        chemin_export = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Enregistrer l'extraction des TAG P31"
        )

        if not chemin_export:
            return

        try:
            with sqlite3.connect(self.chemin_bd) as conn:
                cursor = conn.cursor()
                cursor.execute(requete)
                lignes = cursor.fetchall()

            with open(chemin_export, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["p31", "label", "categorie", "statut", "nb_total", "nb_crossReference"])
                writer.writerows(lignes)

            messagebox.showinfo("Extraction terminée", f"{len(lignes)} P31 extraits dans :\n{chemin_export}")

        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur est survenue :\n{e}")



    def importerFichierP31(self):
        chemin_fichier = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not chemin_fichier:
            return

        try:
            df = pd.read_csv(chemin_fichier, dtype=str).fillna("")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de lecture du fichier : {e}")
            return

        # Contrôle des colonnes attendues
        colonnes_attendues = {"p31", "label", "statut", "categorie"}
        if not colonnes_attendues.issubset(df.columns):
            messagebox.showerror("Erreur", f"Colonnes attendues manquantes : {colonnes_attendues - set(df.columns)}")
            return

        # Contrôle des valeurs de 'statut'
        valeurs_valides = {"garde", "exclu"}
        statuts_invalides = df.loc[~df["statut"].isin(valeurs_valides), "p31"].tolist()
        if statuts_invalides:
            raise ValueError(f"Valeurs invalides dans la colonne 'statut' pour : {', '.join(statuts_invalides)}")

        conn = sqlite3.connect(self.chemin_bd)
        cursor = conn.cursor()

        try:
            # Étape 1 : on supprime toutes les catégories
            cursor.execute("DELETE FROM P31Categorie")
            categories_crees = set()

            # Étape 2 : on met à jour chaque ligne de P31Classification
            for _, ligne in df.iterrows():
                p31 = ligne["p31"]
                label = ligne["label"]
                statut = ligne["statut"]
                categorie = ligne["categorie"] or None

                # Créer la catégorie si nécessaire
                if categorie and categorie not in categories_crees:
                    cursor.execute("INSERT INTO P31Categorie (nom, visible) VALUES (?, ?)",
                                (categorie, 1 if statut == "garde" else 0))
                    categories_crees.add(categorie)

                # Mise à jour dans P31Classification
                cursor.execute("""
                    UPDATE P31Classification
                    SET label = ?, statut = ?, categorie = ?
                    WHERE p31 = ?
                """, (label, statut, categorie, p31))

            conn.commit()
            messagebox.showinfo("Succès", "Importation des P31 effectuée avec succès.")
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Erreur", f"Erreur lors de l'importation : {e}")
        finally:
            conn.close()

    def afficherFiltrageCategories(self):
        fenetre = tk.Toplevel()
        fenetre.title("Filtrage des catégories")

        # Connexion base
        conn = sqlite3.connect(self.chemin_bd)
        cursor = conn.cursor()

        # Onglets
        notebook = ttk.Notebook(fenetre)
        notebook.pack(fill="both", expand=True)

        # === Onglet 1 : CATEGORIES ===
        tab_categories = ttk.Frame(notebook)
        notebook.add(tab_categories, text="Catégories")

        frame_gauche = tk.Frame(tab_categories, padx=10, pady=10)
        frame_gauche.pack(side="left", fill="both", expand=True)
        frame_droite = tk.Frame(tab_categories, padx=10, pady=10)
        frame_droite.pack(side="right", fill="y")

        cursor.execute("""
            SELECT c.nom, c.visible, COUNT(eh.qid) AS nb_cross
            FROM P31Categorie c
            LEFT JOIN P31Classification pc ON pc.categorie = c.nom
            LEFT JOIN EntreeHistorique eh ON eh.p31 = pc.p31 AND eh.crossReference = 1
            GROUP BY c.nom
            ORDER BY nb_cross DESC
        """)
        categories = cursor.fetchall()

        cursor.execute("""
            SELECT pc.categorie, pc.label, COUNT(eh.qid) AS total
            FROM P31Classification pc
            JOIN EntreeHistorique eh ON pc.p31 = eh.p31
            WHERE pc.categorie IS NOT NULL
            GROUP BY pc.p31, pc.label, pc.categorie
            ORDER BY pc.categorie, total DESC
        """)
        rows = cursor.fetchall()

        p31_labels_par_categorie = {}
        for categorie, label, count in rows:
            if categorie not in p31_labels_par_categorie:
                p31_labels_par_categorie[categorie] = []
            if len(p31_labels_par_categorie[categorie]) < 2:
                p31_labels_par_categorie[categorie].append(label)

        checkbox_vars_categories = {}
        for nom, visible, _ in categories:
            var = tk.BooleanVar(value=bool(int(visible)))
            labels = p31_labels_par_categorie.get(nom, [])
            texte = f"{nom} ({', '.join(labels)}...)" if labels else nom
            chk = tk.Checkbutton(frame_gauche, text=texte, variable=var, anchor="w", justify="left")
            chk.pack(anchor="w")
            checkbox_vars_categories[nom] = var

        # === Onglet 2 : THEMES ===
        tab_themes = ttk.Frame(notebook)
        notebook.add(tab_themes, text="Thème")

        frame_theme = tk.Frame(tab_themes, padx=10, pady=10)
        frame_theme.pack(side="left", fill="both", expand=True)
        checkbox_vars_themes = {}

        cursor.execute("SELECT source_backlink, url, visible FROM SourceBacklink ORDER BY source_backlink")
        lignes = cursor.fetchall()

        color_vars_themes = {}

        for source, url, visible in lignes:
            var = tk.BooleanVar(value=bool(int(visible)))
            checkbox_vars_themes[source] = var

            # Lecture couleur actuelle
            cursor.execute("SELECT couleur FROM SourceBacklink WHERE source_backlink = ?", (source,))
            couleur_bgr = cursor.fetchone()[0] or "(0,0,0)"
            couleur_hex = bgrVersHex(eval(couleur_bgr))
            color_vars_themes[source] = tk.StringVar(value=couleur_hex)

            # Ligne contenant tous les widgets
            ligne = tk.Frame(frame_theme)
            ligne.pack(anchor="w", fill="x", pady=1)

            # CheckBox
            chk = tk.Checkbutton(ligne, variable=var)
            chk.pack(side="left")

            # Lien cliquable
            lien = tk.Label(ligne, text=source, fg="blue", cursor="hand2", underline=1)
            lien.pack(side="left", padx=4)
            lien.bind("<Button-1>", lambda e, u=url: webbrowser.open_new(u))

            # Carré de couleur
            def choisirCouleur(source=source):
                old_color = color_vars_themes[source].get()
                new_color = colorchooser.askcolor(initialcolor=old_color)[1]
                if new_color:
                    color_vars_themes[source].set(new_color)
                    frame_couleur.config(bg=new_color)

            frame_couleur = tk.Canvas(ligne, width=20, height=20, bg=couleur_hex, highlightthickness=1, relief="solid")
            frame_couleur.pack(side="left", padx=10)
            frame_couleur.bind("<Button-1>", lambda e, s=source: choisirCouleur(s))


        # === Onglet 3 : FILTRAGE AVANCÉ ===
        tab_filtrage = ttk.Frame(notebook)
        notebook.add(tab_filtrage, text="Filtrage")

        frame_filtrage = tk.Frame(tab_filtrage, padx=10, pady=10)
        frame_filtrage.pack(fill="both", expand=True)

        ttk.Label(frame_filtrage, text="(Paramètres à venir)").pack(anchor="w", pady=(0, 10))
        ttk.Label(frame_filtrage, text="Distance max (km) :").pack(anchor="w")
        entry_distance = ttk.Entry(frame_filtrage)
        entry_distance.pack(anchor="w")

        # === Actions globales
        def appliquer():
            conn = sqlite3.connect(self.chemin_bd)
            cursor = conn.cursor()

            for nom, var in checkbox_vars_categories.items():
                cursor.execute("UPDATE P31Categorie SET visible = ? WHERE nom = ?", (1 if var.get() else 0, nom))

            for nom in checkbox_vars_themes:
                visible = 1 if checkbox_vars_themes[nom].get() else 0
                couleur_bgr = hexVersBGR(color_vars_themes[nom].get())
                cursor.execute("""
                    UPDATE SourceBacklink SET visible = ?, couleur = ?
                    WHERE source_backlink = ?
                """, (visible, str(couleur_bgr), nom))

            conn.commit()
            conn.close()
            fenetre.destroy()

        def annuler():
            fenetre.destroy()

        frame_boutons = tk.Frame(fenetre, padx=10, pady=10)
        frame_boutons.pack(side="bottom", fill="x")


        tk.Button(frame_boutons, text="Appliquer", command=appliquer).pack(side="right", padx=5)
        tk.Button(frame_boutons, text="Annuler", command=annuler).pack(side="right", padx=5)



### Gestion des fonctions activées depuis le menu
    def quitter_application(self):
        import sys
        self.destroy()
        self.quit()
        sys.exit(0)


    def actionSauvegarderProjet(self):
        nom_module = type(self.moteurAlgo).__name__
        fichier = filedialog.asksaveasfilename(
            initialdir=self.dossiers["projets"],
            defaultextension=".pkl",
            filetypes=[("{nom_module} (*.pkl)", "*.pkl")],
            title="Sauvegarder le projet",
            initialfile=f"projet_{nom_module}.pkl"
        )
        if not fichier:
            return

        try:
            self.sauvegarderEtatComplet(fichier)
            messagebox.showinfo("Sauvegarde réussie", f"Projet sauvegardé dans :\n{fichier}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde :\n{e}")



    def actionChargerProjet(self):
        nom_module = type(self.moteurAlgo).__name__
        fichier = filedialog.askopenfilename(
            initialdir=self.dossiers["projets"],
            filetypes=[("{nom_module} (*.pkl)", "*.pkl")],
            title="Charger un projet",
        )
        if not fichier:
            return

        try:
            self.chargerEtatComplet(fichier)
            messagebox.showinfo("Chargement réussi", f"Projet chargé depuis :\n{fichier}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement :\n{e}")

    def actionNouveauProjet(self, algo_cls):
        """Crée un nouveau projet basé sur la classe d'algorithme donnée."""
        layer = LayerManager()
        moteur = algo_cls(layer)
        self.appliquerEtat(layer, moteur)

    def sauvegarder_carte(self):

        filepath = filedialog.asksaveasfilename(
            initialdir=self.dossiers["images"],
            defaultextension=".png",
            filetypes=[("Images PNG", "*.png")],
            title="Enregistrer la carte annotée"
        )
        if filepath:
            sauvegarder_carte_complete(filepath)
            print(f"✅ Carte sauvegardée sous : {filepath}")
            print(f"✅ Carte sauvegardée sous : {filepath}")


    def gerer_regles_algo(self):
        self.ihm_algo.ouvrir_fenetre_regles()

    def creer_scenarios_automatiques(self):
        self.ihm_algo.ouvrir_fenetre_scenarios()

    def demanderGenerationRapport(self):
        self.ihm_algo.ouvrirBoiteGenerationRapport(self.dossiers["exports"])

if __name__ == "__main__":
    app = InterfaceCarte()
    app.mainloop()
