# BaseCadran — Cas 2 pondéré par intersections des cercles

Point de départ : `49ce828`, branche `dev`. Le calcul natif couvre désormais **Fontevraud à 18,333633 km**, avec les paramètres enregistrés inchangés. Aucun point de ville n’entre dans la recherche des candidats ; les distances aux villes sont mesurées après construction.

## Fichiers livrés

- `src/GeometrieCandidatsBase.py` : intersections entre cercles et nouveau cas 2 ; extension optionnelle des fonctions existantes pour imposer AB et sélectionner les bons cercles de tangence.
- `src/AlgorithmeBaseCadran.py` : infobulles du nouveau traitement, avec les points A, B, C, M, G et P.
- `tests/test_candidats_base_intersections_cercles.py` : tests du nouveau cas et des limites.
- `tests/test_candidats_base_non_secants.py` : maintien de la couverture du secours A–Q, adaptation de l’attente Fontevraud.
- Ce rapport. Aucun dataset, scénario, calibration, cache ou autre algorithme modifié.

## Construction et repli

1. **La partition coupe les deux cercles** : cas 1 inchangé, avec le plus court segment parmi AB, AC et BC. La loi de pondération et le calcul des tangentes restent communs aux deux cas.
2. **Un seul cercle est coupé et les cercles ont des intersections isolées** : A parcourt toutes les intersections entre cercles et B toutes celles entre la partition et le cercle coupé. Les tangentes sont prises sur le cercle non coupé en A, et sur le cercle coupé en B. **AB est imposé**, même si AC ou BC est plus court. Présélection AB ≤ 30 km ; M = (A+B)/2 ; G = (A+B+C)/3 ; angle intérieur θ en C ; t = min(1,(θ/45)²) ; P = M+t(G−M).
3. Si les tangentes ne donnent pas de C fini vérifiant leurs équations, le calcul conserve M avec poids nul et le diagnostic explicite `milieu AB (tangentes indéterminées)`. Le seuil parallèle existant de 10⁻¹² est conservé.
4. Si aucun couple du nouveau cas 2 n’est valide pour une partition, le secours A–Q du commit précédent est essayé. Il reste également utilisé quand les cercles n’ont pas d’intersection isolée, ou quand aucun cercle n’est coupé par la partition. Les cercles confondus ne produisent pas de fausses intersections.
5. P est accepté uniquement si ses distances aux deux contours de cercles et à la partition sont chacune ≤ 20 km. Le rayon affiché reste 20 km. Les tolérances métriques et la déduplication à 1 mm restent inchangées.

Un candidat du nouveau cas 2 déjà présent par déduplication reste une construction valide : il ne déclenche pas un secours A–Q redondant. Les diagnostics de tous les couples examinés sont conservés sous le type `ponderee_intersections_cercles`, avec le cercle non sécant. Les types antérieurs restent disponibles. La méthode historique est inchangée.

## Fontevraud — 19 juillet 933

Paramètres vérifiés : Standard ; Saint-Valentin ; heure `=` PM ; côté du cercle AM ; partition Dieppe / `-2` / Flip vertical ; distance Stylet / `=` / `/2`.

Cercles en mètres Lambert-93 :

- Horaire : O = (592166,818074 ; 6780190,829961), R = 131371,240623 m.
- Distance : O = (613724,714104 ; 6650874,874773), R = 133213,957457 m.

La partition 1 coupe le cercle de distance en deux points ; les deux cercles se coupent en deux points. Les **quatre couples A/B** sont examinés. L’écart de la partition au cercle horaire reste **9,883049 km**.

### Couple accepté

| Point | Coordonnées Lambert-93, mètres |
|---|---|
| A | (489304.625171 ; 6698473.193346) |
| B | (485202.194795 ; 6685916.571246) |
| C | (488799.216568 ; 6699109.377153) |
| M | (487253.409983 ; 6692194.882296) |
| G | (487768.678845 ; 6694499.713915) |
| P | (487768.678845 ; 6694499.713915) |

