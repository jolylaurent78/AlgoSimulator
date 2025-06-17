from typing import Any
import copy
from enum import Enum

# Affichage des objects graphiques
from src.affichage_objets import ObjetGraphique

# Gestion des layers graphiques
from src.layerManager import LayerManager, Layer

#
#
### Gestion des modules

class ModuleAlgo:
    """
    Classe de base pour tous les modules algorithmiques utilisés dans le système.
    Chaque module représente une entité logique indépendante (ex: Planete, Etoile, Carte, etc.)
    pouvant être paramétrée, calculée, et liée à d'autres modules.

    Tous les modules doivent dériver de cette classe et redéfinir au minimum :
        - getEntreesModules() : pour déclarer leurs dépendances.
        - calculer() : logique de calcul principale.

    Les attributs utilisés dans les dépendances doivent exister sous forme de variables
    d’instance, injectées automatiquement via AlgorithmeManager.
    """

    def __init__(self):
        pass


    def dupliquer(self):
        return copy.deepcopy(self)


    def setup(self):
        """
        Méthode à redéfinir dans chaque module métier.
        Permet d'initialiser les données à la création de l'objet.
        Les valeurs injectées depuis d'autres modules.sont disponibes à ce moment contrairement au constructeur
        """
        pass

    def getEntreesModules(self) -> list[str]:
        """
        Méthode à redéfinir dans chaque module métier.
        Retourne la liste des dépendances externes de ce module
        sous forme de chaînes "module.attribut".
        """
        return []

    def aAttribut(self, nom: str) -> bool:
        """
        Vérifie si un attribut nommé existe dans le module.
        Utilisé pour la validation des dépendances.
        """
        return hasattr(self, nom)

    def setParametre(self, nom, valeur):
        """
        Affecte une valeur à un attribut existant du module.
        Lève une erreur si l’attribut n’est pas défini, afin d’éviter les fautes de frappe.
        """
        if hasattr(self, nom):
            setattr(self, nom, valeur)
        else:
            raise AttributeError(f"[setParametre] Attribut '{nom}' non défini dans {self.__class__.__name__}")

    def getParametre(self, nom):
        """
        Retourne la valeur d’un attribut si celui-ci existe, sinon None.
        """
        return getattr(self, nom, None)

    def getValeursParametre(self, nom: str) -> list:
        """
        Retourne la liste des valeurs possibles pour un attribut donné,
        en appelant dynamiquement la méthode `getValeursXxx()` si elle existe.
        """
        nom_methode = f"getValeurs{nom[0].upper()}{nom[1:]}"
        return getattr(self, nom_methode, lambda: [])()


    def calculer(self):
        """
        Méthode à redéfinir dans chaque module métier.
        Effectue le calcul principal du module à partir de ses propres paramètres
        et des valeurs injectées depuis d'autres modules.
        """
        pass

    def construireRepresentationCarte(self) -> list[ObjetGraphique]:
        return []  # par défaut, rien à afficher

    def getEtat(self):
        etat = self.__dict__.copy()
        etat.pop('dataset', None)
        return etat

    @classmethod
    def creerDepuisEtat(cls, etat, dataset):
        instance = cls(dataset)
        for k, v in etat.items():
            setattr(instance, k, v)
        instance.calculer()
        return instance


    def getRegles(self):
        """
        Retourne la liste des règles automatiques applicables à ce module.
        Chaque règle est une liste [nom, attribut ciblé, méthode].
        Par défaut : aucune règle.
        """
        return []


#
#
### Gestion des scénarios

class TypeScenario(Enum):
    AUTOMATIQUE = "automatique"
    UTILISATEUR = "utilisateur"
    DEFAULT = "default"

