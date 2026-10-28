"""Contrats temporels du lot 3, sans écriture des projets ni des fixtures."""
from dataclasses import replace
from math import radians, tan

import pytest

import src.AlgorithmeBaseCadran as base
import src.AlgorithmeCadranFinal as final
from src.CadranNationalSentinelles import SentinelleNationale
from src.ReferentielSentinelles import ContexteObservation, HeureMoyenneLocale
from src.calculAstronomique import MyJulianDate, decalageGamme, positionSoleil
from src.data_loader import villes_dict


@pytest.fixture(scope="module")
def references():
    return SentinelleNationale()


@pytest.fixture(autouse=True)
def partager_references(references, monkeypatch):
    monkeypatch.setattr(base, "Sentinelle", lambda *_: references)
    monkeypatch.setattr(final, "Sentinelle", lambda *_: references)


NOTES = tuple("CDEFGABJ")


def contexte(lieu, date):
    lat, lon = villes_dict[lieu].getCoordonneesGPS()
    return ContexteObservation(lieu, lat, lon, date)


def cercle_pret(references, note="C", ampm="AM"):
    module = base.CercleHoraire()
    module.sentinelle = references
    module.styletDataset = "Roncevaux"
    module.dateDataset = "15/08/778"
    module.lettreChoixSegment = note if note != "J" else "C"
    module.heureSubstitution = "11:00" if note == "J" else "="
    module.heureAMPM = ampm
    return module


def lumiere_prete(references, note="C", ampm="AM"):
    module = final.LumiereFinal()
    module.sentinelle = references
    module.dateDataset = "15/08/778"
    module.dateSegmentDataset = "25/07/778"
    module.lieuObservationSegment = "Roncevaux"
    module.lettreDomSegment = note if note != "J" else "C"
    module.lettreDeclDataset = "F"
    module.choixHeure = "11:00" if note == "J" else "="
    module.heureAMPM = ampm
    module.hauteurStylet = 250.1
    module.azimutMidiStylet = 13.56
    return module


def ombre_prete(references, note="C", sens="Endroit"):
    module = final.LigneHoraireFinal()
    module.sentinelleLumiere = references
    module.dateDataset = "15/08/778"
    module.dateSegmentDataset = "25/07/778"
    module.lieuObservationSegment = "Roncevaux"
    module.baseStylet = "Rocamadour"
    module.azimutMidiStylet = 13.56
    module.lettreDomSegment = note if note != "J" else "C"
    module.lettreDeclDataset = "F"
    module.choixHeure = "11:00" if note == "J" else "="
    module.sensCarte = sens
    return module


@pytest.mark.parametrize("note", NOTES)
@pytest.mark.parametrize("ampm", ["AM", "PM"])
def test_base_et_final_conservent_toutes_les_heures_exactes(references, note, ampm):
    direction = references.directionPourNote(note, ampm)
    heure = direction.heure_locale
    branche = "directe" if direction is references.par_note[note].directe else "miroir"
    if note in "EF":
        assert branche == ("miroir" if ampm == "AM" else "directe")
    h = cercle_pret(references, note, ampm)
    h.calculer()
    assert h.heureSentinelleSecondes == heure.secondes
    assert h.heureSentinelle == heure.toString()
    assert h.brancheReference == branche
    ctx = contexte("Carnac", "15/08/778")
    assert float(h.dateObservationUT1) == float(ctx.versUT1(heure))
    _, az = positionSoleil(ctx.coordonnees, ctx.versUT1(heure))
    assert h.angleHoraire == pytest.approx(180 - az)
    assert h.angleHoraire > 0 if ampm == "AM" else h.angleHoraire < 0
    # Le choix de côté géométrique reste indépendant de l'heure.
    premier = h.coordPointChoix
    h.cercleAMPM = "PM"
    h.calculer()
    assert h.coordPointChoix != premier
    assert h.angleHoraire == pytest.approx(180 - az)

    l = lumiere_prete(references, note, ampm)
    l.calculer()
    ctx = contexte("Roncevaux", "25/07/778")
    hauteur, azimut = positionSoleil(ctx.coordonnees, ctx.versUT1(heure))
    assert l.heureLocaleSecondes == heure.secondes
    assert l.brancheReference == branche
    assert float(l.dateObservationUT1) == float(ctx.versUT1(heure))
    assert l.hauteur == pytest.approx(hauteur)
    assert l.azimut == pytest.approx(azimut)
    assert l.distance == pytest.approx(l.hauteurStylet / tan(radians(hauteur)))
    assert len(l.construireRepresentationCarte()) == 2


@pytest.mark.parametrize("note", NOTES)
@pytest.mark.parametrize("sens", ["Endroit", "Envers"])
def test_lignes_finales_identite_branches_axe_image_et_candidats(references, note, sens):
    o = ombre_prete(references, note, sens)
    o.calculer()
    assert len(o.lignesHorairesReference) == 16
    assert len(o.listeCandidatsHeure) == 2
    midi = contexte("Carnac", "25/07/778")
    jd = midi.versUT1(HeureMoyenneLocale(43200))
    _, az = positionSoleil(midi.coordonnees, jd)
    assert float(o.dateMidiUT1) == float(jd)
    assert o.azimutMidiLocale == pytest.approx(az)
    assert az != pytest.approx(180)
    assert az != pytest.approx(125.371)
    correction = (180 - az) * (1 if sens == "Endroit" else -1)
    for r in o.lignesHorairesReference:
        d = references.directionPourNote(r.note, r.ampm)
        ref = references.par_note[r.note]
        assert r.branche == ("directe" if d is ref.directe else "miroir")
        assert r.heure_locale.secondes == d.heure_locale.secondes
        assert r.azimut_solaire == d.azimut
        assert r.ecart_image == pytest.approx(d.azimut - 180 + correction)
        assert r.ligne.azimut_deg == pytest.approx(o.azimutMidiStylet + r.ecart_image)
        assert r.candidat == (r.note == note)
    objets = o.construireRepresentationCarte()
    assert len(objets) == 16
    for r, obj in zip(o.lignesHorairesReference, objets):
        assert r.note in obj.getPrintLabel()
        assert r.branche in obj.getPrintLabel()
        assert r.heure_locale.toString() in obj.getPrintLabel()
        assert ("après-midi" if r.ampm == "PM" else "matin") in obj.tooltips[1]
        assert "Azimut image" in obj.tooltips[2]
        assert obj.tags["level"] == "design"


