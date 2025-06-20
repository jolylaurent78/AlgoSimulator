import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import os
from functools import partial  # à placer en haut du fichier
import logging
import json

# Base de données des villes
from src.data_loader import villes_dict

# Gestion de l'algo
from src.AlgorithmeManager import AlgorithmeManager, TypeScenario
from src.AlgorithmeStyletInitial import AlgorithmeStyletInitial

from src.layerManager import LayerManager

# Gestion des layers graphiques
log_file = "logs/ihm_parsing.log"

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w', encoding='utf-8'),  # vers fichier
        logging.StreamHandler()  # vers console
    ]
)

class ToolTip:
    def __init__(self, widget, text=''):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None

        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, background="#ffffe0", relief="solid", borderwidth=1, font=("TkDefaultFont", 9))
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

    def update_text(self, text):
        self.text = text

class FenetreProgression(tk.Toplevel):
    def __init__(self, parent, titre="Progression", maximum=100):
        super().__init__(parent)
        self.title(titre)
        self.geometry("300x100")
        self.label = ttk.Label(self, text="Création des scénarios...")
        self.label.pack(pady=10)
        self.barre = ttk.Progressbar(self, orient="horizontal", length=250, mode="determinate", maximum=maximum)
        self.barre.pack(pady=5)
        self.update_idletasks()

    def miseAJour(self, valeur):
        self.barre["value"] = valeur
        self.update_idletasks()

    def terminer(self):
        self.destroy()


