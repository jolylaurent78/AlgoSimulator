from unittest.mock import Mock

import pytest

import src.GeometrieCandidatsBase as geo


LIGNE = ((0.,0.),(1.,0.))


@pytest.mark.parametrize(('second','nombre'), [
    (geo.CercleMetrique((12000.,0.),10000.),2),
    (geo.CercleMetrique((20000.,0.),10000.),1),
    (geo.CercleMetrique((5000.,0.),5000.),1),
    (geo.CercleMetrique((21000.,0.),10000.),0),
    (geo.CercleMetrique((1000.,0.),5000.),0),
    (geo.CercleMetrique((0.,0.),10000.),0),
])
def test_intersections_cercles_secants_tangents_disjoints_confondus(second,nombre):
    premier=geo.CercleMetrique((0.,0.),10000.)
    points=geo.intersectionsCercles(premier,second)
    assert len(points)==nombre
    for point in points:
        assert premier.ecart(point)==pytest.approx(0,abs=1e-9)
        assert second.ecart(point)==pytest.approx(0,abs=1e-9)
    if nombre==2:
        assert points[0]==pytest.approx((6000.,-8000.))
        assert points[1]==pytest.approx((6000.,8000.))


@pytest.mark.parametrize('inverse',[False,True])
def test_tous_les_couples_deux_a_deux_b_et_bonnes_tangentes(inverse):
    manque=geo.CercleMetrique((0.,19000.),10000.)
    coupe=geo.CercleMetrique((0.,0.),20000.)
    h,d=(coupe,manque) if inverse else (manque,coupe)
    retenus,diagnostics=geo.chercherCandidatsBasePonderes(h,d,[LIGNE])
    cas2=[r for r in diagnostics if r.traitement=='ponderee_intersections_cercles']
    assert len(cas2)==4
    assert len({r.a for r in cas2})==len({r.b for r in cas2})==2
    assert retenus and all(r.traitement=='ponderee_intersections_cercles' for r in retenus)
    assert len(diagnostics)==4  # Pas de secours A–Q redondant.
    for r in cas2:
        assert r.segment=='AB'
        assert h.ecart(r.a)==pytest.approx(0,abs=1e-9)
        assert d.ecart(r.a)==pytest.approx(0,abs=1e-9)
        assert coupe.ecart(r.b)==pytest.approx(0,abs=1e-9)
        assert r.b[1]==0
        assert r.c is not None
        for point,cercle in ((r.a,manque),(r.b,coupe)):
            # Une tangente est orthogonale au rayon, sur le bon cercle.
            rayon=geo.unitaire(geo.soustraire(point,cercle.centre))
            assert abs(sum((r.c[i]-point[i])*rayon[i] for i in (0,1)))<=geo.TOL_METRES
        if r.accepte:
            assert max(r.contraintes)<=20


@pytest.mark.parametrize(('ab','admis'),[(30000.,True),(30000.001,False)])
def test_ab_impose_meme_si_ac_plus_court_et_limite_30km(ab,admis):
    a,b,c=(0.,0.),(ab,0.),(0.,1000.)
    r=geo.pondererTriangleBase(a,b,c,segment_reference='AB')
    assert r.segment=='AB' and r.d_min==pytest.approx(ab/1000)
    assert r.ac==1 and r.ac<r.ab
    assert r.accepte is admis
    assert geo.pondererTriangleBase(a,b,c).segment=='AC'  # Cas 1 conservé.
    if admis:
        assert r.m==(ab/2,0.)
        assert r.angle==pytest.approx(88.09084756700362)
        assert r.poids==1 and r.p==r.g


def test_pondere_angle_aigu_poids_fractionnaire_avec_ab_impose():
    r=geo.pondererTriangleBase((0.,0.),(10000.,0.),(5000.,20000.),segment_reference='AB')
    assert 0<r.poids<1
    assert r.angle==pytest.approx(28.072486935852957)
    assert r.poids==pytest.approx((r.angle/45)**2)
    assert r.p==pytest.approx(tuple((1-r.poids)*r.m[i]+r.poids*r.g[i] for i in (0,1)))


