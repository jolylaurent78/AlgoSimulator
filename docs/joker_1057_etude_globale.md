# Joker à 10:57 — Étude globale native

## Décision

**10:57 retrouve simultanément Rouen, Château-Gaillard et Bouvines, mais n’est pas recommandé comme calibration globale définitive en l’état.** Les trois bases sont couvertes à 20 km et aucune autre base ne perd sa couverture. En revanche, l’alignement d’Alise-Sainte-Reine se dégrade : sa distance réelle à l’axe Joker miroir passe de **13,883940 à 20,484625 km**, et la sélection native devient **fausse**. L’écart au relevé solaire historique de 153° augmente aussi. L’absence de compromis sur Alise demandée par la mission n’est donc pas satisfaite.

La calibration persistée reste **10:55:00**. Aucun projet, dataset, scénario, réglage de carte ou référentiel n’est enregistré. Le livrable de cette étude est uniquement ce rapport.

## Méthodologie et périmètre exacts

- Code : commit **`d5e8f748c4e0101de9ca645eeac66f10c66218af`**, branche `dev`, soit `d5e8f74`. Le **nouveau cas 2 pondéré de Fontevraud est implémenté et intégré**, AB imposé ; le secours A–Q demeure le repli. L’essai de Rouen utilise effectivement cette construction native.
- Deux copies temporaires de `data/sentinelles_reference_v1.json` sont créées hors dépôt. A reprend 10:55:00 ; B modifie seulement `directions[Joker].valeur_reference` en 10:57:00. L’autorité reste `heure`, le relevé physique reste 153°, les témoins historiques sont conservés. Ils ne remplacent pas le calcul.
- `ReferentielSentinelles.charger(copie_temporaire)` reconstruit les huit références et leurs miroirs avec Skyfield et `data/ephemeride/de406.bsp`. Pendant chaque chargement de projet, une substitution temporaire en mémoire de la fabrique `charger` transmet ce référentiel aux instances `SentinelleNationale`. La fabrique est restaurée ensuite. Les sept autres références sont comparées exactement, sans différence.
- `chargerProjetJsonV1()` charge deux modèles frais par calibration : les **16 bases** et les **38 scénarios du Cadran Final** présents localement. Les paramètres, règles, dates et datasets embarqués restent ceux des JSON. Le chargement recalcule les modules avec leurs paramètres restaurés ; le Cadran Final est également recalculé explicitement par événement/scénario avant la mesure des centres. Aucun décalage graphique ni changement de méthode n’est substitué au calcul.
- Les projets locaux étaient déjà modifiés par l’utilisateur et sont conservés. Les résultats portent sur ces fichiers, identiques dans A et B, pas sur un remplacement par les projets versionnés. A reproduit exactement les 19 centres du relevé du nouveau cas 2 sur ce même état local.
- Observation solaire nationale : Carnac, **15 août 1066 julien**, latitude 47°35′36″ N, longitude 3°04′47″ O ; TML converti en UT1 par le moteur existant. Les bases utilisent leurs dates historiques propres et leurs lieux enregistrés. Les secondes fractionnaires restent intactes jusqu’aux calculs.
- Carte Michelin **899 Extended V2 Corse calibrée**, transformation affine conservée. Les longueurs ci-dessous sont planes Lambert-93, en kilomètres ; coordonnées en mètres EPSG:2154. Les seuils restent 30 km et 20 km. Les villes servent uniquement aux mesures après construction.
- Aucun balayage d’heures, aucune optimisation ni compensation de l’orientation nationale **125,371° depuis le nord de grille** n’est réalisé.

## Résultat demandé pour les trois bases

| Base | Joker AM | Heure effective TML | Candidats | Meilleure distance à la ville (km) | Couverture à 20 km |
|---|---|---|---:|---:|---|
| Rouen | 10:55:00 | 13:05:00 | 0 | — | Non |
| Rouen | 10:57:00 | 13:03:00 | 1 | 15,925816 | Oui |
| Château-Gaillard | 10:55:00 | 10:55:00 | 2 | 0,421360 | Oui |
| Château-Gaillard | 10:57:00 | 10:57:00 | 2 | 3,760440 | Oui |
| Bouvines | 10:55:00 | 10:55:00 | 1 | 17,064029 | Oui |
| Bouvines | 10:57:00 | 10:57:00 | 1 | 14,435028 | Oui |

