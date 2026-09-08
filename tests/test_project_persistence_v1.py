import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.AlgorithmeManager import TypeScenario
from src.AlgorithmeSegment import AlgorithmeSegment, PlaneteAnnee
from src.AlgorithmeStyletInitial import AlgorithmeStyletInitial
from src.calculAstronomique import MyJulianDate
from src.IHMAlgorithme import IHMAlgorithme
from src.ListeSegmentsDataSet import ListeSegmentsDataSet
from src.layerManager import LayerManager
from src.ProjectPersistence import (
    FORMAT_PROJET,
    SCHEMA_VERSION,
    chargerProjetJsonV1,
    construireSnapshotProjetJsonV1,
    lireMetaDonneesProjetJsonV1,
    sauvegarderProjetJsonV1,
)
from src.interface_tk import InterfaceCarte


class ProjectPersistenceV1Tests(unittest.TestCase):
    def setUp(self):
        self.layer_manager = LayerManager()
        self.moteur = AlgorithmeStyletInitial(self.layer_manager)
        self.default = self.moteur.getScenario()

    def test_snapshot_exclut_automatiques_et_conserve_preferences(self):
        utilisateur = self.moteur.creerScenarioUtilisateur("Mon scenario", self.default, self.layer_manager)
        utilisateur.setSolution(True)
        layer = self.layer_manager.getLayer(utilisateur.getDescriptionLisible(), segment=utilisateur.segment)
        layer.setCouleur((12, 34, 56))
        layer.setEpaisseur(4)
        layer.setVisible(False)
        self.moteur.creerScenarioUnitaireAutomatique(
            "Temporaire", [("planete", "nom", "P", "Neptune")], self.default, self.layer_manager,
        )

        snapshot = construireSnapshotProjetJsonV1(self.moteur, self.layer_manager)

        self.assertEqual(snapshot["format"], FORMAT_PROJET)
        self.assertEqual(snapshot["schema_version"], SCHEMA_VERSION)
        self.assertEqual(snapshot["algorithm"], "AlgorithmeStyletInitial")
        scenarios = snapshot["segments"][0]["scenarios"]
        self.assertEqual({scenario["type"] for scenario in scenarios}, {"default", "utilisateur"})
        scenario_utilisateur = next(scenario for scenario in scenarios if scenario["name"] == "Mon scenario")
        self.assertTrue(scenario_utilisateur["solution"])
        self.assertEqual(scenario_utilisateur["layer_preferences"], {
            "color": [12, 34, 56], "thickness": 4, "visible": False,
        })

    def test_csv_definit_les_parametres_persistants(self):
        contenu_csv = (
            "Section,Categorie,Ligne,Widget,FieldType,Alignement,Label,ShortLabel,Hauteur,Type,Style,Module,Attribut\n"
            "Test,Global,1,checkbox,shorttext,left,Sens,S,1,input,std,planete,sensCarte\n"
            "Test,Global,2,checkbox,shorttext,left,Octave,O,1,data,std,stylet,octave\n"
        )
        with tempfile.TemporaryDirectory() as dossier:
            chemin_csv = Path(dossier) / "contrat.csv"
            chemin_csv.write_text(contenu_csv, encoding="utf-8")
            snapshot = construireSnapshotProjetJsonV1(self.moteur, self.layer_manager, chemin_csv)

        parameters = snapshot["segments"][0]["scenarios"][0]["parameters"]
        self.assertEqual(parameters["planete"]["sensCarte"], "Endroit")
        self.assertNotIn("stylet", parameters)


