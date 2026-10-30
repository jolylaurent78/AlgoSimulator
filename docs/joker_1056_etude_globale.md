# Joker à 10:56 — Validation comparative globale

## Recommandation

**10:56:00 TML est recommandé comme nouvelle calibration de référence au regard des critères de cette étude.** Le calcul natif DE406 retrouve simultanément Rouen, Château-Gaillard et Bouvines à moins de 20 km, maintient la sélection native d’Alise-Sainte-Reine, et ne perd aucune couverture mesurable sur les autres constructions contrôlées. L’écart absolu au relevé physique de 153° se réduit à **0,109534°**, contre 0,268166° à 10:55.

**La calibration n’est pas enregistrée par cette mission.** Le référentiel du dépôt reste à **10:55:00**, les paramètres des projets restent inchangés. Le seul fichier publié est ce rapport. L’adoption permanente reste une décision ultérieure.

## Tableau de décision

| Critère | 10:55 | 10:56 | 10:57 |
|---|---|---|---|
| Rouen couvert à 20 km | Non | Oui | Oui |
| Château-Gaillard couvert | Oui | Oui | Oui |
| Bouvines couvert | Oui | Oui | Oui |
| Alise sélectionnée nativement | Oui | Oui | Non |
| Écart absolu du Joker à 153° | 0,268166° | 0,109534° | 0,488412° |
| Bases couvertes sur 16 | 14 | 15 | 15 |
| Couvertures Final mesurables (sur 33) | 29 | 29 | 29 |
| Distance du Pic du Midi | 15,791077 km | 17,798722 km | 19,872536 km |

## Protocole et contrôle des entrées

Code utilisé : **`d07bee282e86024d2d574f28faa7d419ecd33a66`**, branche `dev`. Depuis le code `d5e8f74` de l’étude précédente, seul `docs/joker_1057_etude_globale.md` a été ajouté : les algorithmes sont identiques. La géométrie inclut donc réellement le **cas 2 pondéré à AB imposé** du commit `d5e8f74`, avec maintien du cas 1 et du secours A–Q en repli.

Les empreintes SHA-256 de **tous les fichiers suivis dans la précédente mesure** ont été confrontées aux fichiers actuels : aucune différence. Les deux projets locaux, déjà modifiés par l’utilisateur, sont notamment identiques à ceux de l’étude 10:57. Les résultats natifs **10:55 et 10:57 sont donc réutilisés**, conformément à la mission ; ils ne sont ni interpolés ni transposés vers de nouvelles entrées. Les nouvelles données de 10:56 sont calculées indépendamment.

Le protocole de 10:56 reprend exactement celui de 10:57 :

1. Une copie de `data/sentinelles_reference_v1.json` est créée dans un répertoire temporaire hors dépôt. Seule `valeur_reference` du Joker passe à `10:56:00`. Son autorité reste `heure`, son azimut physique historique reste 153° et l’orientation nationale reste **125,371° depuis le nord de grille Lambert-93**.
2. `ReferentielSentinelles.charger(copie_temporaire)` reconstruit les huit références et leurs deux branches avec Skyfield et `data/ephemeride/de406.bsp`. La référence nationale est observée à Carnac le **15 août 1066 julien**, à 47°35′36″ N / 3°04′47″ O, en temps moyen local converti en UT1. Les témoins historiques du JSON ne remplacent pas la valeur calculée. Les sept autres références sont comparées exactement aux références enregistrées, sans différence.
3. Une substitution temporaire en mémoire de la fabrique `ReferentielSentinelles.charger` transmet ce référentiel aux nouvelles instances `SentinelleNationale`. Elle est restaurée après le calcul. Aucun mécanisme de cache du dépôt n’est modifié.
4. Deux modèles frais sont chargés avec `chargerProjetJsonV1()` : **les 16 bases et les 38 scénarios du Cadran Final**. Le chargement recalcule leurs modules après restauration des paramètres et règles du JSON. Le Final est également recalculé explicitement événement par événement avant les mesures des centres. Les dates et le dataset embarqués dans les projets sont conservés ; aucun scénario n’est sauvegardé.
5. Les calculs utilisent la carte **899 Extended V2 Corse calibrée**, son affine et les données actuelles, sans recalibrage. Les longueurs sont planes Lambert-93 en kilomètres ; les coordonnées sont des mètres EPSG:2154. Toutes les secondes fractionnaires restent disponibles jusqu’aux calculs.
6. Les coordonnées des villes ne servent qu’à mesurer les résultats après construction. Aucun centre n’est déplacé vers une ville, aucun seuil 30/20 km n’est modifié et aucune autre heure n’est recherchée automatiquement.

