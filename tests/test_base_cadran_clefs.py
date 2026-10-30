import copy
from hashlib import sha256
from pathlib import Path
from unittest.mock import Mock

import pytest

import src.AlgorithmeBaseCadran as base
import src.AlgorithmeCadranFinal as final
from src.ProjectPersistence import chargerProjetJsonV1
from src.substitutionsMusicales import noteAvecSubstitution


@pytest.fixture(scope='module')
def modules_reference():
    moteur,_=chargerProjetJsonV1('tests/fixtures/base_cadran_roncevaux_rocamadour_reference.json')
    return moteur.getScenario().modules


@pytest.mark.parametrize(('note','clef','clef2'), [
    ('C','F','G'),('D','C','G'),('E','F','G'),('F','C','G'),
    ('G','G','G'),('A','F','G'),('B','B','B'),
])
@pytest.mark.parametrize('choix',['Clef','Clef 2'])
def test_sept_notes_deux_clefs_trois_modules(modules_reference,note,clef,clef2,choix):
    attendue=clef if choix=='Clef' else clef2
    assert final.noteAvecSubstitutionCadranFinal is base.noteAvecSubstitution is noteAvecSubstitution
    assert noteAvecSubstitution(note,choix)==attendue
    modules=copy.deepcopy(modules_reference)
    h,p,d=[modules[k] for k in ('cercleHoraire','partition','cercleDistance')]
    h.choixCalendrierSegment='Déclinaison'
    h.lettreChoixSegment=note
    h.heureSubstitution=choix
    h.calculer()
    assert not h.horaireLampouy
    assert h.noteHoraire==attendue
    assert h.heureSentinelleSecondes==h.sentinelle.heurePourNote(attendue,'AM').secondes
    p.lettreChoixSegment=note
    p.P2M2=choix
    p.calculer()
    assert p.lettrePartition==attendue
    d.lettreChoixSegment=note
    d.P2M2=choix
    d.calculer()
    assert d.lettreHauteur==attendue


@pytest.mark.parametrize('choix',['=','+2','-2','Clef','Clef 2','11:00'])
def test_joker_preserve_sans_substitution_angulaire(modules_reference,choix):
    h=copy.deepcopy(modules_reference['cercleHoraire'])
    h.styletDataset='Alise-Sainte-Reine'
    h.sentinelleStyletDataset=''
    h.choixCalendrierSegment='Standard'
    h.heureSubstitution=choix
    h.calculer()
    assert h.selectionHoraire.note=='J'
    assert h.noteHoraire=='J'
    assert h.heureSentinelle=='10:55:00'
    assert not h.horaireLampouy


@pytest.mark.parametrize('clef',['Clef','Clef 2'])
@pytest.mark.parametrize('periode',['AM','PM'])
def test_clefs_heures_symetrie_et_lampouy(modules_reference,clef,periode):
    h=copy.deepcopy(modules_reference['cercleHoraire'])
    h.choixCalendrierSegment='Déclinaison'
    h.lettreChoixSegment='A'
    h.heureSubstitution=clef
    h.heureAMPM=periode
    h.calculer()
    assert not h.horaireLampouy
    note='F' if clef=='Clef' else 'G'
    am=h.sentinelle.heurePourNote(note,'AM').secondes
    assert h.heureSentinelleSecondes==(am if periode=='AM' else (86400-am)%86400)
    avant=h.heureSentinelleSecondes
    h.heureSubstitution=f"{h.sentinelle['L']['AzimutCalibre']}°"
    h.calculer()
    assert h.horaireLampouy and h.noteHoraire=='L'
    assert h.heureSentinelleSecondes==avant
    attendu=180-h.azimutSoleil
    assert h.angleHoraire==pytest.approx(-attendu if periode=='PM' else attendu)


def test_carignan_declinaison_f_clef2_recalcule_partitions_et_diagnostics():
    projet=Path('projets/BaseCadran.json')
    empreinte=sha256(projet.read_bytes()).hexdigest()
    moteur,_=chargerProjetJsonV1(projet)
    evenement=next(e for e in moteur._scenarios if e.startswith('15 Juin 1066'))
    scenario=moteur.getScenario('Carignan',evenement)
    moteur.dataset.segment=evenement
    moteur.dataset.calculer()
    modules=scenario.modules
    p,c=modules['partition'],modules['candidatBase']
    # Fixer le contrôle en mémoire, même si l'utilisateur a sauvegardé Clef 2.
    modules['segment'].choixCalendrier='Déclinaison'
    p.P2M2='='
    moteur.calculerModules('Carignan',evenement)
    assert modules['segment'].choixCalendrier=='Déclinaison'
    assert p.lettreChoixSegment=='F'
    avant=[x.getGraphicalSignature() for x in p.candidats]
    anciens_diagnostics=c.diagnosticsCandidats
    p.P2M2='Clef 2'  # Changement uniquement en mémoire, sans sauvegarde.
    moteur.calculerModules('Carignan',evenement)
    assert p.lettrePartition=='G'
    assert p.candidats
    assert [x.getGraphicalSignature() for x in p.candidats]!=avant
    assert p.candidats==[ligne for ligne,note,_ in p.listeLignesPartitions if note=='G']
    assert c.candidatsPartition is p.candidats
    assert c.diagnosticsCandidats and c.diagnosticsCandidats is not anciens_diagnostics
    assert all(g.partition<len(p.candidats) for g in c.diagnosticsCandidats)
    assert all(g.accepte and all(d<=20+1e-9 for d in g.contraintes) for g in c.geometriesCandidats)
    assert all(o.getRayonKm()==20 for o in c.construireRepresentationCarte())
    assert sha256(projet.read_bytes()).hexdigest()==empreinte


def test_trois_selecteurs_acceptent_les_deux_clefs(modules_reference):
    import tkinter as tk
    from src.IHMAlgorithme import IHMAlgorithme
    root=tk.Tk()
    root.withdraw()
    try:
        for module,attribut,methode in [('cercleHoraire','heureSubstitution','getValeursHeureSubstitution'),
                                       ('partition','P2M2','getValeursP2M2'),('cercleDistance','P2M2','getValeursP2M2')]:
            ihm=IHMAlgorithme.__new__(IHMAlgorithme)
            ihm.parametres_widgets={}
            ihm.moteurAlgo=Mock()
            ihm.moteurAlgo.regles_actives={}
            ihm.moteurAlgo.getValeursParametre.return_value=getattr(modules_reference[module],methode)()
            ihm.moteurAlgo.getParametre.return_value='Clef'
            ihm.updateModuleEtInterface=Mock()
            panneau=tk.Frame(root)
            ihm.ajouter_ligne_widgets(panneau,[{'Widget':'checkboxH','FieldType':'lettre',
                'Module':module,'Attribut':attribut,'Label':'Choix','Type':'input_multiple'}])
            def cases(parent):
                return [w for child in parent.winfo_children()
                        for w in ([child] if isinstance(child,tk.Checkbutton) else cases(child))]
            controles={w.cget('text'):w for w in cases(panneau)}
            assert {'Clef','Clef 2'}<=controles.keys()
            assert 'Clef 1' not in controles
            for choix in ('Clef 2','Clef'):
                controles[choix].invoke()
                ihm.updateModuleEtInterface.assert_called_with(module,attribut,choix)
                valeurs=ihm.parametres_widgets[f'{module}.{attribut}']
                assert valeurs[choix].get()
                assert not valeurs['Clef' if choix=='Clef 2' else 'Clef 2'].get()
    finally:
        root.destroy()
