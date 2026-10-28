# Lot 3 — Cadrans de base et final

## Périmètre et interfaces

Migration de `CercleHoraire`, `CercleDistance`, `LumiereFinal` et `LigneHoraireFinal`. Les classes `Partition`, `CandidatBase`, `Segment` final, `StyletFinal`, `StyletLumiere` et `CandidatFinal` conservent leur corps de code (contrôle AST avant/après). Aucun nouveau moteur astronomique.

Les deux modules importent `SentinelleNationale` sous leur ancien nom local `Sentinelle`. Ils utilisent `rechercherLigneHoraire()` pour le stylet initial de la base, `heurePourNote()`, `directionPourNote()` et l'identité des références `par_note`. Le moteur et les données des lots 1 et 2 restent inchangés. Segment continue à utiliser sa classe historique.

Les paramètres persistants, calendriers, tables musicales, octaves, centres, rayons et critères de sélection sont conservés. Les nouveaux champs calculés ne figurent pas parmi les paramètres ou caches persistants des CSV : aucun champ nouveau n'est requis pour charger un ancien JSON. Aucun projet, cache, scénario ni fixture n'est réécrit par cette livraison.

## Heures, branches et précision

Une substitution choisit d'abord la note dans le calendrier du module, puis AM/PM choisit réellement matin/après-midi. S3/E et S4/F ont donc une direction directe PM et une direction miroir AM. Les autres références ont leur direction directe AM (S5 à 12:00 moyenne locale) et leur miroir PM. Le libellé historique `11:00` désigne toujours le Joker, désormais à 10:55:00 pour AM. `Clef`, lorsqu'il existe, conserve son indice musical.

Les valeurs internes sont les `HeureMoyenneLocale.secondes` fractionnaires du lot 1. Les chaînes HH:MM:SS sont arrondies uniquement pour l'IHM et l'impression. Les calculs nationaux passent par `ContexteObservation.versUT1()` :

```text
JD_UT1 = JD(date à 00:00) + (secondes_TML - longitude_est × 240) / 86400
```

Aucune conversion intermédiaire par une chaîne arrondie. Aucun `24 h − heure` pour les huit références. Le champ historique nommé UTC reste un affichage HH:MM:SS du JD UT1 utilisé par le moteur ; cette migration ne redéfinit pas les échelles temporelles historiques du logiciel.

## Dates et quatre rôles du midi

| Construction | Date et lieu | Référence conservée |
|---|---|---|
| Cercle horaire de base | `dataset.date`, lieu du module (Carnac dans la fixture) | Soleil à l'heure nationale réelle ; `angleHoraire = 180 − azimutSoleil` |
| Distance de base, centre Stylet | `dataset.date`, lieu du module | Heure exacte transmise par CercleHoraire |
| Distance de base, centre Ouverture | `dataset.date`, lieu du module | 12:00:00 moyenne locale explicite, indépendamment de S5 |
| Lumière finale | `dataset.dateSegment`, lieu d'observation du segment | Hauteur et azimut du Soleil à l'heure réelle |
| Correction des lignes finales | `dataset.dateSegment`, Carnac | Azimut du Soleil à 12:00:00 moyenne locale |

Pour Roncevaux, les deux dates sont respectivement le 15/08/778 et le 25/07/778. Leur distinction est testée par des calculs solaires indépendants dans les fixtures.

1. Axe national : 125,371°, nord de grille Lambert-93, centre Coëtquidan ; consommé uniquement par la sélection nationale.
2. Axe final : `StyletFinal.azimutMidi`, direction **image** base → Bourges, inchangée (13,559938° pour Lac Trémelin).
3. Soleil à midi moyen local : calcul astronomique daté, environ 177,911707° dans la fixture ; correction des lignes finales.
4. Soleil à midi vrai : 180° astronomique, origine des écarts solaires ; aucune substitution aux trois axes précédents.

Le cercle de base garde Bourges, le stylet, le milieu, la formule du troisième point et le choix indépendant `cercleAMPM`. Le signe provient directement du Soleil calculé. L'ancienne inversion PM supplémentaire disparaît pour les références nationales : elle inversait une seconde fois le côté solaire. Le choix géométrique AM/PM du cercle n'est pas réinterprété.

