from math import atan2, degrees, dist, hypot, sqrt
from hashlib import sha256
from pathlib import Path

import pytest

from src.GeometrieCandidatsBase import (
    CercleMetrique, calculerCandidatBasePondere, chercherCandidatsBasePonderes,
    distancesContraintesBase, intersectionsDroiteCercle, pondererTriangleBase,
)


def cercle_tangent(point, sommet, rayon=100000):
    dx,dy = sommet[0]-point[0],sommet[1]-point[1]
    norme=hypot(dx,dy)
    return CercleMetrique((point[0]-rayon*dy/norme,point[1]+rayon*dx/norme),rayon)


@pytest.mark.parametrize(('a','b','c','segment'), [
    ((0.,0.),(10000.,0.),(5000.,20000.),'AB'),
    ((0.,0.),(40000.,0.),(0.,10000.),'AC'),
    ((0.,0.),(40000.,0.),(40000.,10000.),'BC'),
])
def test_tangentes_et_segment_minimal(a,b,c,segment):
    h,d=cercle_tangent(a,c),cercle_tangent(b,c)
    r=calculerCandidatBasePondere(a,b,h,d,(0.,0.),(1.,0.))
    assert r.segment==segment
    assert r.c==pytest.approx(c,abs=1e-7)
    assert r.d_min==10
    assert r.accepte
    assert r.p==pytest.approx(tuple((1-r.poids)*r.m[i]+r.poids*r.g[i] for i in (0,1)))
    assert r.poids==pytest.approx(min(1,(r.angle/45)**2))
    assert all(d<=20 for d in r.contraintes)


@pytest.mark.parametrize(('b','accepte'), [(30000,True),(30000.001,False)])
def test_preselection_limite_30km(b,accepte):
    r=pondererTriangleBase((0.,0.),(b,0.))
    assert r.accepte is accepte


def test_triangle_plus_petit_segment_trop_long():
    r=pondererTriangleBase((0.,0.),(40000.,0.),(0.,40000.))
    assert not r.accepte
    assert '> 30' in r.rejet


def test_angle_interieur_egalites_deterministes_et_poids_un():
    r=pondererTriangleBase((0.,0.),(10000.,0.),(0.,10000.))
    assert r.segment=='AB'  # AB == AC : l'ordre déclaré tranche.
    assert r.angle==pytest.approx(45)
    assert r.poids==pytest.approx(1)
    assert r.p==pytest.approx(r.g)
    r=pondererTriangleBase((0.,0.),(10000.,0.),(5000.,sqrt(3)*5000))
    assert r.angle==pytest.approx(60)
    assert r.poids==1
    assert r.p==pytest.approx(r.g)


@pytest.mark.parametrize('decalage',[0.,5e-9])
def test_tangentes_paralleles_et_quasi_paralleles_sans_c_artificiel(decalage):
    h=CercleMetrique((-50000.,0.),50000.)
    d=CercleMetrique((60000.,decalage),50000.)
    r=calculerCandidatBasePondere((0.,0.),(10000.,0.),h,d,(0.,0.),(1.,0.))
    assert r.c is None
    assert r.p==(5000.,0.)
    assert r.segment=='AB'
    assert r.accepte
    assert 'milieu AB' in r.methode


def test_cercles_disjoints_coupes_par_partition():
    h=CercleMetrique((-50000.,0.),50000.)
    d=CercleMetrique((60000.,0.),50000.)
    assert dist(h.centre,d.centre)>h.rayon+d.rayon
    retenus,diagnostics=chercherCandidatsBasePonderes(h,d,[((0.,0.),(1.,0.))])
    assert len(diagnostics)==4  # Tous les couples, pas seulement le plus proche.
    assert len(retenus)==1
    assert retenus[0].p==(5000.,0.)
    assert retenus[0].contraintes==(5.,5.,0.)


def test_toutes_combinaisons_et_deduplication():
    h,d=CercleMetrique((0.,0.),10000.),CercleMetrique((0.,0.),20000.)
    ligne=((0.,0.),(1.,0.))
    retenus,diagnostics=chercherCandidatsBasePonderes(h,d,[ligne,ligne])
    assert len(diagnostics)==8
    assert sorted(r.p[0] for r in retenus)==[-15000.,-5000.,5000.,15000.]
    assert sum('doublon' in r.rejet for r in diagnostics)==4


