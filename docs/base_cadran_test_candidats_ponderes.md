# BaseCadran — Candidats pondérés par les tangentes aux partitions

Expérience sur `dev`, révision de départ `d6ff8fa`, avec les 16 scénarios enregistrés. Aucune date, aucun paramètre de scénario, aucune donnée ni calibration ne sont modifiés.

## Fichiers modifiés

- `src/AlgorithmeBaseCadran.py` : choix de méthode, intégration au pipeline et infobulles.
- `src/GeometrieCandidatsBase.py` : calculs métriques purs, contrôles et déduplication.
- `tests/test_candidats_base_ponderes.py` : nouvelle couverture géométrique et pipeline réel.
- `tests/test_algorithme_base_cadran.py`, `tests/test_algorithme_base_cadran_golden.py`, `tests/test_cadrans_sentinelles_lot3.py` : maintien des vérifications historiques via sélection explicite de la méthode.
- `docs/base_cadran_test_candidats_ponderes.md` : ce rapport.

## Accès aux méthodes et constructions conservées

```python
candidat.calculer()                      # ponderee, méthode active par défaut
candidat.calculer(methode="ponderee")
candidat.calculer(methode="historique")   # comparaison ou retour au comportement antérieur
objets = candidat.construireRepresentationCarte()
```

La liste `listeCandidats`, les calques, les tags et les cercles candidats de **20 km** sont conservés. Aucun paramètre d’IHM ou de JSON n’est ajouté. Le corps historique de `calculer()` est conservé intégralement dans `calculerHistorique()` et vérifié identique par AST ; le répartiteur gère le choix de méthode et les diagnostics. Les classes CercleHoraire, CercleDistance et Partition sont vérifiées identiques par AST à la révision de départ.

La méthode pondérée utilise le **centre Lambert et le rayon métier** produits par la construction existante `CercleGraphique.depuisTroisPoints()` pour le cercle horaire, ainsi que le centre/rayon existants du cercle de distance. Cette construction horaire antérieure, fondée sur la calibration, n’est ni remplacée ni recalibrée. Les calculs de candidats qui suivent ne passent plus par les intersections ou distances des caches pixel arrondis : ils utilisent ces données normatives de cercles métriques. Les directions des partitions existantes sont transportées par la partie linéaire inverse de l’affine `A_inv`, puis normalisées ; leur point d’ancrage est converti en Lambert-93 sans arrondi pixel. Le filtrage préalable des partitions admissibles reste celui de l’algorithme existant.

## Formules effectivement implémentées

Pour chaque partition admissible, ses intersections métriques avec les deux cercles sont calculées séparément. Toutes les combinaisons A/B sont examinées. Pour une direction unitaire u, la projection du centre sur la droite et la distance perpendiculaire donnent les deux racines de l’intersection droite–cercle ; une tangence fournit un point unique.

En A et B, les normales sont les rayons normalisés ; leurs orthogonales définissent les tangentes. Si elles sont déterminées, **C = A + s uA**, avec **s = cross(B−A,uB)/cross(uA,uB)**. C est donc l’intersection des tangentes aux points partition/cercle, indépendamment de l’existence d’intersections entre les cercles.

Les longueurs AB, AC et BC sont mesurées en kilomètres. Le plus petit segment est choisi par priorité stable **AB, puis AC, puis BC** en cas d’égalité. Si `d_min > 30 km`, le couple est rejeté. Sinon :

- M est le milieu du segment retenu ; G est `(A+B+C)/3`.
- θ est **l’angle intérieur du triangle au sommet opposé**, calculé par `atan2(|cross(v,w)|, dot(v,w))` sur les directions unitaires issues de ce sommet. Le produit scalaire conserve son signe.
- `t = min(1,(θ/45)²)` ; `P = M+t*(G−M)`.
- Si C est indéterminé : secours **M = milieu AB**, uniquement si AB ≤ 30 km.
- Le contrôle final utilise les trois distances minimales exactes du modèle métrique : `abs(||P−O_h||−R_h)`, `abs(||P−O_d||−R_d)` et `abs(cross(P−H,u_partition))`, converties en kilomètres. **Les trois doivent être ≤ 20 km**. Un échec rejette le candidat, sans chercher un autre centre.
- Aucune inclusion des trois sommets dans le cercle candidat n’est exigée.

