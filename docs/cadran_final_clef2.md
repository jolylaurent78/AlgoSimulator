# Cadran Final — Deuxième clé musicale

Extension sur `dev`, à partir de `da636037e16049c1760742d5fc2055df68450e86`. Seul `src/AlgorithmeCadranFinal.py` est modifié en production ; la fonction partagée `decalageGamme()` et les autres algorithmes restent identiques.

## Règle commune aux trois modules

`noteAvecSubstitutionCadranFinal()` est appelée par StyletFinal, LumiereFinal et LigneHoraireFinal. Pour `=`, `+2`, `-2` et **`Clef`**, elle reprend exactement les indices historiques de `decalageGamme()` : 0, 2, 1 et 3. Aucune valeur persistante n'est renommée en `Clef 1`.

Pour **`Clef 2`**, `_noteSourceClef2()` recherche la première correspondance définie dans l'ordre **note initiale, +2, −2**. Les seules transformations nouvellement définies sont **Do → Sol** et **Fa → Sol**. Si aucune de ces notes n'est rencontrée, la note initiale est conservée selon le principe de repli historique.

| Note de départ | = | +2 | −2 | Clef historique | Clef 2 | Source de Clef 2 |
|---|---|---|---|---|---|---|
| Do / C | C | E | A | F | G | C initiale |
| Ré / D | D | F | B | C | G | F en +2 |
| Mi / E | E | G | C | F | G | C en −2 |
| Fa / F | F | A | D | C | G | F initiale |
| Sol / G | G | B | E | G | G (*) | aucune correspondance définie |
| La / A | A | C | F | F | G | C en +2, prioritaire sur F en −2 |
| Si / B | B | D | G | B | B (*) | aucune correspondance définie |

(*) Il s'agit d'une **conservation par défaut**, sans nouvelle correspondance musicale attribuée à Sol ou Si. La répartition éventuelle **Sol → Do / Sol → Fa** entre les clés reste à définir. L'ancienne `Clef` ne substituant pas directement Sol, son résultat G est strictement conservé. Aucune règle nouvelle pour Sol n'est inventée et sa présence ne remplace pas une correspondance Do/Fa explicitement définie plus loin dans la recherche.

Ré produit donc Do avec `Clef` et Sol avec `Clef 2`. Les sorties La/Mi sont obtenues par le chemin vers Do ou Fa, sans nouvelle transformation directe de ces notes.

## Choix dans l'interface

Les trois champs existants exposent désormais :

- Stylet / `P2M2` : `=`, `+2`, `-2`, `Clef`, `Clef 2`.
- Lumière et Ombre / `choixHeure` : mêmes choix, puis Joker `11:00` ; Lampouy reste disponible aux dates prévues.

Aucun champ ni bouton distinct n'est créé. Le CSV existant interroge les méthodes `getValeursP2M2()` / `getValeursChoixHeure()`, donc **aucune modification de config/AlgorithmeCadranFinal.csv n'est nécessaire**. Le test Tk construit réellement les trois groupes de choix, sélectionne `Clef 2`, puis revient à `Clef`, et vérifie les callbacks et états des cases.

Les calendriers, heures astronomiques AM/PM, Joker, compatibilité Lampouy, origine des ombres à midi TML et réflexion Endroit/Envers restent inchangés. Aucun changement de barycentre, seuil ou formule géométrique. Seule la note issue de la nouvelle option peut modifier une hauteur ou une heure, comme attendu.

## Contrôle Carnac — 19 juillet 933

Le projet **local** fourni au démarrage contient bien une lettre de déclinaison **F** et la date de segment **18/05/933**. Les essais conservent cette date et tous les autres paramètres ; aucune comparaison des dates du 16, 18 ou 21 mai n'est menée.

Réglages locaux enregistrés : les trois calendriers sont Déclinaison ; stylet `=`, lumière `+2`, ombre `+2`. Ces réglages restent intacts dans le JSON : notes F/A/A et heures de lumière/ombre à 11:42:00 avant **et** après ajout de l'option.

Pour le contrôle, les choix des trois modules sont changés uniquement dans les objets en mémoire, sans sauvegarde :

| Essai en mémoire | Note du stylet | Hauteur du stylet | Note lumière / heure AM | Note ombre / heure AM | Date du segment |
|---|---|---|---|---|---|
| Clef dans les trois modules | C | 536,023314 km | C / 09:43:00 | C / 09:43:00 | 18/05/933 |
| Clef 2 dans les trois modules | **G** | **715,505282 km** | **G / 12:00:00** | **G / 12:00:00** | **18/05/933** |

Le test vérifie également que la ligne G à 12:00:00 conserve un écart nul à l'axe Base–Bourges. Les tests génériques couvrent AM et PM : les lumières finales continuent à prendre les vraies heures nationales, y compris pour Sol PM ; aucune symétrie temporelle des bases n'est introduite ici.

Les dates et réglages diffèrent éventuellement de la version publiée du projet car `data/dataset.csv` et `projets/CadranFinal_Solutions.json` étaient **déjà modifiés localement** avant la mission. Ces fichiers, ainsi que la configuration locale, sont préservés et **exclus du commit**. Les tests conservent la date qu'ils chargent et n'imposent pas une nouvelle date au projet.

## Rétrocompatibilité mesurée

Les **54 scénarios locaux** ont été chargés et calculés en mémoire avant et après l'extension. **14 scénarios contiennent Clef, pour 16 usages répartis entre les trois modules.** Les observations sont identiques pour tous les scénarios : notes, secondes exactes, heures affichées, hauteurs, azimuts, rayons, angles des ombres, candidats et états de sélection.

