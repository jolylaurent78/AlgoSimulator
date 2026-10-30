import csv
from hashlib import sha256
import json
from pathlib import Path

import pytest

import src.AlgorithmeBaseCadran as base
from src.CadranNationalSentinelles import SentinelleNationale
from src.ListeSegmentsDataSet import ListeSegmentsDataSet
from src.ProjectPersistence import chargerProjetJsonV1, sauvegarderProjetJsonV1


FIXTURE = Path('tests/fixtures/base_cadran_roncevaux_rocamadour_reference.json')


@pytest.fixture(scope='module')
def national():
    return SentinelleNationale()


@pytest.fixture
def horaire(national, monkeypatch):
    monkeypatch.setattr(base, 'Sentinelle', lambda *_: national)
    h = base.CercleHoraire()
    h.styletDataset = 'Sainte-Catherine-de-Fierbois'
    h.sentinelleStyletDataset = 'S6M'
    h.dateDataset = '30/05/1431'
    h.choixCalendrierSegment = 'Standard'
    h.lettreChoixSegment = 'G'
    return h


@pytest.mark.parametrize('code', [f'S{i}{suffixe}' for i in range(1,8) for suffixe in ('','M')])
@pytest.mark.parametrize('periode', ['AM','PM'])
def test_codes_explicites_identite_independante_periode(horaire, national, monkeypatch, code, periode):
    def interdit(*_):
        pytest.fail('Une affectation explicite ne recherche pas la ligne la plus proche')
    monkeypatch.setattr(national, 'rechercherLigneHoraire', interdit)
    horaire.sentinelleStyletDataset = code
    horaire.heureAMPM = periode
    horaire.calculer()
    reference = national.referentiel.get(code[:2])
    branche = 'miroir' if code.endswith('M') else 'directe'
    assert horaire.selectionHoraire.repere == code[:2]
    assert horaire.selectionHoraire.note == reference.note
    assert horaire.selectionHoraire.branche == branche
    assert horaire.heureStyletSecondes == national.heurePourNote(reference.note, branche).secondes
    am = national.heurePourNote(reference.note,'AM').secondes
    assert horaire.heureSentinelleSecondes == (am if periode=='AM' else (86400-am)%86400)
    if code == 'S6M':
        assert horaire.heureSentinelle == ('11:42:00' if periode=='AM' else '12:18:00')
        # Le témoin 12:21:56 n'est pas l'autorité : conserver le miroir DE406 existant.
        assert horaire.heureStylet == national.heurePourNote('A','miroir').toString()


@pytest.mark.parametrize('calendrier', ['Standard','Déclinaison'])
@pytest.mark.parametrize('substitution', ['=','+2','-2','11:00'])
@pytest.mark.parametrize('periode', ['AM','PM'])
def test_substitutions_calendrier_et_symetrie_preserves(horaire, national, calendrier, substitution, periode):
    horaire.choixCalendrierSegment = calendrier
    horaire.heureSubstitution = substitution
    horaire.heureAMPM = periode
    horaire.calculer()
    notes = {'Standard': {'=':'A','+2':'C','-2':'F','11:00':'J'},
             'Déclinaison': {'=':'G','+2':'B','-2':'E','11:00':'J'}}
    note = notes[calendrier][substitution]
    am = national.heurePourNote(note,'AM').secondes
    assert horaire.noteHoraire == note
    assert horaire.heureSentinelleSecondes == (am if periode=='AM' else (86400-am)%86400)
    assert horaire.selectionHoraire.repere == 'S6'
    assert horaire.selectionHoraire.branche == 'miroir'


@pytest.mark.parametrize('code', ['S0','S8','S6MM','s6m','S6M ','Joker',6])
def test_code_invalide_refuse_sans_repli(horaire, national, monkeypatch, code):
    monkeypatch.setattr(national,'rechercherLigneHoraire',lambda *_:pytest.fail('Repli interdit'))
    horaire.sentinelleStyletDataset = code
    with pytest.raises(ValueError, match='SentinelleStylet invalide'):
        horaire.calculer()


@pytest.mark.parametrize('code', ['',None])
def test_ancienne_configuration_repli_diagnostique(horaire, caplog, code):
    horaire.sentinelleStyletDataset = code
    horaire.calculer()
    assert horaire.selectionHoraire.repere == 'S7'
    assert 'recherche automatique de compatibilité' in caplog.text
    assert 'Sainte-Catherine-de-Fierbois' in horaire.diagnosticAffectation


def test_lampouy_et_cote_du_cercle_preserves(horaire):
    horaire.calculer()
    heure = horaire.heureSentinelleSecondes
    horaire.heureSubstitution = f"{horaire.sentinelle['L']['AzimutCalibre']}°"
    horaire.heureAMPM = 'PM'
    horaire.calculer()
    assert horaire.noteHoraire == 'L'
    assert horaire.heureSentinelleSecondes == heure
    assert horaire.angleHoraire == -(180-horaire.azimutSoleil)
    horaire.heureSubstitution = '='
    horaire.calculer()
    point1 = horaire.coordPointChoix
    horaire.cercleAMPM = 'PM'
    horaire.calculer()
    assert horaire.coordPointChoix != point1
    assert horaire.heureSentinelle == '12:18:00'