| Mesure | Résultat natif |
|---|---:|
| AB | 13,209795 km |
| AC | 0,812507 km |
| BC | 13,674381 km |
| Angle intérieur en C | 53,715975° |
| Poids t | 1 |
| P–cercle horaire | 3,691481 km |
| P–cercle distance | 0,082889 km |
| P–partition | 8,175099 km |
| P–Fontevraud | **18,333633 km** |

AC est bien le plus petit segment, mais **AB est retenu**. L’angle étant supérieur à 45°, t = 1 et P = G. Le cercle candidat couvre Fontevraud sans déplacement ni réglage de seuil. La référence de ville utilisée seulement pour mesurer la couverture est (476749,608118 ; 6679846,995331) m.

### Autres combinaisons et secours

| Partition | Construction | AB ou AQ (km) | Résultat |
|---|---|---:|---|
| 0 | secours A–Q, cercle horaire | 7,764255 | contrainte finale > 20 km |
| 0 | secours A–Q, cercle distance | 119,187789 | écart AQ > 30 km |
| 1 | intersections cercles, AB imposé | 13,209795 | accepté |
| 1 | intersections cercles, AB imposé | 245,797149 | distance minimale > 30 km |
| 1 | intersections cercles, AB imposé | 236,200770 | distance minimale > 30 km |
| 1 | intersections cercles, AB imposé | 213,045637 | distance minimale > 30 km |

Les trois autres couples sont rejetés par AB > 30 km. La partition 0 ne coupe aucun cercle : ses secours A–Q restent évalués. Le secours horaire échoue avec un écart final de 123,924365 km au cercle de distance ; le secours du cercle de distance échoue dès AQ = 119,187789 km. Aucun secours A–Q supplémentaire n’est produit pour la partition 1, où un couple pondéré est valide.

## Comparaison des 16 scénarios locaux

Avant : code `49ce828`. Après : nouveau cas 2. Les projets locaux comportaient déjà des modifications non commitées ; ils ont été conservés tels quels. Le relevé initial natif comporte **18 candidats**, contre 15 dans le rapport de la mission précédente : notamment Carignan dispose maintenant de trois candidats. Cette comparaison utilise les mêmes fichiers locaux avant/après ; elle ne réécrit ni les scénarios ni les attentes golden. « — » signifie aucun candidat.

| Base | Nombre avant | Nombre après | Plus proche avant (km) | Plus proche après (km) | Évolution |
|---|---:|---:|---:|---:|---|
| Saint Amour | 1 | 1 | 8,012738 | 8,012738 | identique |
| Rocamadour | 1 | 1 | 16,992684 | 16,076271 | A–Q remplacé par cas 2 pondéré |
| Gergovie | 1 | 1 | 8,721513 | 8,721513 | identique |
| Carignan | 3 | 3 | 12,723583 | 12,723583 | identique |
| Ile d’Aix | 1 | 1 | 9,358809 | 9,358809 | identique |
| Rouen | 0 | 0 | — | — | identique |
| Metz | 0 | 1 | — | 689,542902 | nouveau candidat, ne couvre pas Metz |
| Chateau Gaillard | 2 | 2 | 0,421360 | 0,421360 | identique |
| Saint Cyr Coetquidan | 1 | 1 | 15,540208 | 15,540208 | identique |
| Domremy | 1 | 1 | 5,404876 | 5,404876 | identique |
| Reims | 1 | 1 | 10,210969 | 10,210969 | identique |
| Bouvines | 1 | 1 | 17,064029 | 17,064029 | identique |
| Chalus | 1 | 1 | 5,768251 | 5,768251 | identique |
| Fontevraud | 1 | 1 | 26,522400 | 18,333633 | A–Q remplacé par cas 2 pondéré |
| Le Goulet | 1 | 1 | 12,533544 | 12,533544 | identique |
| Pont de Noirmoutiers | 2 | 2 | 10,439013 | 10,439013 | identique |

