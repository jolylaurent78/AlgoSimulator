# BaseCadran — Secours pour les partitions non sécantes

Correction sur `dev`, à partir de `dd63ff3`, sans modifier les données ni les 16 scénarios enregistrés. Le traitement pondéré existant est conservé ; un second traitement examine les proximités sans intersection.

**Résultat Fontevraud : un secours devient admissible, mais son cercle de 20 km ne contient pas Fontevraud.** L’écart observé d’environ 9 km est confirmé à **9,883049 km** entre une partition et le contour du cercle horaire. Le centre imposé par le milieu A–Q est à **26,522400 km** de la ville. Ce résultat n’est ni déplacé ni remplacé artificiellement pour satisfaire le critère de couverture.

## Fichiers modifiés

- `src/GeometrieCandidatsBase.py` : secours non sécant, diagnostics et déduplication commune.
- `src/AlgorithmeBaseCadran.py` : préfiltre à 30 km avec garantie métrique, et infobulles du secours.
- `tests/test_candidats_base_non_secants.py` : 14 nouveaux tests.
- `tests/test_candidats_base_ponderes.py` : adaptation du test qui rejetait auparavant toute partition non sécante ; les autres tests sont conservés.
- `docs/base_cadran_secours_non_secants.md` : ce rapport.

## Traitements et contrôles

### Cas 1 préservé

Quand la partition coupe les deux cercles, les mêmes couples A/B sont parcourus. Les tangentes, C, le plus court segment, la présélection à 30 km, M, G, l’angle intérieur, le poids quadratique et P sont inchangés. Les fonctions `intersectionsDroiteCercle`, `pondererTriangleBase`, `calculerCandidatBasePondere` et `distancesContraintesBase` sont vérifiées identiques par AST à la révision de départ. Les 13 candidats précédemment obtenus restent présents avec exactement les mêmes coordonnées.

### Cas 2 ajouté

Pour chaque cercle non sécant avec une partition, la direction u est normalisée en Lambert-93 et n = (−uy, ux). Avec O le centre et L un point de la droite :

- `s = (O−L)·n` ; `H = O−s n`.
- `A = O−sign(s) R n` : point du cercle le plus proche de la droite.
- `Q = H` : H est aussi la projection orthogonale de A sur la droite.
- `d = (|s|−R)/1000` km. Au-delà de 30 km, le secours est rejeté avant construction du centre.
- `P = (A+Q)/2`, sans C, G ni barycentre de tangentes.
- Les trois distances minimales de P aux contours horaire/distance et à la partition sont calculées par le contrôle métrique déjà existant. P est retenu seulement si chacune est ≤ 20 km.
- Si les deux cercles ne coupent pas la partition, les deux secours sont examinés. La déduplication à 1 mm s’applique aux deux traitements.

Les tolérances numériques existantes sont conservées : 1 µm sur les limites métriques, 1 mm pour les centres identiques. Les seuils métier restent **30 km en présélection, 20 km au contrôle final et 20 km de rayon candidat**. Aucun seuil ni paramètre n’est ajusté après observation des résultats.

Le diagnostic conserve les champs antérieurs et ajoute `traitement` (`ponderee` ou `secours_non_secant`), `cercle_non_secant`, `q` et `distance_aq`. A, P, les trois écarts finaux, l’acceptation et le motif de rejet sont consultables dans `diagnosticsCandidats`. Les infobulles des secours acceptés affichent ces informations et leurs coordonnées Lambert-93.

### Préfiltre des partitions

Le cercle de préfiltrage passe de `rayon+20` à **`rayon+30`**. Un contrôle métrique complémentaire retient également une ligne dont la distance exacte au cercle horaire est ≤ 30 km, même si le cache pixel n’annonce aucune intersection. Il évite un rejet à la limite par arrondi ou représentation cartographique. La construction des notes, points et directions reste identique ; seules les conditions d’admission au calcul évoluent. Un test force l’absence d’intersection du cache pixel pour une ligne à 25 km : elle reste examinée.

Dans les 16 scénarios actuels, le nombre de partitions admissibles reste **46** avant/après. Aucun candidat du cas 1 n’est ajouté, supprimé ou déplacé par ce changement de préfiltre sur ce corpus.

## Fontevraud — données et contraintes exactes

Les paramètres enregistrés ont été vérifiés sans modification : Standard, stylet Saint-Valentin, heure `=` PM, cercle horaire AM ; partition Dieppe / `−2` / Flip vertical ; distance centrée Stylet / `=` / octave `/2`. Événement : 19 juillet 933.

Référence Fontevraud : **(476749.608 ; 6679846.995) m EPSG:2154**, issue de `data/villes_database.csv`. Toutes les longueurs ci-dessous sont en kilomètres et les coordonnées en mètres Lambert-93.