Les constantes numériques ont été fixées avant le relevé des scénarios : **1 µm** pour les limites métriques/tangences et résidus des équations de tangentes ; **10⁻¹²** pour le déterminant des directions unitaires quasi parallèles ; **1 mm** pour la déduplication des centres. Il n’existe aucun plafond géographique sur C. Une intersection non finie, un déterminant quasi nul ou des résidus numériques dépassant 1 µm rendent C indisponible et autorisent seulement le secours AB prévu. Les points confondus et triangles dégénérés sont traités avec un poids nul quand l’angle n’est pas défini. Les données de cercle ou de direction invalides sont refusées explicitement. Aucun seuil n’est modifié après observation des résultats.

Les infobulles indiquent P, AB/AC/BC, le segment retenu, d_min, θ, t, la méthode et les distances aux trois contraintes. Les diagnostics des configurations rejetées restent accessibles dans `diagnosticsCandidats` ; les géométries retenues dans `geometriesCandidats`. Ces informations ne sont pas des paramètres persistants.

## Protocole et données constantes

Le projet réel est chargé nativement avec Skyfield/DE406. Les deux méthodes sont exécutées successivement sur les mêmes modules, sans modifier les entrées des cercles ni des partitions. Les 13 centres historiques ont été relevés **avant** le changement de code ; ils sont ensuite retrouvés exactement, dans le même ordre, par le mode historique. Les empreintes ci-dessous sont vérifiées avant/après les mesures.

| Fichier inchangé | SHA-256 |
|---|---|
| `projets\BaseCadran.json` | `eb817453c382b56bc73102ab232d64287409f6fe29b8339bc5235c0322b93d51` |
| `data\dataset.csv` | `5bb2926f17848c7cd32a96deab60e86e4cdc5fb72853ecdbc3ea32ebf8933637` |
| `data\villes_database.csv` | `669d7f4c4ee14af1714801ddd58475aec913d49f6b41c5909955113956eb0efe` |
| `data\carto\899 - extended v2 corse_calibree.json` | `b443ab8ccdec4f8211d03b7a5d66dfd7edef3b093a0c5cad9a5e6cc07004ed7c` |

Les références géographiques proviennent exclusivement de `data/villes_database.csv`. Correspondances de noms explicites : Saint Amour → Saint-Amour ; Ile d’Aix → Île-d’Aix ; Chateau Gaillard → Château-Gaillard ; Saint Cyr Coetquidan → Coetquidan ; Domremy → Domrémy ; Chalus → Châlus ; Pont de Noirmoutiers → Pont de Noirmoutier. Les autres noms correspondent exactement aux entrées. Les 16 scénarios ont donc tous une référence ponctuelle mesurable. Les distances au lieu sont planes Lambert-93, en kilomètres ; les coordonnées ci-dessous sont des mètres EPSG:2154.

## Comparaison des 16 scénarios

« — » signifie aucun candidat. Les distances sont celles du candidat le plus proche de la base. Dans la dernière colonne : **D** = couples rejetés par d_min > 30 km ; **L** = partitions sans intersection avec au moins un des deux cercles ; **F** = couples rejetés au contrôle final de 20 km. Les L ne sont pas des couples : aucun triangle n’a pu être formé sur ces lignes.

