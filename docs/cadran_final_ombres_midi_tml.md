# Cadran Final — Ombres centrées sur midi moyen local à Bourges

Comparaison à `b5f352444fe5290fa73f122842a272d11c18bd94` (dernier état de `dev`, incluant la mise à jour utilisateur des scénarios). Les projets et fixtures sont chargés en mémoire, sans sauvegarde ni modification des caches.

## Règle et contexte astronomique

L'axe image `StyletFinal.azimutMidi`, de la base vers Bourges, reste inchangé. Les lignes d'ombre nationales utilisent désormais :

```text
delta = azimut_national(h) − azimut_national(12:00:00 TML)
Endroit : orientation_image = azimutMidiStylet + delta
Envers  : orientation_image = azimutMidiStylet − delta
```

L'inversion concerne l'écart complet. Le Soleil à 180° ne constitue plus une origine géométrique des ombres. À 12:00:00, delta vaut exactement zéro dans les deux sens et la ligne passe par Bourges.

Pour les huit notes nationales, le midi et les directions proviennent du **même moteur et du même contexte du référentiel : Carnac, 15/08/1066 julien, TML et JD UT1, Skyfield/DE406**. L'azimut solaire de midi TML est **179,150469562301°**. La date du segment historique et son lieu d'observation ne sont plus utilisés pour ce centrage.

Les heures directes/miroirs, leurs branches et leurs secondes fractionnaires sont conservées. S3 et S4 directes restent PM. Aucune symétrie temporelle des heures n'est ajoutée à LumiereFinal ni aux ombres nationales. La calibration S7 reste à 169,5° et le cadran national à 125,371°.

Les références internes sont privées : `_azimutMidiReference`, `_dateMidiReferenceUT1` et, si nécessaire, `_azimutMidiLampouy`. Le champ public/IHM `azimutMidiLocale` est retiré. Le CSV perd uniquement la ligne « Az Midi local » ; Type calendrier, Lettre, Choix, Heure locale et Sens Carte restent présents. La représentation Base–Bourges, les couleurs, niveaux et étiquettes imprimables sont conservés.

## Lampouy : exception historique conservée

Lampouy reste distinct des huit références nationales. Ses heures historiques **10:09:00 / 13:51:00** et ses azimuts angulaires **138,5° / 221,5°** sont conservés. Le midi de comparaison est désormais calculé dans leur contexte historique **Carnac, 20/08/1152**, avec les coordonnées employées par la compatibilité Lampouy. Il vaut **179,755534904461°**. La date historique du segment n'intervient pas dans ce midi.

Les écarts Lampouy sont donc −41,255535° et +41,744465° en Endroit ; Envers inverse ces deux écarts dans leur ensemble. Son nombre de lignes et ses deux candidats horaires restent inchangés.

Le contrôle de contexte confirme une limite préexistante : les heures Lampouy sont arrondies à la minute et sa PM suit une convention historique. Le Soleil calculé à ces heures, dans ce contexte, donne environ 138,595244° et 220,988715°, contre les azimuts angulaires hérités 138,5° et 221,5°. Ces écarts ne sont pas compensés : la mission conserve ce traitement particulier plutôt que recalibrer Lampouy ou changer ses heures. Cette exception angulaire et le midi qui lui est propre restent explicitement séparés du référentiel national.

## Vérification prioritaire — Roncevaux 778 / Lac Trémelin

Fixture `tests/fixtures/cadran_final_roncevaux_lac_tremelin_reference.json`, inchangée. Date du scénario 15/08/778, date de segment 25/07/778. Les lumières continuent à utiliser leur contexte historique ; seules les ombres sont recentrées dans le contexte national de 1066.

