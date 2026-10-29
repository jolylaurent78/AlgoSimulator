# Cadran Final — Comparaison de la convergence à deux intersections

Évaluation sur `dev`, révision de départ `d9319e8`, avec les 37 scénarios actuellement enregistrés. Aucun projet, dataset, cache, réglage astronomique ou cartographique n’est écrit par les calculs. Les constructions sont identiques avant/après.

## Règles comparées

- Ancienne règle de secours : distance entre les deux points ≤ 10 km (`RAYON_CANDIDAT / 2`). Chaque point était donc à 5 km maximum du milieu.
- Nouvelle règle : distance entre les deux points ≤ 40 km (`2 * RAYON_CANDIDAT`). Chaque point est à 20 km maximum du milieu.
- Le rayon candidat reste **20 km**. Le barycentre à trois points reste prioritaire **pour chaque combinaison de points**, avec les trois distances au barycentre ≤ 20 km. Un triplet valide empêche le secours pour cette combinaison ; d’autres combinaisons peuvent produire leurs propres candidats.
- Aucun changement des intersections, de visibilité de leur troisième point, du barycentre, du milieu ni des cercles. Le secours historique pouvait déjà intervenir lorsque le troisième point était absent, hors image ou non convergent ; ce périmètre reste identique.

Diff de production complet, limité à une condition et son commentaire :

```diff
-                        # On gère le cas des droites pratiquement parallèles avec pt1 et pt2 < 10km
-                        if not triplet_valide and distance12 <= CandidatFinal.RAYON_CANDIDAT/2:
+                        # Secours : chaque point doit être à 20 km maximum de leur milieu.
+                        if not triplet_valide and distance12 <= 2 * CandidatFinal.RAYON_CANDIDAT:
```

## Protocole et données constantes

Les deux passes chargent le même JSON avec `chargerProjetJsonV1()` : ce chargeur utilise le snapshot de dataset embarqué dans le projet, et non un remplacement par le CSV courant. Le CSV, le snapshot, les dates et tous les paramètres sont conservés strictement identiques. Les empreintes sont vérifiées avant/après chaque passe :

| Fichier inchangé | SHA-256 |
|---|---|
| `projets\CadranFinal_Solutions.json` | `5e66b5bfd8f956956b45c961d8069c5a0cc0fa6a2a8f08bfd61246f436884adc` |
| `data\dataset.csv` | `4201fdb64be9121cd1469512425c515572975673ce31089d14ed8c63e2b9ffd0` |
| `data\villes_database.csv` | `2d914bfeee7ebb5895c39344a886146e297380d871925cc4282d878396e5ce1a` |

Pour chaque passe, un relevé séparé reconstitue les intersections et attribue la méthode à chaque candidat ; sa liste ordonnée de centres est confrontée à celle du vrai `CandidatFinal.construireRepresentationCarte()` (écart < 10⁻⁶ m). Les intersections, distances, barycentres, milieux et paramètres des 37 scénarios sont comparés exactement avant/après. Tous les anciens centres sont conservés.

Les statistiques fusionnent les centres distants d’au plus **1 mm en Lambert-93** dans un scénario ; aucun changement de déduplication n’est introduit en production. Ici, aucun doublon n’est rencontré : totaux bruts, totaux par scénario et totaux géométriquement distincts sur le corpus sont les mêmes.

Les distances sont les distances planes Lambert-93 de `PointGraphique.distance()`, exprimées en kilomètres. Les coordonnées ci-dessous sont des mètres EPSG:2154. Une référence est couverte si au moins un centre se trouve à **20 km maximum** ; ce contrôle ne modifie pas l’état de sélection sauvegardé des scénarios.

## Bilan global

- Candidats : **54 → 85** ; **31 nouveaux**, tous issus de deux points ; aucune disparition.
- Méthodes : barycentres à trois points **40 → 40**, milieux à deux points **14 → 45**.
- Scénarios gagnant des candidats : **18/37** ; scénarios sans candidat : **9 → 5**.
- Scénarios avec une référence mesurable : **23/37** ; scénarios dont le lieu est couvert : **11 → 16**, soit **5 nouveaux lieux couverts**.
- Nouveaux lieux couverts : Jumièges, Grotte Lombrives, Ferté Alais (scénario 778), Solesmes, Lampouy.
- Restent sans candidat : Loches, La Ferté Alais (scénario 1431, distinct de Ferté Alais 778), Boulogne, Le Bec, Le Mans.
- Parmi les 26 nouveaux centres associés à un lieu mesurable, **6** sont à ≤ 20 km, **20** au-delà de 20 km, dont **14** au-delà de 100 km. Les 5 autres ne peuvent être évalués faute de référence.

