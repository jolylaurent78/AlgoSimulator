import pytest

from src.AlgorithmeManager import ModuleAlgo


class FakeModule(ModuleAlgo):
    def __init__(self):
        self.foo = 1
        self.items = ["original"]
        self.dataset = object()

    def getValeursFoo(self):
        return ["un", "deux"]


def test_set_parametre_modifie_un_attribut_existant():
    module = FakeModule()

    module.setParametre("foo", 42)

    assert module.foo == 42


def test_set_parametre_refuse_un_attribut_inexistant():
    with pytest.raises(AttributeError, match="inconnu"):
        FakeModule().setParametre("inconnu", "valeur")


def test_get_parametre_retourne_la_valeur_ou_none():
    module = FakeModule()

    assert module.getParametre("foo") == 1
    assert module.getParametre("inconnu") is None


def test_get_valeurs_parametre_utilise_la_methode_dynamique_ou_retourne_une_liste_vide():
    module = FakeModule()

    assert module.getValeursParametre("foo") == ["un", "deux"]
    assert module.getValeursParametre("inconnu") == []


def test_a_attribut_reconnait_les_attributs_existants_et_absents():
    module = FakeModule()

    assert module.aAttribut("foo") is True
    assert module.aAttribut("inconnu") is False


def test_dupliquer_realise_une_deepcopy():
    module = FakeModule()

    copie = module.dupliquer()
    copie.items.append("copie")

    assert copie is not module
    assert module.items == ["original"]
    assert copie.items == ["original", "copie"]


def test_get_etat_exclut_explicitement_dataset():
    module = FakeModule()

    etat = module.getEtat()

    assert etat["foo"] == 1
    assert etat["items"] == ["original"]
    assert "dataset" not in etat


def test_construire_representation_carte_par_defaut_est_vide():
    assert FakeModule().construireRepresentationCarte() == []