Chaque ligne finale garde la formule image :

```text
correction = ±(180 − azimutMidiLocale)  # Endroit / Envers
écart_image = azimut_solaire_de_la_branche − 180 + correction
orientation_image = azimutMidiStylet + écart_image
```

Aucune conversion de cette orientation image en nord de grille. Deux lignes par note : 16 normalement, 18 avec Lampouy. Deux lignes horaires candidates pour la note choisie, identifiée par sa note et non par une égalité de chaînes arrondies. Aucun ajout par opposition à 180°. La structure historique `listeLigneHoraire` et les couples `listeCandidatsHeure` restent disponibles ; `lignesHorairesReference` associe explicitement note, repère, branche, heure exacte, azimut et ligne.

Les libellés imprimés des ombres sont désormais `note branche HH:MM:SS`. Les infobulles donnent aussi matin/après-midi et orientation image. Couleurs, niveaux graphiques et objets imprimables restent inchangés.

## Lampouy

Lampouy reste hors des huit références. L'adaptateur du lot 2 charge sa seule ligne CSV et conserve la date historique du 20/08/1152, Carnac, l'azimut spécifique et la compatibilité de Loudun. Aucun recalcul historique national n'est réintroduit.

Dans CercleHoraire, `138.5°` impose toujours l'angle 41,5° (−41,5° en PM), sans appel au calcul solaire et sans substitution angulaire nationale. Comme dans le mécanisme historique, cette option ne remplace pas l'heure issue du calcul précédent : elle substitue uniquement l'angle. Les champs horaires et leurs secondes restent inchangés ; le JD associé à l'angle est absent, car celui-ci est imposé. Si le centre distance est Stylet, l'heure antérieure est conservée avec sa précision nationale, sans lui substituer l'heure de L. Aucun scénario enregistré n'utilise cette combinaison. Pour Le Goulet, centre Ouverture, le troisième point et le candidat sont identiques ; seule la précision de la conversion du midi explicite produit une variation de distance inférieure à un mètre.

Dans LumiereFinal, l'option persistante `10:09` reste reconnue ; seule Lampouy conserve la symétrie historique et sa conversion horaire de compatibilité. Les lignes finales L gardent leurs azimuts historiques, avec la correction du midi local désormais précise.

## Fixtures prioritaires : avant/après

Mesures prises avant modification à `2ee0f62`, puis après modification, avec les mêmes données et fixtures. Coordonnées en mètres Lambert-93 ; distances en km ; angles en degrés. Les fixtures JSON sont inchangées. Les assertions non temporelles restent conservées ; les assertions temporelles sont confrontées à l'heure du référentiel, au JD indépendant, à `positionSoleil` et à la formule d'ombre.

### Base — Rocamadour / Roncevaux 778

| Grandeur | Avant (lot 2) | Après (lot 3) |
|---|---|---|
| Heure retenue | 10:25 | 10:25:04 |
| Heure du stylet initial | 09:42 | 09:43:00 |
| AM/PM temporel | AM | AM |
| Choix du cercle | AM | AM |
| Azimut solaire | 141.384725 | 141.409885 |
| Angle horaire | 38.615275 | 38.590115 |
| Hauteur solaire | 50.036004 | 50.043728 |
| Distance d'ombre | 296.386680 | 296.305532 |
| Troisième point Lambert-93 | -129818.280709 ; 6880405.879429 | -130262.327963 ; 6880713.201016 |
| Nombre de partitions candidates | 3.000000 | 3.000000 |

La branche retenue est **S4/F miroir AM**. Un candidat avant et après, sélectionné dans la fixture. Son centre passe de (583868.257909, 6399217.698404) à (583844.131423, 6399250.149704). Deux intersections des cercles restent présentes ; distance minimale à une partition : 2,512614 → 2,512418 km, sous le seuil strict de 20 km.

### Final — Lac Trémelin / Roncevaux 778

