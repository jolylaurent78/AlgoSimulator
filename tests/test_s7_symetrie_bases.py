"""S7 angulaire et convention temporelle réservée aux bases."""
import json
from pathlib import Path

import pytest

import src.AlgorithmeBaseCadran as base
from src.CadranNationalSentinelles import SentinelleNationale
from src.ReferentielSentinelles import ReferentielSentinelles, HeureMoyenneLocale


@pytest.fixture(scope="module")
def national():
    return SentinelleNationale()


def test_s7_169_de406_trois_heures_et_provenance(national):
    r = national.par_note["B"]
    assert (r.autorite, r.valeur_reference, r.azimut_physique_initial) == ("azimut", 169, 170)
    assert r.azimut_direct == pytest.approx(169, abs=.0001)
    assert r.azimut_miroir == pytest.approx(191, abs=.0001)
    assert r.heure_directe.secondes == pytest.approx(41751.130102, abs=.02)
    assert r.heure_miroir.secondes == pytest.approx(44890.153108, abs=.02)
    base_pm = (86400 - r.heure_directe.secondes) % 86400
    assert base_pm == pytest.approx(44648.869898, abs=.02)
    assert HeureMoyenneLocale(base_pm).toString() == "12:24:09"
    assert r.heure_miroir.toString() == "12:28:10"
    assert r.heure_directe.secondes - HeureMoyenneLocale.depuisTexte("11:35:49").secondes == pytest.approx(2.130102, abs=.02)
    assert r.heure_directe.secondes != round(r.heure_directe.secondes)


def test_ancienne_calibration_archivee_et_autres_references_inchangees(national, tmp_path):
    fichier = Path("data/sentinelles_reference_v1.json")
    donnees = json.loads(fichier.read_text(encoding="utf-8"))
    archive = donnees["historique_calibrations"][-1]
    ancienne = archive["calibration_precedente"]
    assert archive["identifiant"] == "S7"
    assert archive["cible_horaire_indicative"] == "11:35:49"
    assert ancienne["azimut_physique_initial"] == 170
    assert (ancienne["autorite"], ancienne["valeur_reference"]) == ("heure", "11:30:42")
    assert ancienne["temoins"]["azimut_direct"] == 166.885
    donnees["directions"] = [ancienne if d["identifiant"] == "S7" else d for d in donnees["directions"]]
    chemin = tmp_path / "referentiel_avant_s7.json"
    chemin.write_text(json.dumps(donnees), encoding="utf-8")
    avant = ReferentielSentinelles.charger(fichier_donnees=chemin)
    for r in national.referentiel:
        old = avant.get(r.identifiant)
        if r.identifiant != "S7":
            assert (r.directe, r.miroir) == (old.directe, old.miroir)
        else:
            assert old.heure_directe.secondes == 41442
            assert old.azimut_direct == pytest.approx(166.868688, abs=.000001)


@pytest.mark.parametrize("note", list("CDEFGABJ"))
def test_base_pm_ne_demande_jamais_le_miroir_national(national, monkeypatch, note):
    monkeypatch.setattr(base, "Sentinelle", lambda *_: national)
    original = national.heurePourNote
    appels = []
    def seulement_am(n, branche):
        assert branche == "AM"
        appels.append((n, branche))
        return original(n, branche)
    monkeypatch.setattr(national, "heurePourNote", seulement_am)
    h = base.CercleHoraire()
    h.styletDataset = "Roncevaux"
    h.dateDataset = "15/08/778"
    h.choixCalendrierSegment = "Déclinaison"
    h.lettreChoixSegment = note if note != "J" else "C"
    h.heureSubstitution = "11:00" if note == "J" else "="
    h.heureAMPM = "PM"
    h.calculer()
    am = original(note, "AM")
    assert appels == [(note, "AM")]
    assert h.heureSentinelleSecondes == (86400 - am.secondes) % 86400
    assert h.brancheReference == "symetrie_tml"
    assert h.heureSentinelleSecondes != original(note, "PM").secondes
    if note == "G":
        assert h.heureSentinelleSecondes == am.secondes == 43200
    if note in "EF":
        assert national.directionPourNote(note, "AM") is national.par_note[note].miroir