| Grandeur | Avant | Après |
|---|---|---|
| Axe image Base–Bourges | 13,559937904° | identique |
| Hauteur du stylet | 250,083163604 km | identique |
| Heure de lumière S3 directe PM | 15:59:05 ; 57544,78557490508 s | identique |
| Azimut de lumière | 263,223515317° | identique |
| Hauteur solaire de lumière | 35,570403027° | identique |
| Rayon du cercle de lumière | 349,693965525 km | identique |
| Midi utilisé pour centrer les ombres | Carnac, 25/07/778 ; 177,911706506° | Carnac, 15/08/1066 ; 179,150469562° |
| Écart de la ligne 12:00 TML à l'axe du stylet | +1,238763056° | **0°** |
| Distance Bourges → ligne de 12:00 TML | 5,640871 km | **≈ 1,53 × 10⁻¹¹ km** |
| Écart de la ligne C directe, Endroit | −49,093559223° | −50,332322279° |
| Écart de la ligne C miroir, Endroit | +53,270155934° | +52,031392878° |
| Candidats finaux | 1 | 1 |
| Centre Lambert-93 du candidat (m) | (326990,525831 ; 6788874,562568) | (319918,185155 ; 6787297,401259) |

Le nouveau centre n'est pas seulement recopié dans une assertion : le test vérifie les intersections cercle/lumière et cercle/heure, le troisième point d'intersection et le barycentre, avec le rayon de validation inchangé de 20 km.

## Impacts sur les scénarios de référence

Les **65 scénarios** de `projets/CadranFinal_Solutions.json` et la fixture prioritaire donnent **66 observations** avant/après. Les axes et hauteurs de stylet, heures exactes et positions solaires des lumières, rayons de lumière, notes et heures exactes des ombres, ainsi que les états de sélection sauvegardés sont identiques pour chaque observation. La ligne de midi passe par Bourges dans tous les cas, avec un résidu numérique maximal inférieur à **3,5 × 10⁻¹¹ km**.

Sur les 65 scénarios du projet, le total passe de **81 à 85 candidats**. Les variations de nombre sont les suivantes ; les centres peuvent aussi évoluer lorsque le nombre reste identique.

| Scénario / date historique | Sens conservé | Candidats avant → après |
|---|---|---|
| Grotte Lombrives / 15/08/778 | Endroit | 1 → 0 |
| Bordeaux / 15/08/778 | Endroit | 0 → 2 |
| Loches / 15/08/778 | Endroit | 1 → 0 |
| Frontiere Sud Bretagne / 30/05/1431 | Envers | 1 → 2 |
| Turin / 12/04/1365 | Envers | 1 → 2 |
| Vézelay / 20/03/1815 | Endroit | 3 → 6 |
| Bâle / 15/06/1066 | Envers | 1 → 0 |
| Crécy / 19/07/933 | Envers | 1 → 2 |
| St Valéry / 19/07/933 | Endroit | 1 → 0 |
| Beaugency / 18/05/1152 | Endroit | 2 → 1 |
| Rouen / 18/05/1152 | Endroit | 6 → 7 |

Ces variations résultent du recentrage et de la réflexion complète des écarts en Envers. Les seuils de 20 km et le repli de quasi-parallélisme à 10 km de CandidatFinal restent inchangés ; aucune correction ne cherche à rétablir une ancienne solution. Les scénarios et leurs marques de sélection ne sont pas enregistrés après ces essais.

## Tests et non-régression

- Tests ciblés : `python -m pytest tests/test_algorithme_cadran_final.py tests/test_algorithme_cadran_final_golden.py tests/test_cadrans_sentinelles_lot3.py tests/test_lambert_native_characterisation.py tests/test_cadran_final_midi_local.py -q --tb=short` — **158 réussites**.
- Suite complète : `python -m pytest -q --tb=short` — **809 réussites en 236,58 s** sur le comportement final.
- Huit nouveaux cas couvrent les deux sens à midi, la réflexion complète, l'identité des heures exactes, l'indépendance vis-à-vis du contexte historique, Lampouy dans les deux sens, le parsing réel de l'IHM et la vérification géométrique du candidat 778.
- Les corps AST de toutes les classes du fichier Final autres que LigneHoraireFinal sont identiques, notamment StyletFinal, StyletLumiere, LumiereFinal et CandidatFinal. Les **58 fichiers protégés** (autres sources, référentiel S7, données, cartes, projets et fixtures) sont inchangés.
- Trois attentes de l'ancien test Base Cadran étaient déjà obsolètes après le commit utilisateur `b5f3524` modifiant ses scénarios (Fontevraud, Reims, Saint-Cyr–Coëtquidan). Elles sont alignées sur les résultats de cet état de départ, avec conservation des vérifications par intersections/projections et milieux. Le code et les paramètres Base ne sont pas modifiés par cette mission.