class Scenario:
    def __init__(self, nom: str,
        quadruplets: list[tuple[str, str, str, Any]],
        modules: dict,
        ordreModules : list[str],
        segment: str,
        layerManager: LayerManager,
        couleur: tuple = None,
        type_scenario: TypeScenario = TypeScenario.AUTOMATIQUE):
        """
        Initialise un scénario.

        - nom : identifiant du scénario
        - quadruplets : liste de quadruplets (module, attribut, shortlabel, valeur)
        - modules : dictionnaire des modules associés
        - segment : clé du segment lié
        """
        self.nom = nom
        self.parametres = quadruplets
        self.parametres_dict = {
            f"{module}.{attribut}": valeur
            for module, attribut, _, valeur in quadruplets
        }
        self.modules = modules
        self.segment = segment
        self.type_scenario = type_scenario
        self.ordreModules = ordreModules

        # On crée un layer dans l'interface'
        nomLayer = self.getDescriptionLisible()
        layer = layerManager.creerLayer(nomLayer, segment=self.segment)
        if couleur is not None:
            layer.setCouleur(couleur)

        # On initialise la solutoin None pour les algos de type PointGraphique
        self.solutionScenario = False

    def getSolution(self):
        return self.solutionScenario

    def setSolution(self, solution):
        self.solutionScenario =  solution

    def getTypeScenario(self):
        return self.type_scenario

    def getListeParametres(self):
        """
        Retourne la liste des (module, attribut) définis dans le scénario.
        """
        return [(m, a) for (m, a, _, _) in self.parametres]


    def getDescriptionLisible(self) -> str:
        if self.type_scenario == TypeScenario.DEFAULT:
            return self.nom
        elif self.type_scenario == TypeScenario.UTILISATEUR:
            return self.nom
        elif self.type_scenario == TypeScenario.AUTOMATIQUE:
            if not self.parametres:
                return "Automatique"
            return ", ".join(f"{short} = {val}" for _, _, short, val in self.parametres)
        else:
            return self.nom  # fallback


    def getParametre(self, module: str, attribut: str):
        return self.parametres_dict.get(f"{module}.{attribut}")

    def setParametre(self, module: str, attribut: str, valeur):
        cle = f"{module}.{attribut}"
        self.parametres_dict[cle] = valeur

        # Mise à jour du quadruplet correspondant dans la liste
        for i, (m, a, short, _) in enumerate(self.parametres):
            if m == module and a == attribut:
                self.parametres[i] = (m, a, short, valeur)
                break
        else:
            # Si le paramètre n’existait pas encore, on ajoute un nouveau quadruplet
            self.parametres.append((module, attribut, attribut, valeur))  # fallback: shortlabel = attribut

    def construireRepresentationCarte(self, layer:Layer):


        if not layer:
            raise RuntimeError(f"Layer '{nomLayer}' introuvable pour le segment '{self.segment}'")

        # 1. Supprimer les anciens objets et générer les tooltips
        layer.supprimerTousObjets()
        tooltip_scenario = self.genererTooltipScenario()

        # 2. Générer et ajouter les nouveaux
        for module_id in self.ordreModules:
            module = self.modules.get(module_id)
            objets = module.construireRepresentationCarte()
            if objets != []:
                # On inclut automatiquement le tag du modue
                for obj in objets:
                    if isinstance(obj, ObjetGraphique):
                        obj.ajouterTag("module", module_id)
                        obj.tooltips_scenario = tooltip_scenario
                layer.inclureObjetDansLayer(objets)


    def getSolutionAlgorithme(self, module_id: str, nom_methode: str):
        """
        Appelle une méthode spécifique d’un module pour obtenir un PointGraphique.
        """
        module = self.modules.get(module_id)
        if not module:
            return None

        methode = getattr(module, nom_methode, None)
        if not callable(methode):
            return None

        return methode()


    def genererTooltipScenario(self) -> list[str]:
        """
        Construit une liste de lignes textuelles représentant les paramètres
        du scénario sous la forme : AttributModule = valeur
        """
        lignes = []

        if self.parametres != []:
            lignes.append("Paramètres du scénario:")
        for module, attribut, short, valeur in self.parametres:
            module_label = module.capitalize()
            attribut_label = attribut.capitalize()
            label = f"{attribut_label}{module_label}"
            lignes.append(f"- {label} = {valeur}")
        return lignes