@pytest.mark.parametrize("calendrier,lettre", [("Standard", "C"), ("Déclinaison", "F")])
@pytest.mark.parametrize("choix,index", [("=", 0), ("+2", 2), ("-2", 1), ("Clef", 3), ("11:00", None)])
def test_substitutions_et_calendriers_ne_melangent_pas_les_notes(references, calendrier, lettre, choix, index):
    note = "J" if index is None else decalageGamme(lettre)[index]
    l = lumiere_prete(references)
    l.choixCalendrier = calendrier
    l.choixHeure = choix
    l.calculer()
    assert l.noteHoraire == note
    o = ombre_prete(references)
    o.choixCalendrier = calendrier
    o.choixHeure = choix
    o.calculer()
    assert o.noteHoraire == note
    if choix != "Clef":
        h = cercle_pret(references)
        h.lettreChoixSegment = lettre
        h.choixCalendrierSegment = calendrier
        h.heureSubstitution = choix
        h.calculer()
        assert h.noteHoraire == note


@pytest.mark.parametrize("centre", ["Ouverture", "Stylet"])
def test_distance_utilise_secondes_fractionnaires_ou_midi_explicite(references, centre):
    h = cercle_pret(references, "E", "PM")
    h.calculer()
    d = base.CercleDistance()
    d.pointBourges = h.pointBourges
    d.styletCerclehoraire = h.stylet
    d.heureSentinelleCerclehoraire = h.heureSentinelle
    d.heureSentinelleSecondesCerclehoraire = h.heureSentinelleSecondes
    d.lettreChoixSegment = "C"
    d.dateDataset = "15/08/778"
    d.centreCercle = centre
    d.calculer()
    secondes = 43200 if centre == "Ouverture" else h.heureSentinelleSecondes
    assert d.heureReferenceSecondes == secondes
    ctx = contexte("Carnac", "15/08/778")
    jd = ctx.versUT1(HeureMoyenneLocale(secondes))
    assert float(d.dateObservationUT1) == float(jd)
    assert d.hauteurSoleil == pytest.approx(positionSoleil(ctx.coordonnees, jd)[0])
    if centre == "Stylet":
        assert secondes != round(secondes)
        assert abs(ctx.depuisUT1(d.dateObservationUT1).secondes - secondes) < .00005


def test_identite_candidate_ne_depend_pas_de_chaines_arrondies(references):
    # Deux notes partagent volontairement la même seconde affichée.
    copie = SentinelleNationale(referentiel=references.referentiel)
    c, d = copie.par_note["C"], copie.par_note["D"]
    directe = replace(d.directe, heure_locale=c.directe.heure_locale)
    copie.par_note["D"] = replace(d, directe=directe)
    o = ombre_prete(copie, "C")
    o.calculer()
    assert len(o.listeCandidatsHeure) == 2
    assert {r.note for r in o.lignesHorairesReference if r.candidat} == {"C"}


@pytest.mark.parametrize("ampm", ["AM", "PM"])
def test_lampouy_reste_angulaire_et_temporellement_historique(references, monkeypatch, ampm):
    h = cercle_pret(references)
    h.dateDataset = "18/05/1152"
    h.heureAMPM = ampm
    h.calculer()
    heure_precedente = h.heureSentinelle
    secondes_precedentes = h.heureSentinelleSecondes
    h.heureSubstitution = f"{references['L']['AzimutCalibre']}°"
    def interdit(*args):
        pytest.fail("La substitution angulaire Lampouy ne calcule pas un nouveau Soleil")
    monkeypatch.setattr(base, "positionSoleil", interdit)
    h.calculer()
    assert h.angleHoraire == pytest.approx((180 - references['L']['AzimutCalibre']) * (1 if ampm == "AM" else -1))
    assert h.dateObservationUT1 is None
    assert h.heureSentinelle == heure_precedente
    assert h.heureSentinelleSecondes == secondes_precedentes
    l = lumiere_prete(references)
    l.heureAMPM = ampm
    l.choixHeure = references['L']['HeureLocale']
    l.calculer()
    ancienne = final.convertirHeureLocaleVersUTC(references.heurePourNote("L", ampm).toString(), villes_dict['Roncevaux'].getCoordonneesGPS()[1])
    assert float(l.dateObservationUT1) == float(MyJulianDate.fromString("25/07/778", ancienne))
    assert l.brancheReference == "historique_" + ampm
    o = ombre_prete(references)
    o.dateDataset = "18/05/1152"
    o.choixHeure = references['L']['HeureLocale']
    o.calculer()
    assert len(o.lignesHorairesReference) == 18
    assert len(o.listeCandidatsHeure) == 2
    assert {r.note for r in o.lignesHorairesReference if r.candidat} == {"L"}