## Diagnostic détaillé — Grotte Lombrives

Événement : **15 Aout 778 : Bataille de Roncevaux**. Date du segment : **25/07/778**, inchangée. Base **Saint-Amour**, stylet **Roncevaux**, octave **/2**, calendriers Déclinaison dans les trois modules ; substitutions **+2 / −2 / −2**, lumière **PM**, carte **Endroit**. Les deux directions de lumière et les deux heures d’ombre sont explorées comme auparavant. Les intitulés AM/PM ci-dessous désignent les branches géométriques des lignes de lumière, sans changer la période PM enregistrée.

Référence CSV : **Grotte de Lombrives**, (586739.777; 6192530.585).

### Intersections identiques avant/après

| Branche lumière | Cercle–lumière P1[0] / P1[1] |
|---|---|
| AM | (585636.737; 6206440.115) / (723074.499; 7123055.235) |
| PM | (453532.810; 6246895.269) / (855185.719; 7082568.707) |

| Heure ombre | Cercle–ombre P2[0] / P2[1] |
|---|---|
| 08:14:46 | (605913.381; 6203868.455) / (1071170.342; 6868992.870) |
| 15:49:38 | (874506.721; 6256749.070) / (887464.080; 7065526.812) |

| Branche lumière | Heure ombre | Lumière–ombre P3 | P3 visible dans l’image |
|---|---|---|---|
| AM | 08:14:46 | (579613.741; 6166270.882) | oui |
| AM | 15:49:38 | (908162.059; 8357461.655) | non |
| PM | 08:14:46 | (52814.802; 5413166.974) | non |
| PM | 15:49:38 | (888859.553; 7152630.016) | oui |

Les 16 combinaisons de points sont contrôlées. Aucun barycentre à trois points n’est valide. Quand P3 est hors image, la production ne calcule pas son barycentre : « hors image » ne signifie donc pas qu’un tel barycentre a été testé puis rejeté.

| Branche / heure | Indices P1/P2 | Distance P1–P2 (km) | Maximum au barycentre (km) | Décision avant → après |
|---|---|---:|---:|---|
| AM / 08:14:46 | 0/0 | 20,439 | 28,072 | rejet → milieu |
| AM / 08:14:46 | 0/1 | 821,413 | 559,631 | rejet → rejet |
| AM / 08:14:46 | 1/0 | 926,623 | 631,329 | rejet → rejet |
| AM / 08:14:46 | 1/1 | 430,951 | 592,284 | rejet → rejet |
| AM / 15:49:38 | 0/0 | 293,218 | hors image | rejet → rejet |
| AM / 15:49:38 | 0/1 | 910,566 | hors image | rejet → rejet |
| AM / 15:49:38 | 1/0 | 879,442 | hors image | rejet → rejet |
| AM / 15:49:38 | 1/1 | 174,165 | hors image | rejet → rejet |
| PM / 08:14:46 | 0/0 | 158,339 | hors image | rejet → rejet |
| PM / 08:14:46 | 0/1 | 876,631 | hors image | rejet → rejet |
| PM / 08:14:46 | 1/0 | 913,373 | hors image | rejet → rejet |
| PM / 08:14:46 | 1/1 | 303,750 | hors image | rejet → rejet |
| PM / 15:49:38 | 0/0 | 421,089 | 618,962 | rejet → rejet |
| PM / 15:49:38 | 0/1 | 926,528 | 643,691 | rejet → rejet |
| PM / 15:49:38 | 1/0 | 826,046 | 573,903 | rejet → rejet |
| PM / 15:49:38 | 1/1 | 36,501 | 53,677 | rejet → milieu |

### Deux milieux désormais acceptés

| Branche / heure | Barycentre calculé, invalide | Milieu candidat | P1/P2 au milieu (km) | Centre à la grotte (km) | Grotte couverte |
|---|---|---|---:|---:|---|
| AM / 08:14:46 | (590387.953; 6192193.151) | (595775.059; 6205154.285) | 10,220 | 15,524 | oui |
| PM / 15:49:38 | (877169.784; 7100241.845) | (871324.900; 7074047.760) | 18,250 | 926,316 | non |

**Résultat : 0 candidat avant, 2 après, tous deux à deux points.** Le premier couvre la grotte à **15,524 km** ; le second est éloigné et ne la couvre pas. Le barycentre proche de la grotte n’est pas utilisé : son troisième point dépasse le seuil de 20 km. Aucun centre n’est déplacé pour se rapprocher du lieu.

