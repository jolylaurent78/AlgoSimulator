# Base Cadran — Sélection des heures selon le calendrier

État de départ : `f3d1cde0f832744cb5aea9f1b0b2b78682def841`, branche `dev`. Mesures réalisées le 29/10/2026 sur les 18 scénarios existants, sans modification de leurs paramètres ni sauvegarde des JSON ou caches.

## Règle appliquée et diff exact

Le calendrier choisit la note de départ : note automatiquement détectée du stylet pour Standard, lettre de déclinaison transmise par le dataset pour Déclinaison. La substitution conserve cette note (`=`) ou lui applique `decalageGamme()` (`+2` et `-2`). Le choix `11:00` impose le Joker avant cette sélection. La période AM/PM résout ensuite la vraie heure nationale et ses secondes fractionnaires.

**Règle complémentaire confirmée par l'utilisateur : si le stylet est détecté J, J reste J avec `=`, `+2` et `-2`.** J ne figure pas dans la gamme C–D–E–F–G–A–B de `decalageGamme()`. Cette exception locale évite une erreur de chargement, notamment pour Reims (Alise-Sainte-Reine, Joker détecté, Standard +2), sans modifier la fonction musicale ni le référentiel.

```diff
diff --git a/src/AlgorithmeBaseCadran.py b/src/AlgorithmeBaseCadran.py
index 9b7ccf2..17b5f0a 100644
--- a/src/AlgorithmeBaseCadran.py
+++ b/src/AlgorithmeBaseCadran.py
@@ -164,12 +164,18 @@ class CercleHoraire(ModuleAlgo):
             # On prend en compte les heures de substitution
             if self.heureSubstitution == "11:00":
                 choixNote = "J"
-            # elif self.choixCalendrierSegment == "Standard":
-            #    self.heureSentinelle = self.heureStylet
             else:
-                tabDec = {"=": 0, "+2": 2, "-2": 1}
-                listeNotes = decalageGamme(self.lettreChoixSegment)  # On décale sans susbtition Fa/Sol
-                choixNote = listeNotes[tabDec[self.heureSubstitution]]
+                if self.choixCalendrierSegment == "Standard":
+                    noteDepart = self.selectionHoraire.note
+                else:
+                    noteDepart = self.lettreChoixSegment
+                # Le Joker reste hors de la gamme, même avec +2 ou -2.
+                if noteDepart == "J" or self.heureSubstitution == "=":
+                    choixNote = noteDepart
+                else:
+                    tabDec = {"+2": 2, "-2": 1}
+                    listeNotes = decalageGamme(noteDepart)  # On décale sans susbtition Fa/Sol
+                    choixNote = listeNotes[tabDec[self.heureSubstitution]]
             self.noteHoraire = choixNote
             direction = self.sentinelle.directionPourNote(choixNote, self.heureAMPM)
             self.brancheReference = ("directe" if direction is self.sentinelle.par_note[choixNote].directe else "miroir")
```

La détection et l'heure automatique du stylet, les appels `directionPourNote()` et `heurePourNote()`, la conversion TML → UT1, l'angle absolu et le choix du côté du cercle restent intacts. Le contrôle SHA-256 des 59 fichiers protégés et la comparaison AST des autres classes Base confirment l'absence de changement aux distances, partitions, seuils, autres algorithmes, données et cartographie. Les deux fichiers de tests adaptés et ce rapport complètent la livraison.

## Châlus — Validation détaillée

Paramètres sauvegardés : Saint-Valentin, 19/07/933, Standard, PM, cercle PM, Carnac, centre distance Stylet. Le nom du scénario reste `Chalus` dans le JSON. La détection reste **S7 / B, miroir PM, 12:33:19**, soit **45199,456841580075 secondes TML**, pour toutes les substitutions et périodes.

| Substitution | Note finale | Heure AM | Heure PM |
|---|---|---|---|
| `=` | B — Si | 11:30:42 | 12:33:19 |
| `+2` | D — Ré | 08:14:46 | 15:49:38 |
| `-2` | G — Sol | 12:00:00 | 12:04:01 |
| `11:00` | J — Joker | 10:55:00 | 13:09:03 |

Avec les paramètres sauvegardés (`=`, PM), la note de calcul passe de D à B, l'heure de **15:49:38 à 12:33:19** et l'angle de **78,892976° à 14,543273°**. L'azimut solaire calculé à Carnac est 194,543273°. En AM, l'heure devient **11:30:42**, branche directe, avec un angle de **16,825641°** ; l'heure automatique reste 12:33:19. Les tests confrontent les JD et positions solaires au contexte d'observation, en gardant les secondes fractionnaires.

### Propagation à CercleDistance

Aucune formule de distance n'est modifiée. À Châlus, les quatre essais en mémoire donnent :

| Période | Centre | Heure distance | Secondes TML | Hauteur solaire | Rayon |
|---|---|---|---|---|---|
| PM | Stylet | 12:33:19 | 45199,456841580075 | 61,864000° | 160,872804 km |
| AM | Stylet | 11:30:42 | 41442 | 61,659589° | 162,255636 km |
| PM | Ouverture | 12:00:00 | 43200 | 62,475085° | 156,770005 km |
| AM | Ouverture | 12:00:00 | 43200 | 62,475085° | 156,770005 km |