Le champ « Az Midi local » est absent du CSV et du descripteur obtenu par le parseur IHM. Les champs de choix existants restent présents ; aucun bouton n'est ajouté. Aucun recalcul global avec sauvegarde ni invalidation de cache. La configuration locale `config/simulateurAlgo.ini`, modifiée avant la mission, est préservée et exclue du commit. Les approximations historiques de Lampouy restent documentées ; aucune autre anomalie n'est masquée par un ajustement de seuil.

## Diff de production (sans contexte)

```diff
diff --git a/config/AlgorithmeCadranFinal.csv b/config/AlgorithmeCadranFinal.csv
index 4c133fa..62dd505 100644
--- a/config/AlgorithmeCadranFinal.csv
+++ b/config/AlgorithmeCadranFinal.csv
@@ -68 +67,0 @@ Ligne Horaire,Global,3,field,heure,right,Heure Locale,,1,data,std,ombre,heureLoc
-Ligne Horaire, Global,4,field,angle,right,Az Midi local,,1,data,std,ombre,azimutMidiLocale
diff --git a/src/AlgorithmeCadranFinal.py b/src/AlgorithmeCadranFinal.py
index 0debe4b..f65bb75 100644
--- a/src/AlgorithmeCadranFinal.py
+++ b/src/AlgorithmeCadranFinal.py
@@ -475 +475,3 @@ class LigneHoraireFinal(ModuleAlgo):
-        self.azimutMidiLocale = None
+        self._azimutMidiReference = None
+        self._dateMidiReferenceUT1 = None
+        self._azimutMidiLampouy = None
@@ -482 +483,0 @@ class LigneHoraireFinal(ModuleAlgo):
-        self.dateMidiUT1 = None
@@ -507,7 +508,10 @@ class LigneHoraireFinal(ModuleAlgo):
-        # On calcule l'écart d'azimut entre Midi solaire et Midi locale à Carnac
-        coordObs = villes_dict["Carnac"].getCoordonneesGPS()
-        (lat, lon) = coordObs
-        # On calcule l'heure de Midi solaire et l'écart d'azimut
-        contexte = ContexteObservation("Carnac", lat, lon, self.dateSegmentDataset)
-        self.dateMidiUT1 = contexte.versUT1(HeureMoyenneLocale(12 * 3600))
-        _, self.azimutMidiLocale = positionSoleil(coordObs, self.dateMidiUT1)
+        # Même contexte que les directions nationales : Carnac, 15/08/1066 julien.
+        midi = self.sentinelleLumiere.referentiel.moteur.directionPourHeure(HeureMoyenneLocale(12 * 3600))
+        self._azimutMidiReference = midi.azimut
+        self._dateMidiReferenceUT1 = midi.jd_ut1
+        self._azimutMidiLampouy = None
+        if self.dateDataset == "18/05/1152":
+            # Lampouy garde ses azimuts/heures historiques et son propre contexte.
+            contexte = ContexteObservation("Carnac", *villes_dict["Carnac"].getCoordonneesGPS(), "20/08/1152")
+            _, self._azimutMidiLampouy = positionSoleil(
+                contexte.coordonnees, contexte.versUT1(HeureMoyenneLocale(12 * 3600)))
@@ -528,2 +531,0 @@ class LigneHoraireFinal(ModuleAlgo):
-            deltaAzimutMidiLocale = 180 - self.azimutMidiLocale
-            deltaAzimutMidiLocale = deltaAzimutMidiLocale if self.sensCarte == "Endroit" else -deltaAzimutMidiLocale
@@ -543 +545,4 @@ class LigneHoraireFinal(ModuleAlgo):
-                ecart = azimut - 180 + deltaAzimutMidiLocale
+                midi_reference = self._azimutMidiLampouy if note == "L" else self._azimutMidiReference
+                ecart = azimut - midi_reference
+                if self.sensCarte == "Envers":
+                    ecart = -ecart
```
