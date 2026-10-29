# Cadran Final — Test du barycentre pondéré selon l’angle

Expérience sur `dev` à partir de `675926b`, avec les **37 scénarios actuellement enregistrés**. Les paramètres **30 km, 45°, exposant 2 et rayon 20 km** sont fixés avant la mesure et restent ceux de la mission. Aucun réglage n’est adapté aux résultats.

## Implémentation et accès aux deux méthodes

La nouvelle méthode est active dans l’affichage par défaut de `CandidatFinal`. Les constructions du stylet, du cercle, de la lumière et des ombres restent identiques. La méthode précédente, incluant le secours à deux points séparés de 40 km, reste disponible intégralement :

```python
candidat.construireRepresentationCarte()                      # pondérée, affichage par défaut
candidat.construireRepresentationCarte(methode="ponderee")
candidat.construireRepresentationCarte(methode="historique")   # ancienne méthode
candidat.construireRepresentationCarteHistorique()             # même ancienne méthode
```

Aucun nouveau paramètre de scénario ni contrôle de l’IHM n’est introduit. Les deux rendus sont appelables sur le même module chargé, sans recalcul ni sauvegarde des paramètres. Le corps de la méthode historique est vérifié identique par AST à la révision de départ. Les anciens tests et golden continuent de tester explicitement cette méthode ; ils ne sont pas remplacés par les résultats expérimentaux.

## Géométrie et formules réellement utilisées

Pour chaque direction de lumière, chaque droite horaire et chaque intersection A cercle–lumière :

1. Les intersections A et B restent celles des primitives cartographiques existantes. B est l’intersection cercle–ombre la plus proche de A en distance Lambert-93. Une égalité exacte conserve le premier résultat de la primitive, sans préférence géographique.
2. Les directions pixel existantes sont transportées par **la partie linéaire inverse de la calibration affine** `A_inv`, puis normalisées en Lambert-93. On ne réinterprète pas l’azimut d’image comme un azimut de grille et on n’utilise pas la projection orthogonale pixel.
3. Avec H sur l’ombre, v sa direction métrique unitaire et n = (−vy, vx), `h = (A−H)·n`, `Q = A−h n`, `d = |h|/1000` km. **Seul d ≤ 30 km détermine l’admissibilité.**
4. `M = (A+Q)/2`. Avec u la direction métrique de lumière, `det = ux vy−uy vx` et `dot = u·v`, l’angle aigu non orienté vaut `θ = atan2(|det|, |dot|)` en degrés, dans [0°,90°].
5. Si `det ≠ 0`, `s = cross(H−A,v)/det`, `C = A+s u`, `G = (A+B+C)/3`. C n’est pas soumis à la visibilité de l’image ni à un seuil de distance. Il s’agit de l’intersection des mêmes droites infinies dans leur représentation métrique.
6. `t = min(1,(θ/45)²)` puis `P = (1−t) M+t G`. B absent ou C absent/non représentable en nombres finis : P = M avec cause signalée. Droites exactement parallèles : P = M.

Pour les angles quasi nuls, le terme sensible est évalué algébriquement par `P = M + t*(A−M+(B−A)/3) + ((t/det)*cross(H−A,v))*u/3`. On évite ainsi la multiplication directe d’un C gigantesque par un t minuscule ; la limite est M. Aucun seuil angulaire ou géographique supplémentaire n’est ajouté. Un C dépassant la capacité des flottants est traité comme indisponible, ce qui est une limite numérique, pas un filtre géographique.

Le rendu conserve des cercles de **20 km** et les tags de construction. Les infobulles précisent méthode/repli, heure d’ombre, A–Q, θ, t, P–A, distance de P à l’ombre et écart radial au rayon nominal de lumière. Cette dernière information est **|distance Lambert(P,Bourges)−rayon nominal|** : elle n’est pas présentée comme la distance orthogonale exacte à la courbe rendue en pixels. Le cercle existant est conservé avec sa représentation pixel et sa transformation affine ; aucune rectification de cette construction n’est faite.

## Données, références et protocole

Le JSON, le CSV courant, les références de villes et la calibration sont identiques pour les deux méthodes. `chargerProjetJsonV1()` calcule avec le snapshot de dataset embarqué dans le projet, sans remplacer ses dates par le CSV. Toutes les dates demandées sont présentes : Montmirail 19/08/1152 ; Lombrives 25/07/778 ; Carnac et Beaufort 18/05/933.

| Fichier inchangé | SHA-256 |
|---|---|
| `projets\CadranFinal_Solutions.json` | `5e66b5bfd8f956956b45c961d8069c5a0cc0fa6a2a8f08bfd61246f436884adc` |
| `data\dataset.csv` | `4201fdb64be9121cd1469512425c515572975673ce31089d14ed8c63e2b9ffd0` |
| `data\villes_database.csv` | `2d914bfeee7ebb5895c39344a886146e297380d871925cc4282d878396e5ce1a` |
| `data\carto\899 - extended v2 corse_calibree.json` | `b443ab8ccdec4f8211d03b7a5d66dfd7edef3b093a0c5cad9a5e6cc07004ed7c` |