class IHMAlgorithme(tk.Frame):
    """
    Classe principale responsable de la génération dynamique de l'IHM
    à partir d'un fichier CSV décrivant les champs, sections, et widgets liés à un modèle algorithmique.
    Elle communique avec un moteur AlgorithmeManager pour synchroniser IHM ↔ données métiers.
    """

    FIELD_PIXEL_WIDTH = 1.2
    UNIT_WIDTH = 30
    LABEL_WIDTH = 90
    COMBO_WIDTH = 145
    CHECKBOX_WIDTH = 115

    def __init__(self, parent, csv_filename, moteurAlgo, layerManager: LayerManager, callbackRefreshLayers=None, callbackRedessinerCarte=None, callbackMiseAJourMenu=None):
        """
        Initialise l'IHM à partir d’un fichier CSV et d’un moteur algorithmique.

        :param parent: la fenêtre Tkinter parente
        :param csv_filename: nom du fichier CSV (dans le même dossier que ce fichier .py)
        :param moteurAlgo: instance de AlgorithmeManager permettant l'accès aux modules métiers
        """
        super().__init__(parent)

        # Une liste de callbacks pour piloter le reste d l'interface '
        self.callbackRefreshLayers = callbackRefreshLayers
        self.callbackRedessinerCarte = callbackRedessinerCarte
        self.callbackMiseAJourMenu = callbackMiseAJourMenu

        self.parent = parent
        self.parametres_csv = []  # lignes extraites du CSV
        self.parametres_widgets = {}  # { id_widget: variable TK associée }
        self.attributsModulesAffichés = []  # tuples (module, attribut, StringVar)
        self.moteurAlgo = moteurAlgo
        self.layerManager = layerManager

        base_path = os.getcwd()  # répertoire courant (là où le shell Python a démarré)
        chemin_complet = os.path.join(base_path, csv_filename)
        self.parametres_csv = self.parser_csv(chemin_complet)


        self.construire_interface_depuis_parametres(self.parametres_csv, affichage=True)
        self.update_idletasks()  # force le layout à jour

        # On affiche la taille de la fenetre finale
        w = self.winfo_width()
        h = self.winfo_height()
        print(f"[DEBUG] Taille réelle de la fenêtre : {w} x {h} px")



    def parser_csv(self, chemin):
        """
            Parse le fichier CSV et vérifie la validité syntaxique des lignes.
            Remplit aussi la liste attributsModulesAffichés pour les champs champ_type="data".

            Paramètres :
                chemin (str) : chemin complet du fichier CSV

            Retour :
                list[dict] : lignes valides issues du fichier
        """
        with open(chemin, newline='', encoding='utf-8') as fichier:
            reader = csv.reader(fichier)
            lignes_valides = []
            header = []

            for num_ligne, ligne in enumerate(reader, start=1):
                if not ligne or ligne[0].strip().startswith('#'):
                    continue

                if not header:
                    header = ligne
                    if 'Categorie' not in header:
                        header.insert(1, 'Categorie')  # Ajout automatique si absent
                    continue

                # Complétion ou troncature de la ligne
                ligne += ["" for _ in range(len(header) - len(ligne))]
                ligne = ligne[:len(header)]

                donnees = dict(zip(header, ligne))
                widget_type = donnees.get('Widget', '').strip().lower()

                # Vérifications syntaxiques minimales
                erreurs = []
                if 'Section' not in donnees:
                    erreurs.append("Champ 'Section' manquant.")
                if not donnees.get('Ligne') or not donnees['Ligne'].isdigit():
                    erreurs.append("Champ 'Ligne' invalide (non entier ou vide).")
                if not widget_type:
                    erreurs.append("Champ 'Widget' manquant.")

                # Vérification module/attribut seulement si nécessaire
                widgets_requérant_module = {"field", "combo", "checkbox"}
                if widget_type in widgets_requérant_module:
                    module = donnees.get('Module', '').strip()
                    attribut = donnees.get('Attribut', '').strip()

                    if not module or not attribut:
                        erreurs.append("Champs 'Module' ou 'Attribut' manquants ou vides.")
                    elif not self.moteurAlgo.estModuleDisponible(module):
                        erreurs.append(f"Module '{module}' non reconnu.")
                    elif not self.moteurAlgo.estAttributDisponible(module, attribut):
                        erreurs.append(f"Attribut '{attribut}' non défini dans le module '{module}'.")
                    else:
                        self.attributsModulesAffichés.append((module, attribut, None, None)) # On garde en mémore la liste des modules/attributs

                if erreurs:
                    logging.warning(f"Ligne {num_ligne} ignorée : {' | '.join(erreurs)} → {ligne}")
                    continue

                lignes_valides.append(donnees)

        logging.info(f"{len(lignes_valides)} lignes valides chargées depuis le CSV.")
        return lignes_valides





    def rafraichir_valeurs_modules(self):
        """
        Met à jour les widgets de type champ_type='data' à partir des valeurs recalculées dans les modules métiers.
        Cette fonction est appelée après chaque modification de paramètre pour refléter les nouvelles données.
        """

        for module, attribut, var, field_type in self.attributsModulesAffichés:
            if var is not None:
                valeur = self.moteurAlgo.getParametre(module, attribut)
                if valeur is not None:
                    if field_type == "angle":
                        valeur = f"{float(valeur):.2f}"
                    elif field_type == "distance":
                        valeur = f"{float(valeur):.1f}"
                    var.set(valeur)  #

        # 🔁 Mise à jour explicite des checkboxes
        for id_objet, var_dict in self.parametres_widgets.items():
            if isinstance(var_dict, dict):
                # Récupération du module et de l’attribut depuis la clé
                try:
                    module, attribut = id_objet.split(".")
                except ValueError:
                    continue  # pas un widget standard

                valeur = self.moteurAlgo.getParametre(module, attribut)
                valeur = [valeur] if valeur is not None else []

                for val, var in var_dict.items():
                    var.set(val in valeur)

        # On met à jour la carto
        if self.callbackRedessinerCarte:
            self.callbackRedessinerCarte()

    def updateModuleEtInterface(self, module: str, attribut: str, valeur):
        """
        Méthode appelée à chaque changement de paramètre dans l’IHM.

            - Applique la valeur au bon module, dans le segment actif
            - Relance le calcul
            - Met à jour dynamiquement l’IHM si besoin
        """

        # 🎯 Application d’un changement standard
        self.moteurAlgo.setParametre(module, attribut, valeur, self.layerManager)
        self.rafraichir_valeurs_modules()



    def ajouter_ligne_widgets(self, frame_ligne, champs, lectureSeuleGlobal=False):
        """
        Ajoute dynamiquement une ligne de widgets dans une section de l'IHM.
        Cette méthode gère les types : text, field, combo, checkbox, spacer.

        :param frame_ligne: conteneur parent de la ligne
        :param champs: liste des champs à placer dans cette ligne (issus du CSV)
            """
        col_idx = 0
        for champ in champs:
            widget_type = champ.get('Widget', '').lower()
            if widget_type == 'spacer':
                spacer = tk.Label(frame_ligne, text="", height=1)
                spacer.grid(row=0, column=col_idx, sticky="ew")
                col_idx += 1
                continue

            label = champ.get('Label', '')
            align = champ.get('Alignement', 'left').lower()
            style = champ.get('Style', 'std')
            hauteur = int(champ.get('Hauteur', '1')) if champ.get('Hauteur', '').isdigit() else 1
            champ_type = champ.get('Type', '').lower()
            field_type = champ.get('FieldType', '').lower()
            font = ('Arial', 9, style if style in ['bold', 'italic'] else 'normal')
            module = champ.get("Module", "dataset")
            attribut = champ.get("Attribut", "")
            id_objet = f"{module}.{attribut}"

            # Forcer lecture seule si une règle est active pour ce champ, sinon on suit l'état lectureSeuleGlobal'

            if hasattr(self.moteurAlgo, "regles_actives"):
                nom_regle_active = self.moteurAlgo.regles_actives.get(f"{module}.{attribut}")
                if nom_regle_active:
                    lecture_seule = True
                    label = f"{label} (auto)"
                else:
                    lecture_seule = lectureSeuleGlobal

            if widget_type == 'text' or champ_type == 'static':
                lbl = tk.Label(frame_ligne, text=label, font=font)
                lbl.grid(row=0, column=col_idx, sticky="w", padx=5)
                col_idx += 1

            elif widget_type == 'field':
                container = ttk.Frame(frame_ligne)
                container.grid(row=0, column=col_idx, sticky="e" if align == "right" else "w", padx=5)
                labelAffichee = label if len(label) == 0 else label + ":" 
                lbl = tk.Label(container, text=labelAffichee, font=font)
                lbl.pack(side="left")
                readonly = champ_type == 'data'
                var = tk.StringVar()
                width = self.get_field_width(field_type)
                entry = tk.Entry(container, textvariable=var, width=width, state='normal', readonlybackground='white')
                entry.config(state='readonly')
                entry.pack(side="left")
                unit_label = self.get_field_unit(field_type)
                if unit_label:
                    tk.Label(container, text=unit_label, font=font).pack(side="left", padx=(2, 0))

                valeur = self.moteurAlgo.getParametre(module, attribut)
                if valeur is not None:
                    if field_type == "angle":
                        try:
                            valeur = f"{float(valeur):.2f}"
                        except ValueError:
                            pass  # on laisse la valeur telle quelle si non convertible
                    if field_type == "distance":
                        try:
                            valeur = f"{float(valeur):.1f}"
                        except ValueError:
                            pass  # on laisse la valeur telle quelle si non convertible

                    var.set(valeur)
                self.parametres_widgets[id_objet] = var

                # on complète la liaison dans attributsModulesAffichés
                if champ_type == 'data':
                    for i, (mod, attr, _, _) in enumerate(self.attributsModulesAffichés):
                        if mod == module and attr == attribut:
                            self.attributsModulesAffichés[i] = (module, attribut, var, field_type)
                            break

                col_idx += 1

            elif widget_type == 'combo':
                container = ttk.Frame(frame_ligne)
                container.grid(row=0, column=col_idx, sticky="e" if align == "right" else "w", padx=5)
                labelAffichee = label if len(label) == 0 else label + ":" 
                tk.Label(container, text=labelAffichee, font=font).pack(side="left")
                var = tk.StringVar()

                # On affiche la valeur par défaut
                valeur = self.moteurAlgo.getParametre(module, attribut)
                if valeur is not None:
                    var.set(valeur)

                # 2. Obtenir les valeurs possibles depuis getValeursXxx()
                liste = self.moteurAlgo.getValeursParametre(module, attribut)
                etat_combo = 'disabled' if lecture_seule else 'readonly'
                combo = ttk.Combobox(container, values=liste, textvariable=var, state='readonly')
                combo.config(width=self.get_field_char_width(field_type))
                combo.pack(side="left")


                # 4. Réaction au changement
                var.trace_add("write", lambda *_, m=module, a=attribut, v=var: self.updateModuleEtInterface(m, a, v.get()))

                self.parametres_widgets[id_objet] = var
                col_idx += 1


            elif widget_type == "pointville":
                container = ttk.Frame(frame_ligne)
                container.grid(row=0, column=col_idx, sticky="w", padx=5)

                # Label
                labelAffichee = label if len(label) == 0 else label + ":" 
                tk.Label(container, text=labelAffichee, font=font).pack(side="left", padx=(0, 5))

                # Valeur actuelle
                valeur_actuelle = self.moteurAlgo.getParametre(module, attribut)
                var_nom_ville = tk.StringVar(value=valeur_actuelle or "")

                # Champ de texte (readonly)
                entry_ville = ttk.Entry(container, textvariable=var_nom_ville, state="readonly", width=20)
                entry_ville.pack(side="left")

                # Bouton ...
                def ouvrir_selection_ville(module_courant=module, attribut_courant=attribut):
                    popup = tk.Toplevel()
                    popup.title("Choisir une ville")
                    popup.transient(container)
                    popup.grab_set()

                    ttk.Label(popup, text="Ville :").pack(padx=10, pady=(10, 2))
                    var_filtre = tk.StringVar(value=var_nom_ville.get())
                    entry = ttk.Entry(popup, textvariable=var_filtre)
                    entry.pack(padx=10, fill="x")

                    listbox = tk.Listbox(popup, height=8)
                    listbox.pack(padx=10, fill="both", expand=True)
                    listbox.configure(exportselection=False)

                    #On recharge la liste des villes
                    villes_dict.recharger()
                    
                    def filtrer():
                        texte = var_filtre.get().lower()
                        listbox.delete(0, tk.END)
                        for ville in sorted(villes_dict.keys()):
                            if texte in ville.lower():
                                listbox.insert(tk.END, ville)

                    def valider(event=None):
                        selection = listbox.get(tk.ACTIVE)
                        var_nom_ville.set(selection)
                        self.updateModuleEtInterface(module_courant, attribut_courant, selection)
                        popup.destroy()

                    entry.bind("<KeyRelease>", lambda e: filtrer())
                    listbox.bind("<Double-1>", valider)

                    filtrer()
                    if valeur_actuelle:
                        for i, nom in enumerate(listbox.get(0, tk.END)):
                            if nom == valeur_actuelle:
                                listbox.selection_set(i)
                                listbox.see(i)
                                break

                bouton = ttk.Button(container, text="...", width=2, command=ouvrir_selection_ville)
                bouton.pack(side="left", padx=(5, 0))

                self.parametres_widgets[id_objet] = var_nom_ville
                col_idx += 1



            elif widget_type in ('checkbox', 'checkboxv', 'checkboxh'):

                def update_single(valeur_choisie, module, attribut, var_dict):
                    for val, var in var_dict.items():
                        var.set(val == valeur_choisie)
                    self.updateModuleEtInterface(module, attribut, valeur_choisie)

                def make_checkbox_cb(valeur_choisie, module, attribut, var_dict):
                    return lambda: update_single(valeur_choisie, module, attribut, var_dict)


                container = ttk.Frame(frame_ligne)
                container.grid(row=0, column=col_idx, sticky="w", padx=5)
                est_horizontal = widget_type == "checkboxh"

                valeurs = self.moteurAlgo.getValeursParametre(module, attribut)
                valeur_actuelle = self.moteurAlgo.getParametre(module, attribut)
                valeur_actuelle = [valeur_actuelle] if valeur_actuelle is not None else []

                var_dict = {}
                if est_horizontal:
                    # ✅ Label + cases sur la même ligne
                    labelAffichee = label if len(label) == 0 else label + ":" 
                    tk.Label(container, text=labelAffichee, font=font).pack(side="left", padx=(0, 5))
                    for val in valeurs:
                        var = tk.BooleanVar()
                        var.set(val in valeur_actuelle)
                        var_dict[val] = var

                        cb = tk.Checkbutton(
                            container,
                            text=val,
                            variable=var,
                            onvalue=True,
                            offvalue=False,
                            command=make_checkbox_cb(val, module, attribut, var_dict)
                        )
                        cb.config(state="disabled" if lecture_seule else "normal")
                        cb.pack(side="left", padx=2)
                else:
                    # ✅ Label sur sa propre ligne + cases en colonne
                    tk.Label(container, text=label + ":", font=font).grid(row=0, column=0, sticky="w")
                    for i, val in enumerate(valeurs):
                        var = tk.BooleanVar()
                        var.set(val in valeur_actuelle)
                        var_dict[val] = var

                        cb = tk.Checkbutton(
                            container,
                            text=val,
                            variable=var,
                            onvalue=True,
                            offvalue=False,
                            command=make_checkbox_cb(val, module, attribut, var_dict)
                        )
                        cb.config(state="disabled" if lecture_seule else "normal")
                        cb.grid(row=i + 1, column=0, sticky="w", pady=1)

                self.parametres_widgets[id_objet] = var_dict
                col_idx += 1


    def construire_interface_depuis_parametres(self, parametres_csv, affichage=False):
        """
        Construit les sections de l'IHM à partir des données CSV triées par section et par ligne.
        Si le mode affichage est activé, ajoute également les filtres de contrôle pour chaque section.

        :param parametres_csv: liste des champs lus depuis le CSV
        :param affichage: booléen pour ajouter les contrôles de visibilité / couleur
        """
        def sauvegarder_algo():

            chemin = filedialog.asksaveasfilename(
                title="Sauvegarder la simulation",
                defaultextension=".pkl",
                filetypes=[("Fichiers pickle", "*.pkl")]
            )
            if chemin:
                self.moteurAlgo.sauvegarder(chemin)






        # On gère les scnéarios
    ### On affiche maintenant chaque ligne de l'IHM'
        donnees_par_section = {}
        for ligne in parametres_csv:
            section = ligne['Section']
            donnees_par_section.setdefault(section, []).append(ligne)

        # Si le scénario est automatique... l'édition est locké'
        lecture_seule = self.moteurAlgo.getScenario().getTypeScenario() == TypeScenario.AUTOMATIQUE


        for section, lignes in donnees_par_section.items():
            frame_section = ttk.LabelFrame(self, text=section)
            frame_section.configure(labelanchor="n")
            style = ttk.Style()
            style.configure("TitreSection.TLabelframe.Label", font=("TkDefaultFont", 8, "bold"), anchor="w")

            nom_section_affiche = section
            if lecture_seule:
                nom_section_affiche += " 🔒"
            frame_section = ttk.LabelFrame(self, text=nom_section_affiche, style="TitreSection.TLabelframe")

            frame_section.grid(sticky="ew", padx=10, pady=4)
            frame_section.columnconfigure(0, weight=1)
            lignes_triees = sorted(lignes, key=lambda l: int(l['Ligne']))
            ligne_widgets = {}
            for ligne in lignes_triees:
                no_ligne = int(ligne['Ligne'])
                ligne_widgets.setdefault(no_ligne, []).append(ligne)

            for no_ligne in sorted(ligne_widgets):
                lignes_contenu = ligne_widgets[no_ligne]
                frame_ligne = ttk.Frame(frame_section)
                frame_ligne.grid(row=no_ligne + 1, column=0, sticky="w", pady=1)
                self.ajouter_ligne_widgets(frame_ligne, lignes_contenu, lectureSeuleGlobal=lecture_seule)



    def reconstruire_interface(self, nomLisibleScenario = None):
        """
        Reconstruit l'IHM à partir de la configuration CSV,
        sans réinitialiser les modules (utilisé après application d'un scénario).
        """

        for widget in self.winfo_children():
            widget.destroy()
        self.attributsModulesAffiches = []
        self.construire_interface_depuis_parametres(self.parametres_csv, affichage=True)

        """
        # On met à jour l'interface des layers'
        if self.callbackRefreshLayers:
            self.callbackRefreshLayers(nomLisibleScenario)

        # On met à jour la carto
        if self.callbackRedessinerCarte:
            self.callbackRedessinerCarte()
        """



    def get_field_width(self, field_type):
        """
            Donne la largeur (en caractères) d’un champ selon son type.

            Paramètres :
                field_type (str) : type de champ

            Retour :
                int : largeur recommandée
            """
        # Largeur en caractères, utilisée pour les widgets (Entry, Combobox)
        return self.get_field_char_width(field_type)

    def get_field_char_width(self, field_type):
        field_type = field_type.lower()
        if field_type == 'shorttext': return 15
        elif field_type == 'longtext': return 40
        elif field_type == 'date': return 10
        elif field_type == 'heure': return 8
        elif field_type == 'angle': return 8
        elif field_type == 'distance': return 8
        elif field_type == 'lettre': return 2
        elif field_type == 'int': return 5
        else: return 20

    def get_field_unit(self, field_type):
        """
            Retourne l'unité associée à un type de champ (si applicable).

            Paramètres :
                field_type (str) : type de champ

            Retour :
                str : symbole de l’unité (ou vide)
            """
        units = {
            'angle': "°",
            'distance': "km",
            'date': "",
            'heure': "",
            'shorttext': "",
            'longtext': "",
            'lettre': "",
            'int': ""
        }
        return units.get(field_type.lower(), "")

    def get_align(self, align):
        """
            Retourne l'alignement de champ interprété pour Tkinter.

            Paramètres :
                align (str) : chaîne 'left', 'right' ou autre

            Retour :
                str : valeur compatible avec Tkinter
            """
        if align == 'left': return "left"
        elif align == 'right': return "right"
        else: return "top"

