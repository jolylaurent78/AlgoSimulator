# Base Cadran — Clef et Clef 2 communes au Cadran Final

Ajout ciblé sur `dev`, à partir de `8f7130d`. Aucun dataset, scénario ou paramètre de référence n’est modifié par ce correctif. Le projet local `projets/BaseCadran.json`, déjà modifié avant la mission, reste hors commit ; les modifications utilisateur apparues dans la configuration et le projet Cadran Final pendant la session sont également préservées hors livraison.

## Une seule règle musicale

`src/substitutionsMusicales.py` contient `noteAvecSubstitution()` et la recherche de source de Clef 2, extraites à l’identique du Cadran Final. Base Cadran et Cadran Final appellent **le même objet fonction**, sans import d’un algorithme par l’autre. L’ancien symbole `noteAvecSubstitutionCadranFinal()` et `_noteSourceClef2` restent accessibles depuis `AlgorithmeCadranFinal.py` par alias de compatibilité. Le corps de la règle est vérifié identique par AST après renommage de la fonction.

| Note initiale | Clef historique | Clef 2 |
|---|---|---|
| C / Do | F | G |
| D / Ré | C | G |
| E / Mi | F | G |
| F / Fa | C | G |
| G / Sol | G | G |
| A / La | F | G |
| B / Si | B | B |

Clef 2 cherche Do ou Fa dans l’ordre **note initiale, +2, −2** et retourne Sol si une correspondance existe ; sinon la note initiale est conservée. `Clef` garde exactement l’indice historique de `decalageGamme()`, qui n’est pas modifiée. La valeur persistante reste `Clef` ; aucune valeur `Clef 1` n’est créée.

## Trois modules et sélecteurs

- Heure / `CercleHoraire.heureSubstitution` : `=`, `+2`, `−2`, `Clef`, `Clef 2`, Joker `11:00`, puis Lampouy à la date prévue.
- Partition / `Partition.P2M2` : `=`, `+2`, `−2`, `Clef`, `Clef 2`.
- Distance / `CercleDistance.P2M2` : mêmes cinq choix.
- Les getters existants fournissent les nouvelles valeurs à l’IHM ; aucun CSV d’interface ni widget commun n’est modifié.
- Dans Heure, les deux clefs sont explicitement reconnues comme musicales et ne passent pas dans la branche de substitution angulaire Lampouy.
- Le Joker détecté dans Heure reste J pour les choix musicaux, et `11:00` garde son rôle existant. La gestion particulière de Lampouy, la symétrie temporelle AM/PM, les calendriers et le choix du côté du cercle restent inchangés.

## Carignan — 15 juin 1066

Essai natif sur le scénario local Carignan : calendrier **Déclinaison**, lettre de départ **F**, tous les autres paramètres enregistrés conservés. La sélection de `Clef 2` est faite uniquement en mémoire, sans sauvegarde. Le test fixe également son contrôle initial `=` en mémoire, pour rester utilisable si l’utilisateur enregistre ultérieurement une autre sélection.

| Mesure | Réglage local initial `=` | Essai `Clef 2` |
|---|---|---|
| Note de partition | F | **G** |
| Droites de partition candidates | 3 | 4 |
| Candidats pondérés | 0 | 3 |
| Candidat le plus proche de Carignan | aucun | **12,723583 km** |
| Couples rejetés par d_min > 30 km | 4 | 9 |
| Partitions sans intersection avec les deux cercles | 2 | 1 |

Les signatures géométriques des directions candidates changent réellement. La liste injectée dans `CandidatBase.candidatsPartition` est la nouvelle liste de la partition. Les diagnostics sont reconstruits ; les anciens résultats ne sont pas réemployés. Tous les centres retenus satisfont les trois contraintes finales ≤ 20 km. Les règles de tangentes, barycentre, pondération et validation ne sont pas modifiées.