Les **85 centres historiques** sont confrontés aux 85 centres de l’expérience précédente : mêmes coordonnées, même ordre, mêmes paramètres et mêmes dates pour les 37 scénarios. Le nouveau rendu est confronté à ses diagnostics géométriques : mêmes P, même ordre et même nombre. Les autres classes et fonctions préexistantes du module Final sont vérifiées identiques par AST. Les fichiers protégés restent identiques par SHA-256.

Les distances sont planes, en kilomètres Lambert-93 ; toutes les coordonnées des tableaux sont en **mètres EPSG:2154**. Les centres distants d’au plus **1 mm** sont fusionnés pour les seules statistiques. Aucun doublon n’est rencontré ici, y compris entre scénarios : totaux bruts et géométriquement distincts coïncident.

Références issues du CSV : correspondance exacte, ou variantes explicites Grotte Lombrives → Grotte de Lombrives ; Lac Trémelin → Lac-de-Trémelin ; Ferté Alais / La Ferté Alais → La Ferté-Alais ; Beaufort en Vallée → Beaufort-en-Vallée ; Boulogne → Boulogne-sur-Mer. **23 scénarios ont une référence mesurable.**

Frontiere Sud Bretagne et Zone ne sont pas des points. Dinard, Plymouth, Lons-le-Saunier, Le Bec, Dover, Portsmouth, Quiberon, Come, Châlons-en-Champagne, Le Mans et **Montmirail** n’ont pas d’entrée ponctuelle suffisamment explicite dans le CSV. Waterloo (Bouvines) est ambigu entre deux entrées. Aucune coordonnée n’est inventée, aucun de ces cas n’entre dans les statistiques de couverture.

## Bilan global

- Candidats bruts : **85 → 88**. Candidats géographiquement distincts : **85 → 88**.
- **296** configurations A/droite examinées ; **88** satisfont A–Q ≤ 30 km, **208** sont rejetées.
- **81** centres pondérés ; **7** replis sur M parce que B est absent. Aucun repli pour C absent/parallélisme dans ce corpus ; les tests couvrent ces cas.
- Scénarios sans candidat : **5 → 1**. Boulogne reste sans candidat. Loches, La Ferté Alais (1431), Le Bec et Le Mans en gagnent ; seuls les deux premiers ont une référence mesurable.
- Couverture de 20 km parmi les 23 scénarios géoréférencés : **16 → 17**. Gains : **Loches** et **La Ferté Alais (1431)**. Perte : **Donon**.
- La proximité du candidat le plus proche s’améliore pour plusieurs lieux, mais se dégrade dans dix scénarios mesurables. Les très faibles différences < 1 µm ne sont pas comptées comme dégradation.
- **77 centres nouveaux géométriquement** (non confondus à 1 mm avec un ancien centre du même scénario) ; 11 restent identiques. Parmi ces 77, **54** ont une référence : **20** la couvrent et **34** sont au-delà de 20 km ; **23** sont non évaluables. Ces 34 centres sont des faux positifs possibles pour le lieu visé, sans constituer une preuve d’erreur géométrique.
- Sur l’ensemble des 88 nouveaux candidats, **37** sont au-delà de 20 km de la référence de leur scénario. Une augmentation nette de trois candidats masque donc de nombreux déplacements de centres ; elle ne démontre pas un gain de sélectivité.

## Cas prioritaires

### Montmirail — 18 mai 1152

Date du segment : **19/08/1152**. Paramètres conservés : `{"base": "Pont de Noirmoutier", "stylet": "Loudun", "octave": "/4", "calendars": ["Standard", "Standard", "Standard"], "choices": ["=", "-2", "11:00"], "period": "PM", "orientation": "Envers"}`.

Candidats **1 → 2** ; plus proche de la référence : **n.d. → n.d. km**.

Centres anciens : (547753.292 ; 6543396.378).

| Branche lumière / heure ombre / indice A | A–Q (km) | A–B (km) | A–C (km) | θ | t | P–A (km) | P–ombre (km) | Écart radial nominal (km) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AM / 13:09:03 / 1 | 4,340 | n.d. | 4,457 | 76,805° | 1.000000000 | 2,170 | 2,170 | 1,959 |
| PM / 10:55:00 / 1 | 3,550 | 12,213 | 3,673 | 75,112° | 1.000000000 | 4,292 | 1,183 | 1,549 |

| Branche / heure / indice A | A | B retenu | C | Q | M | G | P | Distance P–lieu (km) |
|---|---|---|---|---|---|---|---|---:|
| AM / 13:09:03 / 1 | (543970.539 ; 6784503.097) | absent | (540950.001 ; 6787781.118) | (541835.875 ; 6788281.593) | (542903.207 ; 6786392.345) | absent | (542903.207 ; 6786392.345) | n.d. |
| PM / 10:55:00 / 1 | (550000.109 ; 6539739.308) | (540905.460 ; 6547891.028) | (552354.308 ; 6542558.798) | (551498.836 ; 6542957.229) | (550749.473 ; 6541348.268) | (547753.292 ; 6543396.378) | (547753.292 ; 6543396.378) | n.d. |