class AlgorithmeManager:
    """
    Classe centrale responsable de la gestion des modules algorithmiques.
    - Enregistre et instancie tous les modules.
    - Construit un graphe de dépendances basé sur les déclarations de getEntreesModules().
    - Trie les modules topologiquement pour calculer dans l'ordre correct.
    - Injecte automatiquement les variables externes requises dans chaque module.
    - Assure le recalcul global ou ciblé suite à une modification de paramètre.
    """

    def __init__(self, layerManager: LayerManager):
        self._templates_modules  = {}
        self._scenarios = {}
        self.scenario_actif = "default"

        # On lance le setup et le calcul pour le dataset et on défini la première date comme date active
        self.dataset.setup()
        self.dataset.calculer()
        self.segment_actif = self.dataset.segment


        # Enregistrement des modèles de modules
        self.enregistrerTemplatesModules(self.getListeModulesInitiale())

        # Graphe de dépendances (nécessite les modules enregistrés) et Vérification de la structure déclarée pour les Template
        self.graphDependanceModules = self.construireGrapheDependances()
        self.ordreModules = self.getOrdreCalculModules()
        self.validerStructureGlobale()

        # Activation des règles par défaut
        self.regles_actives = {}
        for module_id, attribut, nom, _ in self.getListeRegles():
            cle = f"{module_id}.{attribut}"
            self.regles_actives[cle] = nom


        # Créer un scénario "default" avec les modules globaux
        self.creerScenarioDefault(layerManager)



#
#
## Methodes virtuelles à redéfinir dans le module métier
    def getListeSegments(self) -> list[str]:
        """
        Retourne la liste complète des segments connus dans le dataset.
        """
        return self.dataset.getValeursSegment()

    def getLargeurHauteurIHM(self):
        return 600, 600


