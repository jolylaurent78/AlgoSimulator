"""Calibration enregistrée, provenance et conventions PM indépendantes."""
import json
from math import cos, radians, sin

import pytest

from src.CadranNationalSentinelles import SentinelleNationale
from src.ReferentielSentinelles import RACINE, ReferentielSentinelles
from src.data_loader import villes_dict


@pytest.fixture(scope='module')
def references():
    return SentinelleNationale()


def test_joker_enregistre_et_ancienne_calibration_archivee(references):
    donnees=json.loads((RACINE/'data/sentinelles_reference_v1.json').read_text(encoding='utf-8'))
    joker=references.referentiel.get('Joker')
    assert (joker.identifiant,joker.note,joker.nature,joker.autorite,joker.valeur_reference)==(
        'Joker','J','axe_rangee','heure','10:56:00')
    assert joker.azimut_physique_initial==153.
    assert references.referentiel.cadran_national.orientation_midi==125.371
    historique=next(h for h in donnees['historique_calibrations'] if h['identifiant']=='Joker')
    ancien=historique['calibration_precedente']
    assert (ancien['autorite'],ancien['valeur_reference'],ancien['azimut_physique_initial'])==('heure','10:55:00',153.)
    assert 'Alise-Sainte-Reine' in ancien['origine']
    assert ancien['statut']=='hypothese_de_travail'
    assert ancien['temoins']['heure_directe']=='10:55:00'
    calcul=historique['calcul_precedent_de406']
    assert calcul['azimut_direct']==pytest.approx(152.7318335370279,abs=1e-8)
    assert calcul['secondes_miroir_tml']==pytest.approx(47343.44082706372,abs=.01)
    assert calcul['heure_miroir_tml']=='13:09:03.440827'
    assert len([h for h in donnees['historique_calibrations'] if h['identifiant']=='S7'])==2


def test_calcul_de406_et_symetrie_tml_distincte_du_miroir(references):
    joker=references.referentiel.get('Joker')
    assert joker.heure_directe.secondes==39360.
    assert joker.azimut_direct==pytest.approx(153.10953410274112,abs=1e-8)
    assert joker.azimut_miroir==pytest.approx(206.89044838586045,abs=1e-6)
    assert joker.heure_miroir.secondes==pytest.approx(47283.36458884875,abs=.01)
    assert joker.heure_miroir.secondes!=round(joker.heure_miroir.secondes)
    # BaseCadran applique la symétrie TML ; le Final consomme le miroir réel.
    assert (86400-joker.heure_directe.secondes)%86400==47040.  # 13:04:00
    assert references.heurePourNote('J','PM').secondes==joker.heure_miroir.secondes
    assert joker.heure_miroir.secondes!=47040.


def test_alise_selection_native_et_distance_lambert(references):
    alise=villes_dict['Alise-Sainte-Reine']
    selection=references.rechercherLigneHoraire(*alise.coordonneesPixelAbs())
    assert (selection.selection,selection.repere,selection.note,selection.branche)==(True,'Joker','J','miroir')
    assert selection.distance_km==17
    direction=references.directionPourNote('J','miroir')
    grille=references.orientationGrille(direction.azimut)
    assert grille==pytest.approx(98.48055161413953,abs=1e-6)
    centre=references.pointCoetquidan.coordonneesLambert()
    point=alise.coordonneesLambert()
    dx,dy=point[0]-centre[0],point[1]-centre[1]
    distance=abs(dx*cos(radians(grille))-dy*sin(radians(grille)))/1000
    assert distance==pytest.approx(17.17966256633054,abs=1e-6)
    assert distance<20


def test_temoins_ne_remplacent_pas_le_calcul_astronomique(tmp_path,references):
    donnees=json.loads((RACINE/'data/sentinelles_reference_v1.json').read_text(encoding='utf-8'))
    joker=next(r for r in donnees['directions'] if r['identifiant']=='Joker')
    joker['temoins']={'azimut_direct':1.,'heure_directe':'01:00:00',
                      'azimut_miroir':2.,'heure_miroir':'02:00:00'}
    fichier=tmp_path/'temoins_non_autoritaires.json'
    fichier.write_text(json.dumps(donnees),encoding='utf-8')
    calcule=ReferentielSentinelles.charger(fichier).get('Joker')
    officiel=references.referentiel.get('Joker')
    assert calcule.directe==officiel.directe
    assert calcule.miroir==officiel.miroir
