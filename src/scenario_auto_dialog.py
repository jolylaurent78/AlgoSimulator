"""Boîte de création des scénarios automatiques."""

import colorsys
import tkinter as tk
from itertools import product
from tkinter import ttk


class FenetreProgression(tk.Toplevel):
    def __init__(self, parent, titre="Progression", maximum=100):
        super().__init__(parent)
        self.title(titre)
        self.geometry("300x100")
        self.label = ttk.Label(self, text="Création des scénarios...")
        self.label.pack(pady=10)
        self.barre = ttk.Progressbar(
            self, orient="horizontal", length=250, mode="determinate", maximum=maximum,
        )
        self.barre.pack(pady=5)
        self.update_idletasks()

    def miseAJour(self, valeur):
        self.barre["value"] = valeur
        self.update_idletasks()

    def terminer(self):
        self.destroy()


def open_automatic_scenario_dialog(
    parent,
    moteur_algo,
    layer_manager,
    on_changed=None,
    *,
    parametres_csv,
):
    """Ouvre la boîte de création des scénarios automatiques.

    ``on_changed`` est appelé une fois la création terminée afin que le
    propriétaire de l'IHM puisse rafraîchir ses vues.
    """
    popup = tk.Toplevel(parent)
    popup.title("Gestion des scénarios")
    popup.transient(parent)
    popup.grab_set()

    main_frame = ttk.Frame(popup)
    main_frame.pack(padx=10, pady=10, fill="both", expand=True)

    conteneur_groupes = ttk.Frame(main_frame)
    conteneur_groupes.grid(row=0, column=0, sticky="nsew")
    colonne_boutons = ttk.Frame(main_frame)
    colonne_boutons.grid(row=0, column=1, sticky="ns", padx=(20, 0))

    main_frame.columnconfigure(0, weight=1)
    main_frame.rowconfigure(1, weight=0)
    scenario_vars = {}
    cadres = []
    groupes = {}

    segment = moteur_algo.segment_actif
    scenario_auto_existant = moteur_algo.aDesScenarioAutomatiques(segment)
    parametres_scenario = (
        moteur_algo.getListeParametresScenarioAutomatique(segment)
        if scenario_auto_existant else []
    )

    for ligne in parametres_csv:
        if ligne.get("Type", "").strip() == "input_multiple":
            section = ligne.get("Section", "Autre").strip()
            groupes.setdefault(section, []).append(ligne)

    def mettre_a_jour_compteur():
        total = 1
        for nom, var in scenario_vars.items():
            if var.get():
                module, attribut = nom.split(".")
                total *= len(moteur_algo.getValeursParametre(module, attribut))
        label_nb_scenarios.config(text=f"Nombre de scénarios générés : {total}")

    for col_index, (section, lignes) in enumerate(groupes.items()):
        cadre = ttk.LabelFrame(conteneur_groupes, text=section)
        cadre.grid(row=0, column=col_index, padx=5, pady=5, sticky="n")
        cadre.columnconfigure(0, weight=1)
        cadres.append(cadre)

        for ligne in lignes:
            module = ligne.get("Module", "").strip()
            attribut = ligne.get("Attribut", "").strip()
            cle = f"{module}.{attribut}"
            if cle in moteur_algo.regles_actives:
                continue

            var = tk.BooleanVar(value=(module, attribut) in parametres_scenario)
            var.trace_add("write", lambda *_args: mettre_a_jour_compteur())
            tk.Checkbutton(cadre, text=ligne.get("Label", attribut).strip(), variable=var).pack(anchor="w")
            scenario_vars[cle] = var

    popup.update_idletasks()
    if cadres:
        hauteur_max = max(cadre.winfo_height() for cadre in cadres)
        largeur_max = max(cadre.winfo_width() for cadre in cadres)
        for cadre in cadres:
            cadre.configure(width=largeur_max)
            tk.Frame(cadre, height=max(hauteur_max - cadre.winfo_height(), 0)).pack(fill="x")

    ligne_footer = ttk.Frame(main_frame)
    ligne_footer.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
    ligne_footer.columnconfigure(0, weight=1)
    label_nb_scenarios = tk.Label(ligne_footer, text="Nombre de scénarios générés : 0", anchor="w")
    label_nb_scenarios.grid(row=0, column=0, sticky="w", padx=5)

    def tout_selectionner():
        for var in scenario_vars.values():
            var.set(True)

    def tout_deselectionner():
        for var in scenario_vars.values():
            var.set(False)

    def generer_couleurs_distinctes(nombre):
        couleurs = []
        for index in range(nombre):
            fraction = index / nombre
            if fraction < 0.2:
                teinte = 0.10 * (fraction / 0.2)
            else:
                teinte = 0.40 + 0.60 * ((fraction - 0.2) / 0.8)
            rouge, vert, bleu = colorsys.hls_to_rgb(teinte, 0.5, 0.65)
            couleurs.append((round(bleu * 255), round(vert * 255), round(rouge * 255)))
        return couleurs

    def sauvegarder():
        liste_parametres = []
        for nom, var in scenario_vars.items():
            if not var.get():
                continue
            module, attribut = nom.split(".")
            shortlabel = next(
                (
                    ligne.get("ShortLabel", attribut).strip()
                    for ligne in parametres_csv
                    if ligne.get("Module", "").strip() == module
                    and ligne.get("Attribut", "").strip() == attribut
                ),
                attribut,
            )
            liste_parametres.append(
                (module, attribut, shortlabel, moteur_algo.getValeursParametre(module, attribut)),
            )

        valeurs = [valeurs for _, _, _, valeurs in liste_parametres]
        combinaisons = list(product(*valeurs))
        progression = FenetreProgression(popup, maximum=len(combinaisons) or 1)
        moteur_algo.supprimerTousScenariosAutomatiques(layer_manager, segment=segment)
        couleurs = generer_couleurs_distinctes(len(combinaisons))

        def creer_un_scenario(index):
            if index >= len(combinaisons):
                progression.terminer()
                popup.destroy()
                if on_changed:
                    on_changed()
                return

            quadruplets = [
                (module, attribut, shortlabel, valeur)
                for (module, attribut, shortlabel, _), valeur in zip(liste_parametres, combinaisons[index])
            ]
            moteur_algo.creerScenarioUnitaireAutomatique(
                f"S{index + 1}", quadruplets, moteur_algo.getScenario(), layer_manager, couleurs[index],
            )
            progression.miseAJour(index + 1)
            popup.after(10, lambda: creer_un_scenario(index + 1))

        creer_un_scenario(0)

    ttk.Button(colonne_boutons, text="Tout sélectionner", command=tout_selectionner).pack(fill="x", pady=2)
    ttk.Button(colonne_boutons, text="Tout désélectionner", command=tout_deselectionner).pack(fill="x", pady=2)
    ttk.Button(colonne_boutons, text="Sauvegarder", command=sauvegarder).pack(fill="x", pady=(20, 2))

    popup.update_idletasks()
    popup.geometry(f"{popup.winfo_width() + 160}x{popup.winfo_height()}")
    return popup
