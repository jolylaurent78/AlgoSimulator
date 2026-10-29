"""Origine des ombres à 12:00 TML, indépendante de la date du segment."""
from pathlib import Path
from unittest.mock import Mock

import pytest

import src.AlgorithmeCadranFinal as final
from src.CadranNationalSentinelles import SentinelleNationale
from src.ReferentielSentinelles import ContexteObservation, HeureMoyenneLocale
from src.affichage_objets import PointGraphique
from src.calculAstronomique import positionSoleil
from src.data_loader import villes_dict


@pytest.fixture(scope="module")
def national():
    return SentinelleNationale()


def ombre_prete(national, sens="Endroit"):
    o = final.LigneHoraireFinal()
    o.sentinelleLumiere = national
    o.baseStylet = "Rocamadour"
    o.azimutMidiStylet = final.Ligne(*villes_dict[o.baseStylet].getCoordonneesPixel(),
                                   *villes_dict["Bourges"].getCoordonneesPixel()).azimut()
    o.dateDataset = "15/08/778"
    o.dateSegmentDataset = "25/07/778"
    o.lieuObservationSegment = "Roncevaux"
    o.lettreDomSegment = "G"
    o.lettreDeclDataset = "F"
    o.sensCarte = sens
    return o


@pytest.mark.parametrize("sens", ["Endroit", "Envers"])
def test_midi_tml_est_exactement_axe_base_bourges(national, sens):
    o = ombre_prete(national, sens)
    o.calculer()
    midi = next(r for r in o.lignesHorairesReference if r.note == "G" and r.ampm == "AM")
    assert midi.heure_locale.secondes == 43200
    assert midi.ecart_image == 0
    assert midi.ligne.azimut_deg == o.azimutMidiStylet
    assert PointGraphique(villes_dict["Bourges"]).distanceLigne(midi.ligne) < 1e-8
    assert PointGraphique(villes_dict[o.baseStylet]).distanceLigne(midi.ligne) < 1e-8
    assert len(o.listeCandidatsHeure) == 2
    assert not hasattr(o, "azimutMidiLocale")


def test_endroit_envers_reflechissent_tout_ecart_sans_changer_heures(national):
    endroit, envers = ombre_prete(national), ombre_prete(national, "Envers")
    endroit.calculer()
    envers.calculer()
    ctx = national.referentiel.contexte
    assert ctx.date == "15/08/1066"
    az_midi = positionSoleil(ctx.coordonnees, ctx.versUT1(HeureMoyenneLocale(43200)))[1]
    for a, b in zip(endroit.lignesHorairesReference, envers.lignesHorairesReference):
        direction = national.directionPourNote(a.note, a.ampm)
        assert a.heure_locale.secondes == b.heure_locale.secondes == direction.heure_locale.secondes
        assert (a.note, a.branche) == (b.note, b.branche)
        assert a.azimut_solaire == b.azimut_solaire == direction.azimut
        assert a.ecart_image == pytest.approx(direction.azimut - az_midi)
        assert b.ecart_image == -a.ecart_image
        assert a.ligne.azimut_deg + b.ligne.azimut_deg == pytest.approx(2 * endroit.azimutMidiStylet)


def test_ombres_nationales_ne_dependent_plus_du_contexte_historique(national, monkeypatch):
    o = ombre_prete(national)
    def interdit(*_):
        pytest.fail("Une ombre nationale ne calcule pas le Soleil à la date du segment")
    monkeypatch.setattr(final, "positionSoleil", interdit)
    o.calculer()
    angles = [r.ligne.azimut_deg for r in o.lignesHorairesReference]
    heures = [r.heure_locale.secondes for r in o.lignesHorairesReference]
    o.dateDataset = "20/03/1815"
    o.dateSegmentDataset = "28/05/1815"
    o.lieuObservationSegment = "Bourges"
    o.calculer()
    assert [r.ligne.azimut_deg for r in o.lignesHorairesReference] == angles
    assert [r.heure_locale.secondes for r in o.lignesHorairesReference] == heures
    assert o._dateMidiReferenceUT1 == float(national.referentiel.contexte.versUT1(HeureMoyenneLocale(43200)))