Le rayon sauvegardé (centre Stylet) était 396,479221 km avant correction. Les essais de changement de centre et de période ne sont pas enregistrés.

## Comparaison des 16 bases principales

Les couples `Base1` / `Base2` des huit dates renseignées dans le dataset identifient les 16 bases principales. Les deux scénarios supplémentaires sont présentés séparément. Les noms d'affichage ci-dessous respectent les lieux ; les variantes d'orthographe des noms enregistrés restent intactes. Les heures et angles sont arrondis pour le tableau uniquement.

| Base / date historique | Calendrier | Substitution | Note de départ avant → après | Note finale avant → après | Heure avant → après | Angle avant → après (°) | Candidats avant → après |
|---|---|---|---|---|---|---|---|
| Saint-Amour / 15 Aout 778 | Standard | `=` | C → C | C → C | 09:43:00 → 09:43:00 | 51.838407 → 51.838407 | 1 → 1 |
| Rocamadour / 15 Aout 778 | Déclinaison | `=` | F → F | F → F | 10:25:04 → 10:25:04 | 38.590115 → 38.590115 | 1 → 1 |
| Gergovie / 15 Juin 1066 | Déclinaison | `=` | F → F | F → F | 10:25:04 → 10:25:04 | 46.274741 → 46.274741 | 1 → 1 |
| Carignan / 15 Juin 1066 | Déclinaison | `+2` | F → F | A → A | 11:42:00 → 11:42:00 | 9.745647 → 9.745647 | 0 → 0 |
| Île-d’Aix / 20 Mars 1815 | Déclinaison | `-2` | E → E | C → C | 09:43:00 → 09:43:00 | 44.530887 → 44.530887 | 2 → 2 |
| Aléria / 20 Mars 1815 | Standard | `=` | B → G | B → G | 12:33:19 → 12:04:01 | 8.547141 → 1.290640 | 1 → 2 |
| Metz / 27 Juillet 1214 | Déclinaison | `-2` | D → D | B → B | 12:33:19 → 12:33:19 | 13.504731 → 13.504731 | 1 → 1 |
| Château-Gaillard / 27 Juillet 1214 | Standard | `11:00` | — (Joker imposé) | J → J | 10:55:00 → 10:55:00 | 31.486580 → 31.486580 | 0 → 0 |
| Saint-Cyr–Coëtquidan / 30 Mai 1431 | Standard | `-2` | C → A | A → F | 11:42:00 → 10:25:04 | 8.538170 → 44.828028 | 1 → 0 |
| Domrémy / 30 Mai 1431 | Déclinaison | `=` | A → A | A → A | 12:22:01 → 12:22:01 | 13.295069 → 13.295069 | 0 → 0 |
| Reims / 12 Avril 1365 | Standard | `+2` | D → J | F → J | 10:25:04 → 10:55:00 | 36.311862 → 25.557788 | 1 → 0 |
| Bouvines / 12 Avril 1365 | Standard | `11:00` | — (Joker imposé) | J → J | 10:55:00 → 10:55:00 | 25.557788 → 25.557788 | 1 → 1 |
| Châlus / 19 Juillet 933 | Standard | `=` | D → B | D → B | 15:49:38 → 12:33:19 | 78.892976 → 14.543273 | 0 → 0 |
| Fontevraud / 19 Juillet 933 | Standard | `-2` | D → B | B → G | 12:33:19 → 12:04:01 | 14.543273 → 0.171529 | 0 → 0 |
| Pont de Noirmoutiers / 18 Mai 1152 | Standard | `=` | E → G | E → G | 08:05:20 → 12:00:00 | 80.643475 → 2.491666 | 0 → 2 |
| Le Goulet / 18 Mai 1152 | Standard | `138.5°` | — (angle Lampouy) | L → L | 08:05:20 → 12:00:00 (*) | 41.500000 → 41.500000 | 1 → 1 |

## Deux scénarios supplémentaires

| Base / date historique | Calendrier | Substitution | Note de départ avant → après | Note finale avant → après | Heure avant → après | Angle avant → après (°) | Candidats avant → après |
|---|---|---|---|---|---|---|---|
| Rouen / 20 Mars 1815 | Standard | `11:00` | — (Joker imposé) | J → J | 13:09:03 → 13:09:03 | 20.224477 → 20.224477 | 0 → 0 |
| St Michael's Mount / 20 Mars 1815 | Standard | `=` | B → G | B → G | 12:33:19 → 12:04:01 | 8.547141 → 1.290640 | 0 → 0 |

Le total passe de **11 à 12 candidats** : Aléria passe de 1 à 2, Pont de Noirmoutiers de 0 à 2, Saint-Cyr–Coëtquidan et Reims de 1 à 0. Les autres nombres restent identiques. Les 18 heures automatiques des stylets et les états de sélection enregistrés sont inchangés.

## Coordonnées des candidats

