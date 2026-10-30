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


def heure_base(references, note, periode):
    am = references.heurePourNote(note, "AM")
    return am if periode == "AM" else HeureMoyenneLocale((86400 - am.secondes) % 86400)


def cercle_pret(references, note="C", ampm="AM"):
    module = base.CercleHoraire()
    module.sentinelle = references
    module.styletDataset = "Roncevaux"
    module.dateDataset = "15/08/778"
    module.choixCalendrierSegment = "Déclinaison"
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
    heure_calcul = heure_base(references, note, ampm)
    assert h.heureSentinelleSecondes == heure_calcul.secondes
    assert h.heureSentinelle == heure_calcul.toString()
    assert h.brancheReference == (branche if ampm == "AM" else "symetrie_tml")
    ctx = contexte("Carnac", "15/08/778")
    assert float(h.dateObservationUT1) == float(ctx.versUT1(heure_calcul))
    _, az = positionSoleil(ctx.coordonnees, ctx.versUT1(heure_calcul))
    assert h.angleHoraire == pytest.approx(abs(180 - az))
    assert h.angleHoraire > 0
    # Le choix de côté géométrique reste indépendant de l'heure.
    premier = h.coordPointChoix
    h.cercleAMPM = "PM"
    h.calculer()
    assert h.coordPointChoix != premier
    assert h.angleHoraire == pytest.approx(abs(180 - az))

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


def cote_axe(module):
    bx, by = module.pointBourges.coordonneesLambert()
    sx, sy = module.pointStylet.coordonneesLambert()
    px, py = module.coordPointChoix
    return (sx - bx) * (py - by) - (sy - by) * (px - bx)


@pytest.mark.parametrize("note", NOTES)
def test_periode_et_cote_du_cercle_sont_independants(references, note):
    h = cercle_pret(references, note)
    cotes = {}
    selection_initiale = None
    for periode in ("AM", "PM"):
        h.heureAMPM = periode
        points = []
        for cercle in ("AM", "PM"):
            h.cercleAMPM = cercle
            h.calculer()
            auto = (h.heureStylet, h.heureStyletSecondes, h.styletAMPM,
                    h.selectionHoraire.repere, h.selectionHoraire.branche)
            selection_initiale = auto if selection_initiale is None else selection_initiale
            assert auto == selection_initiale
            heure = heure_base(references, note, periode)
            assert h.heureSentinelleSecondes == heure.secondes
            assert h.angleHoraire == pytest.approx(abs(180 - h.azimutSoleil))
            cotes[periode, cercle] = cote_axe(h)
            points.append(h.coordPointChoix)
        # Les deux points sont opposés autour du milieu de Bourges–Stylet.
        b = h.pointBourges.coordonneesLambert()
        s = h.pointStylet.coordonneesLambert()
        assert [points[0][i] + points[1][i] for i in (0, 1)] == pytest.approx([b[i] + s[i] for i in (0, 1)])
        assert cotes[periode, "AM"] * cotes[periode, "PM"] < 0
    for cercle in ("AM", "PM"):
        assert cotes["AM", cercle] * cotes["PM", cercle] > 0


def test_rouen_joker_pm_garde_heure_automatique_s5_miroir(references):
    h = cercle_pret(references, "J", "PM")
    h.styletDataset = "Golfe-Juan"
    h.dateDataset = "20/03/1815"
    h.calculer()
    assert (h.selectionHoraire.repere, h.selectionHoraire.branche) == ("S5", "miroir")
    assert h.heureStylet == "12:04:01"
    assert h.heureStyletSecondes == references.heurePourNote("G", "miroir").secondes
    assert h.heureSentinelle == "13:04:00"
    assert h.heureSentinelleSecondes == 47040
    assert h.brancheReference == "symetrie_tml"
    assert h.angleHoraire == pytest.approx(18.606620, abs=.000001)
    cote_pm = cote_axe(h)
    h.heureAMPM = "AM"
    h.calculer()
    assert h.heureSentinelle == "10:56:00"
    assert h.angleHoraire > 0
    assert cote_pm * cote_axe(h) > 0
    assert h.heureStylet == "12:04:01"