Pour les deux combinaisons finalement acceptées par leur milieu, les distances P1/P2/P3 à leur barycentre invalide sont respectivement **15,018 / 19,426 / 28,072 km**, puis **28,207 / 36,209 / 53,677 km**. Le secours applique uniquement la distance P1–P2 ; il n’intègre pas P3 dans le nouveau centre.

## Tous les scénarios enregistrés

Les deux dernières colonnes donnent la distance du candidat le plus proche au lieu de référence (km). « — » : aucun candidat ; « n.d. » : référence absente ou ambiguë, donc aucune distance inventée.

| Événement | Scénario | Candidats avant | Candidats après | Plus proche candidat avant (km) | Plus proche candidat après (km) |
|---|---|---:|---:|---:|---:|
| 15 Aout 778 : Bataille de Roncevaux | Jumièges | 1 | 2 | 425,631 | 11,920 |
| 15 Aout 778 : Bataille de Roncevaux | Grotte Lombrives | 0 | 2 | — | 15,524 |
| 15 Aout 778 : Bataille de Roncevaux | St Julien de Mailloc | 1 | 2 | 16,532 | 16,532 |
| 15 Aout 778 : Bataille de Roncevaux | Ferté Alais | 0 | 4 | — | 11,044 |
| 15 Aout 778 : Bataille de Roncevaux | Lac Trémelin | 1 | 2 | 6,458 | 6,458 |
| 15 Aout 778 : Bataille de Roncevaux | Loches | 0 | 0 | — | — |
| 30 Mai 1431 : Mort de Jeanne d’Arc | Compiègne | 2 | 2 | 22,136 | 22,136 |
| 30 Mai 1431 : Mort de Jeanne d’Arc | Donon | 2 | 2 | 17,126 | 17,126 |
| 30 Mai 1431 : Mort de Jeanne d’Arc | Frontiere Sud Bretagne | 2 | 2 | n.d. | n.d. |
| 30 Mai 1431 : Mort de Jeanne d’Arc | La Ferté Alais | 0 | 0 | — | — |
| 27 Juillet 1214 : Bataille des Bouvines | Brétigny | 2 | 2 | 15,107 | 15,107 |
| 27 Juillet 1214 : Bataille des Bouvines | Vézelay | 2 | 3 | 14,945 | 14,945 |
| 27 Juillet 1214 : Bataille des Bouvines | Dinard | 0 | 1 | n.d. | n.d. |
| 27 Juillet 1214 : Bataille des Bouvines | Plymouth | 1 | 2 | n.d. | n.d. |
| 12 Avril 1365 : Traité de Guérande | Paris | 2 | 2 | 3,523 | 3,523 |
| 12 Avril 1365 : Traité de Guérande | Turin | 2 | 2 | 26,273 | 26,273 |
| 12 Avril 1365 : Traité de Guérande | Boulogne | 0 | 0 | — | — |
| 12 Avril 1365 : Traité de Guérande | Waterloo (Bouvines) | 2 | 2 | n.d. | n.d. |
| 12 Avril 1365 : Traité de Guérande | Lons-le-Saunier | 1 | 1 | n.d. | n.d. |
| 12 Avril 1365 : Traité de Guérande | Le Bec | 0 | 0 | n.d. | n.d. |
| 20 Mars 1815 : Début des 100 jours | Dover | 2 | 2 | n.d. | n.d. |
| 20 Mars 1815 : Début des 100 jours | 3RDV | 2 | 8 | 23,123 | 20,136 |
| 20 Mars 1815 : Début des 100 jours | Portsmouth | 2 | 2 | n.d. | n.d. |
| 20 Mars 1815 : Début des 100 jours | Quiberon | 2 | 2 | n.d. | n.d. |
| 20 Mars 1815 : Début des 100 jours | Vézelay | 6 | 8 | 2,126 | 2,126 |
| 15 Juin 1066 : Guillaume le conquérant | Solesmes | 1 | 2 | 316,039 | 3,084 |
| 15 Juin 1066 : Guillaume le conquérant | Come | 1 | 2 | n.d. | n.d. |
| 15 Juin 1066 : Guillaume le conquérant | Laffrey | 1 | 2 | 19,759 | 19,759 |
| 15 Juin 1066 : Guillaume le conquérant | Châlons-en-Champagne | 6 | 8 | n.d. | n.d. |
| 19 Juillet 933 : Hommage de Guillaume Longue Epée | Beaufort en Vallée | 2 | 2 | 5,285 | 5,285 |
| 19 Juillet 933 : Hommage de Guillaume Longue Epée | Lampouy | 0 | 2 | — | 8,318 |
| 19 Juillet 933 : Hommage de Guillaume Longue Epée | Carnac | 1 | 3 | 14,076 | 14,076 |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Pic du Midi | 1 | 2 | 23,476 | 23,476 |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Mirebeau | 1 | 2 | 9,030 | 9,030 |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Zone | 4 | 4 | n.d. | n.d. |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Le Mans | 0 | 0 | n.d. | n.d. |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Montmirail | 1 | 1 | n.d. | n.d. |

