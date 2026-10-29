# S7 — Mesure du passage de 169° à 169,5°

Branche `dev`, état de départ `69cc4fc2e2538fe19301428f90e5ccf54d0ad1dd`, mesures du 29/10/2026. Ajustement expérimental de S7 uniquement ; aucun fichier de `src`, notamment Base Cadran, n'est modifié.

## Référence astronomique

L'autorité de S7/B reste un **azimut solaire**, porté de **169,000° à 169,500°**. Site : Carnac, 47°35′36″ N et −3°04′47″ ; date : **15 août 1066 julien** ; temps moyen local et JD UT1 ; Skyfield/DE406, position apparente sans réfraction. Aucune heure arrondie ne remplace l'autorité angulaire.

Le relevé physique historique **170°** est conservé dans `azimut_physique_initial`. Le premier historique reste identique et une nouvelle entrée archive intégralement la définition de travail à 169° et ses valeurs calculées. La chaîne de provenance couvre ainsi 170° historique, 169° puis 169,5°. Les sept autres définitions, Joker compris, sont strictement identiques.

| Grandeur S7 | 169° avant | 169,5° après |
|---|---|---|
| Azimut direct calculé | 169,000018372° | **169,500015604°** |
| Heure AM nationale TML | 11:35:51,130102 | **11:37:03,305772** |
| Secondes AM exactes | 41751,13010191123 | **41823,305771581334** |
| Azimut du miroir astronomique calculé | 190,999967503° | **190,499966644°** |
| Heure du miroir national TML | 12:28:10,153108 | **12:26:57,941349** |
| Secondes du miroir national | 44890,1531078736 | **44817,9413490812** |
| Heure PM Base Cadran TML | 12:24:08,869898 | **12:22:56,694228** |
| Secondes PM Base Cadran | 44648,86989808877 | **44576,694228418666** |

Affichages arrondis à la seconde après ajustement : **11:37:03 AM**, **12:26:58 miroir national**, **12:22:57 PM Base**. Les petits résidus angulaires correspondent à la précision de recherche inchangée du moteur (0,01 seconde).

Le mécanisme national de miroir solaire reste intact. Base Cadran conserve exactement son code : PM = `(86400 - secondes_AM) % 86400`, avec les fractions de seconde. Les nouvelles heures se propagent naturellement ; aucune formule de cercle ou de distance n'est réécrite.

## Méthode des mesures géométriques

Les projets concernés sont chargés et recalculés en mémoire avant/après, sans sauvegarde et avec vérification du SHA-256 de chaque fichier. Les réglages des scénarios sont conservés. Les mesures utilisent les API géométriques existantes, la même carte et la même calibration :

- Saint-Valentin : distance de la ville à la ligne horaire nationale la plus proche, par `PointGraphique.distanceLigne()`.
- Bordeaux, Châlus et Fontevraud : distance au contour affiché de leur cercle (ombre pour Bordeaux, horaire pour les bases), par `CercleGraphique.distanceDepuis()`, convertie en km avec `pixelsVersMetres()`.
- Les distances à un centre de candidat sont mesurées séparément en Lambert-93 par `PointGraphique.distance()`.

Ces mesures décrivent la géométrie du simulateur. La proximité d'un cercle n'est pas assimilée à la validation d'un candidat complet ; aucun seuil n'est déplacé pour compenser un écart.

## Les quatre villes : avant/après

| Ville / construction | Heure avant → après | Azimut solaire avant → après | Écart géométrique avant → après (km) | État et candidats |
|---|---|---|---|---|
| Saint-Valentin — détection nationale S7 miroir | 12:28:10 → **12:26:58** | 190,999968° → **190,499967°**, référence nationale 1066 | **11,940128 → 14,757176**, distance à la ligne | Détection vraie ; scénario Stylet Initial « Sélectionné » avant/après ; 1 candidat |
| Bordeaux — Lumière Initiale | 11:35:51 → **11:37:03** | 166,678258° → **167,230619°**, observation historique à Dieppe | **5,834195 → 6,344703**, distance au cercle d'ombre | Stylet « Valide » avant/après ; 2 candidats géométriques ; état de solution enregistré inchangé |
| Châlus — Base Cadran, cercle PM | 12:24:09 → **12:22:57** | 190,002615° → **189,401260°**, Carnac le 19/07/933 | **11,439175 → 4,468854**, distance au cercle horaire | 1 candidat avant/après ; état de solution enregistré inchangé |
| Fontevraud — Base Cadran, `-2`, cercle AM | **12:00:00 → 12:00:00** | **177,788261° → 177,788261°**, Carnac le 19/07/933 | **51,680991 → 51,680991**, distance au cercle horaire | 0 candidat avant/après ; état de solution enregistré inchangé |