@pytest.mark.parametrize("calendrier,substitution,note", [
    ("Standard", "=", "B"),
    ("Standard", "+2", "D"),
    ("Standard", "-2", "G"),
    ("Standard", "11:00", "J"),
    ("Déclinaison", "=", "G"),
    ("Déclinaison", "+2", "B"),
    ("Déclinaison", "-2", "E"),
    ("Déclinaison", "11:00", "J"),
])
@pytest.mark.parametrize("periode", ["AM", "PM"])
def test_calendrier_selectionne_note_depart_avant_substitution(references, calendrier, substitution, note, periode):
    h = cercle_pret(references)
    h.styletDataset = "Saint-Valentin"
    h.dateDataset = "19/07/933"
    h.choixCalendrierSegment = calendrier
    h.lettreChoixSegment = "D" if calendrier == "Standard" else "G"
    h.heureSubstitution = substitution
    h.heureAMPM = periode
    points = []
    for cercle in ("AM", "PM"):
        h.cercleAMPM = cercle
        h.calculer()
        assert (h.selectionHoraire.note, h.selectionHoraire.branche) == ("B", "miroir")
        assert h.heureStylet == "12:26:58"
        assert h.heureStyletSecondes == references.heurePourNote("B", "miroir").secondes
        assert h.styletAMPM == "PM"
        assert h.noteHoraire == note
        direction = references.directionPourNote(note, periode)
        heure_calcul = heure_base(references, note, periode)
        assert h.heureSentinelleSecondes == heure_calcul.secondes
        assert h.heureSentinelle == heure_calcul.toString()
        if calendrier == "Standard":
            attendues = {
                "=": {"AM": "11:37:03", "PM": "12:22:57"},
                "+2": {"AM": "08:14:46", "PM": "15:45:14"},
                "-2": {"AM": "12:00:00", "PM": "12:00:00"},
                "11:00": {"AM": "10:56:00", "PM": "13:04:00"},
            }
            assert h.heureSentinelle == attendues[substitution][periode]
        assert h.brancheReference == ("symetrie_tml" if periode == "PM" else
                                     "directe" if direction is references.par_note[note].directe else "miroir")
        ctx = contexte("Carnac", "19/07/933")
        assert float(h.dateObservationUT1) == float(ctx.versUT1(heure_calcul))
        assert h.angleHoraire == pytest.approx(abs(180 - positionSoleil(ctx.coordonnees, h.dateObservationUT1)[1]))
        assert h.angleHoraire > 0
        points.append(cote_axe(h))
    assert points[0] * points[1] < 0


@pytest.mark.parametrize("periode", ["AM", "PM"])
@pytest.mark.parametrize("substitution", ["=", "+2", "-2"])
def test_standard_joker_detecte_reste_joker_avec_substitutions(references, periode, substitution):
    h = cercle_pret(references)
    h.styletDataset = "Alise-Sainte-Reine"
    h.dateDataset = "12/04/1365"
    h.choixCalendrierSegment = "Standard"
    h.lettreChoixSegment = "G"
    h.heureSubstitution = substitution
    h.heureAMPM = periode
    h.calculer()
    assert h.selectionHoraire.note == "J"
    assert h.heureStylet == "13:08:03"
    assert h.noteHoraire == "J"
    assert h.heureSentinelleSecondes == heure_base(references, "J", periode).secondes
    assert h.heureStyletSecondes == h.selectionHoraire.heure_locale.secondes


@pytest.mark.integration
def test_chalus_standard_et_propagation_distance_sans_ecriture(references):
    from pathlib import Path
    from hashlib import sha256
    from src.ProjectPersistence import chargerProjetJsonV1

    fichier = Path("projets/BaseCadran.json")
    empreinte = sha256(fichier.read_bytes()).hexdigest()
    moteur, _ = chargerProjetJsonV1(fichier)
    # Le nom du scénario est conservé tel qu'il est enregistré dans le JSON.
    segment = next(seg for seg in moteur._scenarios if "933" in seg)
    scenario = moteur.getScenario("Chalus", segment)
    h = scenario.modules["cercleHoraire"]
    d = scenario.modules["cercleDistance"]
    assert (h.choixCalendrierSegment, h.heureSubstitution, h.cercleAMPM) == ("Standard", "=", "PM")
    assert (h.noteHoraire, h.heureSentinelle, h.brancheReference) == ("B", "12:22:57", "symetrie_tml")
    ctx_initial = contexte("Carnac", "19/07/933")
    heure_initiale = heure_base(references, "B", "PM")
    azimut_initial = positionSoleil(ctx_initial.coordonnees, ctx_initial.versUT1(heure_initiale))[1]
    assert h.angleHoraire == pytest.approx(abs(180 - azimut_initial))
    automatique = (h.heureStylet, h.heureStyletSecondes, h.styletAMPM)
    assert automatique[0] == "12:26:58"
    moteur.dataset.segment = segment
    moteur.dataset.calculer()
    for periode in ("AM", "PM"):
        h.heureAMPM = periode
        for centre in ("Stylet", "Ouverture"):
            d.centreCercle = centre
            moteur.calculerModules("Chalus", segment)
            assert (h.heureStylet, h.heureStyletSecondes, h.styletAMPM) == automatique
            assert h.heureSentinelle == ("11:37:03" if periode == "AM" else "12:22:57")
            heure = heure_base(references, "B", periode) if centre == "Stylet" else HeureMoyenneLocale(43200)
            assert d.heureReferenceSecondes == heure.secondes
            assert d.heureSentinelleSecondesCerclehoraire == h.heureSentinelleSecondes
            ctx = contexte("Carnac", "19/07/933")
            assert float(d.dateObservationUT1) == float(ctx.versUT1(heure))
            hauteur = positionSoleil(ctx.coordonnees, ctx.versUT1(heure))[0]
            assert d.hauteurSoleil == pytest.approx(hauteur)
            assert d.distanceRef == pytest.approx(d.hauteurStylet * d.tableauOctave[d.octave] / tan(radians(hauteur)))
    assert sha256(fichier.read_bytes()).hexdigest() == empreinte


