from unittest.mock import Mock

import pytest

import src.IHMAlgorithme as ihm_module
from src.IHMAlgorithme import IHMAlgorithme


class FauxStringVar:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FauxWidget:
    instances = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.bindings = {}
        self.destroyed = False
        type(self).instances.append(self)

    def grid(self, **_kwargs):
        pass

    def pack(self, **_kwargs):
        pass

    def bind(self, sequence, callback):
        self.bindings[sequence] = callback

    def destroy(self):
        self.destroyed = True


class FauxToplevel(FauxWidget):
    def title(self, _title):
        pass

    def transient(self, parent):
        self.transient_parent = parent

    def grab_set(self):
        pass


class FauxListbox(FauxWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.valeurs = []
        self.selection_active = "Nouvelle ville"

    def configure(self, **_kwargs):
        pass

    def delete(self, _premier, _dernier):
        self.valeurs = []

    def insert(self, _index, valeur):
        self.valeurs.append(valeur)

    def get(self, premier, dernier=None):
        if dernier is not None:
            return tuple(self.valeurs)
        return self.selection_active

    def selection_set(self, _index):
        pass

    def see(self, _index):
        pass


class FauxBouton(FauxWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text = kwargs["text"]
        self.command = kwargs["command"]


class FauxMoteur:
    def __init__(self, valeurs=None):
        self.valeurs = valeurs or {("planete", "ville"): "Ancienne ville"}

    def getParametre(self, module, attribut):
        return self.valeurs[(module, attribut)]


class FauxVilles(dict):
    def __init__(self):
        super().__init__({"Ancienne ville": object(), "Nouvelle ville": object()})
        self.rechargee = False

    def recharger(self):
        self.rechargee = True


@pytest.fixture
def pointville(monkeypatch):
    for classe in (FauxWidget, FauxToplevel, FauxListbox, FauxBouton):
        classe.instances = []

    villes = FauxVilles()
    monkeypatch.setattr(ihm_module.tk, "StringVar", FauxStringVar)
    monkeypatch.setattr(ihm_module.tk, "Label", FauxWidget)
    monkeypatch.setattr(ihm_module.tk, "Toplevel", FauxToplevel)
    monkeypatch.setattr(ihm_module.tk, "Listbox", FauxListbox)
    monkeypatch.setattr(ihm_module.ttk, "Frame", FauxWidget)
    monkeypatch.setattr(ihm_module.ttk, "Label", FauxWidget)
    monkeypatch.setattr(ihm_module.ttk, "Entry", FauxWidget)
    monkeypatch.setattr(ihm_module.ttk, "Button", FauxBouton)
    monkeypatch.setattr(ihm_module, "villes_dict", villes)

    ihm = IHMAlgorithme.__new__(IHMAlgorithme)
    ihm.moteurAlgo = FauxMoteur()
    ihm.parametres_widgets = {}
    ihm.attributsModulesAffichés = []
    ihm.updateModuleEtInterface = Mock()
    ihm.ajouter_ligne_widgets(
        FauxWidget(),
        [{"Widget": "pointville", "Label": "Ville", "Module": "planete", "Attribut": "ville"}],
    )

    champ_principal = ihm.parametres_widgets["planete.ville"]
    bouton_ouverture = next(bouton for bouton in FauxBouton.instances if bouton.text == "...")
    bouton_ouverture.command()
    boutons = {bouton.text: bouton for bouton in FauxBouton.instances}
    popup = FauxToplevel.instances[-1]
    return ihm, villes, champ_principal, popup, boutons


def test_pointville_valide_la_ville_avec_la_variable_du_champ_principal(pointville):
    ihm, villes, champ_principal, popup, boutons = pointville

    boutons["Sélectionner"].command()

    assert villes.rechargee is True
    assert champ_principal.get() == "Nouvelle ville"
    ihm.updateModuleEtInterface.assert_called_once_with("planete", "ville", "Nouvelle ville")
    assert popup.destroyed is True
    entree_filtre = [widget for widget in FauxWidget.instances if "textvariable" in widget.kwargs][-1]
    assert "<Return>" in entree_filtre.bindings
    assert "<Double-1>" in FauxListbox.instances[-1].bindings


def test_pointville_annule_sans_modifier_le_champ_ni_le_modele(pointville):
    ihm, _villes, champ_principal, popup, boutons = pointville

    boutons["Annuler"].command()

    assert champ_principal.get() == "Ancienne ville"
    ihm.updateModuleEtInterface.assert_not_called()
    assert popup.destroyed is True
    assert "<Escape>" in popup.bindings


def test_pointville_conserve_sa_propre_closure_parmi_trois_champs(pointville):
    _ihm_initial, _villes, _champ_initial, _popup_initial, _boutons_initiaux = pointville
    ihm = IHMAlgorithme.__new__(IHMAlgorithme)
    ihm.moteurAlgo = FauxMoteur(
        {
            ("segment", "lampouy"): "Lampouy",
            ("segment", "carnac"): "Carnac",
            ("segment", "beaufort"): "Beaufort-en-Vallée",
        }
    )
    ihm.parametres_widgets = {}
    ihm.attributsModulesAffichés = []
    ihm.updateModuleEtInterface = Mock()
    ihm.ajouter_ligne_widgets(
        FauxWidget(),
        [
            {"Widget": "pointville", "Label": "Lampouy", "Module": "segment", "Attribut": "lampouy"},
            {"Widget": "pointville", "Label": "Carnac", "Module": "segment", "Attribut": "carnac"},
            {"Widget": "pointville", "Label": "Beaufort", "Module": "segment", "Attribut": "beaufort"},
        ],
    )

    boutons_ouverture = [bouton for bouton in FauxBouton.instances if bouton.text == "..."][-3:]
    boutons_ouverture[0].command()
    popup = FauxToplevel.instances[-1]
    entree_filtre = [widget for widget in FauxWidget.instances if "textvariable" in widget.kwargs][-1]
    FauxListbox.instances[-1].selection_active = "Rennes"
    bouton_selectionner = [bouton for bouton in FauxBouton.instances if bouton.text == "Sélectionner"][-1]

    assert entree_filtre.kwargs["textvariable"].get() == "Lampouy"
    assert popup.transient_parent is boutons_ouverture[0].args[0]
    bouton_selectionner.command()

    assert ihm.parametres_widgets["segment.lampouy"].get() == "Rennes"
    assert ihm.parametres_widgets["segment.carnac"].get() == "Carnac"
    assert ihm.parametres_widgets["segment.beaufort"].get() == "Beaufort-en-Vallée"
    ihm.updateModuleEtInterface.assert_called_once_with("segment", "lampouy", "Rennes")