**Limite importante : Montmirail n’a pas de coordonnées dans le CSV.** Sa distance et la pertinence géographique de ses cercles ne peuvent pas être conclues sans point de référence confirmé. Les deux configurations admissibles ont θ ≈ 75–77° et **t = 1**. Pour celle dont B existe, **P = G** et l’ancien centre est inchangé. Pour l’autre, **B est absent : P = M** conformément au repli prévu, malgré t = 1. Le triangle très aigu attendu n’est pas reproduit avec cette configuration sauvegardée, et aucun paramètre n’est changé pour le provoquer.

| Branche / heure / indice A | A–Q (km) | θ | Admissible |
|---|---:|---:|---|
| AM / 10:55:00 / 0 | 91,851 | 22,367° | non |
| AM / 10:55:00 / 1 | 215,784 | 22,367° | non |
| AM / 13:09:03 / 0 | 321,413 | 76,805° | non |
| AM / 13:09:03 / 1 | 4,340 | 76,805° | oui |
| PM / 10:55:00 / 0 | 311,157 | 75,112° | non |
| PM / 10:55:00 / 1 | 3,550 | 75,112° | oui |
| PM / 13:09:03 / 0 | 105,442 | 20,675° | non |
| PM / 13:09:03 / 1 | 220,412 | 20,675° | non |

### Grotte de Lombrives — 15 août 778

Date du segment : **25/07/778**. Paramètres conservés : `{"base": "Saint-Amour", "stylet": "Roncevaux", "octave": "/2", "calendars": ["Déclinaison", "Déclinaison", "Déclinaison"], "choices": ["+2", "-2", "-2"], "period": "PM", "orientation": "Endroit"}`.

Candidats **2 → 1** ; plus proche de la référence : **15,524 → 7,769 km**.

Centres anciens : (595775.059 ; 6205154.285) ; (871324.900 ; 7074047.760).

| Branche lumière / heure ombre / indice A | A–Q (km) | A–B (km) | A–C (km) | θ | t | P–A (km) | P–ombre (km) | Écart radial nominal (km) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AM / 08:14:46 / 0 | 18,089 | 20,439 | 40,618 | 26,445° | 0.345365070 | 10,549 | 8,003 | 6,171 |

| Branche / heure / indice A | A | B retenu | C | Q | M | G | P | Distance P–lieu (km) |
|---|---|---|---|---|---|---|---|---:|
| AM / 08:14:46 / 0 | (585636.737 ; 6206440.115) | (605913.381 ; 6203868.455) | (579613.741 ; 6166270.882) | (600459.438 ; 6196071.581) | (593048.088 ; 6201255.848) | (590387.953 ; 6192193.151) | (592129.370 ; 6198125.909) | 7,769 |

Le centre se rapproche de **7,755 km** et couvre toujours la grotte. L’ancien candidat très éloigné disparaît par le nouveau critère d’admissibilité. Le P affiché résulte exactement de la pondération prévue ; aucun repositionnement vers les coordonnées de la grotte n’intervient.

### Carnac — 19 juillet 933

Date du segment : **18/05/933**. Paramètres conservés : `{"base": "Fontevraud", "stylet": "Saint-Valentin", "octave": "x2", "calendars": ["Déclinaison", "Déclinaison", "Déclinaison"], "choices": ["Clef 2", "+2", "+2"], "period": "AM", "orientation": "Endroit"}`.

Candidats **3 → 2** ; plus proche de la référence : **14,076 → 13,721 km**.

Centres anciens : (1056624.142 ; 6689941.252) ; (250894.074 ; 6662941.822) ; (257590.306 ; 6738029.003).

| Branche lumière / heure ombre / indice A | A–Q (km) | A–B (km) | A–C (km) | θ | t | P–A (km) | P–ombre (km) | Écart radial nominal (km) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AM / 11:42:00 / 1 | 12,490 | 12,502 | 458,435 | 1,561° | 0.001203698 | 6,250 | 6,243 | 0,411 |
| PM / 12:22:01 / 1 | 5,778 | 5,790 | 101,696 | 3,257° | 0.005239708 | 2,900 | 2,884 | 0,337 |

| Branche / heure / indice A | A | B retenu | C | Q | M | G | P | Distance P–lieu (km) |
|---|---|---|---|---|---|---|---|---:|
| AM / 11:42:00 / 1 | (250922.270 ; 6656691.065) | (250865.878 ; 6669192.578) | (-207421.839 ; 6647576.197) | (250333.786 ; 6669167.480) | (250628.028 ; 6662929.273) | (98122.103 ; 6657819.947) | (250444.457 ; 6662923.123) | 76,409 |
| PM / 12:22:01 / 1 | (258118.288 ; 6740875.488) | (257062.324 ; 6735182.519) | (158250.717 ; 6760071.497) | (256706.877 ; 6735272.050) | (257412.583 ; 6738073.769) | (224477.110 ; 6745376.501) | (257240.010 ; 6738112.033) | 13,721 |

Le lieu reste couvert et le plus proche centre gagne **0,355 km**. Les petits angles des deux solutions admises donnent un poids très faible à G. Le nombre de candidats diminue de trois à deux, sans perte de couverture.