Les tableaux présentent des arrondis de restitution ; les calculs natifs et les comparaisons utilisent les nombres non arrondis. « — » indique l’absence de candidat ; « n/m » indique l’absence de référence ponctuelle vérifiable.

## Les trois bases — heures, angles et rayons

Paramètres conservés dans les trois exécutions :

- **Rouen** : Standard ; Golfe-Juan ; `11:00` PM ; cercle PM ; Bourges / `=` / Flip vertical ; distance Ouverture / `=` / `/2`.
- **Château-Gaillard** : Standard ; Vouneuil-sur-Vienne ; `11:00` AM ; cercle AM ; Cherbourg / `-2` / Flip vertical ; distance Ouverture / `+2` / `x1`.
- **Bouvines** : Standard ; Alise-Sainte-Reine ; `11:00` AM ; cercle PM ; Dieppe / `+2` / Flip vertical ; distance Stylet / `+2` / `x2`.

| Base | Joker AM | Heure effective TML | Azimut solaire local (°) | Angle horaire de construction (°) | Rayon horaire (km) | Rayon distance (km) | Nombre de candidats |
|---|---|---|---:|---:|---:|---:|---:|
| Rouen | 10:55:00 | 13:05:00 | 198,927594 | 18,927594 | 824,975643 | 258,267872 | 0 |
| Rouen | 10:56:00 | 13:04:00 | 198,606620 | 18,606620 | 838,688414 | 258,267872 | 1 |
| Rouen | 10:57:00 | 13:03:00 | 198,285132 | 18,285132 | 852,915249 | 258,267872 | 1 |
| Chateau Gaillard | 10:55:00 | 10:55:00 | 148,513420 | 31,486580 | 140,773835 | 255,622945 | 2 |
| Chateau Gaillard | 10:56:00 | 10:56:00 | 148,919228 | 31,080772 | 142,424312 | 255,622945 | 2 |
| Chateau Gaillard | 10:57:00 | 10:57:00 | 149,326720 | 30,673280 | 144,128410 | 255,622945 | 2 |
| Bouvines | 10:55:00 | 10:55:00 | 154,442212 | 25,557788 | 192,409016 | 341,341544 | 1 |
| Bouvines | 10:56:00 | 10:56:00 | 154,819655 | 25,180345 | 195,100722 | 340,454985 | 1 |
| Bouvines | 10:57:00 | 10:57:00 | 155,198199 | 24,801801 | 197,885753 | 339,582467 | 1 |

L’azimut local de ces événements historiques est distinct de l’azimut national du 15 août 1066. La période PM des bases conserve la symétrie temporelle autour de midi : à 10:56 AM correspond **13:04:00 PM**. Cette heure ne doit pas être remplacée par le miroir astronomique national.

À Bouvines, le rayon distance est bien recalculé à 10:56, à partir de l’heure du module horaire : **341,341544 → 340,454985 → 339,582467 km**. Il n’est pas figé à la valeur de 10:55. Les deux rayons distance centrés Ouverture utilisent midi moyen et restent inchangés.

### Meilleures constructions et écarts réels

« Cas 1 » conserve le plus court segment parmi AB, AC et BC ; « Cas 2 » impose AB. Les deux utilisent la loi native `t = min(1,(θ/45)²)`. Les centres les plus proches de la ville sont désignés après calcul de toutes les combinaisons.

