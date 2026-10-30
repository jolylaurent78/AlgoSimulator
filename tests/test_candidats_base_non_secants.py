from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import src.GeometrieCandidatsBase as geo
from src.ProjectPersistence import chargerProjetJsonV1


LIGNE=((0.,0.),(1.,0.))


@pytest.mark.parametrize('nom',['horaire','distance'])
def test_un_seul_cercle_non_secant_ecart_9km(nom,monkeypatch):
    non_secant=geo.CercleMetrique((0.,19000.),10000.)
    secant=geo.CercleMetrique((0.,0.),20000.)
    h,d=(non_secant,secant) if nom=='horaire' else (secant,non_secant)
    monkeypatch.setattr(geo,'calculerCandidatBasePondere',Mock(side_effect=AssertionError('Aucun C dans le cas 2')))
    retenus,diagnostics=geo.chercherCandidatsBasePonderes(h,d,[LIGNE])
    assert len(retenus)==len(diagnostics)==1
    r=retenus[0]
    assert r.traitement==r.methode=='secours_non_secant'
    assert r.cercle_non_secant==nom
    assert r.a==(0.,9000.) and r.q==(0.,0.)
    assert r.distance_aq==9
    assert r.p==(0.,4500.)
    assert r.c is r.g is r.angle is None
    assert r.poids==0
    assert r.contraintes[0 if nom=='horaire' else 1]==4.5
    assert all(d<=20 for d in r.contraintes)


def test_deux_cercles_non_secants_deux_secours_examined():
    h=geo.CercleMetrique((0.,19000.),10000.)
    d=geo.CercleMetrique((0.,21000.),10000.)
    retenus,diagnostics=geo.chercherCandidatsBasePonderes(h,d,[LIGNE])
    assert len(retenus)==len(diagnostics)==2
    assert {r.cercle_non_secant for r in retenus}=={'horaire','distance'}
    assert [r.p for r in retenus]==[(0.,4500.),(0.,5500.)]


@pytest.mark.parametrize(('ecart','admis'),[(30000.,True),(30000.001,False)])
def test_limite_presel_30km(ecart,admis):
    h=geo.CercleMetrique((0.,10000.+ecart),10000.)
    d=geo.CercleMetrique((0.,0.),20000.)
    r=geo.calculerSecoursNonSecant(h,'horaire',h,d,*LIGNE)
    assert r.accepte is admis
    assert r.distance_aq==pytest.approx(ecart/1000)
    if admis:assert r.p==(0.,15000.)
    else:
        assert r.p is None
        assert 'AQ > 30' in r.rejet


@pytest.mark.parametrize(('rayon','admis'),[(24500.,True),(24500.001,False)])
def test_controle_final_20km_independant_de_la_presel(rayon,admis):
    h=geo.CercleMetrique((0.,19000.),10000.)
    d=geo.CercleMetrique((0.,0.),rayon)
    r=geo.calculerSecoursNonSecant(h,'horaire',h,d,*LIGNE)
    assert r.distance_aq==9
    assert r.p==(0.,4500.)
    assert r.accepte is admis
    assert r.contraintes[0]==r.contraintes[2]==4.5
    assert r.contraintes[1]==pytest.approx((rayon-4500)/1000)


def test_troisieme_contrainte_empeche_acceptation():
    h=geo.CercleMetrique((0.,19000.),10000.)
    d=geo.CercleMetrique((100000.,0.),10000.)
    retenus,diagnostics=geo.chercherCandidatsBasePonderes(h,d,[LIGNE])
    assert not retenus
    r=diagnostics[0]
    assert r.distance_aq==9
    assert r.contraintes[1]>90
    assert 'contrainte finale' in r.rejet


def test_deux_intersections_cas1_inchange(monkeypatch):
    monkeypatch.setattr(geo,'calculerSecoursNonSecant',Mock(side_effect=AssertionError('Cas 1 uniquement')))
    h,d=geo.CercleMetrique((0.,0.),10000.),geo.CercleMetrique((0.,0.),20000.)
    retenus,diagnostics=geo.chercherCandidatsBasePonderes(h,d,[LIGNE])
    assert len(retenus)==len(diagnostics)==4
    assert sorted(r.p[0] for r in retenus)==[-15000.,-5000.,5000.,15000.]
    assert all(r.traitement=='ponderee' for r in retenus)


def test_tangence_exacte_reste_cas1(monkeypatch):
    monkeypatch.setattr(geo,'calculerSecoursNonSecant',Mock(side_effect=AssertionError('Tangence sécante')))
    h=geo.CercleMetrique((0.,10000.),10000.)
    d=geo.CercleMetrique((0.,0.),20000.)
    retenus,diagnostics=geo.chercherCandidatsBasePonderes(h,d,[LIGNE])
    assert len(diagnostics)==2 and retenus
    assert all(r.traitement=='ponderee' for r in diagnostics)