Les paramètres sont vérifiés identiques à ceux de la mission :

- Rouen : Standard, Golfe-Juan, `11:00` PM, cercle PM, Bourges / `=` / Flip vertical, Ouverture / `=` / `/2`.
- Château-Gaillard : Standard, Vouneuil-sur-Vienne, `11:00` AM, cercle AM, Cherbourg / `-2` / Flip vertical, Ouverture / `+2` / `x1`.
- Bouvines : Standard, Alise-Sainte-Reine, `11:00` AM, cercle PM, Dieppe / `+2` / Flip vertical, Stylet / `+2` / `x2`.

Le libellé historique `11:00` n’est pas renommé. Dans BaseCadran, PM est bien la symétrie temporelle de AM : 13:05:00 puis 13:03:00. Le miroir astronomique national, utilisé par le Cadran Final, reste distinct.

### Géométries solaires et rayons réellement recalculés

| Base | Joker AM | Azimut solaire historique effectif (°) | Rayon horaire (km) | Rayon distance (km) | Heure de calcul distance |
|---|---|---:|---:|---:|---|
| Rouen | 10:55:00 | 198,927594 | 824,975643 | 258,267872 | 12:00 |
| Rouen | 10:57:00 | 198,285132 | 852,915249 | 258,267872 | 12:00 |
| Chateau Gaillard | 10:55:00 | 148,513420 | 140,773835 | 255,622945 | 12:00 |
| Chateau Gaillard | 10:57:00 | 149,326720 | 144,128410 | 255,622945 | 12:00 |
| Bouvines | 10:55:00 | 154,442212 | 192,409016 | 341,341544 | 10:55:00 |
| Bouvines | 10:57:00 | 155,198199 | 197,885753 | 339,582467 | 10:57:00 |

Le rayon distance de Bouvines est recalculé avec l’heure effective : **341,341544 → 339,582467 km**, soit −1,759077 km. Les rayons centrés Ouverture restent calculés à midi moyen, donc inchangés pour Rouen et Château-Gaillard.

### Meilleures constructions, sans choix guidé par la ville

Toutes les combinaisons natives sont évaluées. Le tableau désigne ensuite le centre le plus proche de la ville uniquement pour résumer les résultats.

| Base | Joker AM | Traitement / partition | Centre P Lambert-93 (m) | Écarts horaire / distance / partition (km) | Segment | Longueur retenue (km) | Angle (°) | Poids t |
|---|---|---|---|---|---|---:|---:|---:|
| Rouen | 10:55:00 | aucun candidat | — | — | AB minimal rejeté | 30,136567 | — | — |
| Rouen | 10:57:00 | ponderee_intersections_cercles / 0 | (575580.304 ; 6920162.955) | 0,049942 / 9,050285 / 15,216410 | AB | 27,534477 | 79,363590 | 1,000000000000 |
| Chateau Gaillard | 10:55:00 | ponderee / 0 | (583537.123 ; 6905041.190) | 5,885727 / 5,079991 / 3,335033 | AB | 13,493135 | 28,463484 | 0,400083912427 |
| Chateau Gaillard | 10:57:00 | ponderee / 0 | (585988.932 ; 6908402.212) | 2,895272 / 2,527452 / 1,703776 | AB | 6,711229 | 29,178867 | 0,420447542492 |
| Bouvines | 10:55:00 | ponderee / 1 | (699935.278 ; 7043006.074) | 3,369469 / 4,102904 / 1,735175 | AB | 9,232846 | 24,042662 | 0,285456600491 |
| Bouvines | 10:57:00 | ponderee / 1 | (699835.014 ; 7048390.315) | 8,994672 / 10,990703 / 4,343551 | AB | 24,400507 | 22,452023 | 0,248934971322 |