| Grandeur | Avant (lot 2) | Après (lot 3) |
|---|---|---|
| Heure lumière | 15:59 | 15:59:05 |
| Heure UT1 affichée (champ UTC) | 16:04:18 | 16:04:23 |
| Azimut solaire | 263.209518 | 263.223515 |
| Écart 180 − azimut | -83.209518 | -83.223515 |
| Hauteur solaire | 35.584081 | 35.570403 |
| Distance d'ombre | 349.517593 | 349.693966 |
| Axe image du stylet | 13.559938 | 13.559938 |
| Heure AM de l'ombre | 09:42 | 09:43:00 |
| Deux heures candidates | 09:42 ; 14:18 | 09:43:00 ; 14:21:11 |
| Azimut à midi moyen Carnac | 177.910607 | 177.911707 |
| Écarts image des deux premières lignes | -49.410607 ; 53.589393 | -49.093559 ; 53.270156 |

La lumière est **S3/E directe PM**. Un candidat avant et après, sélectionné dans la fixture. Son centre passe de (325275.437072, 6788452.427900) à (326990.525831, 6788874.562568). Rayon maximal minimal du triplet autour de son barycentre : 4,779094 → 1,333805 km, donc inférieur à 20 km. Le repli des quasi-parallèles n'est pas nécessaire.

## Projets réels examinés en mémoire

Les 18 scénarios de BaseCadran et les 65 de CadranFinal_Solutions ont été chargés depuis leurs JSON, sans sauvegarde. Les deux fixtures complètent les 85 observations. Les états `solutionScenario` sont identiques avant/après pour chaque observation. Les totaux de candidats passent de **15 à 11** pour Base et de **81 à 74** pour Final. Un candidat est un résultat géométrique, pas une validation du scénario sauvegardé : ces états restent indépendants.

Le chargement normal du projet recalcule déjà ses modules en mémoire. Le diagnostic ne déclenche aucune sauvegarde, invalidation de cache, ni recherche globale des projets de l'utilisateur. Aucun résultat n'est forcé pour retrouver une ancienne correspondance.

### Variations du nombre de candidats

Angle = angle horaire signé pour Base, azimut solaire de lumière pour Final. Les autres scénarios conservent leur nombre de candidats, leurs positions peuvent néanmoins évoluer.

| Module / année / scénario | Candidats avant → après | Heure avant → après | Angle avant → après (°) | Distance avant → après (km) |
|---|---|---|---|---|
| Base / 20 Mars 1815 / Rouen | 0 → 1 | 13:04 → 13:09:03 | 18.6059 → -20.2245 | 258.268 → 258.268 |
| Base / 20 Mars 1815 / Aléria | 2 → 0 | 12:22 → 12:33:19 | 4.7577 → -8.5471 | 258.835 → 260.827 |
| Base / 27 Juillet 1214 / Metz | 1 → 0 | 12:22 → 12:33:19 | 8.2048 → -13.5047 | 361.506 → 361.505 |
| Base / 27 Juillet 1214 / Chateau Gaillard | 1 → 0 | 10:56 → 10:55:00 | 31.0817 → 31.4866 | 255.623 → 255.623 |
| Base / 30 Mai 1431 / Domremy | 1 → 0 | 12:18 → 12:22:01 | 11.1425 → -13.2951 | 286.299 → 286.299 |
| Base / 12 Avril 1365 / Bouvines | 0 → 1 | 10:56 → 10:55:00 | 25.1812 → 25.5578 | 340.457 → 341.342 |
| Base / 19 Juillet 933 / Fontevraud | 1 → 0 | 12:22 → 12:33:19 | 8.9269 → -14.5433 | 133.070 → 135.277 |
| Final / 15 Aout 778 / Jumièges | 0 → 1 | 10:25 → 10:25:04 | 131.0884 → 131.1128 | 275.511 → 275.412 |
| Final / 15 Aout 778 / Poitiers | 0 → 1 | 14:18 → 14:21:11 | 240.1494 → 241.0674 | 167.342 → 170.444 |
| Final / 15 Aout 778 / Antioche | 1 → 0 | 12:18 → 12:22:01 | 188.0003 → 190.3005 | 265.960 → 267.423 |
| Final / 30 Mai 1431 / Frontiere Sud Bretagne | 1 → 2 | 11:38 → 11:30:42 | 170.5389 → 166.9759 | 391.668 → 395.871 |
| Final / 27 Juillet 1214 / Barfleur | 1 → 0 | 10:56 → 10:55:00 | 156.5436 → 156.2089 | 383.661 → 384.535 |
| Final / 12 Avril 1365 / Sourdon | 2 → 0 | 12:22 → 12:33:19 | 187.6851 → 192.2752 | 318.088 → 321.807 |
| Final / 20 Mars 1815 / Vézelay | 5 → 3 | 12:00 → 12:04:01 | 181.7294 → 183.8840 | 111.997 → 112.162 |
| Final / 20 Mars 1815 / Dover | 1 → 0 | 11:38 → 11:30:42 | 169.9874 → 166.1753 | 453.471 → 458.652 |
| Final / 20 Mars 1815 / 3RDV | 2 → 1 | 12:00 → 12:04:01 | 181.7294 → 183.8840 | 399.110 → 399.700 |
| Final / 20 Mars 1815 / Portsmouth | 1 → 0 | 11:38 → 11:30:42 | 169.9874 → 166.1753 | 453.471 → 458.652 |
| Final / 20 Mars 1815 / Mayence | 1 → 0 | 12:22 → 12:33:19 | 193.3882 → 199.1803 | 544.480 → 557.487 |
| Final / 15 Juin 1066 / Bâle | 0 → 1 | 09:42 → 09:43:00 | 135.2200 → 135.5014 | 371.189 → 369.678 |
| Final / 19 Juillet 933 /  St Valéry | 0 → 1 | 13:35 → 13:39:02 | 222.9712 → 224.3901 | 364.261 → 370.300 |
| Final / 18 Mai 1152 / Guérande | 2 → 0 | 11:38 → 11:30:42 | 171.2731 → 168.4855 | 377.806 → 380.578 |

