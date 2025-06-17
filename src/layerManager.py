class Layer:
    def __init__(self, nom: str, couleur=(0, 0, 0), epaisseur=1, visible=True):
        """
        Représente un calque logique auquel peuvent appartenir plusieurs objets graphiques.
        """
        self.nom = nom
        self.couleur = couleur
        self.epaisseur = epaisseur
        self.visible = visible
        self.objets = []  #  Tous les objets graphiques associés à ce layer

    def setCouleur(self, couleur: tuple[int, int, int]):
        self.couleur = couleur

    def getCouleur(self):
        return self.couleur

    def getEpaisseur(self):
        return self.epaisseur

    def setEpaisseur(self, epaisseur: int):
        self.epaisseur = epaisseur

    def setVisible(self, visible: bool):
        self.visible = visible

    def estVisible(self) -> bool:
        return self.visible

    def __repr__(self):
        return f"<Layer '{self.nom}' couleur={self.couleur} épaisseur={self.epaisseur} visible={self.visible}>"

    def inclureObjetDansLayer(self, *objets):
        """
        Ajoute un ou plusieurs objets graphiques à ce calque.
        """
        for obj in objets:
            if isinstance(obj, list):
                for o in obj:
                    o.setLayer(self)
                    self.objets.append(o)
            else:
                obj.setLayer(self)
                self.objets.append(obj)

    def retirerObjetDuLayer(self, nom: str):
        """
        Supprime le premier objet ayant ce nom.
        Si plusieurs objets portent ce nom, seul le premier est supprimé.
        """
        for obj in self.objets:
            if obj.nom == nom:
                self.objets.remove(obj)
                return
        raise ValueError(f"Objet nommé '{nom}' introuvable dans le layer '{self.nom}'")

    def supprimerTousObjets(self):
        """
        Supprime tous les objets graphiques contenus dans ce layer.
        """
        self.objets.clear()

    def getListeObjetsGraphiques(self) -> list:
        return self.objets

    def recalculerCoordonneesPixelAbs(self):
        for obj in self.objets:
            obj.recalculerCoordonneesPixelAbs()


class LayerManager:
    def __init__(self):
        self._layers = {}            # nom (str) → Layer
        self.layerCourant = None    # référence directe (Layer)
        self.segmentActif = None    # segment actuellement affiché
        self.filtreActif = {"module": None, "level": "tous"}





    def creerLayer(self, nomLayer, segment = None) -> Layer:
        segment = segment or self.segmentActif
        if segment is None:
            raise ValueError("Aucun segment actif défini et aucun segment fourni.")
        if segment not in self._layers:
            self._layers[segment] = {}
            if self.segmentActif is None:
                self.segmentActif = segment  # premier segment connu

        if nomLayer not in self._layers[segment]:
            layer = Layer(nomLayer)
            self._layers[segment][nomLayer] = layer
        return layer


    def getLayer(self, nomLayer, segment=None) -> Layer | None:
        segment = segment or self.segmentActif
        if segment is None:
            raise ValueError("Aucun segment actif défini.")
        return self._layers.get(segment, {}).get(nomLayer)

    def setLayerCourant(self, nom: str, segment=None):
        segment = segment or self.segmentActif
        layer = self.getLayer(nom, segment)
        if layer is None:
            raise ValueError(f"Layer '{nom}' introuvable dans le segment '{segment}'.")
        self.layerCourant = layer

    def getLayerCourant(self) -> Layer | None:
        return self.layerCourant

    def getNomsLayers(self, segment=None) -> list[str]:
        segment = segment or self.segmentActif
        if segment is None:
            return []
        return list(self._layers.get(segment, {}).keys())

    def supprimerLayer(self, nom: str, segment=None):
        segment = segment or self.segmentActif
        if segment in self._layers and nom in self._layers[segment]:
            if self.layerCourant and self.layerCourant.nom == nom:
                self.layerCourant = None
            del self._layers[segment][nom]


    def renommerLayer(self, ancien_nom: str, nouveau_nom: str, segment: str = None):
        """
        Renomme un layer dans le dictionnaire interne.
        Met à jour la clé et le nom visible du layer.
        """
        segment = segment or self.segmentActif
        dico = self._layers.get(segment)

        if not dico or ancien_nom not in dico:
            raise ValueError(f"Layer '{ancien_nom}' introuvable dans le segment '{segment}'")

        layer = dico.pop(ancien_nom)
        layer.nom = nouveau_nom
        dico[nouveau_nom] = layer

        # On change égalemnt le layer actif si besoin
        if self.layerCourant == ancien_nom:
            self.layerCourant = nouveau_nom

    def getListeSegments(self) -> list[str]:
        return list(self._layers.keys())

    def getListeObjetsGraphiques(self, segment=None) -> list:
        segment = segment or self.segmentActif
        if segment is None:
            return []

        return [
            obj
            for layer in self._layers.get(segment, {}).values()
            for obj in layer.objets
        ]

    def setFiltreTag(self, cle: str, valeur: str | list[str] | None):
        """
        Met à jour un seul tag du filtre actif (ex: 'module' ou 'level').
        Peut recevoir une valeur unique (str), une liste de valeurs (list[str]), ou None.
        Toutes les chaînes sont converties en minuscules.
        """
        if not hasattr(self, "filtreActif"):
            self.filtreActif = {}

        if valeur is None:
            self.filtreActif[cle] = None
        elif isinstance(valeur, list):
            self.filtreActif[cle] = [v.lower() for v in valeur]
        else:
            self.filtreActif[cle] = valeur.lower()


    def estObjetVisible(self, obj) -> bool:
        """
        Retourne True si l’objet est à la fois visible et non filtré.
        """
        for tag, valeur in self.filtreActif.items():
            if valeur is None or valeur == "tous":
                continue

            tag_val = str(obj.tags.get(tag, "")).lower()
            if isinstance(valeur, list):
                if tag_val not in valeur:
                    return False
            else:
                if tag_val != valeur:
                    return False
        return True


    def getListeObjetsGraphiquesVisible(self, segment=None) -> list:
        segment = segment or self.segmentActif
        if segment is None:
            return []

        return [
            obj
            for layer in self._layers.get(segment, {}).values()
            for obj in layer.objets
            if self.estObjetVisible(obj)
        ]

    def recalculerCoordonneesPixelAbsTous(self):
        for segment in self._layers:
            for layer in self._layers[segment].values():
                layer.recalculerCoordonneesPixelAbs()