### Beaufort-en-Vallée — 19 juillet 933

Date du segment : **18/05/933**. Paramètres conservés : `{"base": "Fontevraud", "stylet": "Saint-Valentin", "octave": "x1", "calendars": ["Déclinaison", "Déclinaison", "Déclinaison"], "choices": ["Clef 2", "+2", "Clef"], "period": "AM", "orientation": "Envers"}`.

Candidats **2 → 2** ; plus proche de la référence : **5,285 → 5,292 km**.

Centres anciens : (454904.605 ; 6658588.659) ; (458364.260 ; 6704108.577).

| Branche lumière / heure ombre / indice A | A–Q (km) | A–B (km) | A–C (km) | θ | t | P–A (km) | P–ombre (km) | Écart radial nominal (km) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AM / 14:21:11 / 1 | 4,579 | 6,476 | 6,370 | 45,951° | 1.000000000 | 3,053 | 1,526 | 2,210 |
| PM / 09:43:00 / 1 | 3,682 | 5,077 | 5,274 | 44,276° | 0.968065289 | 2,437 | 1,247 | 1,828 |

| Branche / heure / indice A | A | B retenu | C | Q | M | G | P | Distance P–lieu (km) |
|---|---|---|---|---|---|---|---|---:|
| AM / 14:21:11 / 1 | (452703.254 ; 6660703.786) | (452938.284 ; 6654231.746) | (459072.276 ; 6660830.444) | (456056.746 ; 6657586.460) | (454380.000 ; 6659145.123) | (454904.605 ; 6658588.659) | (454904.605 ; 6658588.659) | 50,861 |
| PM / 09:43:00 / 1 | (456296.266 ; 6702782.780) | (457320.735 ; 6707755.749) | (461475.780 ; 6701787.202) | (459318.178 ; 6704886.506) | (457807.222 ; 6703834.643) | (458364.260 ; 6704108.577) | (458346.471 ; 6704099.829) | 5,292 |

Le lieu reste couvert. Le plus proche centre recule de **0,006917 km**, soit **6,917 m** ; cette légère dégradation est signalée. Une configuration dépasse 45° et conserve P = G ; l’autre est juste sous 45° et conserve une faible part de M.

## Comparaison des 37 scénarios

Les cellules de centres listent **tous** les centres, pas seulement le plus proche. « — » indique aucun candidat ; « n.d. » une référence absente/ambiguë. Les deux dernières colonnes donnent la distance du centre le plus proche au lieu de référence, en kilomètres. Le nombre est indiqué avant la liste des coordonnées.