Les meilleurs candidats acceptés n’ont aucun motif de rejet. Les écarts finaux restent tous sous 20 km. Château-Gaillard conserve deux candidats ; le plus proche recule de 0,421360 à 3,760440 km, mais reste largement couvert. Bouvines se rapproche de 2,629000 km ; son AB de 24,400507 km demeure sous 30 km.

### Rouen : condition bloquante à 10:55 et construction à 10:57

Les deux cercles sont mutuellement sécants dans les deux essais : leur distance minimale entre contours est nulle. Les quatre partitions admissibles coupent le cercle horaire, mais aucune ne coupe le cercle de distance. Leurs écarts exacts à ce dernier, inchangés dans A et B, sont :

| Partition | Écart au cercle horaire (km) | Écart au cercle distance (km) |
|---:|---:|---:|
| 0 | 0 | 0,670944 |
| 1 | 0 | 267,534950 |
| 2 | 0 | 107,305805 |
| 3 | 0 | 892,072679 |

À 10:55, les 16 couples A/B du cas 2 sont rejetés : **le plus petit AB vaut 30,136567 km**, soit 136,567 m au-dessus du seuil de 30 km. Aucun centre pondéré n’est donc accepté. Le secours A–Q de la partition 0 est présélectionné à 0,670944 km, mais son centre est à **104,664820 km du cercle horaire** : rejet `contrainte finale > 20 km`. Les autres secours sont rejetés par AQ > 30 km. Il n’existe pas de « meilleur centre candidat » à 10:55 ; aucun centre rejeté n’est présenté comme accepté.

À 10:57, le déplacement astronomique du cercle horaire ramène AB à **27,534477 km** sur la partition 0. AC vaut seulement **0,452215 km**, mais le nouveau cas 2 impose AB. L’angle est **79,363590°**, donc t = 1 et P = G. Les écarts finaux **0,049942 / 9,050285 / 15,216410 km** sont admissibles. P est à **15,925816 km de Rouen**. Le secours A–Q n’est pas produit en supplément pour cette partition.

Les points de cette construction native sont :

| Point | Lambert-93 (m) |
|---|---|
| A | (576957.935 ; 6911113.275) |
| B | (573256.475 ; 6938397.824) |
| C | (576526.501 ; 6910977.764) |
| M | (575107.205 ; 6924755.550) |
| G | (575580.304 ; 6920162.955) |
| P | (575580.304 ; 6920162.955) |

## Référence nationale, 153° et Alise-Sainte-Reine

Les azimuts solaires sont mesurés depuis le nord géographique. Les orientations après calibration sont mesurées depuis le **nord de grille Lambert-93** ; ce sont deux repères différents. Le moteur applique `orientation_grille = (125,371 + 180 − azimut_solaire) modulo 360` sans modifier l’axe national.

| Joker AM | Azimut solaire direct (°) | Écart signé à 153° | Écart absolu | Heure miroir astronomique TML | Azimut miroir (°) | PM BaseCadran |
|---|---:|---:|---:|---|---:|---|
| 10:55:00 | 152,731834 | -0,268166 | 0,268166 | 13:09:03.440827 | 207,268164 | 13:05:00 |
| 10:57:00 | 153,488412 | 0,488412 | 0,488412 | 13:07:03.294426 | 206,511588 | 13:03:00 |

L’écart absolu à 153° **augmente de 0,268166° à 0,488412°**. Le témoin ancien du référentiel n’est pas substitué aux valeurs DE406 recalculées. Le miroir ne correspond pas à une symétrie temporelle autour de midi : notamment, 13:07:03,294426 n’est pas 13:03:00.

| Joker AM | Branche | Orientation grille (°) | Distance réelle Alise–axe (km) |
|---|---|---:|---:|
| 10:55:00 | directe | 152,639166 | 415,279301 |
| 10:55:00 | miroir | 98,102836 | 13,883940 |
| 10:57:00 | directe | 151,882588 | 411,562075 |
| 10:57:00 | miroir | 98,859412 | 20,484625 |

La correspondance avec Alise est la branche **miroir**, et non la directe. Centre Coëtquidan : **(315205.580 ; 6773022.078) m** ; Alise : **(812149.276 ; 6716295.368) m**, issus du CSV courant. Le relèvement de grille centre–Alise est **96,512193°**. La distance est mesurée orthogonalement à la droite réelle en Lambert-93, sans utiliser une distance en pixels comme distance géographique.

