# 650 — Lot 2 : cadran national et stylets initiaux

## Activation et compatibilité

`AlgorithmeStyletInitial` et `AlgorithmeLumiereStyletInitial` activent
explicitement `SentinelleNationale`, via leur import nommé `Sentinelle`.
Le `Sentinelle` historique, son CSV et ses signatures ne sont pas modifiés.
Segment, Base et Cadran final gardent cette classe historique jusqu'à leur lot
de migration. Les données et le moteur astronomique validés au lot 1 restent
intacts : les huit horaires sont calculés par `ReferentielSentinelles.charger()`.

L'analyse préalable a identifié deux conventions historiques incompatibles
avec le nouveau cadran : une heure directe stockée comme heure de base du
matin, et des azimuts définis dans l'image. L'intégration sépare désormais
l'identité directe/miroir, la branche solaire matin/après-midi, l'orientation
de grille et l'angle image. Aucun nouvel horaire n'est associé automatiquement
à la direction opposée d'une droite.

## Géométrie

Le centre est le point existant `villes_dict["Coetquidan"]` ; l'orientation
du midi est **125,371° depuis le nord de grille Lambert-93 (EPSG:2154), sens
horaire**. Elle ne vient plus de Coëtquidan–Golfe-Juan dans le nouveau mode.

Pour chaque direction solaire A issue du lot 1 :

```text
beta_grille = (125.371 + 180 - A) modulo 360
v_grille = (sin(beta_grille), cos(beta_grille))
v_image = carteConfig.A @ v_grille
beta_image = atan2(v_image.x, -v_image.y) modulo 360
```

`src/GeometrieCadran.py` fournit `azimutGrilleVersImage(theta, matrice)` et
`LigneAzimutGrille`. L'offset intervient dans l'ancrage Lambert → pixels,
jamais dans le vecteur directeur. La ligne garde son orientation de grille :
ses caches de pixels et ceux de sa copie sont recalculés à partir de la matrice
active lors d'un changement de carte. Elle reste une sous-classe de
`LigneAzimut`, compatible avec le rendu et l'export Traces en azimut image.

Les lignes horaires portent dans leur nom, leurs infobulles et leur libellé
d'impression le repère/note, **directe ou miroir**, et l'heure réelle. S3 et S4
directes sont donc identifiées comme des directions d'après-midi.

## Recherche de proximité et API

`src/CadranNationalSentinelles.py` fournit :

- `rechercherLigneHoraire(px, py, inclureLampouy=False)` → `SelectionHoraire` :
  `selection`, `repere`, `note`, `branche` (directe/miroir), `branche_solaire`,
  `heure_locale` non arrondie, `azimut_solaire`, `orientation_grille`,
  `azimut_image`, `distance_km`, `historique_lampouy`.
- `surLigneHoraire(...)` conserve une façade à cinq valeurs, mais son heure
  correspond déjà à la branche retenue. Les consommateurs migrés utilisent
  le résultat structuré ; ils ne reconstruisent pas l'heure à partir de PM.
- `heurePourNote(note, "directe"/"miroir"/"AM"/"PM")` : AM et PM désignent
  les branches solaires réelles, pas des synonymes de directe et miroir.
- `autreHeure(resultat)` : prend l'autre branche du même repère.
- `afficherLigneMidi`, `afficherLigneHoraire`, `getOrigineStylet`, `getAzimut` :
  interfaces adaptées au nouveau cadran ; l'accès historique reste disponible
  dans la classe originale.

La métrique est volontairement **celle de l'ancien calcul image** : distance
perpendiculaire à la droite en pixels, multipliée par le facteur mètres/pixel
horizontal au centre Coëtquidan (`pixelsVersMetres()`), puis tronquée en
kilomètres avec `int`. La comparaison demeure **strictement `< 20`**.
Ce n'est pas une nouvelle distance orthogonale directement mesurée en Lambert.
Une telle modification sous transformation déformante changerait le modèle et
n'appartient pas à ce lot. L'ordre C,D,E,F,G,A,B,J puis Lampouy est conservé ;
en cas d'égalité, la première droite reste retenue.