| Événement | Scénario | Centre(s) ancien(s) — mètres L93 | Centre(s) nouveau(x) — mètres L93 | Distance au lieu ancien (km) | Distance au lieu nouveau (km) |
|---|---|---|---|---:|---:|
| 15 Aout 778 : Bataille de Roncevaux | Jumièges | **2** : (420521.110 ; 6520023.902)<br>(548905.051 ; 6918468.174) | **2** : (420407.958 ; 6519975.125)<br>(545766.629 ; 6922302.620) | 11,920 | 6,974 |
| 15 Aout 778 : Bataille de Roncevaux | Grotte Lombrives | **2** : (595775.059 ; 6205154.285)<br>(871324.900 ; 7074047.760) | **1** : (592129.370 ; 6198125.909) | 15,524 | 7,769 |
| 15 Aout 778 : Bataille de Roncevaux | St Julien de Mailloc | **2** : (488661.963 ; 6895853.893)<br>(905296.019 ; 6776878.525) | **2** : (491131.482 ; 6890907.839)<br>(912333.081 ; 6783282.413) | 16,532 | 13,055 |
| 15 Aout 778 : Bataille de Roncevaux | Ferté Alais | **4** : (647926.205 ; 6824101.706)<br>(641201.936 ; 6505786.119)<br>(592126.534 ; 6517924.599)<br>(740586.009 ; 6798377.631) | **3** : (648166.684 ; 6826595.813)<br>(642984.282 ; 6511734.210)<br>(593610.129 ; 6524434.597) | 11,044 | 11,109 |
| 15 Aout 778 : Bataille de Roncevaux | Lac Trémelin | **2** : (998466.407 ; 6605645.842)<br>(319918.185 ; 6787297.401) | **2** : (1010320.407 ; 6608729.133)<br>(321494.093 ; 6786596.139) | 6,458 | 5,411 |
| 15 Aout 778 : Bataille de Roncevaux | Loches | — | **4** : (536066.865 ; 6675316.636)<br>(780879.350 ; 6643465.970)<br>(536973.943 ; 6707113.840)<br>(766448.213 ; 6615522.931) | — | 12,774 |
| 30 Mai 1431 : Mort de Jeanne d’Arc | Compiègne | **2** : (527505.974 ; 6456605.914)<br>(680792.250 ; 6902760.965) | **2** : (527505.974 ; 6456605.914)<br>(680792.250 ; 6902760.965) | 22,136 | 22,136 |
| 30 Mai 1431 : Mort de Jeanne d’Arc | Donon | **2** : (961918.895 ; 6926095.265)<br>(1024394.310 ; 6834420.750) | **2** : (965826.957 ; 6930470.235)<br>(1028237.747 ; 6835593.018) | 17,126 | 21,112 |
| 30 Mai 1431 : Mort de Jeanne d’Arc | Frontiere Sud Bretagne | **2** : (269526.378 ; 6707784.359)<br>(314283.166 ; 6851270.580) | **2** : (269526.378 ; 6707784.359)<br>(314283.166 ; 6851270.580) | n.d. | n.d. |
| 30 Mai 1431 : Mort de Jeanne d’Arc | La Ferté Alais | — | **2** : (808762.941 ; 6592956.623)<br>(654100.526 ; 6831173.532) | — | 8,665 |
| 27 Juillet 1214 : Bataille des Bouvines | Brétigny | **2** : (633310.581 ; 6807921.698)<br>(592156.729 ; 6799335.085) | **2** : (632208.299 ; 6811897.586)<br>(591718.210 ; 6800779.749) | 15,107 | 13,851 |
| 27 Juillet 1214 : Bataille des Bouvines | Vézelay | **3** : (770453.582 ; 6702598.442)<br>(612070.736 ; 6545489.180)<br>(712101.762 ; 6777400.421) | **2** : (771840.384 ; 6703148.589)<br>(712198.213 ; 6777580.371) | 14,945 | 16,098 |
| 27 Juillet 1214 : Bataille des Bouvines | Dinard | **1** : (341547.060 ; 6857308.577) | **1** : (330728.791 ; 6858656.558) | n.d. | n.d. |
| 27 Juillet 1214 : Bataille des Bouvines | Plymouth | **2** : (177489.466 ; 7066557.815)<br>(832394.207 ; 7262578.736) | **2** : (176926.609 ; 7066913.795)<br>(834175.194 ; 7265720.236) | n.d. | n.d. |
| 12 Avril 1365 : Traité de Guérande | Paris | **2** : (648486.260 ; 6861930.707)<br>(722207.665 ; 6855907.784) | **2** : (648765.895 ; 6864521.222)<br>(722026.416 ; 6854970.906) | 3,523 | 5,356 |
| 12 Avril 1365 : Traité de Guérande | Turin | **2** : (229890.582 ; 6591250.193)<br>(1052128.426 ; 6471362.588) | **2** : (228048.198 ; 6590916.701)<br>(1051649.397 ; 6471626.643) | 26,273 | 26,790 |
| 12 Avril 1365 : Traité de Guérande | Boulogne | — | — | — | — |
| 12 Avril 1365 : Traité de Guérande | Waterloo (Bouvines) | **2** : (636680.805 ; 7089815.214)<br>(795770.753 ; 7067071.017) | **2** : (636680.805 ; 7089815.214)<br>(795770.753 ; 7067071.017) | n.d. | n.d. |
| 12 Avril 1365 : Traité de Guérande | Lons-le-Saunier | **1** : (892434.712 ; 6633580.974) | **2** : (487800.994 ; 6841752.586)<br>(892434.712 ; 6633580.974) | n.d. | n.d. |
| 12 Avril 1365 : Traité de Guérande | Le Bec | — | **1** : (547413.596 ; 6913649.854) | n.d. | n.d. |
| 20 Mars 1815 : Début des 100 jours | Dover | **2** : (429239.102 ; 7058465.944)<br>(588397.611 ; 7107079.999) | **2** : (429341.641 ; 7058329.148)<br>(588316.171 ; 7111398.759) | n.d. | n.d. |
| 20 Mars 1815 : Début des 100 jours | 3RDV | **8** : (1027123.319 ; 6806633.148)<br>(281539.511 ; 6522780.008)<br>(1023046.453 ; 6816112.943)<br>(282098.728 ; 6521396.834)<br>(1022653.268 ; 6817818.225)<br>(286012.878 ; 6511594.970)<br>(1018576.402 ; 6827298.021)<br>(286572.095 ; 6510211.796) | **7** : (1026862.423 ; 6806532.479)<br>(281799.008 ; 6522880.119)<br>(282820.200 ; 6521693.287)<br>(1022379.674 ; 6817706.112)<br>(286287.941 ; 6511707.668)<br>(1018629.438 ; 6827320.977)<br>(286536.797 ; 6510196.519) | 20,136 | 20,510 |
| 20 Mars 1815 : Début des 100 jours | Portsmouth | **2** : (430592.979 ; 7052229.585)<br>(585575.600 ; 7112806.157) | **2** : (427967.582 ; 7055665.338)<br>(585580.469 ; 7112633.261) | n.d. | n.d. |
| 20 Mars 1815 : Début des 100 jours | Quiberon | **2** : (394558.200 ; 6324716.242)<br>(235220.709 ; 6735361.395) | **2** : (394685.025 ; 6324796.632)<br>(235182.776 ; 6735348.579) | n.d. | n.d. |
| 20 Mars 1815 : Début des 100 jours | Vézelay | **8** : (759776.886 ; 6702604.633)<br>(548883.893 ; 6626808.699)<br>(761719.350 ; 6696848.964)<br>(549971.953 ; 6624273.917)<br>(756965.873 ; 6709645.117)<br>(551702.319 ; 6619768.304)<br>(758908.337 ; 6703889.448)<br>(559324.289 ; 6619979.183) | **8** : (759400.765 ; 6702464.996)<br>(549257.007 ; 6626947.134)<br>(761931.722 ; 6696924.407)<br>(550090.012 ; 6624311.456)<br>(756589.597 ; 6709485.219)<br>(552081.949 ; 6619929.541)<br>(757861.412 ; 6703454.495)<br>(552976.961 ; 6617307.093) | 2,126 | 1,894 |
| 15 Juin 1066 : Guillaume le conquérant | Solesmes | **2** : (453012.653 ; 6752221.467)<br>(748586.649 ; 6867477.163) | **2** : (449561.383 ; 6754884.198)<br>(747692.768 ; 6864529.040) | 3,084 | 3,588 |
| 15 Juin 1066 : Guillaume le conquérant | Come | **2** : (384660.003 ; 7113682.222)<br>(1166399.733 ; 6572594.404) | **2** : (384778.515 ; 7113323.306)<br>(1175946.524 ; 6565465.433) | n.d. | n.d. |
| 15 Juin 1066 : Guillaume le conquérant | Laffrey | **2** : (938276.907 ; 6440251.625)<br>(586611.536 ; 6314496.413) | **2** : (935540.930 ; 6441827.081)<br>(584940.047 ; 6310990.003) | 19,759 | 17,096 |
| 15 Juin 1066 : Guillaume le conquérant | Châlons-en-Champagne | **8** : (797819.358 ; 6863787.659)<br>(510894.462 ; 6465657.712)<br>(795422.510 ; 6857640.822)<br>(518293.393 ; 6460829.524)<br>(514155.391 ; 6463358.511)<br>(794559.134 ; 6866088.493)<br>(521554.323 ; 6458530.322)<br>(795823.451 ; 6865184.192) | **8** : (797791.549 ; 6863748.895)<br>(510921.765 ; 6465695.761)<br>(799060.855 ; 6862849.937)<br>(518598.820 ; 6461266.689)<br>(514187.342 ; 6463404.106)<br>(794527.683 ; 6866043.602)<br>(521546.867 ; 6458517.905)<br>(795903.493 ; 6865303.981) | n.d. | n.d. |
| 19 Juillet 933 : Hommage de Guillaume Longue Epée | Beaufort en Vallée | **2** : (454904.605 ; 6658588.659)<br>(458364.260 ; 6704108.577) | **2** : (454904.605 ; 6658588.659)<br>(458346.471 ; 6704099.829) | 5,285 | 5,292 |
| 19 Juillet 933 : Hommage de Guillaume Longue Epée | Lampouy | **2** : (330894.144 ; 6805828.455)<br>(889173.607 ; 6402124.898) | **2** : (325440.905 ; 6811295.862)<br>(900356.290 ; 6396534.233) | 8,318 | 0,815 |
| 19 Juillet 933 : Hommage de Guillaume Longue Epée | Carnac | **3** : (1056624.142 ; 6689941.252)<br>(250894.074 ; 6662941.822)<br>(257590.306 ; 6738029.003) | **2** : (250444.457 ; 6662923.123)<br>(257240.010 ; 6738112.033) | 14,076 | 13,721 |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Pic du Midi | **2** : (448740.929 ; 6193104.052)<br>(1081183.409 ; 6376528.447) | **2** : (448245.766 ; 6191172.392)<br>(1079201.474 ; 6378378.973) | 23,476 | 25,132 |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Mirebeau | **2** : (493356.246 ; 6631909.819)<br>(500152.292 ; 6693002.254) | **2** : (498511.492 ; 6632164.515)<br>(495400.568 ; 6692389.640) | 9,030 | 13,834 |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Zone | **4** : (506974.011 ; 6728801.926)<br>(510442.485 ; 6736246.032)<br>(744967.029 ; 6796103.969)<br>(730731.656 ; 6804958.337) | **2** : (510442.485 ; 6736246.032)<br>(730731.656 ; 6804958.337) | n.d. | n.d. |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Le Mans | — | **1** : (686909.040 ; 6865481.990) | n.d. | n.d. |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Montmirail | **1** : (547753.292 ; 6543396.378) | **2** : (542903.207 ; 6786392.345)<br>(547753.292 ; 6543396.378) | n.d. | n.d. |