@pytest.mark.parametrize("sens", ["Endroit", "Envers"])
def test_lampouy_garde_reference_angulaire_et_contexte_historique(national, sens):
    o = ombre_prete(national, sens)
    o.dateDataset = "18/05/1152"
    o.dateSegmentDataset = "29/06/1152"
    o.choixHeure = national["L"]["HeureLocale"]
    o.calculer()
    ctx = ContexteObservation("Carnac", *villes_dict["Carnac"].getCoordonneesGPS(), "20/08/1152")
    midi = positionSoleil(ctx.coordonnees, ctx.versUT1(HeureMoyenneLocale(43200)))[1]
    assert o._azimutMidiLampouy == midi
    assert o._azimutMidiLampouy != o._azimutMidiReference
    lampouy = [r for r in o.lignesHorairesReference if r.note == "L"]
    assert len(o.lignesHorairesReference) == 18
    assert len(o.listeCandidatsHeure) == len(lampouy) == 2
    for r in lampouy:
        attendu = national["L"]["AzimutCalibre"]
        if r.ampm == "PM":
            attendu = 360 - attendu
        assert r.azimut_solaire == attendu
        assert r.heure_locale == national.heurePourNote("L", r.ampm)
        assert r.branche == "historique_" + r.ampm
        assert r.ecart_image == pytest.approx((attendu - midi) * (1 if sens == "Endroit" else -1))


def test_interface_supprime_uniquement_azimut_midi_local():
    from src.IHMAlgorithme import IHMAlgorithme
    ihm = IHMAlgorithme.__new__(IHMAlgorithme)
    ihm.moteurAlgo = Mock()
    ihm.attributsModulesAffichés = []
    lignes = ihm.parser_csv("config/AlgorithmeCadranFinal.csv")
    ombres = [r for r in lignes if r.get("Module") == "ombre"]
    assert {r["Attribut"] for r in ombres} == {"choixCalendrier", "lettreChoix", "choixHeure", "heureLocale", "sensCarte"}
    assert all(r.get("Label") != "Az Midi local" for r in lignes)
    assert all(attr != "azimutMidiLocale" for _, attr, *_ in ihm.attributsModulesAffichés)


def test_fixture_778_candidat_verifie_par_triplet_geometrique():
    from src.ProjectPersistence import chargerProjetJsonV1
    from src.affichage_objets import CercleGraphique, LigneAzimut
    fichier = Path(__file__).parent / "fixtures/cadran_final_roncevaux_lac_tremelin_reference.json"
    m, _ = chargerProjetJsonV1(fichier)
    modules = m.getScenario().modules
    c = modules["candidat"]
    produit = c.construireRepresentationCarte()
    assert len(produit) == 2
    centres = [p.pointCentre for p in produit]
    cercle = CercleGraphique(villes_dict["Bourges"], c.distanceLumiere)
    triplets_valides = []
    milieux_valides = []
    for signe in (-1, 1):
        lumiere = LigneAzimut(villes_dict["Bourges"], c.azimutMidiStylet + signe * (180 - c.azimutLumiere))
        for _, heure in c.listeCandidatsHeureOmbre:
            xy = heure.intersectionLigne(lumiere)
            p3 = PointGraphique("intersection", *xy) if xy is not None else None
            if p3 is not None and not p3.estVisibledansImage():
                p3 = None
            for p1 in lumiere.intersectionCercle(cercle):
                for p2 in heure.intersectionCercle(cercle):
                    triplet_valide = False
                    if p3 is not None:
                        coords = [p.coordonneesLambert() for p in (p1, p2, p3)]
                        bary = PointGraphique("barycentre", *(sum(p[i] for p in coords) / 3 for i in (0, 1)))
                        triplet_valide = all(p.distance(bary) <= 20 for p in (p1, p2, p3))
                        if triplet_valide:
                            triplets_valides.append(bary)
                    if not triplet_valide and p1.distance(p2) <= 40:
                        assert p1.distance(p2) > 10  # Ce milieu n'était pas admissible auparavant.
                        coords = [p.coordonneesLambert() for p in (p1, p2)]
                        milieu = PointGraphique("milieu", *(sum(p[i] for p in coords) / 2 for i in (0, 1)))
                        assert all(p.distance(milieu) <= 20 for p in (p1, p2))
                        milieux_valides.append(milieu)
    assert len(triplets_valides) == len(milieux_valides) == 1
    assert triplets_valides[0].coordonneesLambert() == pytest.approx((319918.185, 6787297.401), abs=.001)
    for attendu in triplets_valides + milieux_valides:
        assert sum(attendu.distance(centre) < 1e-8 for centre in centres) == 1