| Base | Joker AM | Construction / partition | Segment / longueur (km) | Angle en C (°) | Poids t | Centre P Lambert-93 (m) | Écarts horaire / distance / partition (km) | Distance à la ville (km) | Couverture |
|---|---|---|---|---:|---:|---|---|---:|---|
| Rouen | 10:55:00 | rejet, aucun candidat | AB minimal 30,136567 | — | — | — | — | — | Non |
| Rouen | 10:56:00 | Cas 2 pondéré / 0 | AB / 28,814260 | 79,098908 | 1,000000000000 | (577656.953477 ; 6921227.362257) | 0,055675 / 9,465372 / 15,790979 | 17,218031 | Oui |
| Rouen | 10:57:00 | Cas 2 pondéré / 0 | AB / 27,534477 | 79,363590 | 1,000000000000 | (575580.303533 ; 6920162.954640) | 0,049942 / 9,050285 / 15,216410 | 15,925816 | Oui |
| Chateau Gaillard | 10:55:00 | Cas 1 / 0 | AB / 13,493135 | 28,463484 | 0,400083912427 | (583537.122875 ; 6905041.190445) | 5,885727 / 5,079991 / 3,335033 | 0,421360 | Oui |
| Chateau Gaillard | 10:56:00 | Cas 1 / 0 | AB / 10,149944 | 28,820440 | 0,410181597836 | (584734.200582 ; 6906700.300337) | 4,403770 / 3,821678 / 2,542667 | 1,647971 | Oui |
| Chateau Gaillard | 10:57:00 | Cas 1 / 0 | AB / 6,711229 | 29,178867 | 0,420447542492 | (585988.932365 ; 6908402.211641) | 2,895272 / 2,527452 / 1,703776 | 3,760440 | Oui |
| Bouvines | 10:55:00 | Cas 1 / 1 | AB / 9,232846 | 24,042662 | 0,285456600491 | (699935.277691 ; 7043006.073819) | 3,369469 / 4,102904 / 1,735175 | 17,064029 | Oui |
| Bouvines | 10:56:00 | Cas 1 / 1 | AB / 16,736177 | 23,245668 | 0,266844987311 | (699940.589143 ; 7045649.635350) | 6,136991 / 7,489010 / 3,063053 | 15,550449 | Oui |
| Bouvines | 10:57:00 | Cas 1 / 1 | AB / 24,400507 | 22,452023 | 0,248934971322 | (699835.013895 ; 7048390.315308) | 8,994672 / 10,990703 / 4,343551 | 14,435028 | Oui |

**À 10:56, les trois bases sont couvertes.** Château-Gaillard conserve deux candidats et recule de 0,421360 à 1,647971 km ; Bouvines conserve son candidat et se rapproche de 17,064029 à 15,550449 km. Il n’y a aucun rejet résiduel du meilleur candidat accepté : les trois écarts restent chacun sous 20 km.

### Rouen — franchissement du seuil sans ajustement

À 10:55, les deux cercles sont mutuellement sécants mais la partition 0 coupe seulement le cercle horaire. La distance de cette partition au contour du cercle distance vaut **0,670944 km**, sans changement entre les trois calibrations. Le plus petit AB issu des intersections entre cercles et partition vaut **30,136567 km** : rejet par le seuil 30 km. Le secours A–Q échoue aussi, avec un centre à **104,664820 km du cercle horaire**. Aucun centre rejeté n’est présenté comme candidat.

À 10:56, la reconstruction astronomique du cercle horaire produit **AB = 28,814260 km**, sous 30 km, sur cette même partition. AC ne vaut que **0,504072 km**, et BC **28,905336 km** ; AB reste néanmoins imposé. L’angle en C est **79,098908°**, t = 1, donc P = G. Les écarts **0,055675 / 9,465372 / 15,790979 km** satisfont le contrôle final à 20 km. Le cercle de 20 km contient Rouen à **17,218031 km**, avec une marge de **2,781969 km**. Les autres couples et les autres partitions restent évalués ; un seul candidat est accepté. Le secours A–Q n’est pas ajouté à la partition déjà valide.

| Point du cas 2 Rouen à 10:56 | Coordonnées Lambert-93 (m) |
|---|---|
| A | (578996.024229 ; 6911744.190405) |
| B | (575460.951335 ; 6940340.778506) |
| C | (578513.884867 ; 6911597.117860) |
| M | (577228.487782 ; 6926042.484455) |
| G | (577656.953477 ; 6921227.362257) |
| P | (577656.953477 ; 6921227.362257) |