#
#
## Gesion des templates

    def enregistrerTemplatesModules(self, liste_modules):
        for module_id, _, module_algo in liste_modules:
            version = "default"
            if module_id not in self._templates_modules :
                self._templates_modules [module_id] = {}
            if version not in self._templates_modules [module_id]:
                self._templates_modules [module_id][version] = {}

            self._templates_modules [module_id][version]["template"] = module_algo


    def genererModulesDepuisTemplates(self) -> dict[str, ModuleAlgo]:
        modules = {}
        for module_id, d in self._templates_modules.items():
            if "default" in d and "template" in d["default"]:
                modules[module_id] = copy.deepcopy(d["default"]["template"])
        return modules




    def setSegment(self, segment: str, layerManager:LayerManager):
        """
        Définit le segment actif et bascule sur les scénarios associés.
        Si aucun scénario n’existe encore pour ce segment, crée un scénario 'default'.
        """
        self.dataset.segment = segment
        self.dataset.calculer()

        self.segment_actif = segment

        if segment not in self._scenarios:
            self._scenarios[segment] = {}

        if not self._scenarios[segment]:
            self.creerScenarioDefault(layerManager)
        else:
            # Si le scénario actif précédent n’existe pas dans ce segment, basculer vers le premier trouvé
            if self.scenario_actif not in self._scenarios[segment]:
                self.scenario_actif = list(self._scenarios[segment].keys())[0]



    #
    # Methode de calcul des dépendances entre modules: construction de graph, vérification de l'intégrité...'
    #

    def getModulesTemplate(self) -> dict[str, object]:
        """
        Retourne un dictionnaire des modules template déclarés.
        Format : { module_id: template_module }

        Seuls les modules ayant un template sont inclus.
        """
        return {
            module_id: version_map["default"]["template"]
            for module_id, version_map in self._templates_modules.items()
            if "default" in version_map and "template" in version_map["default"]
        }

    def estModuleDisponible(self, module_id: str) -> bool:
        if module_id == "dataset":
            return True
        return module_id in self.getModulesTemplate()


    def estAttributDisponible(self, module_id: str, attribut: str) -> bool:
        if module_id == "dataset":
            return hasattr(self.dataset, attribut)

        module = self.getModulesTemplate().get(module_id)
        return hasattr(module, attribut) if module else False


    def construireGrapheDependances(self) -> dict[str, list[str]]:
        """
        Construit un graphe dirigé représentant les dépendances entre modules templates.
        Retourne : { module_source : [modules_qui_en_dépendent] }
        """
        templates = self.getModulesTemplate()
        graphe = {module_id: [] for module_id in templates}

        for module_cible_id, module_template in templates.items():
            for entree in module_template.getEntreesModules():
                module_source = entree.split(".")[0]
                if module_source in graphe:
                    graphe[module_source].append(module_cible_id)

        return graphe


    def afficherGrapheDependances(self):
        """
        Effectue un tri topologique des modules selon leurs dépendances.
        Lève une exception en cas de cycle.
        """
        for source, dependants in self.graphDependanceModules.items():
            print(f"{source} → {', '.join(dependants) if dependants else '∅'}")


    def getOrdreCalculModules(self) -> list[str]:
        """
        Effectue un tri topologique des modules selon leurs dépendances.
        Lève une exception en cas de cycle.
        """
        graphe = self.graphDependanceModules
        ordre = []
        marque = {}  # 'temp', 'definitif'

        def visiter(module_id):
            if module_id in marque:
                if marque[module_id] == 'temp':
                    raise ValueError(f"Cycle de dépendance détecté sur {module_id}")
                return
            marque[module_id] = 'temp'
            for dependant in graphe.get(module_id, []):
                visiter(dependant)
            marque[module_id] = 'definitif'
            ordre.insert(0, module_id)  # insertion en tête pour avoir les sources d'abord

        for module_id in graphe:
            if module_id not in marque:
                visiter(module_id)

        return ordre

    def getListeRegles(self):
        """
        Retourne la liste de toutes les règles métier disponibles sur les modules globaux.
        Chaque élément est un tuple : (module_id, attribut, nom, fonction)
        """
        resultats = []
        for module_id, module_obj in self.getModulesTemplate().items():
            for nom, attribut, fonction in module_obj.getRegles():
                resultats.append((module_id, attribut, nom, fonction))
        return resultats



    def validerStructureGlobale(self):
        """
        Vérifie que tous les modules template sont cohérents :
        - Chaque entrée référencée doit pointer vers un module existant
        - Chaque attribut mentionné doit exister sur le module source

        Utilise uniquement les modules template comme référence.
        """
        erreurs = []
        templates = self.getModulesTemplate()

        for module_id, module in templates.items():
            for entree in module.getEntreesModules():
                source_id, attr = entree.split(".")

                if source_id == "dataset":
                    source_module = self.dataset
                else:
                    source_module = templates.get(source_id)

                if not source_module:
                    erreurs.append(f"[ERREUR] Le module '{module_id}' dépend d’un module inexistant : '{source_id}'")
                    continue

                if not hasattr(source_module, attr):
                    erreurs.append(f"[ERREUR] Le module '{module_id}' dépend d’un attribut inexistant : '{source_id}.{attr}'")

        if erreurs:
            print("🛑 Problèmes détectés dans la structure globale :")
            for e in erreurs:
                print("   ", e)
            raise Exception("Structure globale invalide")
        else:
            print("✅ Structure globale des templates validée.")



    def validerStructureScenario(sself, nom_scenario: str = None, segment: str = None):
        """
        Valide les dépendances des modules d’un scénario spécifique (ou du scénario actif par défaut).
        Lève une exception si :
        - un module source est manquant
        - un attribut du module source est manquant
        """
        scenario = self.getScenario(nom_scenario, segment)
        erreurs = []

        for module_id, module in scenario.modules.items():
            for entree in module.getEntreesModules():
                source_id, attr = entree.split(".")

                if source_id == "dataset":
                    source_module = self.dataset
                else:
                    source_module = scenario.modules.get(source_id)

                if not source_module:
                    erreurs.append(f"[ERREUR] Le module '{module_id}' dépend d’un module inexistant : '{source_id}'")
                    continue

                if source_id == "dataset":
                    if not hasattr(self.dataset, attr):
                        erreurs.append(f"[ERREUR] Le module '{module_id}' dépend d’un attribut inexistant : '{source_id}.{attr}'")
                else:
                    if not hasattr(source_module, attr):
                        erreurs.append(f"[ERREUR] Le module '{module_id}' dépend d’un attribut inexistant : '{source_id}.{attr}'")

        if erreurs:
            print("🛑 Problèmes détectés dans les dépendances du scénario :")
            for err in erreurs:
                print(err)
            raise Exception("Structure invalide du scénario :\n" + "\n".join(erreurs))
        else:
            print(f"✅ Scénario '{nom_scenario or self.scenario_actif}' validé avec succès.")





    #
    # L' injection et le calcul se font toujours dans le module Actif'
    #


    def injecterEntreesDansModuleObjet(self, module_id: str, nom_scenario: str = None, segment: str = None):
        """
        Injecte dynamiquement les entrées dans un module donné, que ce soit depuis le dataset
        ou depuis d'autres modules du scénario. Utilise les accesseurs métier.
        """
        scenario = self.getScenario(nom_scenario, segment)
        module = scenario.modules.get(module_id)

        for entree in module.getEntreesModules():
            nom_source, nom_attribut = entree.split(".")

            if nom_source in scenario.modules:
                # Source = un autre module du scénario
                source = scenario.modules[nom_source]
                valeur = source.getParametre(nom_attribut)
            elif hasattr(self.dataset, nom_attribut):
                # Source = dataset (externe)
                valeur = getattr(self.dataset, nom_attribut)
            else:
                raise ValueError(f"Entrée invalide '{entree}' pour le module '{module_id}'")

            module.setParametre(f"{nom_attribut}{nom_source.capitalize()}", valeur)



    def appliquerReglesSurModule(self, module_id: str, nom_scenario: str, segment: str):
        module = self.getModulesScenario(module_id, nom_scenario, segment)
        if not hasattr(module, "getRegles"):
            return

        for description, nom_attribut, regle_callable in module.getRegles():
            valeur = regle_callable()
            module.setParametre(nom_attribut, valeur)




    def calculerModules(self, nom_scenario: str = None, segment: str = None, setup: bool = False):
        """
        Calcule tous les modules d’un scénario donné, dans l’ordre,
        en injectant les dépendances et les règles avant chaque calcul.
        """
        scenario = self.getScenario(nom_scenario, segment)

        for module_id in self.ordreModules:
            self.injecterEntreesDansModuleObjet(module_id, nom_scenario, segment)
            if setup:
                scenario.modules[module_id].setup()
            self.appliquerReglesSurModule(module_id, nom_scenario, segment)
            scenario.modules[module_id].calculer()


    #
    # Access aux données des modules en direct ou via le scénario courant
    #
    def getScenario(self, nom_scenario: str = None, segment: str = None) -> Scenario:
        """
        Retourne l'objet Scenario correspondant au segment et scénario spécifiés.
        Utilise les valeurs actives par défaut si non spécifiées.
        """
        nom = nom_scenario or self.scenario_actif
        seg = segment or self.segment_actif
        return self._scenarios[seg][nom]


    def getScenarioNomLisible(self, label_scenario: str, segment: str = None) -> Scenario:
        """
        Retourne le scénario à partir de son nom lisible (utilisé dans l'IHM).
        """
        seg = segment or self.segment_actif
        scenarios = self._scenarios.get(seg, {})

        for sc in scenarios.values():
            if sc.getDescriptionLisible() == label_scenario:
                return sc

        raise ValueError(f"Aucun scénario trouvé avec le label : {label_scenario}")


    def renommerScenario(self, ancien_nom: str, nouveau_nom: str, segment: str = None):
        """
        Renomme un scénario dans le dictionnaire interne.
        Met à jour la clé du scénario ainsi que son attribut .nom.
        """
        segment = segment or self.segment_actif
        scenarios = self._scenarios.get(segment)

        if not scenarios or ancien_nom not in scenarios:
            raise ValueError(f"Scénario '{ancien_nom}' introuvable dans le segment '{segment}'")

        scenario = scenarios.pop(ancien_nom)
        scenario.nom = nouveau_nom
        scenarios[nouveau_nom] = scenario

        # On change égalemnt le scenario actif si besoin
        if self.scenario_actif == ancien_nom:
            self.scenario_actif = nouveau_nom


    def getModulesScenario(self, module_id: str, nomScenario: str = None, segment: str = None):
        """
        Retourne le module identifié par 'module_id' dans le scénario et segment spécifiés.
        Si aucun scénario ou segment n'est précisé, utilise les valeurs actives.
        """
        scenario = self.getScenario(nomScenario, segment)
        return scenario.modules.get(module_id)



    def findScenarios(self, module_id: str, segment: str) -> list[Scenario]:
        """
        Retourne la liste des scénarios (pour un segment) contenant le module donné.
        """
        scenarios = self._scenarios.get(segment, {})
        return [sc for sc in scenarios.values() if module_id in sc.modules]


    def getParametre(self, module_id: str, attribut: str, nomScenario: str = None, segment: str = None):
        """
        Retourne la valeur d’un attribut pour un module donné dans un scénario et segment spécifiés.
        Si segment ou nomScenario sont None, on utilise les valeurs actifs.
        Si un segment différent du segment actif est fourni, le nom du scénario est obligatoire.
        """
        seg = segment or self.segment_actif

        # 🔐 Si le nom de scénario est omis
        if nomScenario is None:
            if seg == self.segment_actif:
                nomScenario = self.scenario_actif
            else:
                raise ValueError(f"[getParametre] Le nom du scénario est obligatoire si le segment '{seg}' est différent du segment actif '{self.segment_actif}'.")


        # ⚙️ Dataset multi-segment
        if module_id == "dataset":
            if hasattr(self.dataset, "getValeurPourSegment"):
                return self.dataset.getValeurPourSegment(seg, attribut)
            else:
                raise ValueError(f"[Dataset] Le module dataset ne gère pas les segments explicitement.")

        scenario = self.getScenario(nomScenario, seg)
        module = scenario.modules.get(module_id)
        if module is None:
            raise ValueError(
                f"Module '{module_id}' introuvable dans le scénario '{nomScenario}' du segment '{seg}'"
            )

        return module.getParametre(attribut)



    def setParametre(self, module_id: str, attribut: str, valeur: Any, layerManager:LayerManager, nomScenario: str = None, segment: str = None):
        """
        Définit la valeur d’un attribut pour un module donné dans un scénario et segment spécifiés.
        Si nomScenario ou segment sont None, on utilise les valeurs actives.
        """
        segment = segment or self.segment_actif
        if module_id == "dataset":
            setattr(self.dataset, attribut, valeur)
            return

        scenario = self.getScenario(nomScenario, segment)
        module = scenario.modules.get(module_id)
        if module is None:
            raise ValueError(
                f"Module '{module_id}' introuvable dans le scénario '{nomScenario or self.scenario_actif}' "
                f"du segment '{segment or self.segment_actif}'"
            )
        # 1. Affecter la valeur
        module.setParametre(attribut, valeur)

        # 2. Recalcul complet (setup=False pour ne pas réinitialiser les modules)
        self.calculerModules(nomScenario, segment)

        # 3. Reconstruire la carte
        nomLayer = scenario.getDescriptionLisible()
        layer = layerManager.getLayer(nomLayer, segment=segment)
        scenario.construireRepresentationCarte(layer)



    def getValeursParametre(self, module_id: str, attribut: str, nomScenario: str = None, segment: str = None):
        """
        Retourne les valeurs disponibles pour un paramètre donné dans un module d’un scénario/segment.
        """
        module = self.getModulesScenario(module_id, nomScenario, segment)
        if module is None:
            raise ValueError(f"Module '{module_id}' introuvable dans le scénario '{nomScenario or self.scenario_actif}' du segment '{segment or self.segment_actif}'")
        return module.getValeursParametre(attribut)






    #
    # Gestion des scénarios
    #

    def creerScenarioDefault(self, layerManager:LayerManager) -> Scenario:
        """
        Crée un scénario de type DEFAULT pour le segment actif.
        - Génère les modules depuis les templates
        - Enregistre le scénario immédiatement dans self._scenarios
        - Calcule tous les modules
        - Construit la représentation graphique
        """
        nom_scenario = "Scénario par défaut"
        segment = self.segment_actif

        # 1. Génération des modules depuis les templates
        modules = self.genererModulesDepuisTemplates()

        # 2. Création du scénario
        scenario = Scenario(
            nom=nom_scenario,
            quadruplets=[],
            modules=modules,
            ordreModules=self.ordreModules,
            segment=segment,
            layerManager=layerManager,
            type_scenario=TypeScenario.DEFAULT
        )

        # 3. Référencement immédiat dans la structure
        self._scenarios.setdefault(segment, {})[nom_scenario] = scenario
        self.scenario_actif = nom_scenario

        # 4. Calcul des modules (injection + règles + calcul)
        self.calculerModules(nom_scenario=nom_scenario, segment=segment, setup = True)

        # 5. Construction graphique
        nomLayer = scenario.getDescriptionLisible()
        layer = layerManager.getLayer(nomLayer, segment=segment)
        scenario.construireRepresentationCarte(layer)

        return scenario



    def creerScenarioUnitaireAutomatique(self, nom: str, quadruplets: list[tuple[str, str, str, Any]], base_scenario: Scenario, layerManager:LayerManager, couleur: tuple = None) -> Scenario:
        """
        Crée un scénario automatique (lecture seule) à partir d’un scénario de référence (default ou utilisateur).
        Copie les modules initialisés, applique les paramètres spécifiques, puis lance le calcul.
        """
        # 1. Copier les modules déjà setupés et prêts
        modules = {k: copy.deepcopy(v) for k, v in base_scenario.modules.items()}

        # 2. Appliquer uniquement les paramètres définis dans les quadruplets
        for module_id, attribut, _, valeur in quadruplets:
            if module_id in modules:
                modules[module_id].setParametre(attribut, valeur)

        # 3. Créer le scénario, sans le rendre actif
        scenario = Scenario(
            nom,
            quadruplets,
            modules,
            ordreModules=self.ordreModules,
            segment=self.segment_actif,
            layerManager=layerManager,
            couleur=couleur,
            type_scenario=TypeScenario.AUTOMATIQUE
        )
        self._scenarios.setdefault(self.segment_actif, {})[nom] = scenario

        # 4. Calcul explicite, sans modifier scenario_actif
        self.calculerModules(nom_scenario=nom, segment=self.segment_actif)

        # 5. Génération graphique
        nomLayer = scenario.getDescriptionLisible()
        layer = layerManager.getLayer(nomLayer, segment=self.segment_actif)
        scenario.construireRepresentationCarte(layer)

        return scenario


    def creerScenarioUtilisateur(self, nom: str, base: Scenario, layerManager:LayerManager, couleur: Any = None) -> Scenario:
        """
        Crée un nouveau scénario de type UTILISATEUR à partir d’un scénario existant (souvent 'default').

        Args:
            nom: Nom du nouveau scénario
            base: Scénario de base à dupliquer
            couleur: Optionnel, couleur à utiliser dans l'IHM

        Returns:
            Scenario: Le nouveau scénario créé
        """
        segment = base.segment
        modules = copy.deepcopy(base.modules)

        scenario = Scenario(
            nom=nom,
            quadruplets=[],
            modules=modules,
            ordreModules=self.ordreModules,
            segment=segment,
            layerManager=layerManager,
            type_scenario=TypeScenario.UTILISATEUR,
            couleur=couleur,
        )

        self._scenarios.setdefault(segment, {})[nom] = scenario

        # On duplique les solutions
        scenario.solutionScenario = base.solutionScenario

        nomLayer = scenario.getDescriptionLisible()
        layer = layerManager.getLayer(nomLayer, segment=segment)
        scenario.construireRepresentationCarte(layer)

        return scenario


    def supprimerTousScenariosAutomatiques(self, layerManager:LayerManager, segment: str = None) -> list[str]:
        """
        Supprime tous les scénarios automatiques du segment actif.
        Retourne la liste des noms supprimés pour permettre à l’IHM de supprimer les layers associés.
        """
        segment = segment or self.segment_actif
        scenarios = self._scenarios.get(self.segment_actif, {})
        a_supprimer = [nom for nom, sc in scenarios.items() if sc.type_scenario == TypeScenario.AUTOMATIQUE]

        for nom in a_supprimer:
            scenario = scenarios[nom]
            nomLayer = scenario.getDescriptionLisible()
            layerManager.supprimerLayer(nomLayer, segment=segment)
            del scenarios[nom]

        # Si le scénario actif a été supprimé, on rebascule sur un autre
        if self.scenario_actif in a_supprimer:
            restants = list(scenarios.keys())
            if restants:
                self.scenario_actif = restants[0]
            else:
                self.creerScenarioDefault()

        return a_supprimer


    def supprimerScenarioNomLisible(self, nom_lisible: str, layerManager:LayerManager, segment: str = None):
        """
        Supprime un scénario en utilisant son nom lisible (interface utilisateur).
        Met à jour la sélection si le scénario supprimé était actif.
        """
        segment = segment or self.segment_actif
        scenarios = self._scenarios.get(segment, {})

        for nom, sc in list(scenarios.items()):
            if sc.getDescriptionLisible() == nom_lisible:
                layerManager.supprimerLayer(nom_lisible, segment=segment)
                del scenarios[nom]
                print(f"🗑️ Scénario supprimé : {nom_lisible}")

                # Si on supprime le scénario actif, on rebascule vers un autre
                if self.scenario_actif == nom:
                    restants = list(scenarios.keys())
                    if restants:
                        self.scenario_actif = restants[0]
                    else:
                        self.creerScenarioDefault()

                return

        raise ValueError(f"Scénario '{nom_lisible}' introuvable dans le segment '{segment}'")



    #
    # Gestion des paramètres du scénario
    #


    def aDesScenarioAutomatiques(self, segment: str = None) -> bool:
        """
        Retourne True s’il existe au moins un scénario AUTOMATIQUE dans le segment donné.
        """
        segment = segment or self.segment_actif
        return any(
            sc.type_scenario == TypeScenario.AUTOMATIQUE
            for sc in self._scenarios.get(segment, {}).values()
        )


    def getListeParametresScenarioAutomatique(self, segment: str = None) -> list[tuple[str, str]]:
        segment = segment or self.segment_actif
        for scenario in self._scenarios.get(segment, {}).values():
            if scenario.type_scenario == TypeScenario.AUTOMATIQUE:
                return scenario.getListeParametres()
        return []


    def getListeScenarios(self, segment: str = None, type_scenario: TypeScenario = None) -> list:
        """
        Retourne la liste des noms de scénarios disponibles pour un segment donné.
        Si type_scenario est précisé, filtre uniquement les scénarios de ce type.

        Paramètres :
        - segment (optionnel) : identifiant du segment (clé logique)
        - type_scenario (optionnel) : Enum TypeScenario

        Retour :
        - Liste ordonnée des noms de scénarios (ex : ["S1", "S2", "S3"])
        """
        segment = segment or self.segment_actif
        scenarios = self._scenarios.get(segment, {})

        if type_scenario is None:
            return sorted(scenarios.keys())

        return sorted([
            nom for nom, sc in scenarios.items()
            if sc.getTypeScenario() == type_scenario
        ])



    def getScenariosDict(self, segment: str = None, type_scenario: TypeScenario = None) -> dict:
        """
        Retourne un dictionnaire {nom: Scenario} pour un segment donné.
        Si type_scenario est précisé, ne retourne que les scénarios de ce type.

        Paramètres :
        - segment (optionnel) : clé du segment
        - type_scenario (optionnel) : Enum TypeScenario

        Retour :
        - Dictionnaire {nom_scenario: objet Scenario}
        """
        segment = segment or self.segment_actif
        scenarios = self._scenarios.get(segment, {})

        if type_scenario is None:
            return scenarios

        if type_scenario == TypeScenario.UTILISATEUR:
            return {
                nom: sc for nom, sc in scenarios.items()
                if sc.getTypeScenario() in [TypeScenario.UTILISATEUR, TypeScenario.DEFAULT ]
            }

        return {
            nom: sc for nom, sc in scenarios.items()
            if sc.getTypeScenario()==type_scenario
        }


    def getModulesAvecAffichage(self) -> list[str]:
        """
        Retourne la liste des labels des modules ayant redéfini construireRepresentationCarte(),
        donc susceptibles de produire des objets graphiques.
        """
        modules = []
        for module_id, label, module in self.getListeModulesInitiale():
            if type(module).construireRepresentationCarte is not ModuleAlgo.construireRepresentationCarte:
                modules.append((module_id,label))
        return modules




    def appliquerScenario(self, label_scenario: str, segment: str = None):
        """
        Applique un scénario à partir de sa description lisible (label affiché dans l'IHM).
        """
        seg = segment or self.segment_actif
        scenarios = self._scenarios.get(seg, {})

        for nom, sc in scenarios.items():
            if sc.getDescriptionLisible() == label_scenario:
                self.scenario_actif = nom
                return

        print(f"[ERREUR] Aucun scénario avec le label : {label_scenario}")




