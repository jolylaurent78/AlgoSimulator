import json
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from src.AlgorithmeSegment import AlgorithmeSegment, PlaneteAnnee
from src.AlgorithmeStyletInitial import AlgorithmeStyletInitial
from src.calculAstronomique import MyJulianDate
from src.IHMAlgorithme import IHMAlgorithme
from src.ListeSegmentsDataSet import ListeSegmentsDataSet
from src.layerManager import LayerManager
from src.ProjectPersistence import FORMAT_PROJET, SCHEMA_VERSION, chargerProjetJsonV1, construireSnapshotProjetJsonV1, lireMetaDonneesProjetJsonV1
from src.interface_tk import InterfaceCarte


@pytest.fixture
def stylet_state():
    layers = LayerManager()
    return AlgorithmeStyletInitial(layers), layers


@pytest.fixture
def segment_state():
    layers = LayerManager()
    moteur = AlgorithmeSegment(layers)
    cache = moteur.getScenario().modules["annee"]
    cache.listeAnnees = [(1214, MyJulianDate.fromString("12/10/1365"), "Identique", "12.34Â°", "56.78Â°", "0.12Â°")]
    cache.listeAnneesSelection = 3
    return moteur, layers, cache


@pytest.fixture
def ui_mocks():
    with ExitStack() as stack:
        yield SimpleNamespace(
            showinfo=stack.enter_context(patch("src.interface_tk.messagebox.showinfo")),
            showerror=stack.enter_context(patch("src.interface_tk.messagebox.showerror")),
            askyesno=stack.enter_context(patch("src.interface_tk.messagebox.askyesno")),
            askopenfilename=stack.enter_context(patch("src.interface_tk.filedialog.askopenfilename")),
            asksaveasfilename=stack.enter_context(patch("src.interface_tk.filedialog.asksaveasfilename")),
        )


def charger_snapshot(snapshot, tmp_path):
    chemin = tmp_path / "projet.json"
    chemin.write_text(json.dumps(snapshot), encoding="utf-8")
    return chargerProjetJsonV1(chemin)


def parser_sans_tk(moteur):
    ihm = IHMAlgorithme.__new__(IHMAlgorithme)
    ihm.moteurAlgo = moteur
    setattr(ihm, "attributsModulesAffich\u00e9s", [])
    return ihm


@pytest.mark.slow
@pytest.mark.integration
def test_snapshot_exclut_automatiques_et_conserve_preferences(stylet_state):
    moteur, layers = stylet_state
    default = moteur.getScenario()
    utilisateur = moteur.creerScenarioUtilisateur("Mon scenario", default, layers)
    utilisateur.setSolution(True)
    layer = layers.getLayer(utilisateur.getDescriptionLisible(), segment=utilisateur.segment)
    layer.setCouleur((12, 34, 56)); layer.setEpaisseur(4); layer.setVisible(False)
    moteur.creerScenarioUnitaireAutomatique("Temporaire", [("planete", "nom", "P", "Neptune")], default, layers)
    snapshot = construireSnapshotProjetJsonV1(moteur, layers)
    assert snapshot["format"] == FORMAT_PROJET
    assert snapshot["schema_version"] == SCHEMA_VERSION
    assert snapshot["algorithm"] == "AlgorithmeStyletInitial"
    scenarios = snapshot["segments"][0]["scenarios"]
    assert {s["type"] for s in scenarios} == {"default", "utilisateur"}
    scenario = next(s for s in scenarios if s["name"] == "Mon scenario")
    assert scenario["solution"] is True
    assert scenario["layer_preferences"] == {"color": [12, 34, 56], "thickness": 4, "visible": False}


@pytest.mark.slow
@pytest.mark.integration
def test_csv_definit_les_parametres_persistants(stylet_state, tmp_path):
    moteur, layers = stylet_state
    contenu = (
        "Section,Categorie,Ligne,Widget,FieldType,Alignement,Label,ShortLabel,Hauteur,Type,Style,Module,Attribut\n"
        "Test,Global,1,checkbox,shorttext,left,Sens,S,1,input,std,planete,sensCarte\n"
        "Test,Global,2,checkbox,shorttext,left,Octave,O,1,data,std,stylet,octave\n"
    )
    chemin = tmp_path / "contrat.csv"; chemin.write_text(contenu, encoding="utf-8")
    parameters = construireSnapshotProjetJsonV1(moteur, layers, chemin)["segments"][0]["scenarios"][0]["parameters"]
    assert parameters["planete"]["sensCarte"] == "Endroit"
    assert "stylet" not in parameters


