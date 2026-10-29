"""Deuxième clé locale au Cadran Final ; la première garde sa valeur Clef."""
from hashlib import sha256
from pathlib import Path
from unittest.mock import Mock

import pytest

import src.AlgorithmeCadranFinal as final
from src.CadranNationalSentinelles import SentinelleNationale
from src.calculAstronomique import decalageGamme


@pytest.fixture(scope="module")
def national():
    return SentinelleNationale()


@pytest.fixture(autouse=True)
def partager_references(national, monkeypatch):
    monkeypatch.setattr(final, "Sentinelle", lambda *_: national)


@pytest.mark.parametrize("note,attendus", [
    ("C", ("C", "E", "A", "F", "G")),
    ("D", ("D", "F", "B", "C", "G")),
    ("E", ("E", "G", "C", "F", "G")),
    ("F", ("F", "A", "D", "C", "G")),
    ("G", ("G", "B", "E", "G", "G")),
    ("A", ("A", "C", "F", "F", "G")),
    ("B", ("B", "D", "G", "B", "B")),
])
@pytest.mark.parametrize("choix,index", [("=", 0), ("+2", 1), ("-2", 2), ("Clef", 3), ("Clef 2", 4)])
def test_table_des_substitutions_et_conservation_des_anciennes(note, attendus, choix, index):
    assert final.noteAvecSubstitutionCadranFinal(note, choix) == attendus[index]
    if choix != "Clef 2":
        ancien_index = {"=": 0, "+2": 2, "-2": 1, "Clef": 3}[choix]
        assert final.noteAvecSubstitutionCadranFinal(note, choix) == decalageGamme(note)[ancien_index]


@pytest.mark.parametrize("note,source", [("C", "C"), ("F", "F"), ("D", "F"),
                                        ("E", "C"), ("A", "C"), ("G", None), ("B", None)])
def test_priorite_initiale_puis_plus2_puis_moins2(note, source):
    # A rencontre Do en +2 avant Fa en -2 ; E ne rencontre Do qu'en -2.
    assert final._noteSourceClef2(decalageGamme(note)) == source


@pytest.mark.parametrize("calendrier", ["Standard", "Déclinaison"])
@pytest.mark.parametrize("choix", ["Clef", "Clef 2"])
@pytest.mark.parametrize("periode", ["AM", "PM"])
def test_trois_modules_partagent_la_meme_clef(national, calendrier, choix, periode):
    note = "C" if choix == "Clef" else "G"  # D et F ont ces deux issues.
    s = final.StyletFinal()
    s.styletDataset = "Saint-Valentin"
    s.base1Dataset = "Châlus"
    s.base2Dataset = "Fontevraud"
    s.lettreDomSegment = "D"
    s.lettreDeclDataset = "F"
    s.choixCalendrier = calendrier
    s.P2M2 = choix
    s.setup()
    s.calculer()
    assert s.lettre == note
    assert s.hauteur == pytest.approx(s.distanceRef / s.tableauGamme["F"] * s.tableauGamme[note])
    l = final.LumiereFinal()
    l.lettreDomSegment = "D"
    l.lettreDeclDataset = "F"
    l.choixCalendrier = calendrier
    l.choixHeure = choix
    l.heureAMPM = periode
    l.dateDataset = "19/07/933"
    l.dateSegmentDataset = "16/05/933"
    l.lieuObservationSegment = "Carnac"
    l.hauteurStylet = s.hauteur
    l.calculer()
    assert l.noteHoraire == note
    assert l.heureLocaleSecondes == national.heurePourNote(note, periode).secondes
    o = final.LigneHoraireFinal()
    o.sentinelleLumiere = national
    o.lettreDomSegment = "D"
    o.lettreDeclDataset = "F"
    o.choixCalendrier = calendrier
    o.choixHeure = choix
    o.dateDataset = "19/07/933"
    o.baseStylet = s.base
    o.azimutMidiStylet = s.azimutMidi
    o.calculer()
    assert o.noteHoraire == note
    assert o.heureLocaleSecondes == national.heurePourNote(note, "AM").secondes
    assert {r.note for r in o.lignesHorairesReference if r.candidat} == {note}
    assert len(o.listeCandidatsHeure) == 2


