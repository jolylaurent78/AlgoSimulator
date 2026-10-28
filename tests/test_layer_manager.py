import pytest

from src.layerManager import Layer, LayerManager


class FakeObjetGraphique:
    def __init__(self, nom, tags=None):
        self.nom = nom
        self.tags = tags or {}
        self.layer = None
        self.recalculs = 0

    def setLayer(self, layer):
        self.layer = layer

    def recalculerCoordonneesPixelAbs(self):
        self.recalculs += 1


def test_layer_construction_conserve_les_proprietes_significatives():
    layer = Layer("traces", couleur=(1, 2, 3), epaisseur=4, visible=False)

    assert layer.nom == "traces"
    assert layer.getCouleur() == (1, 2, 3)
    assert layer.getEpaisseur() == 4
    assert layer.estVisible() is False
    assert layer.getListeObjetsGraphiques() == []


def test_layer_ajoute_un_objet_dans_lordre_et_definit_son_layer():
    layer = Layer("traces")
    premier = FakeObjetGraphique("premier")
    second = FakeObjetGraphique("second")

    layer.inclureObjetDansLayer(premier, second)

    assert layer.getListeObjetsGraphiques() == [premier, second]
    assert premier.layer is layer
    assert second.layer is layer


def test_layer_accepte_une_liste_dobjets():
    layer = Layer("traces")
    objets = [FakeObjetGraphique("un"), FakeObjetGraphique("deux")]

    layer.inclureObjetDansLayer(objets)

    assert layer.getListeObjetsGraphiques() == objets
    assert all(objet.layer is layer for objet in objets)


def test_layer_retirer_objet_supprime_le_premier_nom_correspondant():
    layer = Layer("traces")
    premier = FakeObjetGraphique("cible")
    second = FakeObjetGraphique("cible")
    layer.inclureObjetDansLayer(premier, second)

    layer.retirerObjetDuLayer("cible")

    assert layer.getListeObjetsGraphiques() == [second]


def test_layer_retirer_objet_absent_leve_une_erreur_explicite():
    with pytest.raises(ValueError, match="introuvable"):
        Layer("traces").retirerObjetDuLayer("absent")


def test_layer_supprimer_tous_objets_vide_le_layer():
    layer = Layer("traces")
    layer.inclureObjetDansLayer(FakeObjetGraphique("un"), FakeObjetGraphique("deux"))

    layer.supprimerTousObjets()

    assert layer.getListeObjetsGraphiques() == []


def test_layer_couleur_et_epaisseur_sont_modifiables():
    layer = Layer("traces")

    layer.setCouleur((4, 5, 6))
    layer.setEpaisseur(3)

    assert layer.getCouleur() == (4, 5, 6)
    assert layer.getEpaisseur() == 3


def test_layer_visibilite_est_independante():
    premier = Layer("premier", visible=True)
    second = Layer("second", visible=False)

    premier.setVisible(False)
    second.setVisible(True)

    assert premier.estVisible() is False
    assert second.estVisible() is True


def test_layer_delegue_le_recalcul_de_coordonnees_a_tous_ses_objets():
    layer = Layer("traces")
    objets = [FakeObjetGraphique("un"), FakeObjetGraphique("deux")]
    layer.inclureObjetDansLayer(objets)

    layer.recalculerCoordonneesPixelAbs()

    assert [objet.recalculs for objet in objets] == [1, 1]


def test_creer_layer_le_rend_accessible_et_initialise_le_premier_segment_actif():
    manager = LayerManager()

    layer = manager.creerLayer("traces", segment="A")

    assert layer.nom == "traces"
    assert manager.segmentActif == "A"
    assert manager.getLayer("traces", segment="A") is layer


def test_creer_layer_sans_segment_actif_est_refuse():
    manager = LayerManager()

    with pytest.raises(ValueError, match="Aucun segment actif"):
        manager.creerLayer("traces")

    with pytest.raises(ValueError, match="Aucun segment actif"):
        manager.getLayer("traces")


def test_creer_deux_fois_le_meme_layer_reutilise_linstance_existante():
    manager = LayerManager()
    premier = manager.creerLayer("traces", segment="A")

    second = manager.creerLayer("traces", segment="A")

    assert second is premier
    assert manager.getLayer("traces", segment="A") is premier


def test_plusieurs_layers_distincts_coexistent_dans_un_segment():
    manager = LayerManager()
    premier = manager.creerLayer("premier", segment="A")
    second = manager.creerLayer("second", segment="A")

    assert manager.getNomsLayers() == ["premier", "second"]
    assert manager.getLayer("premier") is premier
    assert manager.getLayer("second") is second


