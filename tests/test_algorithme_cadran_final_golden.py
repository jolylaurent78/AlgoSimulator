from pathlib import Path

import pytest

from src.ProjectPersistence import chargerProjetJsonV1
from src.carte_config import carteConfig
from src.map_print import PrintViewport, compute_print_label_placements
from src.ReferentielSentinelles import ContexteObservation, HeureMoyenneLocale
from src.calculAstronomique import positionSoleil
from src.data_loader import villes_dict


pytestmark = [
    pytest.mark.slow,
    pytest.mark.integration,
]


FIXTURE_LAC_TREMELIN = Path(__file__).parent / "fixtures" / "cadran_final_roncevaux_lac_tremelin_reference.json"
SEGMENT_RONCEVAUX = "15 Aout 778 : Bataille de Roncevaux"


def test_chargement_golden_lac_tremelin_restitue_le_pipeline_cadran_final_reel():
    moteur, _ = chargerProjetJsonV1(FIXTURE_LAC_TREMELIN)
    scenario = moteur.getScenario()
    modules = scenario.modules

    assert moteur.segment_actif == SEGMENT_RONCEVAUX
    assert moteur.scenario_actif == "Lac Trémelin"
    assert set(modules) == {"segment", "stylet", "lumiere", "styletlumiere", "ombre", "candidat"}

    segment = modules["segment"]
    assert (segment.dateDataset, segment.lettreDom, segment.lieuObservation) == ("15/08/778", "C", "Roncevaux")

    stylet = modules["stylet"]
    assert (
        stylet.styletDataset,
        stylet.base1Dataset,
        stylet.base2Dataset,
        stylet.choixBase,
        stylet.base,
        stylet.choixCalendrier,
        stylet.lettreChoix,
        stylet.P2M2,
        stylet.lettre,
        stylet.octave,
    ) == ("Roncevaux", "Saint-Amour", "Rocamadour", "Base 2", "Rocamadour", "Standard", "C", "+2", "E", "/4")
    assert stylet.distanceRef == pytest.approx(891.2, abs=0.1)
    assert stylet.hauteur == pytest.approx(250.1, abs=0.1)
    assert stylet.azimutMidi == pytest.approx(13.56, abs=0.01)

    lumiere = modules["lumiere"]
    assert (
        lumiere.choixCalendrier,
        lumiere.lettreChoix,
        lumiere.choixHeure,
        lumiere.heureAMPM,
        lumiere.dateSegmentDataset,
        lumiere.heureLocale,
        lumiere.heureUTC,
    ) == ("Standard", "C", "+2", "PM", "25/07/778", "15:59:05", "16:04:23")
    # S3 PM est directe, sans seconde réflexion ; dateSegment reste le 25 juillet.
    heure = lumiere.sentinelle.heurePourNote("E", "directe")
    lat, lon = villes_dict["Roncevaux"].getCoordonneesGPS()
    jd = ContexteObservation("Roncevaux", lat, lon, "25/07/778").versUT1(heure)
    hauteur, azimut = positionSoleil((lat, lon), jd)
    assert lumiere.brancheReference == "directe"
    assert lumiere.heureLocaleSecondes == heure.secondes
    assert lumiere.azimut == pytest.approx(azimut)
    assert lumiere.hauteur == pytest.approx(hauteur)
    assert lumiere.deltaMidi == pytest.approx(180 - azimut)
    from math import tan, radians
    assert lumiere.distance == pytest.approx(stylet.hauteur / tan(radians(hauteur)))
    assert lumiere.distance == pytest.approx(349.6940, abs=0.001)
    assert [objet.getPrintLabel() for objet in lumiere.construireRepresentationCarte()] == ["15:59:05"] * 2

    stylet_lumiere = modules["styletlumiere"]
    objets_stylet_lumiere = stylet_lumiere.construireRepresentationCarte()
    cercle_lumiere = next(objet for objet in objets_stylet_lumiere if objet.getNom() == "Cercle Lumiere")
    assert cercle_lumiere.getRayonKm() == pytest.approx(lumiere.distance)
    assert cercle_lumiere.getPrintLabel() == lumiere.heureLocale

    ombre = modules["ombre"]
    assert (
        ombre.choixCalendrier,
        ombre.lettreChoix,
        ombre.choixHeure,
        ombre.heureLocale,
        ombre.sensCarte,
    ) == ("Standard", "C", "=", "09:43:00", "Endroit")
    ctx_ref = lumiere.sentinelle.referentiel.contexte
    jd_midi = ctx_ref.versUT1(HeureMoyenneLocale(43200))
    assert ombre._dateMidiReferenceUT1 == float(jd_midi)
    assert ombre._azimutMidiReference == pytest.approx(positionSoleil(ctx_ref.coordonnees, jd_midi)[1])
    ligne_midi = next(r for r in ombre.lignesHorairesReference if r.note == "G" and r.ampm == "AM")
    assert ligne_midi.ecart_image == 0
    from src.affichage_objets import PointGraphique
    assert PointGraphique(villes_dict["Bourges"]).distanceLigne(ligne_midi.ligne) < 1e-8
    assert [heure for heure, _ in ombre.listeCandidatsHeure] == ["09:43:00", "14:21:11"]
    objets_ombre = ombre.construireRepresentationCarte()
    assert [objet.getPrintLabel() for objet in objets_ombre] == [f"{r.note} {r.branche} {r.heure_locale.toString()}" for r in ombre.lignesHorairesReference]
    assert all("AM" not in objet.getPrintLabel() and "PM" not in objet.getPrintLabel() for objet in objets_ombre)
    width, height = carteConfig.image_size
    placements = compute_print_label_placements(
        objets_stylet_lumiere + lumiere.construireRepresentationCarte() + objets_ombre,
        PrintViewport.full_map((width, height)),
        600,
        400,
    )
    assert {"15:59:05", "C directe 09:43:00"} <= {placement.text for placement in placements}
    assert all(len(placement.text.split()[-1]) == 8 for placement in placements)
    candidats = modules["candidat"].construireRepresentationCarte(methode="historique")
    assert len(candidats) == 2
    # Le nouveau milieu est ajouté ; l'ancien barycentre reste identique.
    assert candidats[0].pointCentre.coordonneesLambert() == pytest.approx((998466.407, 6605645.842), abs=.001)
    assert candidats[1].pointCentre.coordonneesLambert() == pytest.approx((319918.185, 6787297.401), abs=.001)
    assert all(c.getRayonKm() == 20 for c in candidats)
    assert scenario.solutionScenario is True
