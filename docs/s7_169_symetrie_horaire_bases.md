# S7 à 169° et symétrie horaire des bases

Comparaison au commit `8594b98d7549ceb301207f0d10ef9add8212d72a`, branche `dev`, le 29/10/2026. Les projets sont chargés et calculés uniquement en mémoire, avec contrôle SHA-256 avant/après ; aucune sauvegarde de projet ou cache.

## Calibration S7 : autorité angulaire et provenance

Dans `data/sentinelles_reference_v1.json`, seule S7/B change de définition. Son autorité devient l'azimut solaire **169,000°**, au site de référence Carnac (47°35′36″ N, −3°04′47″), le **15 août 1066 julien**, en temps moyen local et JD UT1, sous Skyfield/DE406. Le moteur solaire et la configuration du site restent inchangés.

L'ancien relevé physique **170°** est conservé dans `azimut_physique_initial`. La section `historique_calibrations` conserve intégralement la définition précédente, ses témoins, son statut et les anciennes valeurs calculées sous DE406. La provenance indique la réévaluation de la lecture physique et conserve la cible horaire indicative 11:35:49. Les sept autres définitions JSON sont identiques à leur état de départ et leurs directions calculées sont testées identiques.

L'ancienne autorité de travail était l'heure 11:30:42, qui donnait un azimut solaire de 166,868688°. Le relevé historique 170° était une provenance distincte de ce calcul ; il n'est ni effacé ni réécrit à 169°.

| Grandeur S7 | Avant | Après |
|---|---|---|
| Autorité | Heure 11:30:42 | Azimut 169° |
| Azimut direct calculé | 166,868688397° | 169,000018372° |
| Heure AM TML | 11:30:42,000 | **11:35:51,130102** |
| Secondes AM | 41442,0 | **41751,13010191123** |
| Azimut miroir national calculé | 193,131316058° | 190,999967503° |
| Heure PM nationale astronomique | 12:33:19,456842 | **12:28:10,153108** |
| Secondes PM nationales | 45199,456841580075 | **44890,1531078736** |
| Heure PM propre aux bases | Ancien miroir national | **12:24:08,869898** |
| Secondes PM des bases | 45199,456841580075 | **44648,86989808877** |

Les affichages arrondis donnent **11:35:51**, **12:28:10** et **12:24:09**. L'heure AM obtenue diffère de 11:35:49 de **+2,130102 secondes** ; la PM des bases diffère de 12:24:11 de −2,130102 secondes. Ces écarts sont signalés, sans forcer simultanément l'heure et l'angle. La précision de recherche du moteur reste 0,01 seconde ; les petits résidus angulaires autour de 169° et 191° proviennent de cette recherche numérique.

## Convention réservée à Base Cadran

La sélection de note (calendrier, substitutions, exception J détecté et Joker explicite) est inchangée. Pour toute note nationale sélectionnée :

```python
heure_am = self.sentinelle.heurePourNote(choixNote, "AM")
heure_pm_base = HeureMoyenneLocale((86400 - heure_am.secondes) % 86400)
```

AM utilise l'heure AM nationale ; PM utilise uniquement cette symétrie temporelle autour de **12:00:00 TML**. Les secondes fractionnaires sont conservées jusqu'à `ContexteObservation.versUT1()` et au calcul solaire. La PM est identifiée par `brancheReference = "symetrie_tml"`, pour ne pas la présenter comme une branche miroir astronomique. L'heure automatique du stylet reste celle de la détection sur le cadran national, avec sa branche astronomique réelle.

Les miroirs nationaux restent la réflexion des azimuts autour de 180°, calculée par le moteur solaire. Stylet Initial, Lumière Initiale et Cadran Final continuent à les consommer sans modification de leur code. S3/E et S4/F partent de leur véritable AM nationale, qui est leur branche miroir ; leur direction directe PM n'est pas utilisée comme point de départ. S5/G donne 12:00:00 dans les deux périodes. Joker donne 10:55:00 AM et 13:05:00 PM pour les bases, tandis que sa PM nationale reste 13:09:03. Lampouy conserve son traitement historique, sans application de cette nouvelle règle.