## Répartition de l’admissibilité et des angles

Chaque observation est une configuration A/droite horaire, donc deux intersections A sur une même droite peuvent partager le même angle. Les 208 rejets ne sont pas comptés parmi les candidats.

| Distance A–Q | Toutes configurations | Admissibles |
|---|---:|---:|
| 0 à 5 km (borne haute incluse) | 29 | 29 |
| 5 à 10 km (borne haute incluse) | 19 | 19 |
| 10 à 20 km (borne haute incluse) | 27 | 27 |
| 20 à 30 km (borne haute incluse) | 13 | 13 |
| 30 à 100 km (borne haute incluse) | 45 | 0 |
| 100 à 300 km (borne haute incluse) | 87 | 0 |
| 300 à +∞ km (borne haute incluse) | 76 | 0 |

| Angle aigu | Toutes configurations | Admissibles |
|---|---:|---:|
| 0 à 5° (borne haute incluse) | 44 | 23 |
| 5 à 15° (borne haute incluse) | 30 | 5 |
| 15 à 30° (borne haute incluse) | 74 | 27 |
| 30 à 45° (borne haute incluse) | 48 | 12 |
| 45 à 90° (borne haute incluse) | 100 | 21 |

## Cas dégradés et faux positifs possibles

| Événement | Scénario | Plus proche avant (km) | Plus proche après (km) | Dégradation (km) |
|---|---|---:|---:|---:|
| 15 Aout 778 : Bataille de Roncevaux | Ferté Alais | 11,044 | 11,109 | 0,065 |
| 30 Mai 1431 : Mort de Jeanne d’Arc | Donon | 17,126 | 21,112 | 3,986 |
| 27 Juillet 1214 : Bataille des Bouvines | Vézelay | 14,945 | 16,098 | 1,152 |
| 12 Avril 1365 : Traité de Guérande | Paris | 3,523 | 5,356 | 1,833 |
| 12 Avril 1365 : Traité de Guérande | Turin | 26,273 | 26,790 | 0,517 |
| 20 Mars 1815 : Début des 100 jours | 3RDV | 20,136 | 20,510 | 0,374 |
| 15 Juin 1066 : Guillaume le conquérant | Solesmes | 3,084 | 3,588 | 0,504 |
| 19 Juillet 933 : Hommage de Guillaume Longue Epée | Beaufort en Vallée | 5,285 | 5,292 | 0,007 |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Pic du Midi | 23,476 | 25,132 | 1,656 |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Mirebeau | 9,030 | 13,834 | 4,804 |