L'autre demi-droite géométrique donne la même distance, mais ne crée pas une
troisième solution temporelle. Les axes planète/étoile, leur intersection,
le contrôle de visibilité et le barycentre des trois droites restent inchangés.
Seule la troisième droite, horaire, vient du nouveau cadran.

## Heures, calendriers et lumière

Les valeurs du lot 1 gardent leurs secondes fractionnaires. `Même heure`
conserve l'heure de la branche sélectionnée ; `Symétrique` choisit l'autre
branche du même repère, y compris lorsque la première est déjà le miroir.
La fonction historique `heureSymetrique()` n'est pas utilisée pour les huit
références nationales.

Les sélecteurs sauvegardés restent `Standard`, `Déclinaison`, `=`, `+2`, `-2`,
`Clef`, `11:00`, `AM`, `PM`, `Stylet`, `Manuel`. L'ancien libellé `11:00`
continue à désigner le Joker ; il résout désormais sa vraie heure, 10:55 en
branche AM. Les deux calendriers choisissent leur lettre respective avant
la substitution musicale ; la résolution des deux branches utilise ensuite
ce même repère. Aucun paramètre de scénario n'est réécrit.

Les sorties texte (`heureLocale`, `heureSentinelle`, `heureObservation`) sont
présentées à la seconde. Les champs `heureLocaleSecondes`,
`heureSentinelleSecondes`, `heureObservationSecondes` conservent la précision
de calcul. `Soleil.selectionHoraire` garde la branche du point/stylet ;
`ampmStylet` la décrit en AM/PM. `Soleil.heureAMPM` décrit la branche de l'heure
effectivement utilisée, après le choix Même heure/Symétrique ou la source
manuelle.

`Soleil.dateObservationUT1` est construit avec le contexte temporel du lot 1,
mais **à la date et au lieu d'observation propres à la construction** :

```text
TML = UT1 + longitude_est × 240 secondes
```

Le module `Stylet` reçoit directement ce JD UT1. Il ne reparcourt pas sa chaîne
d'affichage arrondie. Le nom public `heureUTC` reste présent pour l'IHM et les
contrats existants, mais désigne ici la présentation de l'heure UT1, pas l'heure
légale moderne. Un repli sur la chaîne historique existe pour les appels
isolés à `Stylet` dépourvus de JD exact ; le pipeline normal transmet ce JD.
La hauteur du stylet, les octaves, la formule d'ombre et la rotation de carte
ne changent pas.

## Lampouy

Lampouy n'est pas dans les huit références. Son accès passe par un objet de
compatibilité historique ne contenant **que la ligne Lampouy du CSV** : note
L, date 20/08/1152, coordonnées de Carnac, heure arrondie historique, axe
Coëtquidan–Golfe-Juan et symétrie temporelle ancienne. Aucune des huit heures
nationales n'est recalculée à partir des anciennes lignes du CSV.

La recherche des candidats l'inclut uniquement pour le 18/05/1152, comme
auparavant. La recherche automatique de la lumière garde son exclusion
historique ; ses options explicites Lampouy restent proposées pour Loudun.
Ces options conservent aussi la conversion horaire historique arrondie de
longitude. Le nouveau moteur ne transforme pas Lampouy en neuvième Sentinelle.

## Résultats observés sur les projets connus

Comparaison avant/après du lot, en mémoire, sur les deux projets JSON réels
et les fixtures Roncevaux/Bourges. Ni les projets, ni leurs caches ni les
coordonnées des villes n'ont été réécrits. Carte active : 899 Extended V2 Corse
calibrée, inchangée. Les heures ci-dessous sont des présentations arrondies.

Ancienne colonne : contenu de `Candidats.heureSentinelle`, qui était une heure
de base, accompagné de son ancien champ AM/PM. Nouvelle colonne : véritable
heure de la branche retenue, directement exploitable.