Le déplacement de l’axe miroir augmente l’écart de **6,600684 km**, jusqu’à **20,484625 km**. Le contrôle séparé de `SentinelleNationale.rechercherLigneHoraire()` donne :

| Joker AM | Repère le plus proche | Branche | Distance native entière (km) | Sélection native |
|---|---|---|---:|---|
| 10:55:00 | Joker / J | miroir | 13 | Oui |
| 10:57:00 | Joker / J | miroir | 20 | Non |

Le contrat historique de cette sélection convertit une distance image avec le facteur local, tronque en kilomètres et exige strictement `< 20`. Ce contrôle n’est pas remplacé par le contrôle métrique des candidats. **Les deux contrôles concluent ici à une dégradation : Alise perd sa sélection native à 10:57.** Le repère le plus proche reste J miroir, sans bascule vers une autre Sentinelle ; les bases qui utilisent ce repère conservent leurs calculs natifs mais cette perte de sélection reste une régression à signaler.

## Bilan des 16 bases

| Base | Nombre 10:55 → 10:57 | Plus proche 10:55 (km) | Plus proche 10:57 (km) | Couverture 10:55 → 10:57 |
|---|---:|---:|---:|---|
| Saint Amour | 1 → 1 | 8,012738 | 8,012738 | Oui → Oui |
| Rocamadour | 1 → 1 | 16,076271 | 16,076271 | Oui → Oui |
| Gergovie | 1 → 1 | 8,721513 | 8,721513 | Oui → Oui |
| Carignan | 3 → 3 | 12,723583 | 12,723583 | Oui → Oui |
| Ile d'Aix | 1 → 1 | 9,358809 | 9,358809 | Oui → Oui |
| Rouen | 0 → 1 | — | 15,925816 | Non → Oui |
| Metz | 1 → 1 | 689,542902 | 689,542902 | Non → Non |
| Chateau Gaillard | 2 → 2 | 0,421360 | 3,760440 | Oui → Oui |
| Saint Cyr Coetquidan | 1 → 1 | 15,540208 | 15,540208 | Oui → Oui |
| Domremy | 1 → 1 | 5,404876 | 5,404876 | Oui → Oui |
| Reims | 1 → 1 | 10,210969 | 10,210969 | Oui → Oui |
| Bouvines | 1 → 1 | 17,064029 | 14,435028 | Oui → Oui |
| Chalus | 1 → 1 | 5,768251 | 5,768251 | Oui → Oui |
| Fontevraud | 1 → 1 | 18,333633 | 18,333633 | Oui → Oui |
| Le Goulet | 1 → 1 | 12,533544 | 12,533544 | Oui → Oui |
| Pont de Noirmoutiers | 2 → 2 | 10,439013 | 10,439013 | Oui → Oui |

Total **19 → 20 candidats**, **14 → 15 bases couvertes sur 16**. Gain unique : **Rouen**. Aucune base ne perd sa couverture. Les centres et nombres des 13 autres scénarios sont exactement identiques ; seules Rouen, Château-Gaillard et Bouvines changent. Metz conserve son candidat éloigné et reste non couvert. Fontevraud et Rocamadour restent couverts. La sélection native d’Alise est comptée séparément de la couverture géométrique de ces bases.

## Impact sur les 38 scénarios du Cadran Final

Le rendu pondéré actuellement actif est utilisé, sans activer la méthode historique. Les heures d’ombre AM et PM utilisent les **deux branches astronomiques nationales**, pas la symétrie temporelle propre aux bases. Les lignes horaires J se déplacent dans les références disponibles ; les centres changent seulement dans les 11 scénarios où J est sélectionné pour la lumière ou l’ombre.