## Inventaire des nouveaux candidats

Chaque ligne est un centre ajouté, sans doublon. **Tous proviennent du secours à deux points**, jamais d’un nouveau triplet. Les branches et heures indiquent leur provenance. Une distance élevée signale un candidat sans pertinence pour le lieu du scénario, sans prétendre prouver une erreur de construction.

| Événement | Scénario | Centre Lambert-93 (m) | Branche / heure | Distance au lieu (km) | Couverture ≤ 20 km |
|---|---|---|---|---:|---|
| 15 Aout 778 : Bataille de Roncevaux | Jumièges | (548905.051; 6918468.174) | PM / 13:09:03 | 11,920 | oui |
| 15 Aout 778 : Bataille de Roncevaux | Grotte Lombrives | (595775.059; 6205154.285) | AM / 08:14:46 | 15,524 | oui |
| 15 Aout 778 : Bataille de Roncevaux | Grotte Lombrives | (871324.900; 7074047.760) | PM / 15:49:38 | 926,316 | non |
| 15 Aout 778 : Bataille de Roncevaux | St Julien de Mailloc | (905296.019; 6776878.525) | PM / 13:09:03 | 416,808 | non |
| 15 Aout 778 : Bataille de Roncevaux | Ferté Alais | (647926.205; 6824101.706) | AM / 11:42:00 | 11,044 | oui |
| 15 Aout 778 : Bataille de Roncevaux | Ferté Alais | (641201.936; 6505786.119) | AM / 12:22:01 | 318,716 | non |
| 15 Aout 778 : Bataille de Roncevaux | Ferté Alais | (592126.534; 6517924.599) | PM / 11:42:00 | 313,295 | non |
| 15 Aout 778 : Bataille de Roncevaux | Ferté Alais | (740586.009; 6798377.631) | PM / 12:22:01 | 85,545 | non |
| 15 Aout 778 : Bataille de Roncevaux | Lac Trémelin | (998466.407; 6605645.842) | AM / 14:21:11 | 697,314 | non |
| 27 Juillet 1214 : Bataille des Bouvines | Vézelay | (612070.736; 6545489.180) | PM / 11:37:03 | 217,034 | non |
| 27 Juillet 1214 : Bataille des Bouvines | Dinard | (341547.060; 6857308.577) | AM / 10:25:04 | n.d. | n.d. |
| 27 Juillet 1214 : Bataille des Bouvines | Plymouth | (832394.207; 7262578.736) | PM / 09:43:00 | n.d. | n.d. |
| 20 Mars 1815 : Début des 100 jours | 3RDV | (1027123.319; 6806633.148) | AM / 12:00:00 | 817,874 | non |
| 20 Mars 1815 : Début des 100 jours | 3RDV | (281539.511; 6522780.008) | AM / 12:00:00 | 20,234 | non |
| 20 Mars 1815 : Début des 100 jours | 3RDV | (1023046.453; 6816112.943) | AM / 12:04:01 | 817,533 | non |
| 20 Mars 1815 : Début des 100 jours | 3RDV | (282098.728; 6521396.834) | AM / 12:04:01 | 20,136 | non |
| 20 Mars 1815 : Début des 100 jours | 3RDV | (1022653.268; 6817818.225) | PM / 12:00:00 | 817,801 | non |
| 20 Mars 1815 : Début des 100 jours | 3RDV | (286012.878; 6511594.970) | PM / 12:00:00 | 22,421 | non |
| 20 Mars 1815 : Début des 100 jours | Vézelay | (549971.953; 6624273.917) | AM / 12:04:01 | 222,586 | non |
| 20 Mars 1815 : Début des 100 jours | Vézelay | (758908.337; 6703889.448) | PM / 12:04:01 | 4,498 | oui |
| 15 Juin 1066 : Guillaume le conquérant | Solesmes | (453012.653; 6752221.467) | AM / 13:09:03 | 3,084 | oui |
| 15 Juin 1066 : Guillaume le conquérant | Come | (1166399.733; 6572594.404) | PM / 15:59:05 | n.d. | n.d. |
| 15 Juin 1066 : Guillaume le conquérant | Laffrey | (586611.536; 6314496.413) | PM / 09:43:00 | 354,931 | non |
| 15 Juin 1066 : Guillaume le conquérant | Châlons-en-Champagne | (518293.393; 6460829.524) | AM / 12:04:01 | n.d. | n.d. |
| 15 Juin 1066 : Guillaume le conquérant | Châlons-en-Champagne | (521554.323; 6458530.322) | PM / 12:04:01 | n.d. | n.d. |
| 19 Juillet 933 : Hommage de Guillaume Longue Epée | Lampouy | (330894.144; 6805828.455) | AM / 08:14:46 | 8,318 | oui |
| 19 Juillet 933 : Hommage de Guillaume Longue Epée | Lampouy | (889173.607; 6402124.898) | PM / 15:49:38 | 697,234 | non |
| 19 Juillet 933 : Hommage de Guillaume Longue Epée | Carnac | (1056624.142; 6689941.252) | AM / 11:42:00 | 814,555 | non |
| 19 Juillet 933 : Hommage de Guillaume Longue Epée | Carnac | (250894.074; 6662941.822) | AM / 11:42:00 | 76,432 | non |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Pic du Midi | (1081183.409; 6376528.447) | PM / 10:55:00 | 637,177 | non |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Mirebeau | (500152.292; 6693002.254) | PM / 12:26:58 | 59,362 | non |