@pytest.mark.slow
@pytest.mark.integration
def test_roundtrip_restaure_scenarios_et_etat(stylet_state, tmp_path):
    moteur, layers = stylet_state; default = moteur.getScenario()
    utilisateur = moteur.creerScenarioUtilisateur("Mon scenario", default, layers)
    utilisateur.modules["planete"].nom = "Mars"; utilisateur.setSolution(True); moteur.scenario_actif = utilisateur.nom
    snapshot = construireSnapshotProjetJsonV1(moteur, layers)
    moteur_charge, layers_charges = charger_snapshot(snapshot, tmp_path)
    assert construireSnapshotProjetJsonV1(moteur_charge, layers_charges) == snapshot


@pytest.mark.slow
@pytest.mark.integration
def test_dataset_snapshot_conserve_ordre_sans_lire_csv(stylet_state, tmp_path):
    moteur, layers = stylet_state; snapshot = construireSnapshotProjetJsonV1(moteur, layers); snapshot["dataset"]["events"].reverse()
    with patch.object(ListeSegmentsDataSet, "__init__", side_effect=AssertionError("CSV interdit")):
        moteur_charge, _ = charger_snapshot(snapshot, tmp_path)
    assert list(moteur_charge.dataset.evenements) == [event["event"] for event in snapshot["dataset"]["events"]]


@pytest.mark.slow
@pytest.mark.integration
def test_entete_invalide_est_refuse(stylet_state, tmp_path):
    moteur, layers = stylet_state; snapshot = construireSnapshotProjetJsonV1(moteur, layers); snapshot["algorithm"] = "AlgorithmeInconnu"
    with pytest.raises(ValueError, match="Algorithme JSON non support"):
        charger_snapshot(snapshot, tmp_path)


@pytest.mark.slow
def test_lecture_metadonnees_ne_reconstruit_pas_le_projet(stylet_state, tmp_path):
    moteur, layers = stylet_state; chemin = tmp_path / "projet.json"
    chemin.write_text(json.dumps(construireSnapshotProjetJsonV1(moteur, layers)), encoding="utf-8")
    with patch("src.ProjectPersistence.chargerProjetJsonV1") as loader:
        metadata = lireMetaDonneesProjetJsonV1(chemin)
    loader.assert_not_called(); assert metadata["algorithm"] == "AlgorithmeStyletInitial"


@pytest.mark.slow
@pytest.mark.integration
def test_cache_csv_est_snapshotte_hors_parameters(segment_state):
    moteur, layers, _ = segment_state; scenario = construireSnapshotProjetJsonV1(moteur, layers)["segments"][0]["scenarios"][0]
    assert "listeAnnees" not in scenario["parameters"].get("annee", {})
    assert scenario["parameters"]["annee"]["listeAnneesSelection"] == 3
    assert isinstance(scenario["cached_results"]["annee"]["listeAnnees"][0], list)
    assert scenario["cached_results"]["annee"]["listeAnnees"][0][1]["__persist_type__"] == "MyJulianDate"


@pytest.mark.slow
@pytest.mark.integration
def test_roundtrip_restaure_cache_sans_calcul_lourd(segment_state, tmp_path):
    moteur, layers, _ = segment_state; snapshot = construireSnapshotProjetJsonV1(moteur, layers)
    with patch.object(PlaneteAnnee, "calculerAnnees", side_effect=AssertionError("calcul lourd interdit")) as calcul:
        moteur_charge, _ = charger_snapshot(snapshot, tmp_path)
    calcul.assert_not_called(); liste = moteur_charge.getScenario().modules["annee"].listeAnnees
    assert liste[0][0] == 1214
    assert liste[0][1] == MyJulianDate.fromString("12/10/1365")
    assert isinstance(liste[0], list)
    assert moteur_charge.getScenario().modules["annee"].listeAnneesSelection == 3


@pytest.mark.slow
@pytest.mark.integration
def test_ancien_json_sans_cache_reste_chargeable(segment_state, tmp_path):
    moteur, layers, _ = segment_state; snapshot = construireSnapshotProjetJsonV1(moteur, layers)
    for bloc in snapshot["segments"]:
        for scenario in bloc["scenarios"]: del scenario["cached_results"]
    moteur_charge, _ = charger_snapshot(snapshot, tmp_path)
    assert moteur_charge.getScenario().modules["annee"].listeAnnees == []