| Événement | Base / scénario | Historiques | Pondérés | Distance historique (km) | Distance pondérée (km) | Rejets D / L / F |
|---|---|---:|---:|---:|---:|---|
| 15 Aout 778 : Bataille de Roncevaux | Saint Amour | 1 | 1 | 8,763 | 8,013 | 7 / 1 / 0 |
| 15 Aout 778 : Bataille de Roncevaux | Rocamadour | 1 | 0 | 15,902 | — | 4 / 2 / 0 |
| 15 Juin 1066 : Guillaume le conquérant | Gergovie | 0 | 1 | — | 8,722 | 3 / 0 / 0 |
| 15 Juin 1066 : Guillaume le conquérant | Carignan | 0 | 0 | — | — | 4 / 2 / 0 |
| 20 Mars 1815 : Début des 100 jours | Ile d'Aix | 2 | 1 | 9,463 | 9,359 | 7 / 1 / 0 |
| 20 Mars 1815 : Début des 100 jours | Rouen | 0 | 0 | — | — | 0 / 4 / 0 |
| 27 Juillet 1214 : Bataille des Bouvines | Metz | 0 | 0 | — | — | 4 / 3 / 0 |
| 27 Juillet 1214 : Bataille des Bouvines | Chateau Gaillard | 0 | 2 | — | 0,421 | 6 / 0 / 0 |
| 30 Mai 1431 : Mort de Jeanne d’Arc | Saint Cyr Coetquidan | 1 | 1 | 23,150 | 23,321 | 3 / 3 / 0 |
| 30 Mai 1431 : Mort de Jeanne d’Arc | Domremy | 1 | 1 | 5,791 | 5,405 | 7 / 1 / 0 |
| 12 Avril 1365 : Traité de Guérande | Reims | 1 | 1 | 13,916 | 10,211 | 3 / 1 / 0 |
| 12 Avril 1365 : Traité de Guérande | Bouvines | 1 | 1 | 14,849 | 17,064 | 3 / 1 / 0 |
| 19 Juillet 933 : Hommage de Guillaume Longue Epée | Chalus | 1 | 1 | 6,748 | 5,768 | 7 / 0 / 0 |
| 19 Juillet 933 : Hommage de Guillaume Longue Epée | Fontevraud | 1 | 0 | 16,491 | — | 0 / 2 / 0 |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Le Goulet | 1 | 1 | 19,415 | 12,534 | 7 / 0 / 0 |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Pont de Noirmoutiers | 2 | 2 | 14,484 | 10,439 | 10 / 3 / 0 |

Bilan : **13 → 13 candidats**, tous géographiquement distincts dans chaque méthode (tolérance statistique de 1 mm). **10 → 10 bases couvertes** à 20 km. Gergovie et Château-Gaillard deviennent couvertes ; Rocamadour et Fontevraud perdent leurs candidats et leur couverture. Le nombre de scénarios sans candidat reste **5**. Île-d’Aix perd un des deux centres historiques mais garde sa couverture. Saint-Cyr reste au-delà de 20 km et recule légèrement.

Sur **46 partitions admissibles**, 24 ne permettent pas de former de couple ; les 22 autres fournissent **88 couples A/B**. **75** sont rejetés par d_min > 30 km ; les **13** restants passent les trois contrôles finaux. Aucun rejet final, repli numérique ni doublon ne se produit dans ce corpus ; ces cas sont vérifiés par les tests unitaires. Parmi les 13 retenus : **AB est minimal dans 5 cas, AC dans 4, BC dans 4**.

Le nombre de cercles ne couvrant pas le lieu de leur scénario passe de **2 à 3** : un candidat de Château-Gaillard est proche, mais l’autre est à **58,077 km** ; Saint-Cyr (**23,321 km**) et un candidat du Pont de Noirmoutiers (**682,334 km**) restent également non couvrants. Un candidat satisfait les trois contraintes géométriques locales sans nécessairement identifier le lieu historique attendu.

## Scénarios prioritaires

### Rouen

Paramètres conservés : `{"calendar": "Standard", "substitution": "11:00", "period": "PM", "circle": "PM"}` ; date : **20/03/1815**.

Centres historiques : aucun.

Centres pondérés : aucun.

Distance à Rouen : **— → — km**.

Les quatre partitions admissibles ne coupent pas chacune les deux cercles : aucun couple A/B, donc aucun C ni centre P n’est disponible. Le mode historique ne produisait déjà aucun candidat. Aucun prolongement artificiel, point B fictif ou réglage de partition n’est introduit pour obtenir une solution.

### Ile d'Aix

Paramètres conservés : `{"calendar": "Déclinaison", "substitution": "-2", "period": "AM", "circle": "AM"}` ; date : **20/03/1815**.

Centres historiques : (377128.726; 6539620.079) ; (371660.687; 6546823.649).

Centres pondérés : (371108.392; 6547405.551).

Distance à Île-d'Aix : **9,463 → 9,359 km**.