À 10:57, le même mécanisme passe à AB = 27,534477 km et à 15,925816 km de Rouen ; cette amélioration supplémentaire n’est pas nécessaire pour obtenir la couverture à 10:56.

## Référence nationale et sélection d’Alise-Sainte-Reine

| Joker AM | Azimut solaire direct (°) | Écart signé à 153° | Écart absolu à 153° | Heure miroir astronomique TML | Azimut miroir (°) | Orientation miroir Lambert-93 (°) | Distance Alise–axe miroir (km) | Distance native entière (km) | Sélection native |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| 10:55:00 | 152,731834 | -0,268166° | 0,268166° | 13:09:03.440827 | 207,268164 | 98,102836 | 13,883940 | 13 | Oui |
| 10:56:00 | 153,109534 | 0,109534° | 0,109534° | 13:08:03.364589 | 206,890448 | 98,480552 | 17,179663 | 17 | Oui |
| 10:57:00 | 153,488412 | 0,488412° | 0,488412° | 13:07:03.294426 | 206,511588 | 98,859412 | 20,484625 | 20 | Non |

À 10:56, `SentinelleNationale.rechercherLigneHoraire()` renvoie effectivement **sélection vraie, repère Joker / note J, branche miroir**, avec distance native entière **17 km**. La distance orthogonale exacte Lambert-93 est **17,179662566331 km**, soit une marge métrique de **2,820337433669 km** sous 20 km.

Le centre national reste **(315205.579514 ; 6773022.078036) m**, Alise **(812149.275923 ; 6716295.367566) m** ; leur relèvement de grille est **96,512193°**. La branche miroir vaut **98,480551614140°** à 10:56. La direction est obtenue par la formule native `(125,371 + 180 − azimut_solaire) modulo 360`, sans conversion abusive entre nord géographique solaire et nord de grille.

La sélection native utilise son propre contrat historique : distance image convertie avec le facteur local, troncature en kilomètres puis comparaison **strictement `< 20`**. Cette valeur entière n’est pas utilisée comme distance réelle. Elle est vérifiée séparément des contraintes des cercles de BaseCadran. La perte native à 10:57 est reproduite dans les résultats réutilisés ; à 10:56, elle n’a pas lieu.

L’alignement est moins serré qu’à 10:55 (**13,883940 → 17,179663 km**), mais reste sélectionné et sous 20 km en métrique réelle. L’écart solaire absolu au relevé de 153° est en revanche meilleur à 10:56 (**0,109534°**, contre 0,268166° et 0,488412°). Il n’existe pas de nouvelle tolérance physique officielle dans cette étude ; ce constat relatif favorable et la sélection conservée fondent la recommandation de calibration de travail, sans prétendre transformer le relevé historique en mesure plus précise.

Le miroir national à 10:56 est **13:08:03,364589 TML**, distinct des **13:04:00** utilisés par BaseCadran PM. Les secondes fractionnaires ne sont jamais remplacées par une heure arrondie dans le moteur solaire.

## Bilan des seize bases