**18 → 19 candidats**. Les **16 centres du cas 1** sont tous conservés aux mêmes coordonnées (comparaison à moins d’un micromètre). Les deux secours A–Q de Rocamadour et Fontevraud sont remplacés, conformément au nouveau routage, par leurs constructions pondérées. Aucun scénario ne perd de candidat et aucune meilleure distance ne se dégrade. Les bases couvertes à 20 km passent de 13 à 14.

Rocamadour reste couvert : **16,992684 → 16,076271 km**. Le nouveau candidat de Metz respecte les contraintes géométriques (écarts 0,065053 / 7,189420 / 15,513916 km), mais reste à **689,542902 km de Metz**. Il n’est pas filtré artificiellement en fonction de la ville ; Metz reste donc non retrouvé, comme Rouen. La géométrie n’implique pas automatiquement la correspondance historique attendue.

## Préservation des données et résultats

Les 16 ensembles de paramètres, les entrées des cercles, toutes les partitions et les signatures de droites sont comparés exactement avant/après. Les empreintes SHA-256 du dataset, du projet local et des villes sont identiques :

| Fichier | SHA-256 |
|---|---|
| `data/dataset.csv` | `5bb2926f17848c7cd32a96deab60e86e4cdc5fb72853ecdbc3ea32ebf8933637` |
| `projets/BaseCadran.json` | `2144d5b75258e64f6128a84a832eba3614a1c395b2790eb301833078db15948f` |
| `data/villes_database.csv` | `669d7f4c4ee14af1714801ddd58475aec913d49f6b41c5909955113956eb0efe` |

Les autres fichiers suivis sont également contrôlés contre leur empreinte initiale, en dehors des cinq fichiers livrés. Les deux projets locaux déjà modifiés sont exclus du commit. Les seuils, les calendriers, les Sentinelles, la calibration S7, les substitutions et les constructions de cercles/partitions sont préservés. Les classes Segment, CercleHoraire, Partition et CercleDistance sont identiques au code initial par comparaison AST.

## Tests

Tests ciblés : **69 réussites en 14,88 s**, commande :

```text
python -m pytest tests/test_candidats_base_intersections_cercles.py tests/test_candidats_base_non_secants.py tests/test_candidats_base_ponderes.py tests/test_algorithme_base_cadran.py -q --tb=short
```

Les 18 nouveaux cas couvrent les intersections entre cercles (sécants, tangents, disjoints, emboîtés, confondus), les quatre couples A/B et les deux rôles des cercles, AB imposé malgré AC plus court, 30 km exact et dépassement, poids fractionnaire, tangentes parallèles/quasi parallèles, contrôle final bloquant, repli A–Q, déduplication sans secours redondant et stabilité après translation/rotation Lambert-93. Le test Fontevraud vérifie les paramètres, le résultat natif, la couverture, les infobulles et le rayon de 20 km, sans modifier le projet.

Suite complète : **1033 réussites, 2 échecs en 289,18 s** (`python -m pytest -q --tb=short`).

- `test_ihm_cadran_final_peut_afficher_evenement_sans_bases` : erreur d’initialisation Tk signalant `Can't find a usable tk.tcl`. Le même test, rejoué isolément sans changement, **réussit en 5,25 s**.
- `test_bases_reelles_conservent_les_criteres_geometriques` : les paramètres locaux modifiés ne correspondent pas aux attentes historiques du projet versionné (deux candidats historiques contre zéro attendu pour Carignan). Le même échec est reproduit avec le code de départ et le projet local ; inversement, les assertions golden inchangées passent pour les 16 scénarios avec le projet versionné et le nouveau code. Cette dernière vérification utilise une copie temporaire du JSON versionné, sans remplacer le projet local. Aucun scénario ni golden n’est réécrit pour masquer cet écart préexistant.