@pytest.mark.slow
@pytest.mark.integration
def test_cache_module_ou_attribut_inconnu_est_refuse(segment_state, tmp_path):
    moteur, layers, _ = segment_state; snapshot = construireSnapshotProjetJsonV1(moteur, layers)
    snapshot["segments"][0]["scenarios"][0]["cached_results"] = {"inconnu": {"liste": []}}
    with pytest.raises(ValueError, match="inconnu"): charger_snapshot(snapshot, tmp_path)
    snapshot = construireSnapshotProjetJsonV1(moteur, layers)
    snapshot["segments"][0]["scenarios"][0]["cached_results"] = {"annee": {"inconnu": []}}
    with pytest.raises(ValueError, match="annee.inconnu"): charger_snapshot(snapshot, tmp_path)


@pytest.mark.slow
def test_recalcul_reinitialise_la_selection(segment_state):
    _, _, cache = segment_state; cache.calculerAnnees(init=True)
    assert cache.listeAnnees == []; assert cache.listeAnneesSelection is None


@pytest.mark.slow
def test_ecriture_selection_sans_recalcul(segment_state):
    moteur, _, cache = segment_state
    with patch.object(moteur, "calculerModules") as calcul: moteur.setParametreSansRecalcul("annee", "listeAnneesSelection", 0)
    assert cache.listeAnneesSelection == 0; calcul.assert_not_called()


@pytest.mark.slow
def test_widget_none_et_liaison_tableselection_sont_valides(segment_state):
    moteur, _, _ = segment_state; ihm = parser_sans_tk(moteur); lignes = ihm.parser_csv("config/AlgorithmeSegment.csv"); ihm.parametres_csv = lignes
    selection = next(ligne for ligne in lignes if ligne["Attribut"] == "listeAnneesSelection")
    assert selection["Widget"] == "None"; assert selection["FieldType"] == "tableselection"
    assert ihm.getAttributSelectionTable("annee", "listeAnnees") == "listeAnneesSelection"


@pytest.mark.slow
def test_tableselection_invalide_est_refuse(segment_state, tmp_path):
    moteur, _, _ = segment_state
    contenu = "Section,Categorie,Ligne,Widget,FieldType,Alignement,Label,ShortLabel,Hauteur,Type,Style,Module,Attribut\nTest,Global,1,None,tableselection,left,,,1,input,std,annee,listeAnnees\n"
    chemin = tmp_path / "invalide.csv"; chemin.write_text(contenu, encoding="utf-8")
    with pytest.raises(ValueError, match="doit finir par 'Selection'"): parser_sans_tk(moteur).parser_csv(chemin)


@pytest.mark.slow
def test_table_associee_absente_ou_non_table_est_refusee(segment_state, tmp_path):
    moteur, _, _ = segment_state; entete = "Section,Categorie,Ligne,Widget,FieldType,Alignement,Label,ShortLabel,Hauteur,Type,Style,Module,Attribut\n"
    cas = (("Recherche,Global,1,None,tableselection,left,,,1,input,std,annee,listeAnneesSelection\n", "introuvable"), ("Recherche,Global,1,field,shorttext,left,,,1,data,std,annee,listeAnnees\nRecherche,Global,2,None,tableselection,left,,,1,input,std,annee,listeAnneesSelection\n", "Widget=list"))
    for index, (contenu, message) in enumerate(cas):
        chemin = tmp_path / f"invalide-{index}.csv"; chemin.write_text(entete + contenu, encoding="utf-8")
        with pytest.raises(ValueError, match=message): parser_sans_tk(moteur).parser_csv(chemin)


class FauxTable:
    def __init__(self): self.selection_courante = (); self._restauration_selection = False
    def get_children(self): return tuple(f"item-{index}" for index in range(6))
    def selection_set(self, item): self.selection_courante = (item,)
    def selection_remove(self, _items): self.selection_courante = ()
    def selection(self): return self.selection_courante
    def focus(self, _item): pass
    def see(self, _item): pass


@pytest.mark.slow
def test_selection_est_restauree_par_scenario():
    layers = LayerManager(); moteur = AlgorithmeSegment(layers); scenario_a = moteur.getScenario(); scenario_a.modules["annee"].listeAnneesSelection = 2
    scenario_b = moteur.creerScenarioUtilisateur("B", scenario_a, layers); scenario_b.modules["annee"].listeAnneesSelection = 5
    ihm = IHMAlgorithme.__new__(IHMAlgorithme); ihm.moteurAlgo = moteur; table = FauxTable()
    ihm.restaurerSelectionTable(table, "annee", "listeAnneesSelection"); assert table.selection() == ("item-2",)
    moteur.appliquerScenario("B"); ihm.restaurerSelectionTable(table, "annee", "listeAnneesSelection"); assert table.selection() == ("item-5",)
    scenario_b.modules["annee"].listeAnneesSelection = None; ihm.restaurerSelectionTable(table, "annee", "listeAnneesSelection"); assert table.selection() == ()