## Références géographiques et limites

Les variantes de noms suivantes sont rapprochées explicitement des seules entrées correspondantes du CSV, sans créer de coordonnées : Grotte Lombrives → Grotte de Lombrives ; Lac Trémelin → Lac-de-Trémelin ; Ferté Alais et La Ferté Alais → La Ferté-Alais ; Beaufort en Vallée → Beaufort-en-Vallée ; Boulogne → Boulogne-sur-Mer. Les autres références mesurées utilisent une correspondance exacte.

Désignations non ponctuelles, non mesurées : **Frontiere Sud Bretagne**, **Zone**.

Lieux absents du CSV sous une correspondance suffisamment explicite, non mesurés : **Dinard, Plymouth, Lons-le-Saunier, Le Bec, Dover, Portsmouth, Quiberon, Come, Châlons-en-Champagne, Le Mans, Montmirail**. Aucune coordonnée externe n’est recherchée ou inventée.

**Waterloo (Bouvines)** est ambigu : Waterloo et Bouvines ont chacun une entrée dans le CSV. Aucune des deux n’est choisie arbitrairement ; ce scénario est exclu des statistiques de couverture.

## Pouvoir discriminant et effets indésirables

Le passage de 54 à 85 candidats (+57,4 %) retrouve cinq lieux mesurables, mais multiplie également les solutions éloignées. Lombrives reçoit une solution couvrante **et** une solution très éloignée. Ferté Alais 778 reçoit quatre centres ; 3RDV passe de deux à huit et son centre le plus proche reste à **20,136 km**, donc strictement hors couverture. Les deux scénarios Vézelay doivent être distingués par leur événement. Solesmes gagne un centre proche tout en conservant son ancien centre éloigné.

La nouvelle règle est cohérente géométriquement avec une enveloppe de 20 km, mais cette cohérence ne garantit pas l’identification du lieu attendu. Les candidats éloignés détaillés ci-dessus et les références manquantes empêchent de conclure à une amélioration générale du pouvoir discriminant. Aucun filtrage supplémentaire, aucune optimisation, aucune modification des paramètres enregistrés n’est appliqué.

## Tests et réversibilité

- Tests ciblés : `python -m pytest tests/test_algorithme_cadran_final.py tests/test_algorithme_cadran_final_golden.py tests/test_cadran_final_midi_local.py tests/test_cadran_final_clef2.py -q --tb=short` — **91 réussites en 37,62 s**.
- Suite complète : `python -m pytest -q --tb=short` — **868 réussites en 297,69 s**.

Les tests couvrent les séparations 10, 20, 30 et 40 km (acceptées), 40,000001 km (rejetée), le maintien du cas historique 8 km, les troisièmes points absents/hors image/non convergents, les centres exacts et le rayon de 20 km, ainsi que la priorité d’un triplet valide sur son milieu. La fixture Lac Trémelin est vérifiée géométriquement : son barycentre historique reste inchangé, seul un milieu supplémentaire est ajouté. Les assertions golden sont adaptées sans modifier la fixture JSON.

La modification de production se révoque en remettant le seuil `/ 2` et son commentaire ; les tests associés devront revenir à leur ancienne attente. Aucun format, scénario, cache, bouton ou paramètre n’est migré.