#
#
### Menu Algorithme

    def ouvrir_fenetre_regles(self):
        popup = tk.Toplevel(self)
        popup.title("Règles métier")
        popup.transient(self)
        popup.grab_set()

        main_frame = ttk.Frame(popup)
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)

        conteneur_regles = ttk.LabelFrame(
            main_frame,
            text="Règles métier",
            relief="groove",
            borderwidth=2
        )
        conteneur_regles.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 5))

        colonne_boutons = ttk.Frame(main_frame)
        colonne_boutons.grid(row=0, column=1, sticky="ns", padx=(20, 0))

        main_frame.columnconfigure(0, weight=1)

        self.regle_vars = {}  # ex : {"planete.sensZeta": tk.BooleanVar()}

        ligne = 0
        scenario = None
        params_scenario = set()

        if self.moteurAlgo.aDesScenarioAutomatiques():
            params_scenario = set(self.moteurAlgo.getListeParametresScenarioAutomatique())

        for module_id, attribut, nom, _ in self.moteurAlgo.getListeRegles():
            cle = f"{module_id}.{attribut}"
            verrouille = (module_id, attribut) in params_scenario

            var = tk.BooleanVar(value=self.moteurAlgo.regles_actives.get(cle) == nom)
            texte = f"{nom} ({cle})"
            if verrouille:
                texte += " [verrouillé par scénario]"

            cb = tk.Checkbutton(conteneur_regles, text=texte, variable=var, state="disabled" if verrouille else "normal")
            cb.grid(row=ligne, column=0, sticky="w")
            self.regle_vars[cle] = (var, nom)
            ligne += 1


        # 🔘 Boutons à droite
        def tout_selectionner():
            for var, _ in self.regle_vars.values():
                var.set(True)

        def tout_deselectionner():
            for var, _ in self.regle_vars.values():
                var.set(False)

        def sauvegarder():
            self.moteurAlgo.regles_actives.clear()
            for cle, (var, nom) in self.regle_vars.items():
                if var.get():
                    self.moteurAlgo.regles_actives[cle] = nom
            popup.destroy()
            self.reconstruire_interface()

        def annuler():
            popup.destroy()

        ttk.Button(colonne_boutons, text="Tout sélectionner", command=tout_selectionner).pack(fill="x", pady=2)
        ttk.Button(colonne_boutons, text="Tout désélectionner", command=tout_deselectionner).pack(fill="x", pady=2)
        ttk.Button(colonne_boutons, text="Sauvegarder", command=sauvegarder).pack(fill="x", pady=(20, 2))
        ttk.Button(colonne_boutons, text="Annuler", command=annuler).pack(fill="x", pady=2)


    def ouvrir_fenetre_scenarios(self):
        popup = tk.Toplevel(self)
        popup.title("Gestion des scénarios")
        popup.transient(self)
        popup.grab_set()

        main_frame = ttk.Frame(popup)
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)

        conteneur_groupes = ttk.Frame(main_frame)
        conteneur_groupes.grid(row=0, column=0, sticky="nsew")

        colonne_boutons = ttk.Frame(main_frame)
        colonne_boutons.grid(row=0, column=1, sticky="ns", padx=(20, 0))

        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=0)
        self.scenario_vars = {}
        cadres = []
        groupes = {}

        # On récupère le scénario en cours
        segment = self.moteurAlgo.segment_actif

        scenarioAutoExistant = self.moteurAlgo.aDesScenarioAutomatiques(segment)
        if scenarioAutoExistant:
            parametresScenario = self.moteurAlgo.getListeParametresScenarioAutomatique(segment)

        for ligne in self.parametres_csv:
            if ligne.get("Type", "").strip() == "input_multiple":
                section = ligne.get("Section", "Autre").strip()
                groupes.setdefault(section, []).append(ligne)

        for col_index, (section, lignes) in enumerate(groupes.items()):
            cadre = ttk.LabelFrame(conteneur_groupes, text=section)
            cadre.grid(row=0, column=col_index, padx=5, pady=5, sticky="n")
            cadre.columnconfigure(0, weight=1)
            cadres.append(cadre)

            for ligne in lignes:
                module = ligne.get("Module", "").strip()
                attribut = ligne.get("Attribut", "").strip()
                cle = f"{module}.{attribut}"
                if cle in self.moteurAlgo.regles_actives:
                    continue  # Ignoré car géré par une règle
                nom_affiche = f"{module}.{attribut}"
                label = ligne.get("Label", attribut).strip()

                var = tk.BooleanVar(value=False)
                if scenarioAutoExistant and (module, attribut) in parametresScenario:
                    var.set(True)

                # 🔁 Attacher le trigger dynamique
                var.trace_add("write", lambda *args: mettre_a_jour_compteur())

                cb = tk.Checkbutton(cadre, text=label, variable=var)
                cb.pack(anchor="w")
                self.scenario_vars[nom_affiche] = var

        # Espacements verticaux harmonisés
        popup.update_idletasks()
        hauteur_max = max(cadre.winfo_height() for cadre in cadres)
        largeur_max = max(cadre.winfo_width() for cadre in cadres)
        for cadre in cadres:
            cadre.configure(width=largeur_max)
            manque = max(hauteur_max - cadre.winfo_height(), 0)
            spacer = tk.Frame(cadre, height=manque)
            spacer.pack(fill="x")

        # Label de scénario en bas
        ligne_footer = ttk.Frame(main_frame)
        ligne_footer.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ligne_footer.columnconfigure(0, weight=1)

        self.label_nb_scenarios = tk.Label(ligne_footer, text="Nombre de scénarios générés : 0", anchor="w")
        self.label_nb_scenarios.grid(row=0, column=0, sticky="w", padx=5)

        # Fonctions liées aux boutons
        def tout_selectionner():
            for var in self.scenario_vars.values():
                var.set(True)

        def tout_deselectionner():
            for var in self.scenario_vars.values():
                var.set(False)

        def sauvegarder():
            liste_parametres = []

            for nom, var in self.scenario_vars.items():
                if var.get():  # case cochée
                    module, attribut = nom.split(".")

                    # Récupération du shortlabel
                    shortlabel = attribut  # fallback
                    for ligne in self.parametres_csv:
                        if (
                            ligne.get("Module", "").strip() == module and
                            ligne.get("Attribut", "").strip() == attribut
                        ):
                            shortlabel = ligne.get("ShortLabel", attribut).strip()
                            break

                    # Récupération de toutes les valeurs possibles
                    valeurs = self.moteurAlgo.getValeursParametre(module, attribut)

                    liste_parametres.append((module, attribut, shortlabel, valeurs))

            # Créer les scénarios pour le segment actif
            segment = self.moteurAlgo.segment_actif

            # On crée la progress bar
            nb_total = 1
            for _, _, _, valeurs in liste_parametres:
                nb_total *= len(valeurs)
            progress = FenetreProgression(self, maximum=nb_total)
            genererScenariosProgressivement(liste_parametres, segment, progress, popup)


        def genererScenariosProgressivement(liste_parametres, segment, fenetre_progression, popup):

            import colorsys
            def genererCouleursDistinctes(n: int) -> list[tuple[int, int, int]]:
                """
                Génère n couleurs bien réparties, lisibles sur fond cartographique,
                en format BGR (OpenCV).
                """
                if n <= 0:
                    return []

                couleurs = []
                plages_hue = [(0.0, 0.10), (0.40, 1.0)]  # exclut les verts/jaunes

                # Étend l’échelle réduite à n points
                for i in range(n):
                    # Réparti dans la double plage (en concaténant linéairement)
                    frac = i / n
                    if frac < 0.2:  # 20% dans [0.0 – 0.10]
                        h = 0.0 + (0.10 - 0.0) * (frac / 0.2)
                    else:  # 80% dans [0.40 – 1.0]
                        h = 0.40 + (1.0 - 0.40) * ((frac - 0.2) / 0.8)

                    s = 0.65
                    l = 0.5
                    r, g, b = colorsys.hls_to_rgb(h, l, s)
                    couleurs.append((round(b * 255), round(g * 255), round(r * 255)))  # BGR

                return couleurs

            from itertools import product

            self.moteurAlgo.supprimerTousScenariosAutomatiques(self.layerManager)

            champs = [(m, a) for (m, a, _, _) in liste_parametres]
            valeurs = [v for (_, _, _, v) in liste_parametres]
            combinaisons = list(product(*valeurs))
            couleurs = genererCouleursDistinctes(len(combinaisons))

            quadruplets = [
                (m, a, s, None)  # on injectera la valeur dans la boucle
                for (m, a, s, _) in liste_parametres
            ]



            def creer_un_scenario(i):
                if i >= len(combinaisons):
                    fenetre_progression.terminer()
                    # On met à jour l'interface des layers'
                    self.callbackRefreshLayers()
                    popup.destroy()
                    return

                combinaison = combinaisons[i]
                nom = f"S{i+1}"
                couleur = couleurs[i]

                q = [(m, a, s, v) for (m, a, s, _), v in zip(liste_parametres, combinaison)]

                base_scenario = self.moteurAlgo.getScenario()
                self.moteurAlgo.creerScenarioUnitaireAutomatique(nom, q, base_scenario, self.layerManager, couleur)

                fenetre_progression.miseAJour(i + 1)
                self.after(10, lambda: creer_un_scenario(i + 1))

            creer_un_scenario(0)

        def supprimer_scenarios(popup):

            if not messagebox.askyesno("Confirmation", "Supprimer tous les scénarios automatiques pour ce segment ?"):
                    return


            # Suppression côté moteur
            self.moteurAlgo.supprimerTousScenariosAutomatiques(self.layerManager)


            # On met à jour l'interface des layers'
            self.callbackRefreshLayers()

            # Fermer la popup
            popup.destroy()

        def annuler():
            popup.destroy()

        def mettre_a_jour_compteur():
            total = 1
            for nom, var in self.scenario_vars.items():
                if var.get():
                    module, attribut = nom.split(".")
                    try:
                        valeurs = self.moteurAlgo.getValeursParametre(module, attribut)
                        total *= len(valeurs)
                    except Exception:
                        total *= 1  # fallback
            self.label_nb_scenarios.config(text=f"Nombre de scénarios générés : {total}")


        # Ajout des boutons
        ttk.Button(colonne_boutons, text="Tout sélectionner", command=tout_selectionner).pack(fill="x", pady=2)
        ttk.Button(colonne_boutons, text="Tout désélectionner", command=tout_deselectionner).pack(fill="x", pady=2)
        ttk.Button(colonne_boutons, text="Sauvegarder", command=sauvegarder).pack(fill="x", pady=(20, 2))

        segment = self.moteurAlgo.segment_actif
        liste_scenarios = self.moteurAlgo.getListeScenarios(segment)

        if self.moteurAlgo.aDesScenarioAutomatiques(segment):
            ttk.Button(colonne_boutons, text="Supprimer", command=lambda: supprimer_scenarios(popup)).pack(fill="x", pady=(2, 10))

        # Ajustement dynamique largeur fenêtre
        popup.update_idletasks()
        popup_width = popup.winfo_width()
        popup_height = popup.winfo_height()
        largeur_boutons = 120
        marge_interne = 40
        popup.geometry(f"{popup_width + largeur_boutons + marge_interne}x{popup_height}")



    def ouvrirBoiteGenerationRapport(self, dossierExport : str):

        def getParametresEtendus() -> list[dict]:
            """
            Retourne la liste des paramètres enrichie (incluant le module Résultat si disponible),
            avec suppression des doublons sur (Module, Attribut).
            """
            cles_vues = set()
            parametres_filtres = []

            # Étape 1 — Parcours du CSV original
            for p in self.parametres_csv:
                module = p["Module"].strip()
                attribut = p["Attribut"].strip()
                cle = (module, attribut)

                if cle in cles_vues:
                    continue
                cles_vues.add(cle)
                parametres_filtres.append(p)

            return parametres_filtres


        # -- On esaye de charger une précédente sauvegarde
        nom_algo = self.moteurAlgo.__class__.__name__
        nom_fichier = os.path.join(dossierExport, f".rapport_colonnes_{nom_algo}.json")

        colonnes_sauvegardees = set()
        taille_fenetre = [600, 500]
        if os.path.exists(nom_fichier):
            try:
                with open(nom_fichier, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    colonnes_sauvegardees = set(tuple(c) for c in config.get("colonnes", []))
                    taille_fenetre = config.get("taille_fenetre", [600, 500])
            except Exception as e:
                print(f"[WARN] Impossible de charger les colonnes sauvegardées : {e}")



        fenetre = tk.Toplevel()
        fenetre.title("Génération de rapport")
        fenetre.geometry(f"{taille_fenetre[0]}x{taille_fenetre[1]}")
        fenetre.transient(self)
        fenetre.grab_set()
        fenetre.columnconfigure(0, weight=1)
        fenetre.rowconfigure(0, weight=1)

        self.variables_rapport = {}

        # === Regrouper les attributs par module ===
        modules = {}
        cle_vues = set()

        # On construit les paramètres du rapport
        self.parametres_rapport_etendus = getParametresEtendus()
        for param in self.parametres_rapport_etendus:
            module = param["Module"]
            attribut = param["Attribut"]
            nom = param["Label"]
            format_ = param.get("FieldType", "texte")

            modules.setdefault(module, []).append((attribut, nom, format_))


        # === Scrollable Frame ===
        canvas = tk.Canvas(fenetre)
        scrollbar = ttk.Scrollbar(fenetre, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas)

        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        canvas.create_window((0, 0), window=frame, anchor="nw", tags="fenetre_scrollable")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig("fenetre_scrollable", width=e.width))
        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # === Ligne 0 : conteneur des modules + boutons verticaux ===
        frame_modules = ttk.Frame(frame)
        frame_modules.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        frame_modules.columnconfigure(0, weight=1)
        frame_modules.columnconfigure(1, weight=0)

        conteneur_groupes = ttk.Frame(frame_modules)
        conteneur_groupes.grid(row=0, column=0, sticky="nsew")

        cadre_boutons_selection = ttk.Frame(frame_modules)
        cadre_boutons_selection.grid(row=0, column=1, sticky="n", padx=10)

        def tout_selectionner():
            for var in self.variables_rapport.values():
                var.set(True)

        def tout_deselectionner():
            for var in self.variables_rapport.values():
                var.set(False)

        def sauvegarderConfig():
            # On sauvegarde les infos de la fenetres et les cases à cocher
            largeur = fenetre.winfo_width()
            hauteur = fenetre.winfo_height()

            colonnes_cochees = [
                [m, a]
                for (m, a), var in self.variables_rapport.items()
                if var.get()
            ]

            scope_selectionne = self.var_scope.get()

            config = {
                "colonnes": colonnes_cochees,
                "taille_fenetre": [largeur, hauteur],
                "scope": scope_selectionne
            }

            with open(nom_fichier, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)


        def genererRapport():
            sauvegarderConfig()
            scope = self.var_scope.get()  # "tous" ou "solutions"

            colonnes = [col["key"] for col in self.colonnes_actives]
            self.apercu_tableau["columns"] = colonnes

            for col in self.colonnes_actives:
                key = col["key"]
                label = col["label"]
                self.apercu_tableau.heading(key, text=label, anchor="center")
                self.apercu_tableau.column(key, width=100, minwidth=60, stretch=True, anchor="center")

            self.apercu_tableau.delete(*self.apercu_tableau.get_children())

            # Parcours de tous les segments
            segments = self.moteurAlgo.getListeSegments()

            for segment in segments:
                scenarios_dict = self.moteurAlgo.getScenariosDict(segment, TypeScenario.UTILISATEUR)

                for scenario in scenarios_dict.values():
                    if scope == "solutions" and not scenario.getSolution():
                        continue

                    ligne = []

                    for col in self.colonnes_actives:
                        module = col["module"]
                        attribut = col["attribut"]
                        format_ = col["format"]

                        valeur = self.moteurAlgo.getParametre(module, attribut, nomScenario=scenario.nom, segment=segment)

                        if valeur is None:
                            texte = "—"
                        else:
                            unite = self.get_field_unit(format_)
                            try:
                                if isinstance(valeur, float):
                                    texte = f"{valeur:.2f}{unite}"
                                else:
                                    texte = f"{valeur}{unite}"
                            except:
                                texte = str(valeur)

                        ligne.append(texte)
                    self.apercu_tableau.insert("", "end", values=ligne)




        def copierApercuDansPressePapier():
            lignes = []

            colonnes = [col["label"] for col in self.colonnes_actives]
            lignes.append("\t".join(colonnes))

            for item_id in self.apercu_tableau.get_children():
                valeurs = self.apercu_tableau.item(item_id)["values"]
                lignes.append("\t".join(str(v) for v in valeurs))

            texte = "\n".join(lignes)

            self.clipboard_clear()
            self.clipboard_append(texte)
            self.update()


        ttk.Button(cadre_boutons_selection, text="Tout sélectionner", command=tout_selectionner).pack(pady=5, fill="x")
        ttk.Button(cadre_boutons_selection, text="Tout désélectionner", command=tout_deselectionner).pack(pady=5, fill="x")

        # === Scope Frame ===
        frame_scope = ttk.LabelFrame(cadre_boutons_selection, text="Scope")
        frame_scope.pack(pady=5, fill="x")

        self.var_scope = tk.StringVar(value="tous")  # Valeur par défaut

        ttk.Radiobutton(frame_scope, text="Tous les scénarios", value="tous", variable=self.var_scope).pack(anchor="w", padx=5, pady=2)
        ttk.Radiobutton(frame_scope, text="Seulement les solutions", value="solutions", variable=self.var_scope).pack(anchor="w", padx=5, pady=2)

        ttk.Button(cadre_boutons_selection, text="Générer", command=genererRapport).pack(pady=5, fill="x")
        ttk.Button(cadre_boutons_selection, text="Copier Presse-Papier", command=copierApercuDansPressePapier).pack(pady=5, fill="x")

        self.colonnes_actives = []
        self.colonnes_rapport_definies = modules


        def renderTableauApercu():
            colonnes = [col["key"] for col in self.colonnes_actives]
            self.apercu_tableau["columns"] = colonnes

            for col in self.colonnes_actives:
                key = col["key"]
                texte_entete = col["label"]  # Simple : une seule ligne
                self.apercu_tableau.heading(key, text=texte_entete, anchor="center")
                self.apercu_tableau.column(key, width=100, minwidth=60, stretch=True, anchor="center")

            self.apercu_tableau.delete(*self.apercu_tableau.get_children())

            if colonnes:
                ligne = []

                for col in self.colonnes_actives:
                    module = col["module"]
                    attribut = col["attribut"]
                    valeur = self.moteurAlgo.getParametre(module, attribut)

                    if valeur is None:
                        texte = "—"
                    else:
                        unite = self.get_field_unit(col["format"])
                        try:
                            if isinstance(valeur, float):
                                texte = f"{valeur:.2f}{unite}"
                            else:
                                texte = f"{valeur}{unite}"
                        except:
                            texte = str(valeur)

                    ligne.append(texte)

                self.apercu_tableau.insert("", "end", values=ligne)

        def mettreAJourColonnesActives(module, attribut, label, format_, est_coche):
            # Reconstruire colonnes_actives selon l’ordre du fichier CSV
            self.colonnes_actives = []

            for param in self.parametres_rapport_etendus:
                m = param["Module"].strip()
                a = param["Attribut"].strip()
                l = param["Label"]
                f = param.get("FieldType", "texte")

                if self.variables_rapport.get((m, a)) and self.variables_rapport[(m, a)].get():

                    self.colonnes_actives.append({
                        "module": m,
                        "attribut": a,
                        "label": l,
                        "format": f,
                        "key": f"{m}.{a}"
                    })
            renderTableauApercu()




        cadres = []
        for col_index, (module, attributs) in enumerate(modules.items()):
            titre_module = module.capitalize()
            cadre = ttk.LabelFrame(conteneur_groupes, text=titre_module)
            cadre.grid(row=0, column=col_index, padx=5, pady=5, sticky="n")
            cadre.columnconfigure(0, weight=1)
            cadres.append(cadre)

            for attribut, nom, format_ in attributs:
                etat_initial = (module, attribut) in colonnes_sauvegardees
                var = tk.BooleanVar(value=etat_initial)

                def make_callback(module, attribut, label, format_, var=var):
                    def callback(*args):
                        mettreAJourColonnesActives(module, attribut, label, format_, var.get())
                    return callback

                var.trace_add("write", make_callback(module, attribut, nom, format_))
                chk = tk.Checkbutton(cadre, text=nom, variable=var)
                chk.pack(anchor="w")
                self.variables_rapport[(module, attribut)] = var

            # Forcer initialisation des colonnes cochées selon état actuel des variables
            self.colonnes_actives = []



        # Espacement harmonisé
        fenetre.update_idletasks()
        hauteur_max = max(c.winfo_height() for c in cadres)
        largeur_max = max(c.winfo_width() for c in cadres)
        for c in cadres:
            c.configure(width=largeur_max)
            manque = max(hauteur_max - c.winfo_height(), 0)
            spacer = tk.Frame(c, height=manque)
            spacer.pack(fill="x")



        # === Aperçu du tableau ===
        frame_apercu = ttk.LabelFrame(frame, text="Aperçu du tableau")
        frame_apercu.grid(row=1, column=0, sticky="nsew", padx=5, pady=(10, 5))

        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        frame_apercu.rowconfigure(0, weight=1)
        frame_apercu.columnconfigure(0, weight=1)

        self.apercu_tableau = ttk.Treeview(frame_apercu, columns=[], show="headings")
        self.apercu_tableau.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(frame_apercu, orient="horizontal", command=self.apercu_tableau.xview)
        self.apercu_tableau.configure(xscrollcommand=scrollbar.set)
        scrollbar.grid(row=1, column=0, sticky="ew")

        # On initialise la tableau avec les valeurs précédentes
        for param in self.parametres_rapport_etendus:
            m = param["Module"]
            a = param["Attribut"]
            l = param["Label"]
            f = param.get("FieldType", "texte")
            if self.variables_rapport.get((m, a)) and self.variables_rapport[(m, a)].get():
                self.colonnes_actives.append({
                    "module": m,
                    "attribut": a,
                    "label": l,
                    "format": f,
                    "key": f"{m}.{a}"
                })

        renderTableauApercu()




if __name__ == "__main__":
    root = tk.Tk()
    root.title("Test IHM Algorithme Dynamique")
    layerManager = LayerManager()
    # 1. Demander un fichier de sauvegarde
    chemin = filedialog.askopenfilename(
        title="Charger une sauvegarde existante ?",
        filetypes=[("Sauvegardes pickle", "*.pkl")],
    )

    # 2. Si un fichier est sélectionné → on le charge
    if chemin and os.path.exists(chemin):
        moteurAlgo = AlgorithmeManager.charger(chemin)
        if moteurAlgo is None:
            messagebox.showerror("Erreur", "Impossible de charger la sauvegarde.")
            exit(1)
    else:
        # 3. Sinon → charger depuis un CSV comme avant
        moteurAlgo = AlgorithmeStyletInitial(layerManager)

    app = IHMAlgorithme(root, "exemple_test_ihm.csv", moteurAlgo)
    app.grid(sticky="nsew")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    app.grid(row=0, column=0, sticky="nsew")
    root.mainloop()