| Partition | Segment minimal / d_min (km) | Angle intérieur | t | Centre P (Lambert-93 m) | Écarts horaire / distance / partition (km) | Distance à Carignan (km) |
|---:|---|---:|---:|---|---|---:|
| 0 | BC / 26,851457 | 30,823583° | 0.469181850 | (862393.225 ; 6961786.434) | 9,761246 / 5,230432 / 8,017340 | 12,723583 |
| 1 | BC / 28,892469 | 13,083569° | 0.084533228 | (873565.156 ; 6963947.925) | 0,571519 / 3,033026 / 13,148711 | 21,615686 |
| 1 | BC / 25,816202 | 13,083569° | 0.084533228 | (870864.673 ; 6958782.490) | 0,812486 / 2,728754 / 11,748729 | 16,439216 |

Ces trois candidats résultent du nouveau choix musical et des critères géométriques existants. Deux couvrent Carignan (12,724 et 16,439 km) ; le troisième est hors rayon, à 21,616 km. Aucune formule n’est ajustée pour obtenir ce résultat.

## Compatibilité et données préservées

Les **16 scénarios Base Cadran enregistrés**, avec leurs choix existants, donnent exactement les mêmes résultats avant/après : notes, heures et secondes fractionnaires, angles, troisième point, directions de partition, hauteurs, distances et centres candidats. Le calcul antérieur est chargé depuis la révision de départ et comparé sur le même état local du projet, avec le même enrichissement ciblé des affectations de Sentinelles.

Empreinte du projet utilisé, conservée avant/après les essais : `af927bf050545f62c37d3e12157792d946f6d73a957f2b7eec79810889225b5a`.

Toutes les classes du Cadran Final restent identiques par AST ; seules les fonctions musicales ont été extraites puis réexportées. La classe `CandidatBase` et le fichier `GeometrieCandidatsBase.py` sont inchangés. Dataset, projets, Sentinelles, calibrations, méthodes géométriques et paramètres de scénarios restent hors modification.

## Tests

- Nouveaux tests : les sept notes et les deux clefs dans les trois modules, identité de la fonction partagée, Joker, Lampouy, AM/PM, sélecteurs Tk et pipeline réel de Carignan.
- Tests ciblés finaux : `python -m pytest tests/test_base_cadran_clefs.py tests/test_cadran_final_sans_bases.py::test_ihm_cadran_final_peut_afficher_evenement_sans_bases -q --tb=short` — **27 réussites en 15,25 s**, dont les 26 nouveaux cas.
- Une première passe ciblée Base/Final a donné **96 réussites et un incident Tcl/Tk** dans l'ancien test de sélecteurs du Cadran Final. Ce test a réussi au rejeu isolé : **1 réussite en 3,64 s**.
- Suite complète : `python -m pytest -q --tb=short` — **1001 réussites et 2 échecs en 364,10 s**. L’échec Tcl/Tk à l’initialisation de l’IHM Cadran Final est résolu au rejeu dans les 27 tests ci-dessus. L’autre concerne le golden historique de Saint Cyr : le projet local modifié donne `(330717,608618 ; 6775354,348258)` au lieu du centre attendu du projet versionné `(314502,221191 ; 6796161,738146)`.
- L’échec de cette assertion a été reproduit avec **le code HEAD antérieur à la mission et le même projet local** : il préexiste à la modification musicale. Les assertions historiques inchangées des **16 scénarios réussissent avec le projet versionné**, extrait vers un fichier temporaire et chargé sans modifier le fichier utilisateur. Aucune attente golden n’est adaptée aux préférences locales ; ce test reste en échec si on lance la suite complète sur ce projet local modifié. La suite n’est donc pas annoncée intégralement verte dans cet état de travail.
- Les tests existants sont conservés ; seules les assertions de listes de choix Base Cadran sont complétées. Les anciens tests musicaux du Cadran Final restent exécutés sans modification.

## Fichiers livrés

- `src/substitutionsMusicales.py` — règle commune.
- `src/AlgorithmeBaseCadran.py` — trois sélecteurs, appels communs et détection de Lampouy.
- `src/AlgorithmeCadranFinal.py` — import et alias compatibles de la règle extraite.
- `tests/test_base_cadran_clefs.py` — nouvelles vérifications.
- `tests/test_algorithme_base_cadran.py` — attentes des choix disponibles.
- `docs/base_cadran_clefs_communes.md` — ce bilan.