class ProjectPersistenceV1LoaderTests(unittest.TestCase):
    def setUp(self):
        self.layer_manager = LayerManager()
        self.moteur = AlgorithmeStyletInitial(self.layer_manager)

    def _charger_snapshot(self, snapshot):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "projet.json"
            chemin.write_text(json.dumps(snapshot), encoding="utf-8")
            return chargerProjetJsonV1(chemin)

    def test_roundtrip_restaure_scenarios_et_etat(self):
        default = self.moteur.getScenario()
        utilisateur = self.moteur.creerScenarioUtilisateur("Mon scenario", default, self.layer_manager)
        utilisateur.modules["planete"].nom = "Mars"
        utilisateur.setSolution(True)
        self.moteur.scenario_actif = utilisateur.nom
        snapshot = construireSnapshotProjetJsonV1(self.moteur, self.layer_manager)

        moteur_charge, layers_charges = self._charger_snapshot(snapshot)

        self.assertEqual(construireSnapshotProjetJsonV1(moteur_charge, layers_charges), snapshot)

    def test_dataset_snapshot_conserve_ordre_sans_lire_csv(self):
        snapshot = construireSnapshotProjetJsonV1(self.moteur, self.layer_manager)
        snapshot["dataset"]["events"].reverse()
        with patch.object(ListeSegmentsDataSet, "__init__", side_effect=AssertionError("CSV interdit")):
            moteur_charge, _ = self._charger_snapshot(snapshot)

        self.assertEqual(list(moteur_charge.dataset.evenements), [event["event"] for event in snapshot["dataset"]["events"]])

    def test_entete_invalide_est_refuse(self):
        snapshot = construireSnapshotProjetJsonV1(self.moteur, self.layer_manager)
        snapshot["algorithm"] = "AlgorithmeInconnu"
        with self.assertRaisesRegex(ValueError, "Algorithme JSON non support"):
            self._charger_snapshot(snapshot)

    def test_lecture_metadonnees_ne_reconstruit_pas_le_projet(self):
        snapshot = construireSnapshotProjetJsonV1(self.moteur, self.layer_manager)
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "projet.json"
            chemin.write_text(json.dumps(snapshot), encoding="utf-8")
            with patch("src.ProjectPersistence.chargerProjetJsonV1") as loader:
                metadata = lireMetaDonneesProjetJsonV1(chemin)

        loader.assert_not_called()
        self.assertEqual(metadata["algorithm"], "AlgorithmeStyletInitial")


class ProjectPersistenceV1CacheTests(unittest.TestCase):
    def setUp(self):
        self.layer_manager = LayerManager()
        self.moteur = AlgorithmeSegment(self.layer_manager)
        self.scenario = self.moteur.getScenario()
        self.cache = self.scenario.modules["annee"]
        self.cache.listeAnnees = [
            (1214, MyJulianDate.fromString("12/10/1365"), "Identique", "12.34°", "56.78°", "0.12°"),
        ]
        self.cache.listeAnneesSelection = 3

    def _charger_snapshot(self, snapshot):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "segment.json"
            chemin.write_text(json.dumps(snapshot), encoding="utf-8")
            return chargerProjetJsonV1(chemin)

    def test_cache_csv_est_snapshotte_hors_parameters(self):
        snapshot = construireSnapshotProjetJsonV1(self.moteur, self.layer_manager)
        scenario_json = snapshot["segments"][0]["scenarios"][0]

        self.assertNotIn("listeAnnees", scenario_json["parameters"].get("annee", {}))
        self.assertEqual(scenario_json["parameters"]["annee"]["listeAnneesSelection"], 3)
        resultat = scenario_json["cached_results"]["annee"]["listeAnnees"]
        self.assertIsInstance(resultat[0], list)
        self.assertEqual(resultat[0][1]["__persist_type__"], "MyJulianDate")

    def test_roundtrip_restaure_cache_sans_calcul_lourd(self):
        snapshot = construireSnapshotProjetJsonV1(self.moteur, self.layer_manager)
        with patch.object(PlaneteAnnee, "calculerAnnees", side_effect=AssertionError("calcul lourd interdit")) as calcul:
            moteur_charge, _ = self._charger_snapshot(snapshot)

        calcul.assert_not_called()
        liste_chargee = moteur_charge.getScenario().modules["annee"].listeAnnees
        self.assertEqual(liste_chargee[0][0], 1214)
        self.assertEqual(liste_chargee[0][1], MyJulianDate.fromString("12/10/1365"))
        self.assertIsInstance(liste_chargee[0], list)
        self.assertEqual(moteur_charge.getScenario().modules["annee"].listeAnneesSelection, 3)

    def test_ancien_json_sans_cache_reste_chargeable(self):
        snapshot = construireSnapshotProjetJsonV1(self.moteur, self.layer_manager)
        for bloc in snapshot["segments"]:
            for scenario in bloc["scenarios"]:
                del scenario["cached_results"]

        moteur_charge, _ = self._charger_snapshot(snapshot)

        self.assertEqual(moteur_charge.getScenario().modules["annee"].listeAnnees, [])

    def test_cache_module_ou_attribut_inconnu_est_refuse(self):
        snapshot = construireSnapshotProjetJsonV1(self.moteur, self.layer_manager)
        scenario_json = snapshot["segments"][0]["scenarios"][0]
        scenario_json["cached_results"] = {"inconnu": {"liste": []}}
        with self.assertRaisesRegex(ValueError, "inconnu"):
            self._charger_snapshot(snapshot)

        snapshot = construireSnapshotProjetJsonV1(self.moteur, self.layer_manager)
        scenario_json = snapshot["segments"][0]["scenarios"][0]
        scenario_json["cached_results"] = {"annee": {"inconnu": []}}
        with self.assertRaisesRegex(ValueError, "annee.inconnu"):
            self._charger_snapshot(snapshot)

    def test_recalcul_reinitialise_la_selection(self):
        self.cache.calculerAnnees(init=True)

        self.assertEqual(self.cache.listeAnnees, [])
        self.assertIsNone(self.cache.listeAnneesSelection)

    def test_ecriture_selection_sans_recalcul(self):
        with patch.object(self.moteur, "calculerModules") as calcul:
            self.moteur.setParametreSansRecalcul("annee", "listeAnneesSelection", 0)

        self.assertEqual(self.cache.listeAnneesSelection, 0)
        calcul.assert_not_called()