@pytest.mark.parametrize('decalage',[0.,5e-9])
def test_cas2_tangentes_paralleles_ou_presque_secours_m(decalage):
    h=geo.CercleMetrique((-50000.,0.),50000.)
    d=geo.CercleMetrique((60000.,decalage),50000.)
    r=geo.calculerCandidatBasePondere((0.,0.),(10000.,0.),h,d,*LIGNE,cercle_non_secant='horaire')
    assert r.c is r.g is r.angle is None
    assert r.p==r.m==(5000.,0.) and r.poids==0
    assert r.accepte and 'tangentes indéterminées' in r.methode
    assert r.traitement=='ponderee_intersections_cercles'


def test_cas2_rejet_final_malgre_ab_admissible():
    # A est sur les deux cercles, B sur le second et la partition.
    h=geo.CercleMetrique((-51000.,159000.),151000.)
    d=geo.CercleMetrique((-35000.,16000.),62000.)
    assert not geo.intersectionsDroiteCercle(*LIGNE,h)
    a=geo.intersectionsCercles(h,d)[1]
    b=geo.intersectionsDroiteCercle(*LIGNE,d)[1]
    r=geo.calculerCandidatBasePondere(a,b,h,d,*LIGNE,cercle_non_secant='horaire')
    assert r.ab<30 and r.p is not None
    assert r.contraintes[2]>20 and not r.accepte
    assert r.rejet=='contrainte finale > 20 km'


def test_repli_aq_si_aucun_couple_valide(monkeypatch):
    h=geo.CercleMetrique((0.,19000.),10000.)
    d=geo.CercleMetrique((0.,0.),20000.)
    # Isole la décision de repli ; le secours lui-même reste calculé réellement.
    calcul=Mock(side_effect=lambda *a,**k:geo.ResultatCandidatBase(rejet='refus du couple'))
    monkeypatch.setattr(geo,'calculerCandidatBasePondere',calcul)
    retenus,diagnostics=geo.chercherCandidatsBasePonderes(h,d,[LIGNE])
    assert calcul.call_count==4 and len(diagnostics)==5
    assert len(retenus)==1 and retenus[0].traitement=='secours_non_secant'
    assert retenus[0].p==(0.,4500.)


def test_cercles_sans_intersection_conservent_aq(monkeypatch):
    h=geo.CercleMetrique((0.,19000.),10000.)
    d=geo.CercleMetrique((0.,0.),50000.)  # Cercles emboîtés sans intersection.
    calcul=Mock(side_effect=AssertionError('Aucune intersection à inventer'))
    monkeypatch.setattr(geo,'calculerCandidatBasePondere',calcul)
    _,diagnostics=geo.chercherCandidatsBasePonderes(h,d,[LIGNE])
    assert len(diagnostics)==1 and diagnostics[0].traitement=='secours_non_secant'
    assert diagnostics[0].distance_aq==9


def test_dedup_cas2_ne_declenche_pas_un_secours_aq(monkeypatch):
    h=geo.CercleMetrique((0.,19000.),10000.)
    d=geo.CercleMetrique((0.,0.),20000.)
    monkeypatch.setattr(geo,'calculerSecoursNonSecant',Mock(side_effect=AssertionError('Pas de repli redondant')))
    uniques,_=geo.chercherCandidatsBasePonderes(h,d,[LIGNE])
    retenus,diagnostics=geo.chercherCandidatsBasePonderes(h,d,[LIGNE,LIGNE])
    assert [r.p for r in retenus]==[r.p for r in uniques]
    assert len(diagnostics)==8
    assert sum('doublon' in r.rejet for r in diagnostics)==len(uniques)


def test_intersections_stables_apres_translation_lambert_et_rotation():
    origine=(700000.,6600000.);u=(.6,.8);n=(-.8,.6)
    second=tuple(origine[i]+12000*u[i] for i in (0,1))
    points=geo.intersectionsCercles(geo.CercleMetrique(origine,10000.),geo.CercleMetrique(second,10000.))
    for point,signe in zip(points,(-1,1)):
        assert point==pytest.approx(tuple(origine[i]+6000*u[i]+signe*8000*n[i] for i in (0,1)),abs=1e-6)