def test_intersection_tangente_et_tangentes_confondues():
    cercle=CercleMetrique((0.,0.),10000.)
    ligne=((0.,10000.),(1.,0.))
    assert intersectionsDroiteCercle(*ligne,cercle)==[(0.,10000.)]
    retenus,diagnostics=chercherCandidatsBasePonderes(cercle,cercle,[ligne])
    assert len(retenus)==len(diagnostics)==1
    assert retenus[0].p==(0.,10000.)
    assert retenus[0].ab==0
    assert retenus[0].c is None


@pytest.mark.parametrize('inverse',[False,True])
def test_preselection_ne_suffit_pas_controle_final_rejette(inverse):
    a,b,c=(0.,0.),(80000.,0.),(0.,10000.)
    if inverse:a,b=b,a
    h,d=cercle_tangent(a,c),cercle_tangent(b,c)
    r=calculerCandidatBasePondere(a,b,h,d,(0.,0.),(1.,0.))
    assert r.d_min<=30
    assert not r.accepte
    assert '> 20' in r.rejet
    assert r.contraintes[0 if inverse else 1]>20


def test_distances_minimales_aux_trois_contraintes_limite_20km():
    h=d=CercleMetrique((0.,0.),40000.)
    assert distancesContraintesBase((0.,20000.),h,d,(0.,0.),(1.,0.))==(20.,20.,20.)
    ecarts=distancesContraintesBase((0.,20000.001),h,d,(0.,0.),(1.,0.))
    assert ecarts[2]>20


def test_points_confondus_triangle_degenere_et_coordonnees_non_finies():
    r=pondererTriangleBase((0.,0.),(0.,0.),(0.,0.))
    assert r.accepte and r.p==(0.,0.) and r.angle==0
    r=pondererTriangleBase((0.,0.),(10000.,0.),(20000.,0.))
    assert r.accepte and r.angle==0 and r.poids==0
    assert not pondererTriangleBase((float('inf'),0.),(0.,0.)).accepte
    with pytest.raises(ValueError):CercleMetrique((0.,0.),float('nan'))
    with pytest.raises(ValueError):intersectionsDroiteCercle((0.,0.),(0.,0.),CercleMetrique((0.,0.),1))
    with pytest.raises(ValueError):intersectionsDroiteCercle((float('nan'),0.),(1.,0.),CercleMetrique((0.,0.),1))


def test_partition_non_secante_secours_diagnostique_et_deduplique():
    c=CercleMetrique((0.,0.),1000.)
    retenus,diagnostics=chercherCandidatsBasePonderes(c,c,[((0.,5000.),(1.,0.))])
    assert len(retenus)==1
    assert retenus[0].traitement=='secours_non_secant'
    assert retenus[0].p==(0.,3000.)
    assert len(diagnostics)==2
    assert {g.cercle_non_secant for g in diagnostics}=={'horaire','distance'}
    assert 'doublon' in diagnostics[1].rejet


def test_limite_triangle_tres_aigu_et_translation_lambert():
    a,b,c=(0.,0.),(10000.,0.),(5000.,1e10)
    r=pondererTriangleBase(a,b,c)
    assert r.accepte and r.angle<.001
    assert dist(r.p,r.m)<1
    decale=lambda p:(p[0]+700000.,p[1]+6600000.)
    autre=pondererTriangleBase(decale(a),decale(b),decale(c))
    assert autre.p==pytest.approx(decale(r.p),abs=1e-6)
    assert autre.angle==pytest.approx(r.angle)


def test_pipeline_reel_methodes_calques_tooltips_et_sans_ecriture():
    from src.ProjectPersistence import chargerProjetJsonV1
    fichier=Path('tests/fixtures/base_cadran_roncevaux_rocamadour_reference.json')
    sha=sha256(fichier.read_bytes()).hexdigest()
    moteur,_=chargerProjetJsonV1(fichier)
    c=moteur.getScenario().modules['candidatBase']
    c.calculer('ponderee')
    assert c.listeCandidats
    cercles=c.construireRepresentationCarte()
    for objet,g in zip(cercles,c.geometriesCandidats):
        assert objet.pointCentre.coordonneesLambert()==g.p
        assert objet.getRayonKm()==20
        assert objet.tags=={'level':'construction'}
        assert len(objet.tooltips)==9
        assert all(d<=20+1e-9 for d in g.contraintes)
    c.calculer('historique')
    assert len(c.listeCandidats)==1
    assert c.listeCandidats[0].coordonneesLambert()==pytest.approx((583844.131,6399250.150),abs=.001)
    assert all(objet.tooltips==[] for objet in c.construireRepresentationCarte())
    with pytest.raises(ValueError,match='Méthode'):c.calculer('inconnue')
    assert sha256(fichier.read_bytes()).hexdigest()==sha