### Diagnostic des diminutions

Pour Base, les deux cercles s'intersectent encore dans les cinq cas ci-dessous. Le critère actif est alors la distance intersection → projection sur les partitions candidates, strictement inférieure à 20 km ; le repli réservé à l'absence d'intersection n'est pas utilisé. La correction du signe PM explique les grands déplacements, outre le changement d'heure. Les partitions restent calculées par leur code inchangé.

| Scénario / année | Candidats | Partitions avant → après | Distance minimale à une partition avant → après (km) |
|---|---|---|---|
| Aléria / 20 Mars 1815 | 2 → 0 | 5 → 6 | 6.001 → 24.881 |
| Metz / 27 Juillet 1214 | 1 → 0 | 4 → 2 | 18.142 → 79.978 |
| Chateau Gaillard / 27 Juillet 1214 | 1 → 0 | 2 → 2 | 18.537 → 25.031 |
| Domremy / 30 Mai 1431 | 1 → 0 | 3 → 2 | 7.836 → 112.709 |
| Fontevraud / 19 Juillet 933 | 1 → 0 | 2 → 1 | 7.777 → 46.670 |

Pour Final, R est le plus petit rayon maximal des triplets dont l'intersection est visible ; p est la plus petite distance entre les deux intersections sur le cercle. Un triplet exige R ≤ 20 km ; à défaut, le repli exige p ≤ 10 km. Les minima peuvent appartenir à des combinaisons différentes. Les nombres de triplets/replis acceptés reproduisent exactement les compteurs avant/après des candidats, sans modifier le code de CandidatFinal.