| Stylet / scénario | Ancien champ heure / sens | Nouvelle heure et branche | Distance ancienne → nouvelle | État |
| --- | --- | --- | --- | --- |
| Roncevaux | 09:42 / AM | S1 directe 09:43:00 | 12 → 17 km | Sélectionné |
| Golfe Juan | 12:00 / PM | S5 miroir 12:04:01 | 4 → 11 km | Sélectionné |
| Sainte Catherine de Fierbois | 11:42 / PM | S6 miroir 12:22:01 | 2 → 6 km | Sélectionné |
| Alésia | 10:56 / PM | Joker miroir 13:09:03 | 4 → 9 km | Sélectionné |
| Poitiers - Moussai | 12:00 / PM | S5 miroir 12:04:01 | 9 → 14 km | Sélectionné |
| Nouaille Maupertuis | 11:42 / AM | S6 directe 11:42:00 | 1 → 5 km | Sélectionné |
| Saint Valentin | 11:38 / PM | S7 miroir 12:33:19 | 15 → 2 km | Sélectionné |
| 3RDV | 08:12 / AM | S2 directe 08:14:46 | 40 → 42 km | Toujours refusé |
| Loudun | 12:00 / PM | S5 miroir 12:04:01 | 0 → 3 km | Sélectionné |

| Lumière / scénario | Source / option conservée | Heure ancienne → nouvelle | Distance d'ombre ancienne → nouvelle |
| --- | --- | --- | --- |
| Bourges | Stylet / Même heure | 09:42 → 09:43:00 | 543,744 → 540,884 km |
| Strasbourg | Stylet / Même heure | 12:00 → 12:04:01 | 560,833 → 560,384 km |
| Orléans | Stylet / Même heure | 12:22 → 12:22:01 | 117,939 → 117,943 km |
| Sedan | Stylet / Symétrique | 10:56 → 10:55:00 | 231,312 → 231,852 km |
| Cherbourg | Stylet / Même heure | 12:00 → 12:00:00 | 349,193 → 349,193 km |
| Mont Saint Michel | Stylet / Même heure | 11:42 → 11:42:00 | 280,897 → 280,896 km |
| Bordeaux | Stylet / Même heure | 12:22 → 12:33:19 | 292,650 → 296,754 km |
| Pevensey | Manuel / Joker AM Standard | 10:56 → 10:55:00 | 620,578 → 621,623 km |
| Soulac | Stylet / Symétrique | 12:00 → 12:00:00 | 156,770 → 156,770 km |

Les changements proviennent de l'axe de grille fixe, de la conversion affine,
des nouvelles heures et de l'absence d'arrondi temporel avant le calcul solaire.
Sedan et Soulac utilisent bien l'autre branche du repère retenu par leur
stylet. Pevensey garde sa source manuelle : le rattachement du point 3RDV
reste invalide, mais sa lumière manuelle reste calculable. Aucun stylet
précédemment sélectionné dans ces projets ne devient refusé. Le barycentre
Roncevaux passe de (356992,976 ; 6235808,619) à (353782,245 ; 6232108,579) mètres
Lambert, sans changement des axes planète et étoile.

## Contrôles et limites

Les tests couvrent matrices non triviales, offset, recalibrage et copie,
concordance recherche/rendu/légendes, absence d'heure supplémentaire à 180°,
seuil 20 km, Lampouy, les deux calendriers et toutes les substitutions, les
deux branches des huit repères, Même heure/Symétrique, conservation des secondes
jusqu'à l'appel solaire au lieu réel, chargement et persistance des scénarios.
Les deux tests golden migrés gardent toutes les assertions non concernées et
documentent la cause des nouveaux nombres ; les fixtures JSON restent intactes.

```text
python -m pytest tests/test_cadran_national_lot2.py -q
python -m pytest -q
```

La métrique image historique reste dépendante de la calibration : elle est
préservée volontairement, pas présentée comme une distance Lambert exacte.
Les écarts astronomiques du lot 1 demeurent ceux de DE406/Skyfield, sans nouvelle
calibration. Aucun seuil ou résultat n'a été ajusté pour retrouver les anciennes
solutions. Base, Cadran final et les autres usages de `azimutMidi` attendent
leur migration dédiée. Aucun fichier de scénario, cache, donnée physique ou
corpus documentaire des solutions 520/650 n'est modifié par ce lot.