| Partition | A | B | C | M | G | P |
|---:|---|---|---|---|---|---|
| 2 | (371777.049; 6547643.831) | (369583.758; 6549652.280) | (370805.805; 6546627.825) | (371291.427; 6547135.828) | (370722.204; 6547974.646) | (371108.392; 6547405.551) |

Un seul couple passe la présélection (sept autres sont rejetés) ; une partition ne fournit pas de couple. Le centre restant est légèrement plus proche : **9,463 → 9,359 km**. La disparition du deuxième centre ne supprime pas la couverture de l’île.

### Saint Cyr Coetquidan

Paramètres conservés : `{"calendar": "Standard", "substitution": "=", "period": "AM", "circle": "AM"}` ; date : **30/05/1431**.

Centres historiques : (314502.221; 6796161.738).

Centres pondérés : (314009.692; 6796312.581).

Distance à Coetquidan : **23,150 → 23,321 km**.

| Partition | A | B | C | M | G | P |
|---:|---|---|---|---|---|---|
| 3 | (333880.218; 6771031.289) | (316039.761; 6803968.595) | (308932.353; 6792533.611) | (312486.057; 6798251.103) | (319617.444; 6789177.832) | (314009.692; 6796312.581) |

Le seul couple présélectionné est retenu après les trois contrôles. Sa distance au lieu passe de **23,150 à 23,321 km** : la base n’est couverte par aucune des deux méthodes. Ce résultat est signalé comme une légère dégradation, sans déplacer P vers Coëtquidan.

## Diagnostics des 13 candidats pondérés

Les trois écarts finaux sont indiqués dans l’ordre horaire / distance / partition. Tous sont ≤ 20 km. Les longueurs et écarts sont en kilomètres.

| Scénario / partition | AB / AC / BC | Segment / d_min | θ intérieur | t | Centre P (m L93) | Écarts finaux (km) | Distance à la base (km) |
|---|---|---|---:|---:|---|---|---:|
| Saint Amour / 1 | 32,295 / 28,668 / 6,662 | BC / 6,662 | 10,537° | 0.054832088 | (887893.004; 6596545.856) | 4,171 / 0,492 / 2,573 | 8,013 |
| Gergovie / 0 | 21,087 / 33,552 / 25,291 | AB / 21,087 | 38,903° | 0.747381609 | (701784.128; 6509074.697) | 5,111 / 8,021 / 6,296 | 8,722 |
| Ile d'Aix / 2 | 2,974 / 1,406 / 3,262 | AC / 1,406 | 25,517° | 0.321551610 | (371108.392; 6547405.551) | 0,319 / 0,560 / 0,627 | 9,359 |
| Chateau Gaillard / 0 | 13,493 / 25,009 / 28,310 | AB / 13,493 | 28,463° | 0.400083912 | (583537.123; 6905041.190) | 5,886 / 5,080 / 3,335 | 0,421 |
| Chateau Gaillard / 1 | 13,854 / 42,339 / 44,563 | AB / 13,854 | 18,113° | 0.162007050 | (526843.407; 6893463.785) | 6,533 / 6,264 / 2,286 | 58,077 |
| Saint Cyr Coetquidan / 3 | 37,459 / 32,935 / 13,464 | BC / 13,464 | 20,800° | 0.213651970 | (314009.692; 6796312.581) | 5,047 / 2,198 / 5,431 | 23,321 |
| Domremy / 0 | 43,231 / 38,271 / 12,022 | BC / 12,022 | 15,473° | 0.118231850 | (897126.440; 6813861.684) | 3,361 / 1,369 / 4,904 | 5,405 |
| Reims / 1 | 19,578 / 28,076 / 14,467 | BC / 14,467 | 28,919° | 0.412996949 | (784975.178; 6904163.346) | 2,693 / 2,604 / 5,854 | 10,211 |
| Bouvines / 1 | 9,233 / 22,252 / 18,572 | AB / 9,233 | 24,043° | 0.285456600 | (699935.278; 7043006.074) | 3,369 / 4,103 / 1,735 | 17,064 |
| Chalus / 1 | 25,034 / 10,823 / 18,292 | AC / 10,823 | 22,820° | 0.257156011 | (548233.166; 6510238.828) | 1,241 / 3,281 / 3,243 | 5,768 |
| Le Goulet / 1 | 7,169 / 15,537 / 12,957 | AB / 7,169 | 27,265° | 0.367100467 | (595165.973; 6888299.471) | 2,553 / 3,127 / 1,574 | 12,534 |
| Pont de Noirmoutiers / 0 | 22,539 / 11,448 / 19,005 | AC / 11,448 | 30,502° | 0.459456778 | (990041.096; 6630775.013) | 2,898 / 4,452 / 4,085 | 682,334 |
| Pont de Noirmoutiers / 5 | 21,318 / 5,722 / 20,763 | AC / 5,722 | 15,556° | 0.119504392 | (309692.980; 6645950.346) | 0,824 / 3,315 / 2,673 | 10,439 |