def test_charger_projet_charge_json_et_met_a_jour_chemin(ui_mocks):
    moteur, layers = object(), object(); interface = SimpleNamespace(cheminProjetCourant=None, dossiers={"projets": "projets"}, appliquerEtat=Mock(), mettreAJourTitreFenetre=Mock(), memoriserDernierProjet=Mock())
    ui_mocks.askopenfilename.return_value = "projets/Cadran.json"
    with patch("src.interface_tk.chargerProjetJsonV1", return_value=(moteur, layers)) as loader: InterfaceCarte.actionChargerProjet(interface)
    ui_mocks.askopenfilename.assert_called_once_with(initialdir="projets", filetypes=[("Projet JSON", "*.json")], title="Charger un projet")
    loader.assert_called_once_with("projets/Cadran.json"); interface.appliquerEtat.assert_called_once_with(layers, moteur)
    assert interface.cheminProjetCourant == "projets/Cadran.json"; interface.memoriserDernierProjet.assert_called_once_with("projets/Cadran.json"); ui_mocks.showinfo.assert_not_called()


def test_charger_projet_en_erreur_conserve_message_derreur(ui_mocks):
    interface = SimpleNamespace(cheminProjetCourant=None, dossiers={"projets": "projets"}, appliquerEtat=Mock(), mettreAJourTitreFenetre=Mock(), memoriserDernierProjet=Mock())
    ui_mocks.askopenfilename.return_value = "projets/invalide.json"
    with patch("src.interface_tk.chargerProjetJsonV1", side_effect=ValueError("JSON invalide")): InterfaceCarte.actionChargerProjet(interface)
    ui_mocks.showerror.assert_called_once_with("Erreur chargement", "Erreur lors du chargement :\nJSON invalide"); ui_mocks.showinfo.assert_not_called(); interface.memoriserDernierProjet.assert_not_called()


def test_annulation_chargement_neffectue_aucun_changement(ui_mocks):
    interface = SimpleNamespace(cheminProjetCourant="projets/precedent.json", dossiers={"projets": "projets"}); ui_mocks.askopenfilename.return_value = ""
    with patch("src.interface_tk.chargerProjetJsonV1") as loader: InterfaceCarte.actionChargerProjet(interface)
    loader.assert_not_called(); assert interface.cheminProjetCourant == "projets/precedent.json"


def test_sauvegarder_ecrit_json_sans_dialogue_ni_confirmation(ui_mocks):
    interface = SimpleNamespace(moteurAlgo=object(), layerManager=object(), cheminProjetCourant="projets/projet.json")
    with patch("src.interface_tk.sauvegarderProjetJsonV1") as writer: InterfaceCarte.actionSauvegarder(interface)
    writer.assert_called_once_with("projets/projet.json", interface.moteurAlgo, interface.layerManager); ui_mocks.asksaveasfilename.assert_not_called(); ui_mocks.showinfo.assert_not_called()


def test_sauvegarder_sans_chemin_delegate_vers_sauvegarder_sous():
    interface = SimpleNamespace(cheminProjetCourant=None, actionSauvegarderProjet=Mock()); InterfaceCarte.actionSauvegarder(interface)
    interface.actionSauvegarderProjet.assert_called_once_with()


def test_sauvegarder_sous_propose_et_ecrit_json_sans_confirmation(ui_mocks):
    interface = SimpleNamespace(moteurAlgo=object(), layerManager=object(), cheminProjetCourant=None, dossiers={"projets": "projets"}, mettreAJourTitreFenetre=Mock(), _setup_menu=Mock(), memoriserDernierProjet=Mock())
    ui_mocks.asksaveasfilename.return_value = "projets/nouveau.json"
    with patch("src.interface_tk.sauvegarderProjetJsonV1") as writer: InterfaceCarte.actionSauvegarderProjet(interface)
    ui_mocks.asksaveasfilename.assert_called_once_with(initialdir="projets", defaultextension=".json", filetypes=[("Projet JSON", "*.json")], title="Sauvegarder le projet", initialfile="projet_object.json")
    writer.assert_called_once_with("projets/nouveau.json", interface.moteurAlgo, interface.layerManager); assert interface.cheminProjetCourant == "projets/nouveau.json"; interface.memoriserDernierProjet.assert_called_once_with("projets/nouveau.json"); ui_mocks.showinfo.assert_not_called()