Après choix de l'heure, le Soleil est recalculé au lieu du module et à `dataset.date` du scénario. La référence S7 à 169° en 1066 n'est jamais substituée à l'azimut de cette date historique. L'angle reste `abs(180 - azimutSoleil)` ; les points fixes Bourges et stylet, les formules et le choix indépendant `cercleAMPM` sont inchangés. CercleDistance reprend les secondes exactes pour le centre Stylet et conserve 43200 secondes pour Ouverture.

## Comparaison des 18 scénarios Base Cadran

L'écart cible–cercle est mesuré sur le contour effectivement affiché par `CercleGraphique.distanceDepuis()`, en pixels, puis converti en km avec l'échelle locale `PointGraphique.pixelsVersMetres()`. Cette mesure utilise les API et la calibration existantes ; elle représente la géométrie affichée et n'est pas une nouvelle distance géodésique ni un critère de sélection des candidats. Les candidats restent déterminés par les intersections et partitions, avec les seuils inchangés.

Les heures de calcul PM des lignes PM ci-dessous sont celles des bases après symétrie TML. Les lignes AM restent des heures nationales. La colonne AM de référence décrit la note finalement sélectionnée dans chaque état ; un changement de note dû à la détection recalibrée peut donc modifier cette colonne.

### Seize bases principales

| Base / date | Stylet / note détectée avant → après | Calendrier / substitution / période | Note finale avant → après | AM nationale de référence avant → après | Heure de calcul avant → après | Angle avant → après (°) | Écart cible–cercle avant → après (km) | Candidats avant → après |
|---|---|---|---|---|---|---|---|---|
| Saint-Amour / 15/08/778 | Roncevaux / C → C | Standard / `=` / AM | C → C | 09:43:00 → 09:43:00 | 09:43:00 → 09:43:00 | 51.838407 → 51.838407 | 0.787025 → 0.787025 | 1 → 1 |
| Rocamadour / 15/08/778 | Roncevaux / C → C | Déclinaison / `=` / AM | F → F | 10:25:04 → 10:25:04 | 10:25:04 → 10:25:04 | 38.590115 → 38.590115 | 1.534708 → 1.534708 | 1 → 1 |
| Gergovie / 15/06/1066 | Nouaillé-Maupertuis / A → A | Déclinaison / `=` / AM | F → F | 10:25:04 → 10:25:04 | 10:25:04 → 10:25:04 | 46.274741 → 46.274741 | 0.593866 → 0.593866 | 1 → 1 |
| Carignan / 15/06/1066 | Nouaillé-Maupertuis / A → A | Déclinaison / `+2` / AM | A → A | 11:42:00 → 11:42:00 | 11:42:00 → 11:42:00 | 9.745647 → 9.745647 | 12.014332 → 12.014332 | 0 → 0 |
| Île-d’Aix / 20/03/1815 | Golfe-Juan / G → G | Déclinaison / `-2` / AM | C → C | 09:43:00 → 09:43:00 | 09:43:00 → 09:43:00 | 44.530887 → 44.530887 | 1.304445 → 1.304445 | 2 → 2 |
| Aléria / 20/03/1815 | Golfe-Juan / G → G | Standard / `=` / PM | G → G | 12:00:00 → 12:00:00 | 12:04:01 → 12:00:00 | 1.290640 → 2.641259 | 54.333742 → 63.003688 | 2 → 2 |
| Metz / 27/07/1214 | Vouneuil-sur-Vienne / G → G | Déclinaison / `-2` / PM | B → B | 11:30:42 → 11:35:51 | 12:33:19 → 12:24:09 | 13.504731 → 9.218471 | 114.720756 → 42.180706 | 1 → 0 |
| Château-Gaillard / 27/07/1214 | Vouneuil-sur-Vienne / G → G | Standard / `11:00` / AM | J → J | 10:55:00 → 10:55:00 | 10:55:00 → 10:55:00 | 31.486580 → 31.486580 | 6.525965 → 6.525965 | 0 → 0 |
| Saint-Cyr–Coëtquidan / 30/05/1431 | Sainte-Catherine-de-Fierbois / A → B | Standard / `-2` / AM | F → G | 10:25:04 → 12:00:00 | 10:25:04 → 12:00:00 | 44.828028 → 1.325648 | 186.969904 → 66.472924 | 0 → 0 |
| Domrémy / 30/05/1431 | Sainte-Catherine-de-Fierbois / A → B | Déclinaison / `=` / PM | A → A | 11:42:00 → 11:42:00 | 12:22:01 → 12:18:00 | 13.295069 → 11.143693 | 26.541878 → 5.375256 | 0 → 1 |
| Reims / 12/04/1365 | Alise-Sainte-Reine / J → J | Standard / `+2` / AM | J → J | 10:55:00 → 10:55:00 | 10:55:00 → 10:55:00 | 25.557788 → 25.557788 | 82.726074 → 82.726074 | 0 → 0 |
| Bouvines / 12/04/1365 | Alise-Sainte-Reine / J → J | Standard / `11:00` / AM | J → J | 10:55:00 → 10:55:00 | 10:55:00 → 10:55:00 | 25.557788 → 25.557788 | 9.460635 → 9.460635 | 1 → 1 |
| Châlus / 19/07/933 | Saint-Valentin / B → B | Standard / `=` / PM | B → B | 11:30:42 → 11:35:51 | 12:33:19 → 12:24:09 | 14.543273 → 10.002615 | 52.498097 → 11.439175 | 0 → 1 |
| Fontevraud / 19/07/933 | Saint-Valentin / B → B | Standard / `-2` / PM | G → G | 12:00:00 → 12:00:00 | 12:04:01 → 12:00:00 | 0.171529 → 2.211739 | 70.326637 → 51.680991 | 0 → 0 |
| Pont de Noirmoutiers / 18/05/1152 | Loudun / G → G | Standard / `=` / AM | G → G | 12:00:00 → 12:00:00 | 12:00:00 → 12:00:00 | 2.491666 → 2.491666 | 13.926783 → 13.926783 | 2 → 2 |
| Le Goulet / 18/05/1152 | Loudun / G → G | Standard / `138.5°` / AM | L → L | angle imposé → angle imposé | 12:00:00 → 12:00:00 | 41.500000 → 41.500000 | 2.279393 → 2.279393 | 1 → 1 |