@pytest.mark.integration
def test_bases_reelles_conservent_les_criteres_geometriques():
    from pathlib import Path
    from hashlib import sha256
    from src.ProjectPersistence import chargerProjetJsonV1
    from src.affichage_objets import CercleGraphique

    fichier = Path("projets/BaseCadran.json")
    empreinte = sha256(fichier.read_bytes()).hexdigest()
    moteur, _ = chargerProjetJsonV1(fichier)
    attendus = {
        "Saint Amour": [(888574.512428, 6594140.364372)],
        "Rocamadour": [(580473.206445, 6400068.708559)],
        "Gergovie": [],
        "Carignan": [],
        "Ile d'Aix": [(377128.725772, 6539620.079491), (371660.686958, 6546823.649281)],
        "Metz": [],
        "Chateau Gaillard": [(576904.964799, 6902698.291993)],
        "Domremy": [(895978.733016, 6813738.873863)],
        "Fontevraud": [(485382.000222, 6693897.652441)],
        "Rouen": [],
        "Chalus": [(549397.625005, 6509742.069402)],
        "Pont de Noirmoutiers": [(311026.032588, 6642076.836875), (990823.506573, 6627332.295081)],
        "Reims": [(786717.909090, 6899512.556359)],
        "Bouvines": [],
        "Le Goulet": [(601259.816918, 6885070.436900)],
        # Valeurs historiques du projet d6ff8fa, sans modifier ses paramètres.
        "Saint Cyr Coetquidan": [(314502.221191, 6796161.738146)],
    }
    verifies = set()
    for scenarios in moteur._scenarios.values():
        for nom, scenario in scenarios.items():
            if nom not in attendus:
                continue
            verifies.add(nom)
            h = scenario.modules["cercleHoraire"]
            c = scenario.modules["candidatBase"]
            c.calculer(methode="historique")
            assert h.angleHoraire > 0
            assert len(c.listeCandidats) == len(attendus[nom])
            for pt, coord in zip(c.listeCandidats, attendus[nom]):
                assert pt.coordonneesLambert() == pytest.approx(coord, abs=.001)
            # Vérification géométrique des deux retours : le candidat est
            # le milieu d'une intersection des cercles et de sa projection
            # sur une partition, avec l'écart strictement inférieur à 20 km.
            ch = CercleGraphique.depuisTroisPoints(c.pointBourges, c.pointStylet, c.pointChoix)
            cd = CercleGraphique(c.centreCercledistance, c.distanceRefCercledistance)
            intersections = cd.intersectionCercle(ch)
            if not intersections:
                milieux = []
                for ligne in c.candidatsPartition:
                    couples = [(p.distance(q), p, q) for p in ligne.intersectionCercle(ch)
                               for q in ligne.intersectionCercle(cd)]
                    if couples:
                        ecart, p, q = min(couples, key=lambda c:c[0])
                        if ecart < 20:
                            milieux.append(tuple((a+b)/2 for a,b in zip(p.coordonneesLambert(),q.coordonneesLambert())))
                assert len(milieux) == len(attendus[nom])
                for milieu, coord in zip(milieux,attendus[nom]):
                    assert milieu == pytest.approx(coord,abs=.001)
                continue
            assert len(intersections) == 2
            milieux = []
            for pt in intersections:
                for ligne in c.candidatsPartition:
                    projection = ligne.projectionPointGraphique(pt)
                    if pt.distance(projection) < 20:
                        p, q = pt.coordonneesLambert(), projection.coordonneesLambert()
                        milieux.append(tuple((p[i] + q[i]) / 2 for i in (0, 1)))
            assert len(milieux) == len(attendus[nom])
            for milieu, coord in zip(milieux, attendus[nom]):
                assert milieu == pytest.approx(coord, abs=.001)
    assert verifies == set(attendus)
    assert sha256(fichier.read_bytes()).hexdigest() == empreinte


@pytest.mark.parametrize("note", NOTES)
@pytest.mark.parametrize("sens", ["Endroit", "Envers"])
def test_lignes_finales_identite_branches_axe_image_et_candidats(references, note, sens):
    o = ombre_prete(references, note, sens)
    o.calculer()
    assert len(o.lignesHorairesReference) == 16
    assert len(o.listeCandidatsHeure) == 2
    midi = references.referentiel.contexte
    jd = midi.versUT1(HeureMoyenneLocale(43200))
    _, az = positionSoleil(midi.coordonnees, jd)
    assert float(o._dateMidiReferenceUT1) == float(jd)
    assert o._azimutMidiReference == pytest.approx(az)
    assert az != pytest.approx(180)
    assert az != pytest.approx(125.371)
    for r in o.lignesHorairesReference:
        d = references.directionPourNote(r.note, r.ampm)
        ref = references.par_note[r.note]
        assert r.branche == ("directe" if d is ref.directe else "miroir")
        assert r.heure_locale.secondes == d.heure_locale.secondes
        assert r.azimut_solaire == d.azimut
        assert r.ecart_image == pytest.approx((d.azimut - az) * (1 if sens == "Endroit" else -1))
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