### Saint-Valentin

La note détectée reste B/S7 et la branche reste miroir astronomique. L'heure automatique devient 12:26:58 ; elle n'est pas remplacée par la PM temporelle des bases. Dans le scénario Stylet Initial sauvegardé « Saint Valentin », le diagnostic entier intersection planète–étoile → ligne nationale passe de **14 à 17 km** ; l'algorithme reste « Sélectionné » selon ses critères inchangés. La distance de Saint-Valentin au centre du candidat passe de **10,082420 à 11,445074 km**.

### Bordeaux

Les paramètres restent `sourceHeure = "Stylet"` et `choixHeure = "Symétrique"`. Lumière Initiale utilise l'autre branche astronomique nationale, ici l'AM S7 à 11:37:03, à la date historique du scénario et au lieu Dieppe. Son code ne reçoit pas la symétrie temporelle propre aux bases. Le rayon d'ombre passe de **296,446726 à 295,930579 km** ; la distance de Bordeaux au candidat le plus proche passe de **108,323919 à 105,430591 km**. Cette dernière mesure reste distincte de l'écart au cercle d'ombre.

### Châlus et Fontevraud : paramètres réels

Le stylet Saint-Valentin est toujours détecté S7 miroir, maintenant à 12:26:58. Les deux bases conservent Standard et la période PM, mais leurs notes finales diffèrent :

- **Châlus** conserve `=` et le cercle PM : note finale B, heure PM Base 12:22:57, angle horaire **9,401260°** (contre 10,002615° à 169°). Le rayon de distance passe de **158,649443 à 158,418986 km**.
- **Fontevraud** conserve **`-2`** et le cercle AM : B −2 donne **G**, dont l'AM et la PM Base valent 12:00:00. Son angle **2,211739°**, son rayon de distance **131,827335 km**, sa géométrie et l'absence de candidat sont identiques.

Les deux projets restent marqués comme solutions dans leurs JSON, sans réévaluation de ces marques. Ce statut sauvegardé ne signifie pas qu'un candidat géométrique est produit, notamment pour Fontevraud.

## Essai théorique S7 PM à Fontevraud — séparé du scénario

Un objet CercleHoraire indépendant a été construit en mémoire à l'heure B/S7 PM, avec le même stylet, la même date, Carnac et le même **côté AM** du cercle que Fontevraud. Cette expérience théorique utilise `=` au lieu de `-2` ; elle n'est pas appliquée au scénario enregistré.

| Essai théorique Fontevraud | 169° | 169,5° |
|---|---|---|
| Note de calcul | B | B |
| Heure PM Base | 12:24:09 | 12:22:57 |
| Azimut solaire historique | 190,002615° | 189,401260° |
| Angle horaire | 10,002615° | 9,401260° |
| Écart de Fontevraud au cercle théorique | **26,676618 km** | **21,741340 km** |

L'écart réel du scénario Fontevraud `-2` reste **51,680991 km**. Aucun candidat complet n'est calculé ou annoncé pour cet essai isolé ; aucune partition, distance ou sélection n'est réoptimisée.

## Coordonnées des candidats

Centres en mètres Lambert-93, arrondis au millimètre dans le tableau.

| Construction | Avant, 169° | Après, 169,5° |
|---|---|---|
| Stylet Initial — Saint-Valentin | (617303.595 ; 6641449.016) | (616415.676 ; 6639750.647) |
| Lumière Initiale — Bordeaux | (513705.737 ; 6372567.619)<br>(713841.753 ; 6929454.992) | (511198.331 ; 6374019.673)<br>(716351.124 ; 6928000.181) |
| Base — Châlus | (555798.305 ; 6503124.557) | (548079.691 ; 6508194.248) |
| Base — Fontevraud | Aucun | Aucun |