Centres en mètres Lambert-93, arrondis au millimètre. Les scénarios absents de cette table n'ont aucun candidat avant ni après. Aucun réglage n'est ajusté pour retrouver une correspondance historique.

| Base | Centres avant | Centres après |
|---|---|---|
| Saint-Amour | (888574.512 ; 6594140.364) | (888574.512 ; 6594140.364) |
| Rocamadour | (583844.131 ; 6399250.150) | (583844.131 ; 6399250.150) |
| Gergovie | (695227.736 ; 6486010.239) | (695227.736 ; 6486010.239) |
| Île-d’Aix | (377128.726 ; 6539620.079)<br>(371660.687 ; 6546823.649) | (377128.726 ; 6539620.079)<br>(371660.687 ; 6546823.649) |
| Aléria | (856647.524 ; 6476757.133) | (851613.573 ; 6469725.117)<br>(1210156.204 ; 6085830.625) |
| Metz | (288918.834 ; 6708245.351) | (288918.834 ; 6708245.351) |
| Saint-Cyr–Coëtquidan | (330364.998 ; 6772578.619) | — |
| Reims | (786717.909 ; 6899512.556) | — |
| Bouvines | (709697.984 ; 7039227.429) | (709697.984 ; 7039227.429) |
| Pont de Noirmoutiers | — | (311417.214 ; 6642264.743)<br>(988498.335 ; 6626489.522) |
| Le Goulet | (602578.049 ; 6885749.081) | (602578.049 ; 6885749.081) |

### Diagnostic géométrique des variations

Lorsque les cercles s'intersectent, une intersection doit être à moins de 20 km de sa projection sur une partition candidate. En l'absence d'intersection, le repli compare les intersections des partitions avec les deux cercles, avec le même seuil strict de 20 km. Ces conditions restent inchangées.

| Base | Intersections des cercles après | Partitions candidates après | Plus petite distance pertinente après | Résultat |
|---|---|---|---|---|
| Châlus | 2 | 1 | Projection : 120,526514 km | Aucun candidat |
| Aléria | 2 | 5 | Projection : 2,136230 km | Deux candidats |
| Pont de Noirmoutiers | 2 | 6 | Projection : 4,055618 km | Deux candidats |
| Saint-Cyr–Coëtquidan | 0 | 1 | Écart du repli : 212,362013 km | Aucun candidat |
| Reims | 2 | 2 | Projection : 41,275298 km | Aucun candidat |
| Fontevraud | 2 | 6 | Projection : 54,089831 km | Aucun candidat |
| St Michael's Mount | 2 | 4 | Projection : 85,100499 km | Aucun candidat |

Les tests vérifient les centres nouveaux d'Aléria et de Pont de Noirmoutiers à partir des intersections, projections admissibles et milieux, avant de les comparer aux coordonnées attendues. Les disparitions de Saint-Cyr–Coëtquidan et Reims sont aussi contrôlées, sans modification des seuils. La fixture golden Rocamadour, en Déclinaison, conserve toutes ses assertions.

### Particularité historique de Lampouy (*)

Pour Le Goulet, l'angle imposé de 41,5°, le troisième point, la distance et le candidat restent identiques. Le traitement historique du signe PM reste intact. Cette substitution angulaire conserve toutefois le champ horaire issu du calcul précédent, comme documenté au lot 3. Lors du chargement, le calcul initial Standard + `=`, effectué avant restauration de l'option Lampouy, utilise maintenant S5 : le champ horaire résiduel passe de 08:05:20 à 12:00:00. Ce champ n'est pas l'origine de l'angle Lampouy. Le centre sauvegardé est Ouverture, donc sa distance reste également identique. Aucun nouveau mécanisme de migration ou de remplacement d'heure n'est introduit.

## Tests et limites

- Tests ciblés : `python -m pytest tests/test_algorithme_base_cadran.py tests/test_algorithme_base_cadran_golden.py tests/test_cadrans_sentinelles_lot3.py -q --tb=short` — **99 réussites**.
- Suite complète : `python -m pytest -q --tb=short` — **791 réussites en 221,34 s**, sur la règle finale incluant l'exception J confirmée.
- Couverture nouvelle : Standard et Déclinaison, toutes substitutions, les deux périodes et côtés du cercle, heures exactes et fractions de seconde, S3/S4 directes PM, stabilité de la détection automatique, J détecté avec `=`/`+2`/`-2`, propagation vers les deux centres de distance, chargement des projets et contrôles géométriques des candidats.
- Les chargements et essais conservent le SHA-256 du projet source. Les autres sources et données protégées sont comparées à leur état de début de mission.

Les absences et disparitions indiquées ci-dessus sont les conséquences mesurées de la règle de sélection, sans compensation artificielle. La dépendance historique du champ horaire Lampouy au calcul précédent reste documentée ; la géométrie de ce cas sauvegardé est inchangée. La revue visuelle intégrée reste celle du lot 4.

Les modifications locales préexistantes de `config/simulateurAlgo.ini`, `projets/Lumiere_Solutions.json` et `projets/StyletInitial_solutions.json` sont préservées et exclues du commit. Aucun projet ni cache n'est sauvegardé par la mission et aucune intervention n'est faite sur `main`.