def test_secours_dedupliques_entre_cercles_et_partitions():
    c=geo.CercleMetrique((0.,19000.),10000.)
    retenus,diagnostics=geo.chercherCandidatsBasePonderes(c,c,[LIGNE,LIGNE])
    assert len(retenus)==1 and len(diagnostics)==4
    assert sum('doublon' in r.rejet for r in diagnostics)==3


def test_stabilite_projection_lambert_oblique():
    origine=(700000.,6600000.);u=(.6,.8);n=(-.8,.6)
    centre=tuple(origine[i]+19000*n[i] for i in (0,1))
    h=geo.CercleMetrique(centre,10000.)
    d=geo.CercleMetrique(origine,20000.)
    r=geo.calculerSecoursNonSecant(h,'horaire',h,d,origine,u)
    assert r.accepte
    assert r.distance_aq==pytest.approx(9,abs=1e-9)
    assert r.q==pytest.approx(origine,abs=1e-6)
    assert r.a==pytest.approx(tuple(origine[i]+9000*n[i] for i in (0,1)),abs=1e-6)
    assert r.p==pytest.approx((696400.,6602700.),abs=1e-6)
    assert geo.ecartDroiteCercle(origine,u,h)==pytest.approx(9)


def test_prefiltre_garde_une_ligne_a_25km_malgre_cache_pixel(monkeypatch):
    import src.AlgorithmeBaseCadran as base
    from src.carte_config import carteConfig
    m,_=chargerProjetJsonV1('tests/fixtures/base_cadran_roncevaux_rocamadour_reference.json')
    p=m.getScenario().modules['partition']
    centre=base.PointGraphique('Centre',0.,0.)
    rayons=[]
    class CercleVide:
        def __init__(self,centre,rayon):rayons.append(rayon)
        @staticmethod
        def depuisTroisPoints(*_):return SimpleNamespace(getCentre=lambda:centre,getRayonKm=lambda:1.)
        def intersectionLigne(self,_):return []
    class Ligne:
        def __init__(self,*args,**kwargs):
            self.pointReference=carteConfig.lambert93_to_pixels(0.,26000.)
            self.vecteur=tuple(carteConfig.A @ (1.,0.))
        def pointsEquidistants(self,*_):return centre,centre
    monkeypatch.setattr(base,'CercleGraphique',CercleVide)
    monkeypatch.setattr(base,'LigneAzimut',Ligne)
    p.lettreChoixSegment='G';p.P2M2='='
    p.calculer()
    assert rayons==[31.]
    assert p.candidats  # Le préfiltre de 20 km aurait éliminé toutes ces droites.


def test_fontevraud_sans_changer_les_parametres_ni_forcer_la_couverture():
    fichier=Path('projets/BaseCadran.json');sha=sha256(fichier.read_bytes()).hexdigest()
    m,layers=chargerProjetJsonV1(fichier)
    event=next(e for e in m._scenarios if '933' in e)
    s=m.getScenario('Fontevraud',event)
    segment,h,p,d,c=[s.modules[k] for k in ('segment','cercleHoraire','partition','cercleDistance','candidatBase')]
    assert (segment.choixCalendrier,h.stylet,h.heureSubstitution,h.heureAMPM,h.cercleAMPM)==('Standard','Saint-Valentin','=','PM','AM')
    assert (p.lieuObservation,p.P2M2,p.typeSymetrie)==('Dieppe','-2','Flip vertical')
    assert (d.centreCercle,d.P2M2,d.octave)==('Stylet','=','/2')
    assert len(c.listeCandidats)==1
    g=c.geometriesCandidats[0]
    assert g.traitement=='secours_non_secant' and g.cercle_non_secant=='horaire'
    assert g.distance_aq==pytest.approx(9.883048873832566,abs=1e-6)
    assert g.p==tuple((g.a[i]+g.q[i])/2 for i in (0,1))
    assert g.contraintes==pytest.approx((4.941524436916312,19.566304223185885,4.941524436916276),abs=1e-6)
    from src.data_loader import villes_dict
    assert c.listeCandidats[0].distance(villes_dict['Fontevraud'])==pytest.approx(26.522400278494533,abs=1e-6)
    tooltip=' '.join(c.construireRepresentationCarte()[0].tooltips)
    assert 'secours_non_secant' in tooltip and 'AQ' in tooltip and 'Q (m)' in tooltip
    assert c.construireRepresentationCarte()[0].getRayonKm()==20
    assert sha256(fichier.read_bytes()).hexdigest()==sha