| Contrainte | Centre | Rayon (km) |
|---|---|---:|
| Horaire | (592166.818 ; 6780190.830) | 131,371241 |
| Distance | (613724.714 ; 6650874.875) | 133,213957 |

Les deux cercles sont mutuellement sécants : distance de leurs centres **131,100569 km**, comprise entre la différence et la somme des rayons. **L’intersection manquante est celle de la partition avec le cercle horaire**, pas une absence d’intersection mutuelle des deux cercles.

| Partition (indice) | Ancrage Lambert | Direction unitaire Lambert | Intersections horaire / distance | Écart partition–horaire / distance (km) |
|---:|---|---|---|---|
| 0 | (708719.449 ; 7057790.509) | (-0.769400740895 ; -0.638766389152) | 0 / 0 | 7,764255 / 119,187789 |
| 1 | (481660.132 ; 6688972.803) | (0.757121345375 ; -0.653274267346) | 0 / 2 | 9,883049 / 0,000000 |

### Les trois possibilités de secours examinées

| Partition / cercle non sécant | A | Q (= H) | AQ (km) | Centre P | Écarts P horaire / distance / partition (km) | Décision |
|---|---|---|---:|---|---|---|
| 0 / horaire | (508251.285 ; 6881267.960) | (503291.740 ; 6887241.783) | 7,764255 | (505771.513 ; 6884254.872) | 3,882127 / 123,924365 / 3,882127 | contrainte finale > 20 km |
| 0 / distance | (528632.116 ; 6753369.792) | (452498.962 ; 6845072.966) | 119,187789 | non construit | non calculés | écart AQ > 30 km |
| 1 / horaire | (506345.367 ; 6680726.860) | (499889.026 ; 6673244.192) | 9,883049 | (503117.196 ; 6676985.526) | 4,941524 / 19,566304 / 4,941524 | accepté |

La partition 0 ne coupe aucun cercle. Son secours horaire est admissible à 7,764255 km mais échoue au troisième élément : **123,924365 km du cercle de distance**. Le secours de ce cercle distance est rejeté directement : AQ = **119,187789 km**.

La partition 1 coupe le cercle de distance en deux points, mais manque le cercle horaire de **9,883049 km**. Son secours horaire est retenu à **(503117,196 ; 6676985,526)**, avec les écarts finaux **4,941524 / 19,566304 / 4,941524 km**. Il satisfait donc intégralement la règle prescrite.

**La couverture de Fontevraud n’est néanmoins pas obtenue : P est à 26,522400 km de la référence.** Le point de la ville est lui-même à 21,566712 km du contour horaire, 6,791626 km du contour distance et 10,117263 km de la partition 1. Ces distances ne sont pas utilisées pour choisir le centre. Elles ne démontrent pas une impossibilité globale de trouver un autre centre : le secours examine uniquement le milieu prescrit A–Q, sans recherche ou déplacement vers la ville.

Le mode historique reste accessible par `calculer(methode="historique")`. Sur ce même scénario, il conserve un candidat à **16,490578 km**, centré en (485382.000 ; 6693897.652). Aucun mélange automatique avec ce résultat historique n’est ajouté au nouveau mode.

## Comparaison avant/après des 16 bases

Avant : méthode pondérée du cas 1 seule. Après : même méthode complétée par le secours non sécant. Les deux exécutions utilisent les mêmes données et paramètres. « — » indique l’absence de candidat. Les distances donnent le candidat le plus proche de la référence ponctuelle du scénario.

| Événement | Base | Avant | Après | Nouveaux cas 2 | Distance avant (km) | Distance après (km) |
|---|---|---:|---:|---:|---:|---:|
| 15 Aout 778 : Bataille de Roncevaux | Saint Amour | 1 | 1 | 0 | 8,012738 | 8,012738 |
| 15 Aout 778 : Bataille de Roncevaux | Rocamadour | 0 | 1 | 1 | — | 16,992684 |
| 15 Juin 1066 : Guillaume le conquérant | Gergovie | 1 | 1 | 0 | 8,721513 | 8,721513 |
| 15 Juin 1066 : Guillaume le conquérant | Carignan | 0 | 0 | 0 | — | — |
| 20 Mars 1815 : Début des 100 jours | Ile d'Aix | 1 | 1 | 0 | 9,358809 | 9,358809 |
| 20 Mars 1815 : Début des 100 jours | Rouen | 0 | 0 | 0 | — | — |
| 27 Juillet 1214 : Bataille des Bouvines | Metz | 0 | 0 | 0 | — | — |
| 27 Juillet 1214 : Bataille des Bouvines | Chateau Gaillard | 2 | 2 | 0 | 0,421360 | 0,421360 |
| 30 Mai 1431 : Mort de Jeanne d’Arc | Saint Cyr Coetquidan | 1 | 1 | 0 | 15,540208 | 15,540208 |
| 30 Mai 1431 : Mort de Jeanne d’Arc | Domremy | 1 | 1 | 0 | 5,404876 | 5,404876 |
| 12 Avril 1365 : Traité de Guérande | Reims | 1 | 1 | 0 | 10,210969 | 10,210969 |
| 12 Avril 1365 : Traité de Guérande | Bouvines | 1 | 1 | 0 | 17,064029 | 17,064029 |
| 19 Juillet 933 : Hommage de Guillaume Longue Epée | Chalus | 1 | 1 | 0 | 5,768251 | 5,768251 |
| 19 Juillet 933 : Hommage de Guillaume Longue Epée | Fontevraud | 0 | 1 | 1 | — | 26,522400 |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Le Goulet | 1 | 1 | 0 | 12,533544 | 12,533544 |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Pont de Noirmoutiers | 2 | 2 | 0 | 10,439013 | 10,439013 |