Le même contrôle a été effectué séparément sur les **65 scénarios du projet publié** à la révision de départ, extraits vers un fichier temporaire : résultats également strictement identiques avant/après, sans modifier le projet local.

Ce contrôle n'introduit pas de nouvelle valeur dans les projets : les scénarios existants continuent à utiliser leur valeur technique `Clef`. Une vérification permanente confronte chaque occurrence de `Clef` dans le JSON chargé à l'ancien calcul `decalageGamme(note)[3]` et aux heures nationales correspondantes. Les sept notes et les quatre anciennes substitutions sont aussi confrontées à la table historique.

## Tests et périmètre

- Tests ciblés : `python -m pytest tests/test_cadran_final_clef2.py tests/test_algorithme_cadran_final.py tests/test_algorithme_cadran_final_golden.py tests/test_cadrans_sentinelles_lot3.py tests/test_cadran_final_midi_local.py -q --tb=short` — **165 réussites**.
- Suite complète : `python -m pytest -q --tb=short` — **862 réussites en 249,00 s**.
- Une première passe complète a donné 861 réussites et un incident de lecture de `init.tcl` à l'initialisation de Tk dans un test de l'IHM Segment, hors du code modifié. Le fichier est présent et la suite concernée a ensuite réussi : **36 tests**. Aucun test n'est exclu et aucun contournement de Tcl/Tk n'est ajouté ; la reprise complète réussit avec les 862 tests.
- 53 nouveaux cas couvrent les 35 couples note/substitution, les sept priorités de recherche, les trois modules dans les deux calendriers et périodes, les contrôles Tk, la compatibilité des JSON et Carnac.
- Les **59 fichiers protégés** sont identiques à leur état initial : autres algorithmes, fonction musicale globale, référentiel/S7, données, CSV, cartes, projets et fixtures. Les classes du fichier Final autres que les trois consommateurs sont vérifiées identiques par AST.

Les correspondances manquantes pour Sol restent ouvertes, sans changement de l'ancienne clé. Aucun cache ni projet n'est migré, invalidé ou sauvegardé. Les modifications locales de `config/simulateurAlgo.ini`, `data/dataset.csv` et `projets/CadranFinal_Solutions.json` sont conservées hors livraison ; aucune intervention sur `main`.

## Diff de production, sans lignes de contexte

```diff
diff --git a/src/AlgorithmeCadranFinal.py b/src/AlgorithmeCadranFinal.py
index f65bb75..7ff416c 100644
--- a/src/AlgorithmeCadranFinal.py
+++ b/src/AlgorithmeCadranFinal.py
@@ -25,0 +26,14 @@ from src.layerManager import LayerManager
+def _noteSourceClef2(notes):
+    """Première note définie pour Clef 2 : initiale, puis +2, puis -2."""
+    return next((note for note in (notes[0], notes[2], notes[1]) if note in ("C", "F")), None)
+
+
+def noteAvecSubstitutionCadranFinal(note, substitution):
+    """Conserver les choix historiques ; Clef 2 envoie Do ou Fa vers Sol."""
+    notes = decalageGamme(note)
+    if substitution == "Clef 2":
+        # Sol et les autres cas sans correspondance définie gardent leur note.
+        return "G" if _noteSourceClef2(notes) is not None else note
+    return notes[{"=": 0, "+2": 2, "-2": 1, "Clef": 3}[substitution]]
+
+
@@ -98 +112 @@ class StyletFinal(ModuleAlgo):
-        return "=", "+2", "-2", "Clef"
+        return "=", "+2", "-2", "Clef", "Clef 2"
@@ -156,3 +170 @@ class StyletFinal(ModuleAlgo):
-        tabDec = {"=": 0, "+2": 2, "-2": 1, "Clef": 3}
-        listeNotes = decalageGamme(self.lettreChoix)  # On décale sans susbtition Fa/Sol
-        self.lettre = listeNotes[tabDec[self.P2M2]]
+        self.lettre = noteAvecSubstitutionCadranFinal(self.lettreChoix, self.P2M2)
@@ -266 +278 @@ class LumiereFinal(ModuleAlgo):
-        list = ["=", "+2", "-2", "Clef", "11:00"]
+        list = ["=", "+2", "-2", "Clef", "Clef 2", "11:00"]
@@ -332,4 +344,2 @@ class LumiereFinal(ModuleAlgo):
-        elif self.choixHeure in ("=", "+2", "-2", "Clef"):
-            tabDec = {"=": 0, "+2": 2, "-2": 1, "Clef": 3}
-            listeNotes = decalageGamme(self.lettreChoix)  # On décale sans susbtition Fa/Sol
-            choixNote = listeNotes[tabDec[self.choixHeure]]
+        elif self.choixHeure in ("=", "+2", "-2", "Clef", "Clef 2"):
+            choixNote = noteAvecSubstitutionCadranFinal(self.lettreChoix, self.choixHeure)
@@ -431 +441 @@ class LigneHoraireFinal(ModuleAlgo):
-        list = ["=", "+2", "-2", "Clef", "11:00"]
+        list = ["=", "+2", "-2", "Clef", "Clef 2", "11:00"]
@@ -496,4 +506,2 @@ class LigneHoraireFinal(ModuleAlgo):
-        elif self.choixHeure in ("=", "+2", "-2", "Clef"):
-            tabDec = {"=": 0, "+2": 2, "-2": 1, "Clef": 3}
-            listeNotes = decalageGamme(self.lettreChoix)  # On décale sans susbtition Fa/Sol
-            self.noteHoraire = listeNotes[tabDec[self.choixHeure]]
+        elif self.choixHeure in ("=", "+2", "-2", "Clef", "Clef 2"):
+            self.noteHoraire = noteAvecSubstitutionCadranFinal(self.lettreChoix, self.choixHeure)
```