def test_un_meme_nom_de_layer_est_independant_par_segment():
    manager = LayerManager()
    layer_a = manager.creerLayer("traces", segment="A")
    layer_b = manager.creerLayer("traces", segment="B")

    assert layer_a is not layer_b
    assert manager.getLayer("traces", segment="A") is layer_a
    assert manager.getLayer("traces", segment="B") is layer_b
    assert manager.getListeSegments() == ["A", "B"]


def test_get_layer_absent_retourne_none():
    manager = LayerManager()
    manager.creerLayer("traces", segment="A")

    assert manager.getLayer("absent", segment="A") is None


def test_layer_courant_est_selectionnable_et_invalide_est_refuse():
    manager = LayerManager()
    layer = manager.creerLayer("traces", segment="A")

    manager.setLayerCourant("traces")

    assert manager.getLayerCourant() is layer
    with pytest.raises(ValueError, match="introuvable"):
        manager.setLayerCourant("absent")


def test_supprimer_layer_preserve_les_autres_et_reinitialise_layer_courant():
    manager = LayerManager()
    premier = manager.creerLayer("premier", segment="A")
    second = manager.creerLayer("second", segment="A")
    manager.setLayerCourant("premier")

    manager.supprimerLayer("premier")

    assert manager.getLayer("premier") is None
    assert manager.getLayer("second") is second
    assert manager.getLayerCourant() is None
    assert premier not in manager.getListeObjetsGraphiques()


def test_supprimer_layer_absent_est_silencieux():
    manager = LayerManager()
    manager.creerLayer("present", segment="A")

    manager.supprimerLayer("absent")

    assert manager.getNomsLayers() == ["present"]


def test_renommer_layer_conserve_linstance_et_le_layer_courant():
    manager = LayerManager()
    layer = manager.creerLayer("ancien", segment="A")
    manager.setLayerCourant("ancien")

    manager.renommerLayer("ancien", "nouveau")

    assert manager.getLayer("ancien") is None
    assert manager.getLayer("nouveau") is layer
    assert layer.nom == "nouveau"
    assert manager.getLayerCourant() is layer


def test_filtre_par_defaut_et_filtre_reinitialise_laissent_tous_les_objets_visibles():
    manager = LayerManager()
    objet = FakeObjetGraphique("objet", tags={"module": "planete", "level": "design"})

    assert manager.estObjetVisible(objet) is True
    manager.setFiltreTag("module", "planete")
    manager.setFiltreTag("module", None)
    assert manager.estObjetVisible(objet) is True


def test_filtre_tag_simple_est_insensible_a_la_casse_et_exclut_les_objets_sans_tag():
    manager = LayerManager()
    manager.setFiltreTag("module", "PLANETE")

    assert manager.estObjetVisible(FakeObjetGraphique("ok", {"module": "planete"})) is True
    assert manager.estObjetVisible(FakeObjetGraphique("absent")) is False


def test_filtre_tag_liste_et_plusieurs_tags_sont_combines():
    manager = LayerManager()
    manager.setFiltreTag("module", ["planete", "etoile"])
    manager.setFiltreTag("level", "design")

    assert manager.estObjetVisible(FakeObjetGraphique("ok", {"module": "ETOILE", "level": "design"})) is True
    assert manager.estObjetVisible(FakeObjetGraphique("mauvais niveau", {"module": "etoile", "level": "resultat"})) is False


def test_liste_objets_visibles_est_limitee_au_segment_demande_et_aux_tags():
    manager = LayerManager()
    layer_a = manager.creerLayer("traces", segment="A")
    layer_b = manager.creerLayer("traces", segment="B")
    objet_a = FakeObjetGraphique("a", {"module": "planete"})
    objet_b = FakeObjetGraphique("b", {"module": "etoile"})
    layer_a.inclureObjetDansLayer(objet_a)
    layer_b.inclureObjetDansLayer(objet_b)
    manager.setFiltreTag("module", "planete")

    assert manager.getListeObjetsGraphiquesVisible(segment="A") == [objet_a]
    assert manager.getListeObjetsGraphiquesVisible(segment="B") == []


def test_recalculer_coordonnees_pixel_abs_tous_visite_tous_les_layers_et_segments():
    manager = LayerManager()
    objets = [FakeObjetGraphique("a"), FakeObjetGraphique("b")]
    manager.creerLayer("premier", segment="A").inclureObjetDansLayer(objets[0])
    manager.creerLayer("second", segment="B").inclureObjetDansLayer(objets[1])

    manager.recalculerCoordonneesPixelAbsTous()

    assert [objet.recalculs for objet in objets] == [1, 1]