Bilan : **13 → 15 candidats**, avec conservation exacte des 13 centres précédents et des entrées géométriques amont. Les seuls centres ajoutés proviennent du **cas 2**, pour Rocamadour et Fontevraud. Aucun scénario ne perd de candidat ni ne voit sa meilleure distance se dégrader. Les bases couvertes à 20 km passent de **11 à 12** : Rocamadour est retrouvé à **16,992684 km** ; Fontevraud n’est pas couvert par son nouveau centre.

Sur les **25 secours examinés**, 16 sont rejetés par AQ > 30 km, 7 par un contrôle final > 20 km et 2 retenus. Aucun doublon natif n’a été rencontré ; les tests synthétiques vérifient sa suppression, y compris quand les deux cercles produisent le même centre. Les méthodes, calculs de tangentes et 13 résultats du cas 1 restent identiques.

Les références proviennent du CSV de villes existant, avec les correspondances usuelles : Saint Amour → Saint-Amour ; Ile d’Aix → Île-d’Aix ; Chateau Gaillard → Château-Gaillard ; Saint Cyr Coetquidan → Coetquidan ; Domremy → Domrémy ; Chalus → Châlus ; Pont de Noirmoutiers → Pont de Noirmoutier. Aucun point géographique n’est inventé.

## Données et vérifications

Les modifications locales préexistantes de projets sont préservées et exclues du commit. Les fichiers suivants sont vérifiés identiques avant/après les mesures :

| Fichier | SHA-256 |
|---|---|
| `data\dataset.csv` | `5bb2926f17848c7cd32a96deab60e86e4cdc5fb72853ecdbc3ea32ebf8933637` |
| `projets\BaseCadran.json` | `af927bf050545f62c37d3e12157792d946f6d73a957f2b7eec79810889225b5a` |
| `data\villes_database.csv` | `669d7f4c4ee14af1714801ddd58475aec913d49f6b41c5909955113956eb0efe` |

Les paramètres des 16 scénarios et les centres/rayons des cercles sont comparés exactement ; les candidats antérieurs restent identiques à moins d’un micromètre. Les formules du cas 1 et le calcul historique sont vérifiés identiques par AST. Les fichiers de Sentinelles, le dataset, les substitutions, les calibrations et `AlgorithmeCadranFinal.py` ne sont pas modifiés.

## Tests

- Tests ciblés : `python -m pytest tests/test_candidats_base_non_secants.py tests/test_candidats_base_ponderes.py tests/test_algorithme_base_cadran.py -q --tb=short` — **51 réussites en 17,27 s**.
- 14 nouveaux cas couvrent un seul cercle non sécant (les deux rôles), deux cercles non sécants, 9 km, les limites 30 et 20 km, la troisième contrainte bloquante, la conservation du cas 1, les tangences, la déduplication, la stabilité en Lambert-93, le préfiltre et le scénario réel Fontevraud. Le test ancien qui rejetait une partition non sécante est adapté au secours désormais attendu.
- Suite complète : **1016 réussites et 1 échec en 339,64 s**. L’échec concerne le golden historique Saint Cyr sur le projet local modifié, avec le centre `(330717,608618 ; 6775354,348258)` au lieu de l’attente versionnée `(314502,221191 ; 6796161,738146)`. Le même échec est reproduit avec le code de départ et le projet local ; inversement, les assertions golden inchangées passent pour les 16 scénarios avec le projet versionné et le nouveau code. La vérification utilise une copie temporaire du JSON versionné, sans remplacer le projet local. Aucune assertion ni aucun scénario n’est modifié pour masquer cet échec préexistant.

## Limites restantes

La correction reconnaît maintenant les proximités sans exiger une intersection parfaite, et n’introduit aucune régression géométrique sur les 16 bases contrôlées. Elle ne garantit pas que le milieu A–Q couvre le lieu attendu : **le critère de couverture de Fontevraud reste non atteint**. Obtenir un autre centre exigerait une évolution du modèle, hors de cette correction ; aucune optimisation ni utilisation des coordonnées de la ville pour déplacer P n’est ajoutée.
