from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

import pytest

import src.AlgorithmeCadranFinal as final
from src.CadranNationalSentinelles import SentinelleNationale
from src.ReferentielLampouyFinal import CHOIX_LAMPOUY, ReferentielLampouyFinal
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


def test_projet_historique_10_09_charge_sauve_et_recharge(tmp_path):
    from src.ProjectPersistence import chargerProjetJsonV1,sauvegarderProjetJsonV1
    fichier=Path('projets/CadranFinal_Solutions.json')
    empreinte=sha256(fichier.read_bytes()).hexdigest()
    m,layers=chargerProjetJsonV1(fichier)
    selectionnes=[(event,name,s) for event,ss in m._scenarios.items() for name,s in ss.items()
                 if s.modules['lumiere'].choixHeure==CHOIX_LAMPOUY or s.modules['ombre'].choixHeure==CHOIX_LAMPOUY]
    assert selectionnes
    sortie=tmp_path/'compatibilite_lampouy.json'
    sauvegarderProjetJsonV1(sortie,m,layers)
    recharge,_=chargerProjetJsonV1(sortie)
    for event,name,s in selectionnes:
        for cle in ('lumiere','ombre'):
            a=s.modules[cle];b=recharge.getScenario(name,event).modules[cle]
            assert a.choixHeure==b.choixHeure
            assert a.heureLocaleSecondes==b.heureLocaleSecondes
            if a.choixHeure==CHOIX_LAMPOUY:
                assert a.noteHoraire==b.noteHoraire=='L'
                assert a.heureLocale!='10:09'
                assert a.referenceLampouy==b.referenceLampouy
    assert sha256(fichier.read_bytes()).hexdigest()==empreinte
