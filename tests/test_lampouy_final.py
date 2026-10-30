from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

import pytest

import src.AlgorithmeCadranFinal as final
from src.CadranNationalSentinelles import SentinelleNationale
from src.AlgorithmeCadranFinal import CHOIX_LAMPOUY
from src.ReferentielLampouyFinal import ReferentielLampouyFinal
from src.ReferentielSentinelles import ContexteObservation
from src.calculAstronomique import positionSoleil
from src.data_loader import villes_dict


@pytest.fixture(scope='module')
def reference():
    return ReferentielLampouyFinal.charger()


@pytest.fixture(scope='module')
def national():
    return SentinelleNationale()


@pytest.mark.parametrize(('periode','azimut','secondes','branche'),[
    ('AM',138.5,36490.30073472659,'matin'),
    ('PM',221.5,50020.141651121776,'apres_midi'),
])
def test_alignement_de406_heure_azimut_et_secondes(reference,periode,azimut,secondes,branche):
    d=reference.directionPourPeriode(periode)
    assert reference.contexte==ContexteObservation('Lampouy',*villes_dict['Lampouy'].getCoordonneesGPS(),'19/08/1152')
    assert reference.contexte.origine_date_jd==2142056.5  # 19 août 1152 julien.
    assert d.branche==branche
    assert d.heure_locale.secondes==pytest.approx(secondes,abs=.01)
    assert d.heure_locale.secondes!=round(d.heure_locale.secondes)
    # Recalcul direct de la position aux heures résolues par le moteur.
    jd=reference.contexte.versUT1(d.heure_locale)
    altitude,mesure=positionSoleil(reference.contexte.coordonnees,jd)
    assert altitude>0
    assert mesure==pytest.approx(azimut,abs=.0001)
    assert d.azimut==pytest.approx(mesure,abs=1e-8)


def test_references_fixes_et_absence_de_symetrie_24h(reference,national):
    avant=[asdict(r) for r in national.referentiel]
    assert ReferentielLampouyFinal.charger()==reference
    assert reference.contexte.date=='19/08/1152'
    assert reference.miroir.heure_locale.secondes!=(86400-reference.directe.heure_locale.secondes)%86400
    assert [asdict(r) for r in national.referentiel]==avant
    assert len(avant)==8
    with pytest.raises(ValueError,match='Période Lampouy'):
        reference.directionPourPeriode('autre')


def lumiere_prete(national,periode):
    l=final.LumiereFinal()
    l.sentinelle=national
    l.dateDataset='18/05/1152'
    l.dateSegmentDataset='19/08/1152'
    l.lieuObservationSegment='Lampouy'
    l.lettreDomSegment='C';l.lettreDeclDataset='F'
    l.hauteurStylet=250.;l.azimutMidiStylet=13.56
    l.choixHeure=CHOIX_LAMPOUY;l.heureAMPM=periode
    return l


def ombre_prete(national):
    o=final.LigneHoraireFinal()
    o.sentinelleLumiere=national
    o.dateDataset='18/05/1152'
    o.dateSegmentDataset='19/08/1152'
    o.lieuObservationSegment='Lampouy'
    o.baseStylet='Rocamadour';o.azimutMidiStylet=13.56
    o.lettreDomSegment='C';o.lettreDeclDataset='F'
    o.choixHeure=CHOIX_LAMPOUY
    return o


@pytest.mark.parametrize('periode',['AM','PM'])
def test_lumiere_emploie_heure_fixe_et_labels_calcules(reference,national,periode):
    l=lumiere_prete(national,periode)
    d=reference.directionPourPeriode(periode)
    l.calculer()
    assert l.noteHoraire=='L' and l.horaireLampouy
    assert l.directionReference==d
    assert l.heureLocaleSecondes==d.heure_locale.secondes
    assert l.azimut==pytest.approx(d.azimut,abs=1e-8)
    assert CHOIX_LAMPOUY in l.getValeursChoixHeure()
    assert l.heureLocale!=CHOIX_LAMPOUY
    for ligne in l.construireRepresentationCarte():
        assert ligne.getPrintLabel()==d.heure_locale.toString()
        assert f'Heure {d.heure_locale.toString()}' in ligne.tooltips
        assert any('Lampouy, 19/08/1152' in t for t in ligne.tooltips)
    # L'observation peut changer, la calibration de l'heure reste Lampouy/18 mai.
    l.lieuObservationSegment='Carnac';l.dateSegmentDataset='29/06/1152'
    l.calculer()
    assert l.heureLocaleSecondes==d.heure_locale.secondes
    assert l.referenceLampouy==reference
    assert l.azimut!=pytest.approx(d.azimut,abs=.001)
    ctx=ContexteObservation('Carnac',*villes_dict['Carnac'].getCoordonneesGPS(),'29/06/1152')
    assert float(l.dateObservationUT1)==float(ctx.versUT1(d.heure_locale))


def test_ombres_labels_tooltips_et_observation_independante(reference,national):
    o=ombre_prete(national);o.calculer()
    assert o.referenceLampouy==reference
    assert o.heureLocaleSecondes==reference.directe.heure_locale.secondes
    assert len(o.listeCandidatsHeure)==2
    assert [h for h,_ in o.listeCandidatsHeure]==[reference.directe.heure_locale.toString(),reference.miroir.heure_locale.toString()]
    lampouy=[v for v in o.lignesHorairesReference if v.note=='L']
    rendus=[v for v in o.construireRepresentationCarte() if 'Lampouy' in v.getNom()]
    assert len(lampouy)==len(rendus)==2
    for metadata,ligne in zip(lampouy,rendus):
        d=reference.directionPourPeriode(metadata.ampm)
        assert metadata.heure_locale==d.heure_locale
        assert metadata.azimut_solaire==d.azimut
        assert d.heure_locale.toString() in ligne.getPrintLabel()
        assert any('Lampouy, 19/08/1152' in t for t in ligne.tooltips)
        assert any(f'{d.azimut:.6f}' in t for t in ligne.tooltips)
    avant=[(v.note,v.heure_locale,v.ecart_image) for v in o.lignesHorairesReference]
    o.lieuObservationSegment='Bourges';o.dateSegmentDataset='29/06/1152';o.calculer()
    assert [(v.note,v.heure_locale,v.ecart_image) for v in o.lignesHorairesReference]==avant
    # Ce chemin Final ne doit pas initialiser le Lampouy historique Carnac/août.
    assert national._lampouy is None