## Tests et vérification du périmètre

- Tests ciblés : référentiel, S7/symétrie, Base Cadran et contrat du lot 2 — **253 réussites**.
- Suite complète : `python -m pytest -q --tb=short` — **801 réussites en 231,61 s** sur l'état final.
- Les assertions dépendant de S7 sont adaptées aux valeurs DE406. Le nouveau centre de Châlus est également vérifié par les intersections des cercles, projections sur les partitions admissibles et milieux, avant comparaison à la référence numérique.
- Les sept autres directions calculées sont vérifiées identiques à la calibration précédente reconstituée depuis son archive. Le premier historique est conservé et la définition 169° archivée est comparée à l'état de départ.
- **59 fichiers protégés sont inchangés, dont tous les fichiers de `src`**, la configuration nationale à 125,371°, les données géographiques, cartes, projets et fixtures.

Les écarts plus grands à la ligne de Saint-Valentin et au cercle de Bordeaux sont rapportés sans ajustement compensatoire. La dépendance historique Lampouy reste intacte ; aucune autre référence, formule, substitution, calendrier, seuil ou orientation n'est modifié. Les modifications locales préexistantes de `config/simulateurAlgo.ini`, `projets/Lumiere_Solutions.json` et `projets/StyletInitial_solutions.json` sont préservées et exclues du commit. Aucun projet, cache ni corpus 650/520 n'est modifié par la mission ; aucune intervention sur `main`.

## Diff exact du référentiel (sans lignes de contexte)

```diff
diff --git a/data/sentinelles_reference_v1.json b/data/sentinelles_reference_v1.json
index 488f3bd..54db742 100644
--- a/data/sentinelles_reference_v1.json
+++ b/data/sentinelles_reference_v1.json
@@ -19,0 +20,14 @@
+    },
+    {
+      "date_reevaluation": "2026-10-29",
+      "identifiant": "S7",
+      "motif": "Ajustement expérimental de 169° à 169,5° ; relevé physique historique 170° inchangé.",
+      "calibration_precedente": {
+        "identifiant": "S7", "note": "B", "nature": "sentinelle",
+        "azimut_physique_initial": 170.0,
+        "autorite": "azimut", "valeur_reference": 169.0,
+        "origine": "Réévaluation de la lecture physique des Sentinelles : 169° solaire de travail ; relevé historique 170° conservé en provenance. Heure cible 11:35:49 indicative, heure exacte déterminée par DE406.",
+        "statut": "reevaluee_physiquement",
+        "temoins": {"azimut_direct": 169.0, "heure_directe": "11:35:51", "azimut_miroir": 191.0, "heure_miroir": "12:28:10"}
+      },
+      "calcul_precedent_de406": {"azimut_direct": 169.0000183724259, "secondes_directes_tml": 41751.13010191123, "azimut_miroir": 190.99996750271725, "secondes_miroir_tml": 44890.1531078736}
@@ -74,2 +88,2 @@
-      "autorite": "azimut", "valeur_reference": 169.0,
-      "origine": "Réévaluation de la lecture physique des Sentinelles : 169° solaire de travail ; relevé historique 170° conservé en provenance. Heure cible 11:35:49 indicative, heure exacte déterminée par DE406.",
+      "autorite": "azimut", "valeur_reference": 169.5,
+      "origine": "Ajustement expérimental de la valeur de travail de 169° à 169,5° solaire. Relevé physique historique 170° et calibration 169° conservés en provenance ; heures calculées par DE406, sans heure imposée.",
@@ -77 +91 @@
-      "temoins": {"azimut_direct": 169.0, "heure_directe": "11:35:51", "azimut_miroir": 191.0, "heure_miroir": "12:28:10"}
+      "temoins": {"azimut_direct": 169.5, "heure_directe": "11:37:03", "azimut_miroir": 190.5, "heure_miroir": "12:26:58"}
```