def test_interface_trois_champs_existants_acceptent_les_deux_clefs():
    import tkinter as tk
    from src.IHMAlgorithme import IHMAlgorithme
    root = tk.Tk()
    root.withdraw()
    try:
        for module, attribut, objet, methode in [
            ("stylet", "P2M2", final.StyletFinal(), "getValeursP2M2"),
            ("lumiere", "choixHeure", final.LumiereFinal(), "getValeursChoixHeure"),
            ("ombre", "choixHeure", final.LigneHoraireFinal(), "getValeursChoixHeure"),
        ]:
            ihm = IHMAlgorithme.__new__(IHMAlgorithme)
            ihm.parametres_widgets = {}
            ihm.moteurAlgo = Mock()
            ihm.moteurAlgo.regles_actives = {}
            ihm.moteurAlgo.getValeursParametre.return_value = getattr(objet, methode)()
            ihm.moteurAlgo.getParametre.return_value = "Clef"
            ihm.updateModuleEtInterface = Mock()
            panneau = tk.Frame(root)
            ihm.ajouter_ligne_widgets(panneau, [{"Widget": "checkboxH", "FieldType": "lettre",
                "Module": module, "Attribut": attribut, "Label": "Choix", "Type": "input_multiple"}])
            def cases(parent):
                return [w for child in parent.winfo_children()
                        for w in ([child] if isinstance(child, tk.Checkbutton) else cases(child))]
            controles = {w.cget("text"): w for w in cases(panneau)}
            assert {"Clef", "Clef 2"} <= controles.keys()
            assert "Clef 1" not in controles
            for choix in ("Clef 2", "Clef"):
                controles[choix].invoke()
                ihm.updateModuleEtInterface.assert_called_with(module, attribut, choix)
                valeurs = ihm.parametres_widgets[f"{module}.{attribut}"]
                assert valeurs[choix].get()
                assert not valeurs["Clef" if choix == "Clef 2" else "Clef 2"].get()
    finally:
        root.destroy()


def test_projets_clef_historique_gardent_notes_et_heures():
    from src.ProjectPersistence import chargerProjetJsonV1
    fichier = Path("projets/CadranFinal_Solutions.json")
    empreinte = sha256(fichier.read_bytes()).hexdigest()
    moteur, _ = chargerProjetJsonV1(fichier)
    verifies = 0
    for scenarios in moteur._scenarios.values():
        for scenario in scenarios.values():
            for cle in ("stylet", "lumiere", "ombre"):
                m = scenario.modules[cle]
                choix = m.P2M2 if cle == "stylet" else m.choixHeure
                if choix != "Clef":
                    continue
                attendu = decalageGamme(m.lettreChoix)[3]
                assert (m.lettre if cle == "stylet" else m.noteHoraire) == attendu
                if cle != "stylet":
                    branche = m.heureAMPM if cle == "lumiere" else "AM"
                    sentinelle = m.sentinelle if cle == "lumiere" else m.sentinelleLumiere
                    secondes = m.heureLocaleSecondes
                    assert secondes == sentinelle.heurePourNote(attendu, branche).secondes
                verifies += 1
    assert verifies > 0
    assert sha256(fichier.read_bytes()).hexdigest() == empreinte


def test_carnac_933_fa_donne_sol_sans_modifier_projet_ni_date():
    from src.ProjectPersistence import chargerProjetJsonV1
    fichier = Path("projets/CadranFinal_Solutions.json")
    empreinte = sha256(fichier.read_bytes()).hexdigest()
    moteur, _ = chargerProjetJsonV1(fichier)
    segment = next(s for s in moteur._scenarios if "933" in s)
    scenario = moteur.getScenario("Carnac", segment)
    modules = scenario.modules
    date_initiale = modules["lumiere"].dateSegmentDataset
    moteur.dataset.segment = segment
    moteur.dataset.calculer()
    for cle, attribut in (("stylet", "P2M2"), ("lumiere", "choixHeure"), ("ombre", "choixHeure")):
        assert modules[cle].choixCalendrier == "Déclinaison"
        assert modules[cle].lettreDeclDataset == "F"
        setattr(modules[cle], attribut, "Clef 2")
    moteur.calculerModules("Carnac", segment)
    assert modules["stylet"].lettre == modules["lumiere"].noteHoraire == modules["ombre"].noteHoraire == "G"
    assert modules["lumiere"].heureLocale == "12:00:00"
    assert modules["ombre"].heureLocale == "12:00:00"
    assert modules["lumiere"].dateSegmentDataset == date_initiale
    midi = next(r for r in modules["ombre"].lignesHorairesReference if r.note == "G" and r.ampm == "AM")
    assert midi.ecart_image == 0
    assert sha256(fichier.read_bytes()).hexdigest() == empreinte