**Donon perd sa couverture : 17,126 → 21,112 km.** Mirebeau recule de 4,804 km tout en restant couvert ; Paris, Solesmes, Vézelay 1214 et Beaufort reculent aussi sans perdre la couverture. 3RDV et Pic du Midi restent hors rayon et reculent davantage. Compiègne est inchangée à la précision géométrique, pas classée artificiellement en dégradation.

Pour rendre les faux positifs possibles vérifiables, voici les **34 centres géométriquement nouveaux** situés au-delà de 20 km du lieu de leur scénario. Ce classement évalue la concordance avec le lieu visé, sans prétendre disposer d’une vérité externe sur les solutions. Les 23 centres nouveaux non géoréférencés restent non classés.

| Événement | Scénario | Centre P (m L93) | Distance au lieu (km) |
|---|---|---|---:|
| 15 Aout 778 : Bataille de Roncevaux | Jumièges | (420407.958 ; 6519975.125) | 425,710 |
| 15 Aout 778 : Bataille de Roncevaux | St Julien de Mailloc | (912333.081 ; 6783282.413) | 421,918 |
| 15 Aout 778 : Bataille de Roncevaux | Ferté Alais | (642984.282 ; 6511734.210) | 312,681 |
| 15 Aout 778 : Bataille de Roncevaux | Ferté Alais | (593610.129 ; 6524434.597) | 306,619 |
| 15 Aout 778 : Bataille de Roncevaux | Lac Trémelin | (1010320.407 ; 6608729.133) | 707,960 |
| 15 Aout 778 : Bataille de Roncevaux | Loches | (780879.350 ; 6643465.970) | 234,295 |
| 15 Aout 778 : Bataille de Roncevaux | Loches | (536973.943 ; 6707113.840) | 37,312 |
| 15 Aout 778 : Bataille de Roncevaux | Loches | (766448.213 ; 6615522.931) | 225,254 |
| 30 Mai 1431 : Mort de Jeanne d’Arc | Donon | (965826.957 ; 6930470.235) | 107,110 |
| 30 Mai 1431 : Mort de Jeanne d’Arc | Donon | (1028237.747 ; 6835593.018) | 21,112 |
| 30 Mai 1431 : Mort de Jeanne d’Arc | La Ferté Alais | (808762.941 ; 6592956.623) | 275,358 |
| 27 Juillet 1214 : Bataille des Bouvines | Brétigny | (632208.299 ; 6811897.586) | 36,157 |
| 27 Juillet 1214 : Bataille des Bouvines | Vézelay | (712198.213 ; 6777580.371) | 82,753 |
| 12 Avril 1365 : Traité de Guérande | Paris | (722026.416 ; 6854970.906) | 70,901 |
| 12 Avril 1365 : Traité de Guérande | Turin | (228048.198 ; 6590916.701) | 853,065 |
| 12 Avril 1365 : Traité de Guérande | Turin | (1051649.397 ; 6471626.643) | 26,790 |
| 20 Mars 1815 : Début des 100 jours | 3RDV | (1026862.423 ; 6806532.479) | 817,594 |
| 20 Mars 1815 : Début des 100 jours | 3RDV | (281799.008 ; 6522880.119) | 20,510 |
| 20 Mars 1815 : Début des 100 jours | 3RDV | (282820.200 ; 6521693.287) | 20,915 |
| 20 Mars 1815 : Début des 100 jours | 3RDV | (1022379.674 ; 6817706.112) | 817,505 |
| 20 Mars 1815 : Début des 100 jours | 3RDV | (286287.941 ; 6511707.668) | 22,687 |
| 20 Mars 1815 : Début des 100 jours | 3RDV | (1018629.438 ; 6827320.977) | 817,670 |
| 20 Mars 1815 : Début des 100 jours | 3RDV | (286536.797 ; 6510196.519) | 23,090 |
| 20 Mars 1815 : Début des 100 jours | Vézelay | (549257.007 ; 6626947.134) | 222,265 |
| 20 Mars 1815 : Début des 100 jours | Vézelay | (550090.012 ; 6624311.456) | 222,463 |
| 20 Mars 1815 : Début des 100 jours | Vézelay | (552081.949 ; 6619929.541) | 222,308 |
| 20 Mars 1815 : Début des 100 jours | Vézelay | (552976.961 ; 6617307.093) | 222,537 |
| 15 Juin 1066 : Guillaume le conquérant | Solesmes | (747692.768 ; 6864529.040) | 314,166 |
| 15 Juin 1066 : Guillaume le conquérant | Laffrey | (584940.047 ; 6310990.003) | 357,747 |
| 19 Juillet 933 : Hommage de Guillaume Longue Epée | Lampouy | (900356.290 ; 6396534.233) | 709,573 |
| 19 Juillet 933 : Hommage de Guillaume Longue Epée | Carnac | (250444.457 ; 6662923.123) | 76,409 |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Pic du Midi | (448245.766 ; 6191172.392) | 25,132 |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Pic du Midi | (1079201.474 ; 6378378.973) | 635,758 |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Mirebeau | (495400.568 ; 6692389.640) | 57,736 |