| Scénario / année | Candidats | R minimum avant → après (km) | p minimum avant → après (km) | Triplets/replis avant → après |
|---|---|---|---|---|
| Antioche / 15 Aout 778 | 1 → 0 | 14.291 → 27.098 | 12.908 → 22.626 | 1/0 → 0/0 |
| Barfleur / 27 Juillet 1214 | 1 → 0 | 18.902 → 23.049 | 15.250 → 18.150 | 1/0 → 0/0 |
| Sourdon / 12 Avril 1365 | 2 → 0 | 0.209 → 23.558 | 0.215 → 27.785 | 2/0 → 0/0 |
| Vézelay / 20 Mars 1815 | 5 → 3 | 17.374 → 4.186 | 1.103 → 0.706 | 1/4 → 2/1 |
| Dover / 20 Mars 1815 | 1 → 0 | 0.526 → 40.962 | 0.214 → 16.532 | 1/0 → 0/0 |
| 3RDV / 20 Mars 1815 | 2 → 1 | 130.911 → 113.768 | 3.524 → 3.966 | 0/2 → 0/1 |
| Portsmouth / 20 Mars 1815 | 1 → 0 | 0.522 → 40.932 | 0.212 → 16.544 | 1/0 → 0/0 |
| Mayence / 20 Mars 1815 | 1 → 0 | 39.206 → 79.475 | 5.219 → 16.138 | 0/1 → 0/0 |
| Guérande / 18 Mai 1152 | 2 → 0 | 15.480 → 30.604 | 19.812 → 36.023 | 2/0 → 0/0 |

Vézelay garde trois candidats : deux triplets et un repli. Parmi les combinaisons désormais rejetées, le plus petit écart de paire est 10,347 km et le plus petit rayon de triplet visible est 110,319 km. Pour 3RDV, un seul repli subsiste ; les combinaisons rejetées ont p ≥ 16,685 km et R ≥ 187,249 km. Les autres disparitions totales dépassent les deux seuils, comme indiqué dans le tableau. Aucune compensation géométrique n'est introduite.

## Vérifications et limites

- Suite ciblée existante : **171 tests réussis** (Base, Final, fixtures, contrat de consommation lot 2 et caractérisation Lambert native).
- Nouvelle suite `tests/test_cadrans_sentinelles_lot3.py` : **47 tests réussis**, incluant huit références × deux branches, deux sens de carte, fractions de seconde, calendriers, substitutions, distances, collision volontaire d'heures affichées, Lampouy et légendes.
- Suite complète finale : `python -m pytest -q --tb=short` — **758 tests réussis en 218,04 s**, après les dernières modifications du code.
- Une passe complète intermédiaire a donné 757 réussites et un incident de lecture Tcl à l'initialisation Tk du test de combo `longtext-40`, hors du code modifié. Le fichier `ttk/cursors.tcl` était présent au contrôle suivant ; la suite IHM concernée a ensuite réussi intégralement : **36 tests**. Aucun contournement, exclusion ni changement de test pour cet incident.
- Les corps AST des six classes géométriques protégées sont identiques. Les moteurs des lots 1 et 2, Segment, les données astronomiques/géographiques, calibration et fixtures sont contrôlés par SHA-256.
- Chargement supplémentaire des cinq projets JSON existants : **109 scénarios** (18 Base, 65 Final, 9 Lumière, 8 Segment, 9 Stylet initial). Le SHA-256 de chaque fichier avant/après son chargement est identique.

Les changements de candidats documentés sont attendus de la migration et du retrait de la double inversion PM, avec les seuils métier inchangés. Les états de sélection sauvegardés ne prouvent pas qu'un candidat recalculé subsiste ; leur revue métier relève du lot 4. Aucune référence Swiss Ephemeris/Moshier n'a été utilisée ni recalibrée pour faire correspondre les résultats.

La vérification d'impression porte sur les objets, leurs libellés et leur placement par le moteur d'impression ; aucune impression physique n'est lancée. La validation intégrée et l'examen visuel exhaustif de toutes les superpositions restent au lot 4. La combinaison Lampouy angulaire + centre Stylet n'existe pas dans les scénarios sauvegardés ; son heure dépend toujours du calcul antérieur, comme historiquement. Ce comportement est conservé et signalé pour la validation métier du lot 4 ; aucune nouvelle politique horaire n'est imposée à la substitution angulaire. Les projets et caches restent à recalculer manuellement par l'utilisateur lors de la stabilisation.

Deux changements locaux hors livraison sont préservés et exclus du commit : `config/simulateurAlgo.ini` (déjà modifié au démarrage) et `projets/StyletInitial_solutions.json` (ajout de champs `cached_results: {}` apparu pendant la session, sans appel d'écriture de la mission).