def test_ancien_choix_10_09_charge_comme_lampouy(tmp_path):
    import json
    from types import SimpleNamespace
    from src.ProjectPersistence import _restaurer_parametres_scenario
    modules={cle:classe.__new__(classe) for cle,classe in (
        ('lumiere',final.LumiereFinal),('ombre',final.LigneHoraireFinal))}
    modules['autre']=SimpleNamespace(choixHeure='=')
    for module in modules.values():module.choixHeure='='
    scenario=SimpleNamespace(nom='Ancien',modules=modules)
    fichier=tmp_path/'ancien.json'
    fichier.write_text(json.dumps({cle:{'choixHeure':'10:09'} for cle in modules}),encoding='utf-8')
    avant=fichier.read_bytes()
    _restaurer_parametres_scenario(scenario,json.loads(fichier.read_text(encoding='utf-8')))
    assert modules['lumiere'].choixHeure==modules['ombre'].choixHeure=='Lampouy'
    assert modules['autre'].choixHeure=='10:09'
    assert fichier.read_bytes()==avant


def test_nouveau_choix_sauvegarde_lampouy(tmp_path,monkeypatch):
    import json
    from types import SimpleNamespace
    import src.ProjectPersistence as persistance
    scenario=SimpleNamespace(nom='Nouveau',modules={
        cle:SimpleNamespace(choixHeure='Lampouy') for cle in ('lumiere','ombre')})
    # Exerce les primitives réelles d'extraction et d'écriture, sans calcul de projet.
    monkeypatch.setattr(persistance,'construireSnapshotProjetJsonV1',lambda *args:
        {'parameters':persistance._snapshot_parametres_scenario(scenario,
            [('lumiere','choixHeure'),('ombre','choixHeure')])})
    sortie=tmp_path/'nouveau.json'
    persistance.sauvegarderProjetJsonV1(sortie,None,None)
    params=json.loads(sortie.read_text(encoding='utf-8'))['parameters']
    assert params=={'lumiere':{'choixHeure':'Lampouy'},'ombre':{'choixHeure':'Lampouy'}}


def test_selection_lampouy_reutilise_le_referentiel(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from src.ReferentielSentinelles import HeureMoyenneLocale
    direction=SimpleNamespace(heure_locale=HeureMoyenneLocale(36490.30073472659))
    reference=SimpleNamespace(directe=direction,directionPourPeriode=Mock(return_value=direction))
    charger=Mock(return_value=reference)
    monkeypatch.setattr(final.ReferentielLampouyFinal,'charger',charger)
    monkeypatch.setattr(final,'ContexteObservation',lambda *args:SimpleNamespace(versUT1=lambda heure:0.))
    monkeypatch.setattr(final,'positionSoleil',Mock(return_value=(45.,138.5)))
    l=final.LumiereFinal.__new__(final.LumiereFinal)
    l.choixCalendrier='Standard';l.lettreDomSegment='C';l.lettreDeclDataset='F'
    l.lieuObservationSegment='Lampouy';l.dateSegmentDataset='19/08/1152';l.dateDataset='18/05/1152'
    l.choixHeure='Lampouy';l.heureAMPM='AM';l.hauteurStylet=1.
    l.calculer()
    charger.assert_called_once_with()
    reference.directionPourPeriode.assert_called_once_with('AM')
    assert l.noteHoraire=='L' and l.referenceLampouy is reference
    assert l.heureLocaleSecondes==direction.heure_locale.secondes
    assert 'Lampouy' in l.getValeursChoixHeure() and '10:09' not in l.getValeursChoixHeure()
    o=final.LigneHoraireFinal.__new__(final.LigneHoraireFinal);o.dateDataset='18/05/1152'
    assert 'Lampouy' in o.getValeursChoixHeure() and '10:09' not in o.getValeursChoixHeure()


def test_lampouy_relit_azimut_csv_et_recalcule_les_deux_heures(tmp_path,monkeypatch):
    source=Path('data/sentinelle.csv').read_bytes()
    dossier=tmp_path/'data';dossier.mkdir()
    fichier=dossier/'sentinelle.csv';fichier.write_bytes(source)
    monkeypatch.chdir(tmp_path)
    avant=ReferentielLampouyFinal.charger()
    contenu=fichier.read_text(encoding='utf-8')
    modifie=contenu.replace('Lampouy,L,138.5,','Lampouy,L,138,')
    assert modifie!=contenu
    fichier.write_text(modifie,encoding='utf-8')
    apres=ReferentielLampouyFinal.charger()
    assert avant.directe.azimut==pytest.approx(138.5,abs=.0001)
    assert apres.directe.azimut==pytest.approx(138.,abs=.0001)
    assert apres.miroir.azimut==pytest.approx(222.,abs=.0001)
    assert apres.contexte==avant.contexte
    for ancienne,nouvelle in ((avant.directe,apres.directe),(avant.miroir,apres.miroir)):
        assert nouvelle.heure_locale.secondes!=ancienne.heure_locale.secondes
        assert nouvelle.heure_locale.toString()!=ancienne.heure_locale.toString()