def test_memoriser_dernier_projet_ecrit_la_preference_globale():
    cfg = SimpleNamespace(set=Mock(), save=Mock()); InterfaceCarte.memoriserDernierProjet(SimpleNamespace(cfg=cfg), "C:/projets/Cadran.json")
    cfg.set.assert_called_once_with("Application", "last_project_path", "C:/projets/Cadran.json"); cfg.save.assert_called_once_with()


def test_demarrage_sans_dernier_projet_cree_un_projet_neuf():
    layer, moteur = object(), object(); interface = SimpleNamespace(cfg=SimpleNamespace(get=Mock(return_value="")), cheminProjetCourant=None)
    with patch("src.interface_tk.LayerManager", return_value=layer), patch("src.interface_tk.AlgorithmeSegment", return_value=moteur) as constructeur, patch("src.interface_tk.chargerProjetJsonV1") as loader: est_nouveau = InterfaceCarte.initialiserEtatProjetDemarrage(interface)
    assert est_nouveau is True; assert interface.layerManager is layer; assert interface.moteurAlgo is moteur; constructeur.assert_called_once_with(layer); loader.assert_not_called()


def test_demarrage_avec_dernier_projet_valide_charge_directement(ui_mocks):
    moteur, layers = object(), object(); chemin = "C:/projets/Cadran.json"; interface = SimpleNamespace(cfg=SimpleNamespace(get=Mock(return_value=chemin)), cheminProjetCourant=None)
    with patch("src.interface_tk.os.path.isfile", return_value=True), patch("src.interface_tk.chargerProjetJsonV1", return_value=(moteur, layers)) as loader, patch("src.interface_tk.AlgorithmeSegment") as constructeur: est_nouveau = InterfaceCarte.initialiserEtatProjetDemarrage(interface)
    assert est_nouveau is False; assert interface.moteurAlgo is moteur; assert interface.layerManager is layers; assert interface.cheminProjetCourant == chemin; loader.assert_called_once_with(chemin); constructeur.assert_not_called(); ui_mocks.showinfo.assert_not_called()


def test_demarrage_avec_dernier_projet_absent_repart_sur_un_projet_neuf_sans_popup(ui_mocks):
    layer, moteur = object(), object(); interface = SimpleNamespace(cfg=SimpleNamespace(get=Mock(return_value="C:/projets/absent.json")), cheminProjetCourant=None)
    with patch("src.interface_tk.os.path.isfile", return_value=False), patch("src.interface_tk.LayerManager", return_value=layer), patch("src.interface_tk.AlgorithmeSegment", return_value=moteur), patch("src.interface_tk.chargerProjetJsonV1") as loader: est_nouveau = InterfaceCarte.initialiserEtatProjetDemarrage(interface)
    assert est_nouveau is True; assert interface.moteurAlgo is moteur; loader.assert_not_called(); ui_mocks.showerror.assert_not_called(); ui_mocks.showinfo.assert_not_called()


def test_demarrage_avec_dernier_projet_invalide_affiche_lerreur_et_repart_sur_un_projet_neuf(ui_mocks):
    layer, moteur = object(), object(); cfg = SimpleNamespace(get=Mock(return_value="C:/projets/invalide.json"), set=Mock(), save=Mock()); interface = SimpleNamespace(cfg=cfg, cheminProjetCourant=None)
    with patch("src.interface_tk.os.path.isfile", return_value=True), patch("src.interface_tk.chargerProjetJsonV1", side_effect=ValueError("JSON invalide")), patch("src.interface_tk.LayerManager", return_value=layer), patch("src.interface_tk.AlgorithmeSegment", return_value=moteur): est_nouveau = InterfaceCarte.initialiserEtatProjetDemarrage(interface)
    assert est_nouveau is True; assert interface.moteurAlgo is moteur; ui_mocks.showerror.assert_called_once_with("Erreur chargement", "Erreur lors du chargement :\nJSON invalide"); cfg.set.assert_not_called(); cfg.save.assert_not_called()


def test_nouveau_projet_reinitialise_le_chemin():
    moteur, layer = object(), object(); interface = SimpleNamespace(cheminProjetCourant="projets/projet.json", appliquerEtat=Mock(), mettreAJourTitreFenetre=Mock())
    with patch("src.interface_tk.LayerManager", return_value=layer): InterfaceCarte.actionNouveauProjet(interface, Mock(return_value=moteur))
    assert interface.cheminProjetCourant is None


def test_actions_transitoires_ont_ete_supprimees():
    assert not hasattr(InterfaceCarte, "actionChargerProjetJsonV1")
    assert not hasattr(InterfaceCarte, "actionSauvegarderProjetJsonV1")
    assert not hasattr(InterfaceCarte, "actionExporterProjetJsonV1")