| Base | Nombre 10:55 / 10:56 / 10:57 | Plus proche 10:55 (km) | Plus proche 10:56 (km) | Plus proche 10:57 (km) | Couverture 10:55 / 10:56 / 10:57 |
|---|---:|---:|---:|---:|---|
| Saint Amour | 1 / 1 / 1 | 8,012738 | 8,012738 | 8,012738 | Oui / Oui / Oui |
| Rocamadour | 1 / 1 / 1 | 16,076271 | 16,076271 | 16,076271 | Oui / Oui / Oui |
| Gergovie | 1 / 1 / 1 | 8,721513 | 8,721513 | 8,721513 | Oui / Oui / Oui |
| Carignan | 3 / 3 / 3 | 12,723583 | 12,723583 | 12,723583 | Oui / Oui / Oui |
| Ile d'Aix | 1 / 1 / 1 | 9,358809 | 9,358809 | 9,358809 | Oui / Oui / Oui |
| Rouen | 0 / 1 / 1 | — | 17,218031 | 15,925816 | Non / Oui / Oui |
| Metz | 1 / 1 / 1 | 689,542902 | 689,542902 | 689,542902 | Non / Non / Non |
| Chateau Gaillard | 2 / 2 / 2 | 0,421360 | 1,647971 | 3,760440 | Oui / Oui / Oui |
| Saint Cyr Coetquidan | 1 / 1 / 1 | 15,540208 | 15,540208 | 15,540208 | Oui / Oui / Oui |
| Domremy | 1 / 1 / 1 | 5,404876 | 5,404876 | 5,404876 | Oui / Oui / Oui |
| Reims | 1 / 1 / 1 | 10,210969 | 10,210969 | 10,210969 | Oui / Oui / Oui |
| Bouvines | 1 / 1 / 1 | 17,064029 | 15,550449 | 14,435028 | Oui / Oui / Oui |
| Chalus | 1 / 1 / 1 | 5,768251 | 5,768251 | 5,768251 | Oui / Oui / Oui |
| Fontevraud | 1 / 1 / 1 | 18,333633 | 18,333633 | 18,333633 | Oui / Oui / Oui |
| Le Goulet | 1 / 1 / 1 | 12,533544 | 12,533544 | 12,533544 | Oui / Oui / Oui |
| Pont de Noirmoutiers | 2 / 2 / 2 | 10,439013 | 10,439013 | 10,439013 | Oui / Oui / Oui |

Total de candidats : **19 / 20 / 20**. Bases couvertes : **14 / 15 / 15 sur 16**. À 10:56, **Rouen est la seule base gagnée**, aucune n’est perdue. Les 13 bases autres que Rouen, Château-Gaillard et Bouvines gardent exactement leurs centres et nombres. Fontevraud et Rocamadour restent couverts ; Metz reste non couvert avec son candidat géométrique éloigné, sans ajout d’un filtre artificiel sur la ville attendue.

## Contrôle des 38 scénarios du Cadran Final

Le calcul utilise le rendu pondéré actif du Cadran Final. Les 38 scénarios incluent la transition sans bases, qui reste sans géométrie. Le Joker PM de la lumière et des ombres utilise le **miroir astronomique**, pas la symétrie temporelle des bases.