### Deux scénarios supplémentaires

| Base / date | Stylet / note détectée avant → après | Calendrier / substitution / période | Note finale avant → après | AM nationale de référence avant → après | Heure de calcul avant → après | Angle avant → après (°) | Écart cible–cercle avant → après (km) | Candidats avant → après |
|---|---|---|---|---|---|---|---|---|
| Rouen / 20/03/1815 | Golfe-Juan / G → G | Standard / `11:00` / PM | J → J | 10:55:00 → 10:55:00 | 13:09:03 → 13:05:00 | 20.224477 → 18.927594 | 26.125033 → 16.854518 | 0 → 0 |
| St Michael's Mount / 20/03/1815 | Golfe-Juan / G → G | Standard / `=` / PM | G → G | 12:00:00 → 12:00:00 | 12:04:01 → 12:00:00 | 1.290640 → 2.641259 | 107.328340 → 71.749676 | 0 → 0 |

Le total passe de **12 à 13 candidats** : Châlus et Domrémy gagnent chacun un candidat, Metz perd le sien. Les autres nombres restent identiques ; les centres d'Aléria se déplacent. La détection de Sainte-Catherine-de-Fierbois passe de S6/A à S7/B, ce qui change naturellement la note finale du scénario Standard Saint-Cyr–Coëtquidan (−2 : F → G). Sa construction en Déclinaison, Domrémy, conserve la note finale A. Aucune sélection ou substitution enregistrée n'est modifiée pour compenser ces effets.

### Centres des candidats, Lambert-93 en mètres

Les scénarios absents de cette table n'ont de candidat dans aucun des deux états.

| Base | Centres avant | Centres après |
|---|---|---|
| Saint-Amour | (888574.512 ; 6594140.364) | (888574.512 ; 6594140.364) |
| Rocamadour | (583844.131 ; 6399250.150) | (583844.131 ; 6399250.150) |
| Gergovie | (695227.736 ; 6486010.239) | (695227.736 ; 6486010.239) |
| Île-d’Aix | (377128.726 ; 6539620.079)<br>(371660.687 ; 6546823.649) | (377128.726 ; 6539620.079)<br>(371660.687 ; 6546823.649) |
| Aléria | (851613.573 ; 6469725.117)<br>(1210156.204 ; 6085830.625) | (852694.661 ; 6470829.983)<br>(1203409.397 ; 6079766.538) |
| Metz | (288918.834 ; 6708245.351) | — |
| Domrémy | — | (895978.733 ; 6813738.874) |
| Bouvines | (709697.984 ; 7039227.429) | (709697.984 ; 7039227.429) |
| Châlus | — | (555798.305 ; 6503124.557) |
| Pont de Noirmoutiers | (311417.214 ; 6642264.743)<br>(988498.335 ; 6626489.522) | (311417.214 ; 6642264.743)<br>(988498.335 ; 6626489.522) |
| Le Goulet | (602578.049 ; 6885749.081) | (602578.049 ; 6885749.081) |