## Pertes et limites observées

- **Rocamadour** : le candidat historique était à 15,902 km ; la méthode pondérée n’en fournit aucun. Quatre couples possibles sont rejetés, leur d_min minimal étant **131,672 km**, et deux partitions ne permettent pas de couple. La méthode historique peut utiliser une intersection des deux cercles proche d’une partition même lorsque cette partition ne fournit pas un couple de points convenable pour le nouveau triangle.
- **Fontevraud** : le candidat historique était à 16,491 km ; aucune des deux partitions ne fournit de couple A/B. La nouvelle méthode perd donc la solution malgré la proximité historique. Le filtre d’intersection de la nouvelle construction constitue une limite réelle.
- **Bouvines** : le candidat reste couvrant mais s’éloigne de 14,849 à 17,064 km.
- **Château-Gaillard** : deux nouveaux candidats, dont un à 0,421 km ; l’autre est éloigné et peut constituer un faux positif pour cette base.
- **Saint-Cyr** : légère dégradation et absence de couverture, détaillées ci-dessus.
- Le modèle métrique exploite les centres/rayons normatifs des cercles existants. Les écarts avec l’historique associent donc la nouvelle construction pondérée et l’abandon des approximations des intersections pixel ; ils ne résultent pas d’un changement de calibration.
- Les passages aux cas numériques particuliers sont déterministes. La déduplication ne modifie que le nouveau résultat, jamais le mode historique.

Cette expérience ne démontre pas une amélioration générale : la couverture reste identique en nombre, avec deux gains et deux pertes significatives. La méthode est activée conformément à la mission, mais doit rester **expérimentale** et comparable au mode historique. Aucun seuil ni scénario n’est ajusté pour privilégier une base.

## Tests

- Nouveaux tests de géométrie : **19 réussites**. Ils couvrent AB/AC/BC, les limites 30 et 20 km, les tangentes parallèles/quasi parallèles/confondues, les cercles disjoints, les combinaisons multiples, le rejet final, les dégénérescences, les données non finies, la stabilité et la déduplication, ainsi que le rendu réel et ses infobulles.
- Tests ciblés rejoués : `python -m pytest tests/test_candidats_base_ponderes.py tests/test_cadrans_sentinelles_lot3.py::test_bases_reelles_conservent_les_criteres_geometriques -q --tb=short` — **20 réussites en 16,11 s**.
- Une passe ciblée plus large a donné 185 réussites et révélé des attentes historiques devenues anciennes depuis la mise à jour `d6ff8fa` du projet. Les assertions du projet réel sont synchronisées avec le relevé historique préalable à cette mission, puis vérifiées par reconstruction géométrique. La fixture historique Rocamadour reste inchangée et testée séparément.
- Suite complète : `python -m pytest -q --tb=short` — **975 réussites et 2 erreurs d’initialisation Tcl/Tk en 470,53 s**, dans `test_ihm_cadran_final_peut_afficher_evenement_sans_bases` et `test_interface_propose_les_nouveaux_choix_sans_lancer_de_recherche`. Les erreurs signalent des fichiers Tcl non lisibles/absents, pourtant présents lors de la vérification. Ces deux tests sont rejoués ensemble, sans changement de code ni exclusion : **2 réussites en 26,51 s**. Les 977 tests ont ainsi réussi, mais pas dans une même passe complète ; l’intermittence de l’environnement Tcl/Tk reste signalée.
- Tous les scénarios ont été exécutés nativement. Les fichiers de projets, le dataset, le référentiel, le Cadran Final, la calibration et les constructions amont sont vérifiés inchangés.