| Scénario | Date lumière enregistrée | Notes lumière / ombre | Nombre 10:55 / 10:56 / 10:57 | Distance 10:55 (km) | Distance 10:56 (km) | Distance 10:57 (km) | Couverture 10:55 / 10:56 / 10:57 |
|---|---|---|---:|---:|---:|---:|---|
| Jumièges | 25/07/778 | F / J | 2 / 2 / 2 | 6,973694 | 7,830431 | 8,963911 | Oui / Oui / Oui |
| Grotte Lombrives | 25/07/778 | D / D | 1 / 1 / 1 | 7,768871 | 7,768871 | 7,768871 | Oui / Oui / Oui |
| St Julien de Mailloc | 25/07/778 | F / J | 2 / 2 / 2 | 13,054606 | 11,246382 | 9,420906 | Oui / Oui / Oui |
| Ferté Alais | 25/07/778 | A / A | 3 / 3 / 3 | 11,109340 | 11,109340 | 11,109340 | Oui / Oui / Oui |
| Lac Trémelin | 25/07/778 | E / C | 2 / 2 / 2 | 5,411040 | 5,411040 | 5,411040 | Oui / Oui / Oui |
| Loches | 25/07/778 | D / J | 4 / 4 / 4 | 12,773909 | 10,988199 | 10,509405 | Oui / Oui / Oui |
| Compiègne | 19/04/1431 | E / F | 2 / 2 / 2 | 15,620133 | 15,620133 | 15,620133 | Oui / Oui / Oui |
| Donon | 19/04/1431 | B / J | 2 / 2 / 2 | 13,196265 | 12,922930 | 12,648909 | Oui / Oui / Oui |
| Frontiere Sud Bretagne | 19/04/1431 | B / E | 2 / 2 / 2 | — | — | — | n/m / n/m / n/m |
| Thury sous Clermont | 19/04/1431 | C / C | 2 / 2 / 2 | 15,321620 | 15,321620 | 15,321620 | Oui / Oui / Oui |
| Brétigny | 29/03/1214 | B / B | 2 / 2 / 2 | 13,850852 | 13,850852 | 13,850852 | Oui / Oui / Oui |
| Vézelay | 29/03/1214 | J / B | 2 / 2 / 2 | 16,097791 | 15,916545 | 15,739265 | Oui / Oui / Oui |
| Dinard | 29/03/1214 | E / F | 1 / 1 / 1 | 10,371631 | 10,371631 | 10,371631 | Oui / Oui / Oui |
| Plymouth | 29/03/1214 | F / C | 2 / 2 / 2 | 16,392393 | 16,392393 | 16,392393 | Oui / Oui / Oui |
| Paris | 08/08/1365 | B / B | 2 / 2 / 2 | 5,355728 | 5,355728 | 5,355728 | Oui / Oui / Oui |
| Turin | 08/08/1365 | D / F | 1 / 1 / 1 | 6,687211 | 6,687211 | 6,687211 | Oui / Oui / Oui |
| Boulogne | 08/08/1365 | F / D | 0 / 0 / 0 | — | — | — | Non / Non / Non |
| Lons-le-Saunier | 08/08/1365 | D / C | 2 / 2 / 2 | 11,339380 | 11,339380 | 11,339380 | Oui / Oui / Oui |
| Le Bec | 08/08/1365 | F / F | 1 / 1 / 1 | — | — | — | n/m / n/m / n/m |
| Waterloo | 08/08/1365 | B / D | 2 / 2 / 2 | 4,510437 | 4,510437 | 4,510437 | Oui / Oui / Oui |
| Dover | 28/05/1815 | B / J | 2 / 2 / 2 | — | — | — | n/m / n/m / n/m |
| 3RDV | 28/05/1815 | G / G | 7 / 7 / 7 | 20,510101 | 20,510101 | 20,510101 | Non / Non / Non |
| Portsmouth | 28/05/1815 | B / J | 2 / 2 / 2 | 34,776761 | 34,381043 | 34,006260 | Non / Non / Non |
| Quiberon | 28/05/1815 | J / D | 2 / 2 / 2 | 7,276350 | 3,801047 | 0,355099 | Oui / Oui / Oui |
| Vézelay | 28/05/1815 | G / G | 8 / 8 / 8 | 1,893917 | 1,893917 | 1,893917 | Oui / Oui / Oui |
| Solesmes | 01/09/1066 | C / J | 2 / 2 / 2 | 3,588304 | 2,591807 | 1,876143 | Oui / Oui / Oui |
| Come | 01/09/1066 | D / D | 2 / 2 / 2 | 18,471176 | 18,471176 | 18,471176 | Oui / Oui / Oui |
| Laffrey | 01/09/1066 | F / C | 2 / 2 / 2 | 17,095565 | 17,095565 | 17,095565 | Oui / Oui / Oui |
| Châlons-en-Champagne | 01/09/1066 | G / G | 8 / 8 / 8 | 9,516566 | 9,516566 | 9,516566 | Oui / Oui / Oui |
| Beaufort en Vallée | 18/05/933 | A / C | 2 / 2 / 2 | 5,291691 | 5,291691 | 5,291691 | Oui / Oui / Oui |
| Lampouy | 18/05/933 | D / D | 2 / 2 / 2 | 0,815389 | 0,815389 | 0,815389 | Oui / Oui / Oui |
| Carnac | 18/05/933 | A / A | 2 / 2 / 2 | 13,720955 | 13,720955 | 13,720955 | Oui / Oui / Oui |
| Pic du Midi | 19/08/1152 | F / J | 1 / 1 / 1 | 15,791077 | 17,798722 | 19,872536 | Oui / Oui / Oui |
| Mirebeau | 19/08/1152 | B / B | 2 / 2 / 2 | 13,834458 | 13,834458 | 13,834458 | Oui / Oui / Oui |
| Zone | 19/08/1152 | C / L | 2 / 2 / 2 | — | — | — | n/m / n/m / n/m |
| Le Mans | 19/08/1152 | F / C | 2 / 2 / 2 | 21,747307 | 21,747307 | 21,747307 | Non / Non / Non |
| Montmirail | 19/08/1152 | C / J | 2 / 2 / 2 | 10,954246 | 15,086739 | 11,989224 | Oui / Oui / Oui |
| Scénario par défaut | sans bases | — / — | 0 / 0 / 0 | — | — | — | n/m / n/m / n/m |