### Replis sur le milieu

Les sept cas B absent sont maintenus conformément à la mission, et signalés dans les infobulles. Ils ne sont pas confondus avec un centre pondéré ayant un vrai triangle ABC.

| Événement | Scénario | Branche / heure | A–Q (km) | θ | Centre M (m L93) |
|---|---|---|---:|---:|---|
| 15 Aout 778 : Bataille de Roncevaux | Loches | AM / 10:55:00 | 5,591 | 72,124° | (536066.865 ; 6675316.636) |
| 15 Aout 778 : Bataille de Roncevaux | Loches | AM / 13:09:03 | 29,892 | 53,253° | (780879.350 ; 6643465.970) |
| 15 Aout 778 : Bataille de Roncevaux | Loches | PM / 10:55:00 | 20,953 | 55,042° | (536973.943 ; 6707113.840) |
| 15 Aout 778 : Bataille de Roncevaux | Loches | PM / 13:09:03 | 13,646 | 70,335° | (766448.213 ; 6615522.931) |
| 30 Mai 1431 : Mort de Jeanne d’Arc | La Ferté Alais | AM / 13:39:02 | 23,378 | 83,358° | (808762.941 ; 6592956.623) |
| 30 Mai 1431 : Mort de Jeanne d’Arc | La Ferté Alais | PM / 10:25:04 | 16,034 | 84,982° | (654100.526 ; 6831173.532) |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Montmirail | AM / 13:09:03 | 4,340 | 76,805° | (542903.207 ; 6786392.345) |

## Tests

- Tests ciblés : `python -m pytest tests/test_cadran_final_pondere.py tests/test_algorithme_cadran_final.py tests/test_algorithme_cadran_final_golden.py tests/test_cadran_final_midi_local.py tests/test_cadran_final_clef2.py -q --tb=short` — **113 réussites en 34,83 s**.
- Suite complète : `python -m pytest -q --tb=short` — **890 réussites en 243,76 s**.
- 22 nouveaux cas : angles 0°, quasi nuls, 5/10/15/30/45/60/90/135/180°, projection orthogonale oblique, limite 30 km et dépassement millimétrique, C très lointain, absence de B/C, sélection du B proche, inversion des directions, direction nulle refusée, pipeline réel avec calibration, informations d’affichage et accès historique.
- Les tests historiques de convergence, les golden, les heures nationales et les substitutions Clef/Clef 2 restent exécutés. Aucun JSON golden ni scénario n’est modifié.

## Recommandation

**Ajuster et poursuivre l’évaluation avant toute adoption définitive.** Cette expérience mérite d’être conservée accessible : Lombrives et Lampouy se rapprochent nettement, Loches et La Ferté Alais sont retrouvées, les petits angles restent numériquement stables et Carnac/Beaufort restent couverts. Mais le gain net de couverture n’est que d’un scénario, Donon est perdu et les centres éloignés restent nombreux. Le cas aigu attendu de Montmirail n’est pas reproduit et sa référence manque. Ces limites empêchent de recommander un remplacement définitif validé.

La méthode est activée à titre expérimental comme demandé ; l’ancienne reste appelable pour comparaison et retour immédiat par l’appel `methode="historique"`. **Aucun ajustement de seuil, poids, date ou scénario n’est réalisé après observation.** Toute évolution ultérieure nécessite une nouvelle expérience explicitement définie.