| Scénario | Date lumière | Notes lumière / ombre | Candidats 10:55 → 10:57 | Meilleure distance 10:55 (km) | Meilleure distance 10:57 (km) | Couverture 10:55 → 10:57 |
|---|---|---|---:|---:|---:|---|
| Jumièges | 25/07/778 | F / J | 2 → 2 | 6,973694 | 8,963911 | Oui → Oui |
| Grotte Lombrives | 25/07/778 | D / D | 1 → 1 | 7,768871 | 7,768871 | Oui → Oui |
| St Julien de Mailloc | 25/07/778 | F / J | 2 → 2 | 13,054606 | 9,420906 | Oui → Oui |
| Ferté Alais | 25/07/778 | A / A | 3 → 3 | 11,109340 | 11,109340 | Oui → Oui |
| Lac Trémelin | 25/07/778 | E / C | 2 → 2 | 5,411040 | 5,411040 | Oui → Oui |
| Loches | 25/07/778 | D / J | 4 → 4 | 12,773909 | 10,509405 | Oui → Oui |
| Compiègne | 19/04/1431 | E / F | 2 → 2 | 15,620133 | 15,620133 | Oui → Oui |
| Donon | 19/04/1431 | B / J | 2 → 2 | 13,196265 | 12,648909 | Oui → Oui |
| Frontiere Sud Bretagne | 19/04/1431 | B / E | 2 → 2 | — | — | non mesurable → non mesurable |
| Thury sous Clermont | 19/04/1431 | C / C | 2 → 2 | 15,321620 | 15,321620 | Oui → Oui |
| Brétigny | 29/03/1214 | B / B | 2 → 2 | 13,850852 | 13,850852 | Oui → Oui |
| Vézelay | 29/03/1214 | J / B | 2 → 2 | 16,097791 | 15,739265 | Oui → Oui |
| Dinard | 29/03/1214 | E / F | 1 → 1 | 10,371631 | 10,371631 | Oui → Oui |
| Plymouth | 29/03/1214 | F / C | 2 → 2 | 16,392393 | 16,392393 | Oui → Oui |
| Paris | 08/08/1365 | B / B | 2 → 2 | 5,355728 | 5,355728 | Oui → Oui |
| Turin | 08/08/1365 | D / F | 1 → 1 | 6,687211 | 6,687211 | Oui → Oui |
| Boulogne | 08/08/1365 | F / D | 0 → 0 | — | — | Non → Non |
| Lons-le-Saunier | 08/08/1365 | D / C | 2 → 2 | 11,339380 | 11,339380 | Oui → Oui |
| Le Bec | 08/08/1365 | F / F | 1 → 1 | — | — | non mesurable → non mesurable |
| Waterloo | 08/08/1365 | B / D | 2 → 2 | 4,510437 | 4,510437 | Oui → Oui |
| Dover | 28/05/1815 | B / J | 2 → 2 | — | — | non mesurable → non mesurable |
| 3RDV | 28/05/1815 | G / G | 7 → 7 | 20,510101 | 20,510101 | Non → Non |
| Portsmouth | 28/05/1815 | B / J | 2 → 2 | 34,776761 | 34,006260 | Non → Non |
| Quiberon | 28/05/1815 | J / D | 2 → 2 | 7,276350 | 0,355099 | Oui → Oui |
| Vézelay | 28/05/1815 | G / G | 8 → 8 | 1,893917 | 1,893917 | Oui → Oui |
| Solesmes | 01/09/1066 | C / J | 2 → 2 | 3,588304 | 1,876143 | Oui → Oui |
| Come | 01/09/1066 | D / D | 2 → 2 | 18,471176 | 18,471176 | Oui → Oui |
| Laffrey | 01/09/1066 | F / C | 2 → 2 | 17,095565 | 17,095565 | Oui → Oui |
| Châlons-en-Champagne | 01/09/1066 | G / G | 8 → 8 | 9,516566 | 9,516566 | Oui → Oui |
| Beaufort en Vallée | 18/05/933 | A / C | 2 → 2 | 5,291691 | 5,291691 | Oui → Oui |
| Lampouy | 18/05/933 | D / D | 2 → 2 | 0,815389 | 0,815389 | Oui → Oui |
| Carnac | 18/05/933 | A / A | 2 → 2 | 13,720955 | 13,720955 | Oui → Oui |
| Pic du Midi | 19/08/1152 | F / J | 1 → 1 | 15,791077 | 19,872536 | Oui → Oui |
| Mirebeau | 19/08/1152 | B / B | 2 → 2 | 13,834458 | 13,834458 | Oui → Oui |
| Zone | 19/08/1152 | C / L | 2 → 2 | — | — | non mesurable → non mesurable |
| Le Mans | 19/08/1152 | F / C | 2 → 2 | 21,747307 | 21,747307 | Non → Non |
| Montmirail | 19/08/1152 | C / J | 2 → 2 | 10,954246 | 11,989224 | Oui → Oui |
| Scénario par défaut | sans bases | — / — | 0 → 0 | — | — | non mesurable → non mesurable |