def test_csv_actuel_et_ancien_sans_colonne(tmp_path):
    with Path('data/dataset.csv').open(encoding='utf-8',newline='') as f:
        lecteur = csv.DictReader(f)
        champs = lecteur.fieldnames
        rows = list(lecteur)
    assert champs.index('SentinelleStylet') == champs.index('Stylet')+1
    dataset = ListeSegmentsDataSet('data/dataset.csv')
    event = next(r['Evènement'] for r in rows if r['Stylet']=='Sainte-Catherine-de-Fierbois')
    dataset.segment = event
    dataset.calculer()
    assert dataset.sentinelleStylet == 'S6M'
    assert dataset.getValeurPourSegment(event,'SentinelleStylet') == 'S6M'
    ancien = tmp_path/'ancien.csv'
    with ancien.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=[c for c in champs if c!='SentinelleStylet'])
        writer.writeheader()
        writer.writerows({k:v for k,v in r.items() if k!='SentinelleStylet'} for r in rows)
    compatible=ListeSegmentsDataSet(ancien)
    compatible.calculer()
    assert compatible.sentinelleStylet == ''


def ecrire(tmp_path, snapshot):
    p=tmp_path/'projet.json'
    p.write_text(json.dumps(snapshot,ensure_ascii=False),encoding='utf-8')
    return p


def test_base_ancien_enrichit_uniquement_champ_manquant_et_persiste(tmp_path, monkeypatch):
    projet=Path('projets/BaseCadran.json')
    sha=sha256(projet.read_bytes()).hexdigest()
    avant=json.loads(projet.read_text(encoding='utf-8'))
    moteur,layers=chargerProjetJsonV1(projet)
    for event in avant['dataset']['events']:
        actuel=moteur.dataset.evenements[event['event']]
        assert {k:v for k,v in actuel.items() if k!='SentinelleStylet'} == {k:v for k,v in event.items() if k not in ('event','SentinelleStylet')}
    assert sum(len(s) for s in moteur._scenarios.values()) == 16
    cible=next(s for s in moteur.dataset.evenements if '1431' in s)
    h=moteur.getScenario('Saint Cyr Coetquidan',cible).modules['cercleHoraire']
    assert h.sentinelleStyletDataset=='S6M'
    assert (h.selectionHoraire.repere,h.selectionHoraire.note,h.selectionHoraire.branche)==('S6','A','miroir')
    # Ne modifier aucun réglage enregistré pour produire les heures de référence.
    for segment in avant['segments']:
        for sc in segment['scenarios']:
            modules=moteur.getScenario(sc['name'],segment['segment']).modules
            for identifiant,params in sc['parameters'].items():
                assert all(getattr(modules[identifiant],k)==v for k,v in params.items())
    sortie=tmp_path/'sauvegarde.json'
    snapshot=sauvegarderProjetJsonV1(sortie,moteur,layers)
    original=Path.open
    def ouvrir(p,*args,**kwargs):
        if p.as_posix()=='data/dataset.csv':pytest.fail('Un snapshot complet est autonome')
        return original(p,*args,**kwargs)
    monkeypatch.setattr(Path,'open',ouvrir)
    recharge,layers2=chargerProjetJsonV1(sortie)
    assert sauvegarderProjetJsonV1(tmp_path/'second.json',recharge,layers2)==snapshot
    assert sha256(projet.read_bytes()).hexdigest()==sha


@pytest.mark.parametrize('affectation', ['S2M',''])
def test_affectation_presente_jamais_ecrasee(tmp_path, affectation):
    snapshot=json.loads(FIXTURE.read_text(encoding='utf-8'))
    snapshot['dataset']['events'][0]['SentinelleStylet']=affectation
    moteur,_=chargerProjetJsonV1(ecrire(tmp_path,snapshot))
    assert moteur.dataset.sentinelleStylet==affectation
    if affectation:
        assert moteur.getScenario().modules['cercleHoraire'].selectionHoraire.repere=='S2'


def test_rapprochement_evenements_strict(tmp_path, caplog):
    snapshot=json.loads(FIXTURE.read_text(encoding='utf-8'))
    ancien=snapshot['active_segment']; nouveau=ancien+' '
    snapshot['dataset']['events'][0]['event']=nouveau
    snapshot['active_segment']=nouveau
    snapshot['segments'][0]['segment']=nouveau
    snapshot['segments'][0]['scenarios'][0]['segment']=nouveau
    moteur,_=chargerProjetJsonV1(ecrire(tmp_path,snapshot))
    assert moteur.dataset.sentinelleStylet==''
    assert 'compatibilité' in caplog.text


def test_autres_projets_non_enrichis(monkeypatch):
    fichier=Path('tests/fixtures/cadran_final_roncevaux_lac_tremelin_reference.json')
    original=Path.open
    def ouvrir(p,*args,**kwargs):
        if p.as_posix()=='data/dataset.csv':pytest.fail('Aucun enrichissement hors BaseCadran')
        return original(p,*args,**kwargs)
    monkeypatch.setattr(Path,'open',ouvrir)
    moteur,_=chargerProjetJsonV1(fichier)
    snapshot=json.loads(fichier.read_text(encoding='utf-8'))
    assert moteur.dataset.evenements == {r['event']:{k:v for k,v in r.items() if k!='event'} for r in snapshot['dataset']['events']}
    assert moteur.dataset.sentinelleStylet==''


def test_csv_absent_ancien_base_reste_chargeable(tmp_path, monkeypatch, caplog):
    original=Path.open
    def ouvrir(p,*args,**kwargs):
        if p.as_posix()=='data/dataset.csv':raise FileNotFoundError(p)
        return original(p,*args,**kwargs)
    monkeypatch.setattr(Path,'open',ouvrir)
    moteur,_=chargerProjetJsonV1(FIXTURE)
    assert moteur.dataset.sentinelleStylet==''
    assert 'CSV absent' in caplog.text