**87 / 87 / 87 candidats**, aucune apparition ni disparition de candidat à 10:56 par rapport à 10:55. **29 / 29 / 29 références couvertes sur 33 mesurables**, sans couverture gagnée ou perdue. Le nombre total stable ne signifie pas des centres identiques : les 11 scénarios sélectionnant J en lumière ou en ombre sont recalculés et leurs centres changent ; les autres conservent exactement leurs centres.

- **Pic du Midi** : 15,791077 → **17,798722** → 19,872536 km. À 10:56, la marge est **2,201278 km**, contre seulement 0,127464 km à 10:57. Le candidat reste unique et couvert.
- **Jumièges** et **Montmirail** reculent à 10:56, à 7,830431 et 15,086739 km, mais restent couverts. Le résultat de Montmirail est non monotone entre les trois heures : ce sont des constructions natives, pas une interpolation entre les centres de 10:55 et 10:57.
- Les autres scénarios Joker avec référence mesurable restent couverts, ou restent non couverts pour Portsmouth ; aucune perte n’est cachée par les totaux.

Les 33 références ponctuelles proviennent du CSV courant, avec les correspondances explicites de l’étude précédente : Grotte Lombrives → Grotte de Lombrives ; Lac Trémelin → Lac-de-Trémelin ; Ferté Alais / La Ferté Alais → La Ferté-Alais ; Beaufort en Vallée → Beaufort-en-Vallée ; Boulogne → Boulogne-sur-Mer ; Thury sous Clermont → Thury-sous-Clermont ; Come → Côme. Montmirail utilise en mémoire le point fourni par l’utilisateur (48,10° N ; 0,769° E), sans écriture dans le CSV. **Frontiere Sud Bretagne, Le Bec, Dover, Zone et Scénario par défaut** n’ont pas de référence ponctuelle vérifiable ; leurs nombres de candidats sont contrôlés, mais leur couverture n’est pas inventée.

### Heures et directions Joker sélectionnées dans le Final

Pour les neuf scénarios à ombre J, les heures nationales passent à **10:56:00 AM** et **13:08:03,364589 PM**. Les directions sont recalculées avec les azimuts nationaux 153,109534102741° et 206,890448385860°, en conservant l’axe du stylet et le sens de carte enregistrés.

| Scénario à ombre J | Direction image AM à 10:56 (°) | Direction image PM à 10:56 (°) |
|---|---:|---:|
| Jumièges | 260,480732 | 314,261646 |
| St Julien de Mailloc | 347,519002 | 41,299917 |
| Loches | 347,519002 | 41,299917 |
| Donon | 263,046303 | 209,265389 |
| Dover | 134,208219 | 187,989134 |
| Portsmouth | 186,290090 | 132,509176 |
| Solesmes | 5,519598 | 311,738684 |
| Pic du Midi | 188,687777 | 134,906863 |
| Montmirail | 114,097575 | 60,316661 |

La lumière J de **Vézelay (1214)** utilise 13:08:03,364589 ; celle de **Quiberon** utilise 10:56:00. Leurs ombres sélectionnées restent B et D. Les autres lignes J disponibles sont elles aussi recalculées, mais ne deviennent pas candidates lorsqu’elles ne sont pas sélectionnées.

## Vérifications, tests et conservation

- Empreintes des entrées de 10:55/10:57 vérifiées avant réutilisation : aucune différence. Le fichier de mesures antérieur provient du code `d5e8f74` ; la différence jusqu’au point de départ `d07bee2` ne porte que sur son rapport.
- Exécution native à 10:56 : **16 bases et 38 scénarios Final**, sans exception, mêmes paramètres, règles et dates. Toutes les références solaires hors Joker restent exactement identiques. La carte et son orientation ne changent pas.
- Vérification de chaque candidat Base accepté : présélection ≤ 30 km, chacun des trois écarts finaux ≤ 20 km ; pour le nouveau cas 2, AB est imposé et le poids suit la loi native. Les seuils ne sont pas ajustés.
- Comparaison des listes de centres : les 13 bases non ciblées et les scénarios Final sans Joker sélectionné conservent exactement leurs centres. Aucun nombre de candidats Final ni statut de couverture mesurable ne change à 10:56 par rapport à 10:55. La sélection native d’Alise est vraie, contrôlée par appel réel à `rechercherLigneHoraire()`.
- Tests automatisés ciblés : **184 réussites en 14,61 s** :