class TableSelectionCsvTests(unittest.TestCase):
    def setUp(self):
        self.layer_manager = LayerManager()
        self.moteur = AlgorithmeSegment(self.layer_manager)

    def _parser_sans_tk(self):
        ihm = IHMAlgorithme.__new__(IHMAlgorithme)
        ihm.moteurAlgo = self.moteur
        ihm.attributsModulesAffichés = []
        return ihm

    def test_widget_none_et_liaison_tableselection_sont_valides(self):
        ihm = self._parser_sans_tk()
        lignes = ihm.parser_csv("config/AlgorithmeSegment.csv")
        ihm.parametres_csv = lignes

        selection = next(ligne for ligne in lignes if ligne["Attribut"] == "listeAnneesSelection")
        self.assertEqual(selection["Widget"], "None")
        self.assertEqual(selection["FieldType"], "tableselection")
        self.assertEqual(ihm.getAttributSelectionTable("annee", "listeAnnees"), "listeAnneesSelection")

    def test_tableselection_invalide_est_refuse(self):
        contenu = (
            "Section,Categorie,Ligne,Widget,FieldType,Alignement,Label,ShortLabel,Hauteur,Type,Style,Module,Attribut\n"
            "Test,Global,1,None,tableselection,left,,,1,input,std,annee,listeAnnees\n"
        )
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "invalide.csv"
            chemin.write_text(contenu, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "doit finir par 'Selection'"):
                self._parser_sans_tk().parser_csv(chemin)

    def test_table_associee_absente_ou_non_table_est_refusee(self):
        entete = (
            "Section,Categorie,Ligne,Widget,FieldType,Alignement,Label,ShortLabel,Hauteur,Type,Style,Module,Attribut\n"
        )
        cas = (
            ("Recherche,Global,1,None,tableselection,left,,,1,input,std,annee,listeAnneesSelection\n", "introuvable"),
            (
                "Recherche,Global,1,field,shorttext,left,,,1,data,std,annee,listeAnnees\n"
                "Recherche,Global,2,None,tableselection,left,,,1,input,std,annee,listeAnneesSelection\n",
                "Widget=list",
            ),
        )
        for contenu, message in cas:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as dossier:
                chemin = Path(dossier) / "invalide.csv"
                chemin.write_text(entete + contenu, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    self._parser_sans_tk().parser_csv(chemin)


class TableSelectionRestorationTests(unittest.TestCase):
    class FauxTable:
        def __init__(self):
            self.selection_courante = ()
            self._restauration_selection = False

        def get_children(self):
            return tuple(f"item-{index}" for index in range(6))

        def selection_set(self, item):
            self.selection_courante = (item,)

        def selection_remove(self, _items):
            self.selection_courante = ()

        def selection(self):
            return self.selection_courante

        def focus(self, _item):
            pass

        def see(self, _item):
            pass

    def test_selection_est_restauree_par_scenario(self):
        layer_manager = LayerManager()
        moteur = AlgorithmeSegment(layer_manager)
        scenario_a = moteur.getScenario()
        scenario_a.modules["annee"].listeAnneesSelection = 2
        scenario_b = moteur.creerScenarioUtilisateur("B", scenario_a, layer_manager)
        scenario_b.modules["annee"].listeAnneesSelection = 5
        ihm = IHMAlgorithme.__new__(IHMAlgorithme)
        ihm.moteurAlgo = moteur
        table = self.FauxTable()

        ihm.restaurerSelectionTable(table, "annee", "listeAnneesSelection")
        self.assertEqual(table.selection(), ("item-2",))
        moteur.appliquerScenario("B")
        ihm.restaurerSelectionTable(table, "annee", "listeAnneesSelection")
        self.assertEqual(table.selection(), ("item-5",))
        scenario_b.modules["annee"].listeAnneesSelection = None
        ihm.restaurerSelectionTable(table, "annee", "listeAnneesSelection")
        self.assertEqual(table.selection(), ())


class ProjectPersistenceV1UiTests(unittest.TestCase):
    def setUp(self):
        self.patcher_showinfo = patch("src.interface_tk.messagebox.showinfo")
        self.patcher_showerror = patch("src.interface_tk.messagebox.showerror")
        self.patcher_askyesno = patch("src.interface_tk.messagebox.askyesno")
        self.patcher_askopenfilename = patch("src.interface_tk.filedialog.askopenfilename")
        self.patcher_asksaveasfilename = patch("src.interface_tk.filedialog.asksaveasfilename")
        self.mock_showinfo = self.patcher_showinfo.start()
        self.mock_showerror = self.patcher_showerror.start()
        self.mock_askyesno = self.patcher_askyesno.start()
        self.mock_askopenfilename = self.patcher_askopenfilename.start()
        self.mock_asksaveasfilename = self.patcher_asksaveasfilename.start()
        self.addCleanup(self.patcher_asksaveasfilename.stop)
        self.addCleanup(self.patcher_askopenfilename.stop)
        self.addCleanup(self.patcher_askyesno.stop)
        self.addCleanup(self.patcher_showerror.stop)
        self.addCleanup(self.patcher_showinfo.stop)

    def test_charger_projet_charge_json_et_met_a_jour_chemin(self):
        moteur, layers = object(), object()
        interface = SimpleNamespace(
            cheminProjetCourant=None,
            dossiers={"projets": "projets"},
            appliquerEtat=Mock(),
            mettreAJourTitreFenetre=Mock(),
            memoriserDernierProjet=Mock(),
        )
        self.mock_askopenfilename.return_value = "projets/Cadran.json"
        with patch("src.interface_tk.chargerProjetJsonV1", return_value=(moteur, layers)) as loader:
            InterfaceCarte.actionChargerProjet(interface)

        self.mock_askopenfilename.assert_called_once_with(
            initialdir="projets", filetypes=[("Projet JSON", "*.json")], title="Charger un projet",
        )
        loader.assert_called_once_with("projets/Cadran.json")
        interface.appliquerEtat.assert_called_once_with(layers, moteur)
        self.assertEqual(interface.cheminProjetCourant, "projets/Cadran.json")
        interface.memoriserDernierProjet.assert_called_once_with("projets/Cadran.json")
        self.mock_showinfo.assert_not_called()

    def test_charger_projet_en_erreur_conserve_message_derreur(self):
        interface = SimpleNamespace(
            cheminProjetCourant=None,
            dossiers={"projets": "projets"},
            appliquerEtat=Mock(),
            mettreAJourTitreFenetre=Mock(),
            memoriserDernierProjet=Mock(),
        )
        self.mock_askopenfilename.return_value = "projets/invalide.json"
        with patch("src.interface_tk.chargerProjetJsonV1", side_effect=ValueError("JSON invalide")):
            InterfaceCarte.actionChargerProjet(interface)

        self.mock_showerror.assert_called_once_with("Erreur chargement", "Erreur lors du chargement :\nJSON invalide")
        self.mock_showinfo.assert_not_called()
        interface.memoriserDernierProjet.assert_not_called()

    def test_annulation_chargement_neffectue_aucun_changement(self):
        interface = SimpleNamespace(cheminProjetCourant="projets/precedent.json", dossiers={"projets": "projets"})
        self.mock_askopenfilename.return_value = ""
        with patch("src.interface_tk.chargerProjetJsonV1") as loader:
            InterfaceCarte.actionChargerProjet(interface)

        loader.assert_not_called()
        self.assertEqual(interface.cheminProjetCourant, "projets/precedent.json")

    def test_sauvegarder_ecrit_json_sans_dialogue_ni_confirmation(self):
        interface = SimpleNamespace(
            moteurAlgo=object(), layerManager=object(), cheminProjetCourant="projets/projet.json",
        )
        with patch("src.interface_tk.sauvegarderProjetJsonV1") as writer:
            InterfaceCarte.actionSauvegarder(interface)

        writer.assert_called_once_with("projets/projet.json", interface.moteurAlgo, interface.layerManager)
        self.mock_asksaveasfilename.assert_not_called()
        self.mock_showinfo.assert_not_called()

    def test_sauvegarder_sans_chemin_delegate_vers_sauvegarder_sous(self):
        interface = SimpleNamespace(cheminProjetCourant=None, actionSauvegarderProjet=Mock())
        InterfaceCarte.actionSauvegarder(interface)
        interface.actionSauvegarderProjet.assert_called_once_with()

    def test_sauvegarder_sous_propose_et_ecrit_json_sans_confirmation(self):
        interface = SimpleNamespace(
            moteurAlgo=object(), layerManager=object(), cheminProjetCourant=None,
            dossiers={"projets": "projets"}, mettreAJourTitreFenetre=Mock(), _setup_menu=Mock(),
            memoriserDernierProjet=Mock(),
        )
        self.mock_asksaveasfilename.return_value = "projets/nouveau.json"
        with patch("src.interface_tk.sauvegarderProjetJsonV1") as writer:
            InterfaceCarte.actionSauvegarderProjet(interface)

        self.mock_asksaveasfilename.assert_called_once_with(
            initialdir="projets", defaultextension=".json", filetypes=[("Projet JSON", "*.json")],
            title="Sauvegarder le projet", initialfile="projet_object.json",
        )
        writer.assert_called_once_with("projets/nouveau.json", interface.moteurAlgo, interface.layerManager)
        self.assertEqual(interface.cheminProjetCourant, "projets/nouveau.json")
        interface.memoriserDernierProjet.assert_called_once_with("projets/nouveau.json")
        self.mock_showinfo.assert_not_called()

    def test_memoriser_dernier_projet_ecrit_la_preference_globale(self):
        cfg = SimpleNamespace(set=Mock(), save=Mock())
        interface = SimpleNamespace(cfg=cfg)

        InterfaceCarte.memoriserDernierProjet(interface, "C:/projets/Cadran.json")

        cfg.set.assert_called_once_with("Application", "last_project_path", "C:/projets/Cadran.json")
        cfg.save.assert_called_once_with()

    def test_demarrage_sans_dernier_projet_cree_un_projet_neuf(self):
        layer, moteur = object(), object()
        interface = SimpleNamespace(
            cfg=SimpleNamespace(get=Mock(return_value="")), cheminProjetCourant=None,
        )
        with (
            patch("src.interface_tk.LayerManager", return_value=layer),
            patch("src.interface_tk.AlgorithmeSegment", return_value=moteur) as constructeur,
            patch("src.interface_tk.chargerProjetJsonV1") as loader,
        ):
            est_nouveau = InterfaceCarte.initialiserEtatProjetDemarrage(interface)

        self.assertTrue(est_nouveau)
        self.assertIs(interface.layerManager, layer)
        self.assertIs(interface.moteurAlgo, moteur)
        constructeur.assert_called_once_with(layer)
        loader.assert_not_called()

    def test_demarrage_avec_dernier_projet_valide_charge_directement(self):
        moteur, layers = object(), object()
        chemin = "C:/projets/Cadran.json"
        interface = SimpleNamespace(
            cfg=SimpleNamespace(get=Mock(return_value=chemin)), cheminProjetCourant=None,
        )
        with (
            patch("src.interface_tk.os.path.isfile", return_value=True),
            patch("src.interface_tk.chargerProjetJsonV1", return_value=(moteur, layers)) as loader,
            patch("src.interface_tk.AlgorithmeSegment") as constructeur,
        ):
            est_nouveau = InterfaceCarte.initialiserEtatProjetDemarrage(interface)

        self.assertFalse(est_nouveau)
        self.assertIs(interface.moteurAlgo, moteur)
        self.assertIs(interface.layerManager, layers)
        self.assertEqual(interface.cheminProjetCourant, chemin)
        loader.assert_called_once_with(chemin)
        constructeur.assert_not_called()
        self.mock_showinfo.assert_not_called()

    def test_demarrage_avec_dernier_projet_absent_repart_sur_un_projet_neuf_sans_popup(self):
        layer, moteur = object(), object()
        interface = SimpleNamespace(
            cfg=SimpleNamespace(get=Mock(return_value="C:/projets/absent.json")), cheminProjetCourant=None,
        )
        with (
            patch("src.interface_tk.os.path.isfile", return_value=False),
            patch("src.interface_tk.LayerManager", return_value=layer),
            patch("src.interface_tk.AlgorithmeSegment", return_value=moteur),
            patch("src.interface_tk.chargerProjetJsonV1") as loader,
        ):
            est_nouveau = InterfaceCarte.initialiserEtatProjetDemarrage(interface)

        self.assertTrue(est_nouveau)
        self.assertIs(interface.moteurAlgo, moteur)
        loader.assert_not_called()
        self.mock_showerror.assert_not_called()
        self.mock_showinfo.assert_not_called()

    def test_demarrage_avec_dernier_projet_invalide_affiche_lerreur_et_repart_sur_un_projet_neuf(self):
        layer, moteur = object(), object()
        cfg = SimpleNamespace(get=Mock(return_value="C:/projets/invalide.json"), set=Mock(), save=Mock())
        interface = SimpleNamespace(cfg=cfg, cheminProjetCourant=None)
        with (
            patch("src.interface_tk.os.path.isfile", return_value=True),
            patch("src.interface_tk.chargerProjetJsonV1", side_effect=ValueError("JSON invalide")),
            patch("src.interface_tk.LayerManager", return_value=layer),
            patch("src.interface_tk.AlgorithmeSegment", return_value=moteur),
        ):
            est_nouveau = InterfaceCarte.initialiserEtatProjetDemarrage(interface)

        self.assertTrue(est_nouveau)
        self.assertIs(interface.moteurAlgo, moteur)
        self.mock_showerror.assert_called_once_with("Erreur chargement", "Erreur lors du chargement :\nJSON invalide")
        cfg.set.assert_not_called()
        cfg.save.assert_not_called()

    def test_nouveau_projet_reinitialise_le_chemin(self):
        moteur, layer = object(), object()
        interface = SimpleNamespace(
            cheminProjetCourant="projets/projet.json", appliquerEtat=Mock(), mettreAJourTitreFenetre=Mock(),
        )
        with patch("src.interface_tk.LayerManager", return_value=layer):
            InterfaceCarte.actionNouveauProjet(interface, Mock(return_value=moteur))

        self.assertIsNone(interface.cheminProjetCourant)

    def test_actions_transitoires_ont_ete_supprimees(self):
        self.assertFalse(hasattr(InterfaceCarte, "actionChargerProjetJsonV1"))
        self.assertFalse(hasattr(InterfaceCarte, "actionSauvegarderProjetJsonV1"))
        self.assertFalse(hasattr(InterfaceCarte, "actionExporterProjetJsonV1"))


if __name__ == "__main__":
    unittest.main()