**87 → 87 candidats**, aucun scénario ne perd de candidat. **29 → 29 couvertures sur 33 références ponctuelles mesurables**. Aucune couverture mesurable gagnée ou perdue. Les autres scénarios gardent exactement leurs centres. **Pic du Midi recule de 15,791077 à 19,872536 km** : couverture conservée, avec seulement **0,127464 km de marge**.

Références : correspondance exacte au CSV ou variantes explicites Grotte Lombrives → Grotte de Lombrives ; Lac Trémelin → Lac-de-Trémelin ; Ferté Alais / La Ferté Alais → La Ferté-Alais ; Beaufort en Vallée → Beaufort-en-Vallée ; Boulogne → Boulogne-sur-Mer ; Thury sous Clermont → Thury-sous-Clermont ; Come → Côme. Pour Montmirail, seul le point précédemment fourni par l’utilisateur (48,10° N ; 0,769° E) est transformé en Lambert-93 en mémoire, sans ajout au CSV. Les scénarios sans référence ponctuelle vérifiable sont : **Frontiere Sud Bretagne, Le Bec, Dover, Zone, Scénario par défaut**. Leur nombre de candidats est contrôlé, mais aucune conclusion de couverture n’est inventée. Le scénario de transition sans bases reste sans calcul géométrique.

### Heures et directions d’ombre du Joker

Pour les neuf scénarios sélectionnant J en ombre (Jumièges, St Julien de Mailloc, Loches, Donon, Dover, Portsmouth, Solesmes, Pic du Midi et Montmirail), AM passe de 10:55:00 à 10:57:00 et PM de 13:09:03,440827 à 13:07:03,294426. Les deux azimuts solaires J sont ceux du tableau national. Les angles image des lignes sont mesurés séparément, après application du sens de carte :

| Scénario | Branche | Heure 10:55 | Heure 10:57 | Direction ombre image 10:55 (°) | Direction ombre image 10:57 (°) |
|---|---|---|---|---:|---:|
| Jumièges | AM / directe | 10:55:00.000000 | 10:57:00.000000 | 260,103031 | 260,859609 |
| Jumièges | PM / miroir | 13:09:03.440827 | 13:07:03.294426 | 314,639362 | 313,882786 |
| St Julien de Mailloc | AM / directe | 10:55:00.000000 | 10:57:00.000000 | 347,141302 | 347,897880 |
| St Julien de Mailloc | PM / miroir | 13:09:03.440827 | 13:07:03.294426 | 41,677632 | 40,921056 |
| Loches | AM / directe | 10:55:00.000000 | 10:57:00.000000 | 347,141302 | 347,897880 |
| Loches | PM / miroir | 13:09:03.440827 | 13:07:03.294426 | 41,677632 | 40,921056 |
| Donon | AM / directe | 10:55:00.000000 | 10:57:00.000000 | 263,424004 | 262,667426 |
| Donon | PM / miroir | 13:09:03.440827 | 13:07:03.294426 | 208,887673 | 209,644250 |
| Dover | AM / directe | 10:55:00.000000 | 10:57:00.000000 | 133,830519 | 134,587097 |
| Dover | PM / miroir | 13:09:03.440827 | 13:07:03.294426 | 188,366849 | 187,610273 |
| Portsmouth | AM / directe | 10:55:00.000000 | 10:57:00.000000 | 186,667791 | 185,911213 |
| Portsmouth | PM / miroir | 13:09:03.440827 | 13:07:03.294426 | 132,131460 | 132,888037 |
| Solesmes | AM / directe | 10:55:00.000000 | 10:57:00.000000 | 5,897299 | 5,140721 |
| Solesmes | PM / miroir | 13:09:03.440827 | 13:07:03.294426 | 311,360968 | 312,117545 |
| Pic du Midi | AM / directe | 10:55:00.000000 | 10:57:00.000000 | 189,065478 | 188,308900 |
| Pic du Midi | PM / miroir | 13:09:03.440827 | 13:07:03.294426 | 134,529147 | 135,285724 |
| Montmirail | AM / directe | 10:55:00.000000 | 10:57:00.000000 | 114,475276 | 113,718698 |
| Montmirail | PM / miroir | 13:09:03.440827 | 13:07:03.294426 | 59,938945 | 60,695522 |