```text
python -m pytest tests/test_referentiel_sentinelles.py tests/test_cadran_national_lot2.py tests/test_cadran_final_pondere.py tests/test_candidats_base_intersections_cercles.py -q --tb=short
```

Ces tests portent sur la calibration persistée 10:55. L’hypothèse 10:56 est contrôlée par le pipeline natif temporaire et les assertions comparatives ci-dessus ; aucune assertion de calibration enregistrée n’est réécrite pour l’hypothèse.

La suite complète n’est pas répétée pour un rapport sans changement de code. Son dernier résultat sur les mêmes algorithmes, lors de la livraison du cas 2, est **1033 réussites, 2 échecs** : échec Tk d’initialisation `tk.tcl` passant au rejeu isolé, et écart golden historique déjà présent sur le projet local modifié. L’échec golden est reproduit avec le code initial sur ce projet local ; les assertions inchangées passent pour les 16 scénarios du projet versionné. Voir `docs/base_cadran_cas2_intersections_cercles.md` et `docs/joker_1057_etude_globale.md`.

### Empreintes des données inchangées

Tous les fichiers suivis sont contrôlés avant et après l’exécution. Les empreintes essentielles sont :

| Fichier | SHA-256 |
|---|---|
| `data/sentinelles_reference_v1.json` | `3709cc15d107f881333774b69f04dc3efdc2c1468f3f54e3355f40dee70120fa` |
| `config/cadran_national_v1.json` | `700f949d73885b316e3dcd6d3316917a96a8d2fd4442933d025753353acd6ac5` |
| `data/dataset.csv` | `5bb2926f17848c7cd32a96deab60e86e4cdc5fb72853ecdbc3ea32ebf8933637` |
| `projets/BaseCadran.json` | `2144d5b75258e64f6128a84a832eba3614a1c395b2790eb301833078db15948f` |
| `projets/CadranFinal_Solutions.json` | `004d77e6e8a632fdeec9af47f0ae7a1a0fffbec086eebfb81b4affc4ac54cb79` |
| `data/villes_database.csv` | `669d7f4c4ee14af1714801ddd58475aec913d49f6b41c5909955113956eb0efe` |
| `data/carto/899 - extended v2 corse_calibree.json` | `b443ab8ccdec4f8211d03b7a5d66dfd7edef3b093a0c5cad9a5e6cc07004ed7c` |

Matrice affine conservée : `[[0.00587622761992504, -5.598609383340125e-05], [-5.5865560078069346e-05, -0.005888697387310563]]` ; offset : `[69.2397698980756, 44006.2730209867]`.

Empreinte des mesures antérieures réutilisées : `3d3af61803ec028a8e1c3a1239da15d47b9f3193379c9850968553a46dfbe8b6`.

## Décision d’adoption

Les sept critères de la mission sont satisfaits sur les entrées contrôlées : les trois bases sont couvertes, Alise conserve sa sélection native, aucune autre base ni référence Final mesurable ne perd sa couverture et l’écart solaire au relevé de 153° diminue. **Adopter 10:56 comme nouvelle calibration de travail est recommandé.** La marge d’Alise est plus faible qu’à 10:55 mais reste positive ; Pic du Midi conserve davantage de marge qu’à 10:57. Cette recommandation n’affirme pas que toutes les distances s’améliorent, ni que les scénarios sans référence ponctuelle sont validés géographiquement.

**Aucune adoption permanente n’a été effectuée ici** : le Joker reste enregistré à 10:55:00, le relevé de 153°, l’axe 125,371°, les projets, les caches et les algorithmes sont inchangés. Ce rapport constitue la seule livraison de cette mission.