## Châlus et Fontevraud : mesures séparées

Les paramètres sauvegardés sont conservés dans les deux cas : Standard, période PM, stylet Saint-Valentin, 19/07/933, observation Carnac, centre distance Stylet.

| Mesure après | Châlus | Fontevraud |
|---|---|---|
| Substitution sauvegardée | `=` | **`-2`** |
| Note automatique nationale | B / S7, miroir | B / S7, miroir |
| Heure automatique nationale | 12:28:10 | 12:28:10 |
| Note finale de calcul | B | **G** |
| Heure AM de référence | 11:35:51 | 12:00:00 |
| Heure PM des bases | **12:24:09** | **12:00:00** |
| Azimut solaire à la date historique | 190,002615° | 177,788261° |
| Angle horaire | 10,002615° | 2,211739° |
| Écart du lieu cible au cercle horaire, avant → après | **52,498097 → 11,439175 km** | **70,326637 → 51,680991 km** |
| Rayon de CercleDistance après | 158,649443 km | 131,827335 km |
| Nombre de candidats, avant → après | 0 → 1 | 0 → 0 |

Châlus ne prend ni 169° ni son ancien angle historique comme azimut imposé. Fontevraud ne reçoit pas l'heure de B et sa substitution −2 n'est pas changée pour retrouver une correspondance.

## Conséquences de S7 dans les autres algorithmes

Aucune ligne de leurs sources n'est modifiée. Les mêmes projets JSON sont chargés avant/après, sans sauvegarde. Les métriques sont distinguées car la proximité d'un cercle ou d'une ligne n'est pas la distance à un candidat complet.

| Module / cible et mesure | Avant | Après |
|---|---|---|
| Stylet Initial : Saint-Valentin, distance géométrique à la ligne nationale la plus proche | **0,076539 km** | **11,940128 km** |
| Stylet Initial : scénario Saint Valentin, distance diagnostique intersection planète–étoile → ligne nationale (affichage entier) | 2 km | 14 km |
| Stylet Initial : distance Saint-Valentin → centre du candidat | 7,914572 km | 10,082420 km |
| Lumière Initiale : Bordeaux, écart au cercle d'ombre affiché | **3,451822 km** | **5,834195 km** |
| Lumière Initiale : Bordeaux, distance au candidat le plus proche | 120,739252 km | 108,323919 km |
| Lumière Initiale : rayon d'ombre | 298,905810 km | 296,446726 km |

Saint-Valentin reste détecté comme S7 miroir et le scénario Stylet Initial reste « Sélectionné » selon son critère inchangé. Son heure nationale passe à 12:28:10. Le projet Lumière Initiale conserve `choixHeure = "Symétrique"` et `sourceHeure = "Stylet"` : il utilise toujours l'autre branche **astronomique** nationale, ici l'AM S7 à 11:35:51. Il n'adopte pas la PM temporelle des bases. L'augmentation des écarts à la ligne de Saint-Valentin et au cercle de Bordeaux est signalée explicitement ; aucun centre, orientation, seuil ou coordonnées n'est réajusté.

## Validation et périmètre

- Tests ciblés (référentiel, bases, lot 2 et nouveaux tests S7/symétrie) : **253 réussites**.
- Suite complète : `python -m pytest -q --tb=short` — **801 réussites en 241,07 s** sur le code final.
- Dix nouveaux tests : autorité S7/DE406, trois heures distinctes, écart à la cible indicative, archive de calibration, identité des autres directions, et huit références dont les bases PM ne peuvent appeler `heurePourNote(note, "PM")`.
- Les tests existants conservent les vérifications de JD exact, calcul solaire indépendant, deux côtés du cercle, S3/S4, S5 à midi, Joker, Lampouy et propagation vers CercleDistance. Les nouveaux centres de candidats sont confrontés aux intersections, projections et milieux admissibles.
- La définition S7 précédente est comparée à l'archive ; les sept autres définitions sont identiques au commit de départ. Les 58 fichiers protégés et les classes Base hors CercleHoraire sont vérifiés inchangés.