Pour les deux scénarios sélectionnant J en lumière : **Vézelay** utilise la branche PM astronomique, 13:09:03 → 13:07:03, et se rapproche de 16,097791 à 15,739265 km ; **Quiberon** utilise AM, 10:55 → 10:57, et se rapproche de 7,276350 à 0,355099 km. Leurs ombres sélectionnées restent respectivement B et D. Les autres directions disponibles J évoluent aussi, même lorsqu’elles ne sont pas sélectionnées ; elles n’ajoutent pas de candidats hors des choix enregistrés.

## Vérifications et tests

- Deux reconstructions natives complètes : **16 bases + 38 scénarios Final par calibration**, sans exception. Tous les paramètres et dates restent identiques dans A et B. Les sept références solaires hors Joker sont exactement égales, ainsi que l’axe national et la calibration de carte.
- A reproduit exactement les centres de l’étude BaseCadran publiée au commit `d5e8f74`, sur les mêmes projets locaux. Pour chaque candidat Base accepté dans A et B : présélection ≤ 30 km, trois écarts ≤ 20 km, segment AB imposé et poids calculé par la formule pour le nouveau cas 2. Les 13 bases non ciblées gardent exactement leurs centres.
- Tests ciblés : **184 réussites en 14,67 s** :

```text
python -m pytest tests/test_referentiel_sentinelles.py tests/test_cadran_national_lot2.py tests/test_cadran_final_pondere.py tests/test_candidats_base_intersections_cercles.py -q --tb=short
```

Ces tests utilisent la calibration persistée 10:55. L’hypothèse temporaire 10:57 est vérifiée par les deux exécutions comparatives natives et les assertions de conservation/validation ci-dessus ; aucune assertion de calibration enregistrée n’est réécrite pour elle.

La suite complète a été exécutée sur ce même code lors de la livraison du cas 2 : **1033 réussites et 2 échecs en 289,18 s**. L’échec Tk d’initialisation `tk.tcl` réussit au rejeu isolé (1 test en 5,25 s). L’autre échec golden historique est reproduit avec le code initial sur les paramètres locaux modifiés ; les assertions inchangées réussissent pour les 16 scénarios du projet versionné. Ces limites sont documentées dans `docs/base_cadran_cas2_intersections_cercles.md`. La présente étude ne modifie que la documentation ; la suite complète n’est pas répétée sans changement de code.

### Empreintes des entrées conservées

Les fichiers suivis sont contrôlés avant et après chaque exécution ; aucune différence n’est constatée. Les empreintes essentielles sont :

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

## Conclusion opérationnelle

**Oui pour les trois cercles de bases ; non pour une validation globale sans compromis.** À 10:57, Rouen est retrouvé, Château-Gaillard et Bouvines restent couverts, les autres bases ne perdent rien et le Cadran Final conserve ses couvertures mesurables. Mais Alise-Sainte-Reine perd sa sélection native sur l’axe Joker miroir et l’écart au relevé historique de 153° augmente. La calibration **10:57 n’est donc pas recommandée comme remplacement définitif répondant à tous les critères de cette mission**. L’heure 10:55 demeure enregistrée. Aucun nouveau réglage n’a été recherché pour compenser cette limite ; une éventuelle décision d’accepter ce compromis appartient à l’utilisateur.
