from unittest.mock import Mock

import pytest

import src.interface_tk as interface_module
from src.interface_tk import InterfaceCarte


SEGMENT_RONCEVAUX = "15 Aout 778 : Bataille de Roncevaux"
SEGMENT_MARIAGE = "18 Mai 1152 : Mariage d'Aliénor d'Aquitaine"


class FauxStringVar:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FauxCombobox:
    def __init__(self, _parent, **kwargs):
        self.kwargs = kwargs
        self.bindings = {}

    def pack(self, **_kwargs):
        pass

    def bind(self, sequence, callback):
        self.bindings[sequence] = callback


class FauxMoteurSegments:
    def __init__(self, segments, segment_actif):
        self.segments = segments
        self.segment_actif = segment_actif
        self.setSegment = Mock()

    def getListeSegments(self):
        return self.segments


@pytest.fixture
def combo_segments(monkeypatch):
    monkeypatch.setattr(interface_module.tk, "StringVar", FauxStringVar)
    monkeypatch.setattr(interface_module.ttk, "Combobox", FauxCombobox)

    def construire(moteur):
        interface = InterfaceCarte.__new__(InterfaceCarte)
        interface.moteurAlgo = moteur
        interface.layerManager = object()
        interface.varSegmentAffiche = None
        interface.comboSegmentAffiche = None
        InterfaceCarte.creerSelectionSegments(interface, object())
        return interface

    return construire


def test_combo_segment_reflete_le_segment_actif_restaure(combo_segments):
    moteur = FauxMoteurSegments([SEGMENT_RONCEVAUX, SEGMENT_MARIAGE], SEGMENT_MARIAGE)

    interface = combo_segments(moteur)

    assert interface.varSegmentAffiche.get() == SEGMENT_MARIAGE
    moteur.setSegment.assert_not_called()


def test_combo_segment_utilise_le_premier_segment_en_fallback_sans_effet_metier(combo_segments):
    moteur = FauxMoteurSegments([SEGMENT_RONCEVAUX, SEGMENT_MARIAGE], None)

    interface = combo_segments(moteur)

    assert interface.varSegmentAffiche.get() == SEGMENT_RONCEVAUX
    moteur.setSegment.assert_not_called()