Les données géographiques, cartes, centre national et orientation 125,371° restent identiques. Les projets, caches et corpus documentaire ne sont pas modifiés. Les changements locaux préexistants de `config/simulateurAlgo.ini`, `projets/Lumiere_Solutions.json` et `projets/StyletInitial_solutions.json` sont préservés et exclus du commit. La revue visuelle intégrée du lot 4 reste distincte de ces mesures ; aucune impression physique n'est lancée.

## Diff de production

Les changements se limitent à la définition/calibration S7 et à la conversion horaire de CercleHoraire ; les tests et le présent rapport complètent la livraison.

```diff
diff --git a/data/sentinelles_reference_v1.json b/data/sentinelles_reference_v1.json
index d7f9427..488f3bd 100644
--- a/data/sentinelles_reference_v1.json
+++ b/data/sentinelles_reference_v1.json
@@ -4,0 +5,17 @@
+  "historique_calibrations": [
+    {
+      "date_reevaluation": "2026-10-29",
+      "identifiant": "S7",
+      "motif": "Réévaluation de la lecture physique : azimut solaire de travail 169° ; le relevé historique 170° reste conservé dans azimut_physique_initial.",
+      "cible_horaire_indicative": "11:35:49",
+      "calibration_precedente": {
+        "identifiant": "S7", "note": "B", "nature": "sentinelle",
+        "azimut_physique_initial": 170.0,
+        "autorite": "heure", "valeur_reference": "11:30:42",
+        "origine": "Heure affinée par confrontation à la direction de Saint-Valentin.",
+        "statut": "affinee_geographiquement",
+        "temoins": {"azimut_direct": 166.885, "heure_directe": "11:30:42", "azimut_miroir": 193.115, "heure_miroir": "12:33:15"}
+      },
+      "calcul_precedent_de406": {"azimut_direct": 166.86868839693545, "secondes_directes_tml": 41442.0, "azimut_miroir": 193.13131605790574, "secondes_miroir_tml": 45199.456841580075}
+    }
+  ],
@@ -57,4 +74,4 @@
-      "autorite": "heure", "valeur_reference": "11:30:42",
-      "origine": "Heure affinée par confrontation à la direction de Saint-Valentin.",
-      "statut": "affinee_geographiquement",
-      "temoins": {"azimut_direct": 166.885, "heure_directe": "11:30:42", "azimut_miroir": 193.115, "heure_miroir": "12:33:15"}
+      "autorite": "azimut", "valeur_reference": 169.0,
+      "origine": "Réévaluation de la lecture physique des Sentinelles : 169° solaire de travail ; relevé historique 170° conservé en provenance. Heure cible 11:35:49 indicative, heure exacte déterminée par DE406.",
+      "statut": "reevaluee_physiquement",
+      "temoins": {"azimut_direct": 169.0, "heure_directe": "11:35:51", "azimut_miroir": 191.0, "heure_miroir": "12:28:10"}
diff --git a/src/AlgorithmeBaseCadran.py b/src/AlgorithmeBaseCadran.py
index 17b5f0a..658e3a4 100644
--- a/src/AlgorithmeBaseCadran.py
+++ b/src/AlgorithmeBaseCadran.py
@@ -180 +180 @@ class CercleHoraire(ModuleAlgo):
-            direction = self.sentinelle.directionPourNote(choixNote, self.heureAMPM)
+            direction = self.sentinelle.directionPourNote(choixNote, "AM")
@@ -182 +182,5 @@ class CercleHoraire(ModuleAlgo):
-            heure = self.sentinelle.heurePourNote(choixNote, self.heureAMPM)
+            heure = self.sentinelle.heurePourNote(choixNote, "AM")
+            if self.heureAMPM == "PM":
+                # Convention propre aux bases ; le miroir national reste astronomique.
+                heure = HeureMoyenneLocale((86400 - heure.secondes) % 86400)
+                self.brancheReference = "symetrie_tml"
```
