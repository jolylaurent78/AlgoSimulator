# Audit LAMBERT-NATIVE — état initial

Date : 10 septembre 2026.  Périmètre : lecture de `src/` et de `tests/`, sans
exécution ni modification de code métier. Les numéros de ligne ci-dessous sont
ceux de l'état audité.

## Conclusion exécutive

Le projet possède déjà une séparation partielle, mais réelle, entre donnée
native et représentation carte : `PointGraphique`, les cercles, les lignes
entre villes, les lignes à azimut et les segments possèdent un ancrage Lambert.
Les pixels absolus sont recalculables lorsque la carte est changée
(`interface_tk.py:1541-1553`, `layerManager.py:66-68`).

Le point de fragilité n'est donc pas « le pixel partout », mais la classe de
base `LigneGraphique` : son contrat propre est exclusivement
`pointReference` + `vecteur` en pixels, et sa géométrie est déterminée après
découpage par l'image. Ses sous-classes Lambert réutilisent cette mécanique
comme cache et comme repère de calcul. Ce dernier choix affecte des résultats
métier (partitions, candidats, Sentinelle, angle du segment), pas seulement le
rendu.

Fait rassurant : aucune instanciation externe de
`LigneGraphique(point_px=..., vecteur_px=...)` n'a été trouvée dans `src/` ou
`tests/`. Les seules sont internes à `affichage_objets.py` : `copie()`
(`1146`) et `orthogonale()` (`1306`). La future migration peut donc isoler le
contrat historique sans devoir d'abord convertir des appelants algorithmiques
directs.

Il ne faut **pas** remplacer les calculs pixels par des calculs Lambert de
manière globale. La calibration est une transformation affine générale
(`carte_config.py:55-63`), et les deux calibrations livrées ont des termes hors
diagonale. Une direction/orthogonalité/angle dans l'image peut donc être
volontairement différent de son analogue Lambert. Les tests déclarent d'ailleurs
explicitement la convention boussole des pixels
(`tests/test_geometrie_critique.py:68-79`).

## Référentiel des repères

| Terme | Sens observé |
|---|---|
| Lambert | EPSG:2154, mètres ; les distances exposées par `PointGraphique.distance` et `SegmentEntreVilles.distanceSegment` sont en km. |
| Pixel image absolu | Coordonnées de l'image source, via `A @ [x_l93,y_l93] + offset`; c'est le repère de `pointReference`, `vecteur`, `Ligne`, `Cercle` et `lignePixelImage`. |
| Pixel affichage | Pixel après pan/zoom fourni à `afficher`; il sert seulement à OpenCV/UI. |
| GPS | `(lat, lon)` destiné aux calculs astronomiques ; le constructeur du point le dérive du Lambert si absent. |

`CarteConfig` conserve la matrice affine et son inverse, puis fournit les
conversions Lambert/pixel et Lambert/GPS. Une carte changeante implique donc
une régénération des caches pixels, sans changer les données Lambert natives.

## Cartographie de `affichage_objets.py`

Notation : **N** = normatif actuel, **D** = cache/dérivé, **A** = affichage/UI.

| Classe | Données géométriques et statut | Lambert / pixel | Dépendances directes | Lecture architecturale |
|---|---|---|---|---|
| `ObjetGraphique` | **A** : nom, style, couche, tags, tooltips, visibilité/sélection; `pointReference` générique | `pointReference` pixel, sans Lambert | `carteConfig.image_size`; `cv2` pour texte | Base de présentation; `pointReference` est son point d'accroche, pas une géométrie universelle. |
| `PointGraphique` | **N** : `x_l93`, `y_l93`; GPS associé | **D** : `pointReference`; GPS dérivé si absent | conversions `carteConfig`; `cv2.circle` | Déjà Lambert-native. |
| `SymboleWiki` | Hérite du point ; **A** : URL, chemin/icône et cache statique d'icône | Lambert hérité, pixel dérivé | `cv2.imread`, alpha blending | Aucun enjeu géométrique nouveau. |
| `Cercle` | **D** : centre/rayon pixels | pixels seulement | aucun | Primitive interne de géométrie image, utilisée comme cache de cercle graphique. |
| `CercleGraphique` | **N** : `pointCentre` (point Lambert) + `rayon_km` | **D** : `cercle` (`Cercle` pixel), `pointReference` | conversions; `cv2.circle` | Déjà Lambert-native pour le stockage. La construction « trois points » est, elle, pixel-first. |
| `ArcOriente` | **N** : centre/rayon hérités + `azimut_depart`, `rotation` | cercle/centre pixel dérivés | `cv2.ellipse`, `cv2.line` | Paramètres angulaires métier; dessin et conventions OpenCV seulement dans `afficher`. |
| `Ligne` | **N** : `pt1`, `pt2`, coefficients A/B/C dans le même repère | par contrat/documentation : pixels absolus | aucun | Primitive générique en apparence, mais utilisée comme géométrie pixel dans tout le projet. |
| `LigneGraphique` | **N actuel** : `pointReference`, `vecteur`, et `distance` facultative | `lignePixelImage` est un cache découpé aux bords | `carteConfig.image_size`; `cv2.line` | Seule classe de la famille qui est intrinsèquement pixel-native. |
| `LigneEntreVilles` | **N** : deux extrémités `x1/y1`, `x2/y2` Lambert | **D** : milieu/vector pixel, ligne découpée | conversion + découpage | Lambert-native; la direction image sert aujourd'hui aussi aux calculs. |
| `LigneAzimut` | **N** : un point Lambert + `azimut_deg` | **D** : point/vector image et ligne découpée | conversion + découpage | Lambert-native de stockage; son vecteur est actuellement construit dans la convention azimut de l'image. |
| `LigneVerticale` | **N ambigu** : point Lambert mémorisé, mais seul `x_l93` est utilisé | **D** : `(px,0)`, `(0,1)` pixels | conversion + découpage | Pas d'appel trouvé. « Verticale » signifie verticale de l'image, non une preuve d'intention Lambert. |
| `LigneHorizontale` | **N ambigu** : point Lambert mémorisé, mais seul `y_l93` est utilisé | **D** : `(0,py)`, `(1,0)` pixels | conversion + découpage | Pas d'appel trouvé. Même réserve que la verticale. |
| `SegmentEntreVilles` | **N** : deux extrémités Lambert et références aux villes | **D** : point/vector/distance pixels | conversion; `cv2.line` hérité | Lambert-native pour les bouts; longueur affichée est pixel, tandis que `distanceSegment` est Lambert/km. Aucun appel trouvé. |

Tous les dessins (`afficher`, `afficherTexte`, icône, arc) et les méthodes de
sélection par clic (`distanceDepuis`) sont à classer **A/UI**. Les appels directs
à `cv2` sont confinés à `affichage_objets.py`; ils ne prescrivent pas le repère
des calculs métier.

### Ce que recalcule vraiment le changement de carte

`recalculerCoordonneesPixelAbsTous()` parcourt les objets des layers. Les
points, cercles et sous-classes de lignes réémettent leurs caches pixels depuis
le Lambert; `LigneGraphique` ne le fait pas. Cela confirme que ses données
pixels sont normatives, alors qu'elles sont dérivées dans les sous-classes.

À noter pour un ticket ultérieur : `CercleGraphique.getCentre()` reconstruit un
nouveau point depuis `pointReference` (`580-582`) au lieu de retourner
`pointCentre`; c'est une dépendance au cache à auditer par test de non-régression,
pas une correction à faire dans ce ticket. `estVisibledansImage()` du cercle
appelle `coordonnéesPixelAbs` avec un accent (`666`), différent de la méthode
définie. Aucun appel de production à cette méthode de cercle n'a été trouvé.

## Méthodes géométriques : repères et classifications

| Classe / méthode | Entrées réelles | Calcul → résultat | Nature / appels métier | Pixel à conserver ? / risque |
|---|---|---|---|---|
| `PointGraphique.coordonneesLambert` | x/y stockés | Lambert → Lambert | conversion d'accès | NON; faible |
| `ObjetGraphique.coordonneesPixelAbs` | `pointReference` | pixel → pixel | cache/conversion; utilisé par UI et algorithmes | OUI comme accès de cache; moyen |
| `recalculerCoordonneesPixelAbs` | Lambert natif (sous-classes) | Lambert → pixel | cache de carte, appelé au changement de carte | OUI; faible si contrat de cache inchangé |
| `PointGraphique.distance` | deux points Lambert | Lambert → km | métier : distances de candidats, stylets | NON; faible |
| `PointGraphique.pixelsVersMetres` | pixel du point et inverse de carte | pixel/mixte → m/pixel | conversion locale alimentant distances/décalages | A VERIFIER; élevé |
| `PointGraphique.distanceDepuis` | curseur et disque pixel | pixel → px | sélection UI | OUI; faible |
| `PointGraphique.distanceLigne` | point + `lignePixelImage`; échelle locale | pixel/mixte → km | pas d'appel externe trouvé | A VERIFIER; moyen |
| `CercleGraphique.depuisTroisPoints` | trois points pixels | pixel puis conversion → cercle Lambert/km | géométrie métier : cercle horaire | PROBABLEMENT; élevé |
| `getCentreEtRayonPixels` | centre Lambert, rayon km | Lambert → pixel | cache/rendu | OUI comme dérivé; faible |
| `CercleGraphique.intersectionLigne` | `Cercle` + ligne pixels | pixel → tuples Lambert | candidat/filtrage | A VERIFIER; élevé |
| `CercleGraphique.intersectionCercle` | deux cercles pixels | pixel → `PointGraphique` Lambert | candidats | A VERIFIER; élevé |
| `Ligne.depuisPointEtVecteur`, `depuisPointEtAzimut` | point/vecteur ou azimut pixels | pixel → `Ligne` pixel | Sentinelle, candidats initiaux | OUI; élevé |
| `Ligne.azimut`, `angleAvec` | vecteurs pixels | pixel → degrés | calibration Sentinelle, axe Midi | OUI / PROBABLEMENT; très élevé |
| `Ligne.distanceAuPoint`, `projection`, `intersection` | points/lignes pixels | pixel → px | Sentinelle et candidats initiaux | OUI / A VERIFIER; élevé |
| `Ligne.intersections_avec_cercle` | ligne/cercle pixels | pixel → px | noyau des intersections graphiques | A VERIFIER; élevé |
| `Ligne.barycentreTriangle`, `longueur` | lignes pixels | pixel → px | candidat initial; pas un simple rendu | PROBABLEMENT; élevé |
| `LigneGraphique.cropToImage` | point/vector pixels, `image_size` | pixel → `lignePixelImage` pixel | visibilité et support de calcul | OUI comme cache; très élevé |
| `pointEtvecteur` | cache pixel | pixel → `(Lambert, azimut image)` | aucun appel externe trouvé | A VERIFIER; moyen |
| `cadreAffichage`, `estVisibledansImage` | cache pixel/segment | pixel → pixel/bool | UI et filtre de candidats | OUI; faible à moyen |
| `LigneGraphique.distanceDepuis` | clic pixel + ligne découpée | pixel → px | sélection UI | OUI; faible |
| `getAzimutCarte` | vecteur pixel | pixel → degrés | segment, partition, Sentinelle | OUI / PROBABLEMENT; très élevé |
| `intersectionLigne`, `intersectionCercle` | caches de lignes/cercles pixels | pixel → Lambert point(s) | CandidatBase/CandidatFinal | A VERIFIER; très élevé |
| `projectionPointGraphique` | point + ligne pixels | pixel → Lambert point | CandidatBase | A VERIFIER; élevé |
| `orthogonale`, `parallele` | vector pixel + point Lambert/pixel | pixel → ligne graphique/azimut | aucun appel externe trouvé | PROBABLEMENT; moyen |
| `pointsEquidistants`, `pointsLateraux` | ligne et point pixels, km convertis localement | pixel/mixte → points Lambert | CercleHoraire/Partition | PROBABLEMENT; très élevé |
| `parallelesDecalees` | point/vector pixels | pixel/mixte → `LigneAzimut` | aucun appel externe trouvé | A VERIFIER; moyen |
| `SegmentEntreVilles.distanceSegment` | extrémités Lambert | Lambert → km | aucun appel externe trouvé | NON; faible |
| `ArcOriente.afficher`, `Cercle/Point/Ligne.afficher` | caches pixels + transformeur écran | pixel image → pixel affichage | rendu | OUI; faible |

`LigneGraphique.orthogonale()` est annotée `LigneEntreVilles`, mais retourne une
`LigneGraphique` pixel (`1306-1311`); la future spécification doit corriger le
contrat documentaire sans changer le comportement dans une migration
structurelle non protégée.

## Appelants significatifs

| Producteur/appelant | Objets / méthode | Finalité et repère effectif |
|---|---|---|
| `data_loader.py:46` et UI | `PointGraphique` | Chargement des villes et interactions; Lambert natif. |
| `affichage_fenetre.py:213-242` | `PointGraphique`, `distanceDepuis` | hit-testing souris, pixel/UI. |
| `Sentinelle.completerAzimutPrecis` (`58-77`) | `Ligne`, `azimut`, `angleAvec` | calibration des azimuts de sentinelles depuis alignements visibles sur carte, pixel. |
| `Sentinelle.surLigneHoraire` (`189-228`) | `Ligne.depuisPointEtAzimut`, `distanceAuPoint` | choix de ligne horaire la plus proche, pixels puis facteur local px→km. |
| `Segment` / `PlaneteChemin` (`AlgorithmeSegment.py:88-95,221-245`) | `LigneEntreVilles`, `getAzimutCarte` | angle et choix de planète; données de sortie golden dépendantes du pixel. |
| `CercleHoraire` (`AlgorithmeBaseCadran.py:166-187`) | `LigneEntreVilles.pointsLateraux`, cercle à trois points | construit le troisième point et le cercle horaire, mixte pixel→Lambert. |
| `Partition` (`298-348`) | axe entre villes, azimut, équidistants, intersections | génération/filtrage des lignes de partition; géométrie image avec résultats Lambert. |
| `CandidatBase` (`527-559`) | intersections cercles/lignes, projection, distances Lambert | sélection de candidats; les intersections/projections sont pixel, le seuil km est Lambert. |
| `StyletFinal.calculer` (`160-163`) | `Ligne(...).azimut` | azimut Midi à partir de deux pixels de ville; golden. |
| `LigneHoraireFinal.calculer` (`453-493`) | `LigneAzimut(point Lambert, azimut)` | produit les lignes horaires persistées dans le module puis habillées par la représentation. |
| `CandidatFinal.construireRepresentationCarte` (`542-595`) | intersections pixel, barycentres/distances Lambert | crée seulement des cercles candidats, mais leur sélection dépend du comportement pixel. |
| `Candidats` initial (`AlgorithmeStyletInitial.py:589-628`) | `Ligne` pixel, intersection, barycentre | algorithme de candidat intrinsèquement pixel dans son état actuel. |

`LigneVerticale`, `LigneHorizontale`, `SegmentEntreVilles`,
`LigneGraphique.pointEtvecteur`, `orthogonale`, `parallele` et
`parallelesDecalees` n'ont aucun appel de production externe. Ils restent des
zones à couvrir avant changement, mais n'augmentent pas le rayon de blast
immédiat.

## Angles et azimuts — analyse spécifique

Les calculs d'azimut astronomique (`positionSoleil`, etc.) sont GPS et ne font
pas partie de la géométrie de carte. Les azimuts ci-dessous sont, eux, dans la
convention image : 0° vers le haut, 90° vers la droite.

1. `Ligne.azimut` et `LigneGraphique.getAzimutCarte` appliquent
   `atan2(dx, -dy)`. Le test unitaire nomme explicitement cette « convention
   boussole des pixels ».
2. `Sentinelle.completerAzimutPrecis` prend Coëtquidan→Golfe-Juan et les villes
   de sentinelles en pixels, puis calcule `180 - angleAvec`. Son résultat est
   persisté comme `AzimutCalibre` et gouverne heures/lignes : c'est le signal
   le plus fort qu'il faut conserver cette géométrie image tant que le métier ne
   confirme pas une autre définition.
3. `Segment`, `PlaneteChemin`, `Partition` et `StyletFinal` consomment les
   azimuts de ligne pour des décisions métier, avec golden tests sur les
   nombres. Ils sont donc à préserver bit à bit dans les premiers tickets.
4. `LigneAzimut` convertit directement un azimut en `(sin(a), -cos(a))` pixel.
   Cela semble volontaire pour tracer ce que l'angle boussole signifie sur la
   carte, mais aucune documentation métier ne tranche la différence avec une
   direction Lambert transformée par la matrice affine : **à valider métier**.
5. `ArcOriente` ne recalcule pas une géométrie métier; ses conversions
   boussole/trigonométrie/OpenCV sont de rendu et doivent rester pixel écran.

## `construireRepresentationCarte()`

Les producteurs sont presque tous déjà Lambert-first :

| Module | Objets produits | Observation |
|---|---|---|
| Base cadran (`CercleHoraire`, `Partition`, `CercleDistance`, `CandidatBase`) | points, `LigneEntreVilles`, `LigneAzimut`, cercles | Aucune `LigneGraphique` brute; certains résultats préparatoires viennent néanmoins de calculs pixels. |
| Cadran final (`StyletFinal`, `LumiereFinal`, `LigneHoraireFinal`, `CandidatFinal`) | points, lignes entre villes/azimut, cercles | Aucun brut pixel. Les intersections dans `CandidatFinal` gardent le comportement image actuel. |
| Stylet initial et lumière/stylet initial | points, `LigneAzimut`, `ArcOriente`, cercles | Aucun brut pixel produit par les méthodes de représentation. Le calcul de candidats juste en amont est pixel. |
| Segment / Sentinelle | points, lignes entre villes/azimut, arcs | Aucun brut pixel en sortie. |

### Focus `LigneHoraireFinal`

`calculer()` crée `LigneAzimut(self.pointBase, azimutAM/PM)` à partir d'un point
Lambert et des azimuts calibrés (`456-493`).
`construireRepresentationCarte()` ne crée aucune nouvelle géométrie : elle
renomme, colore, étiquette et retourne exactement ces lignes (`499-510`). La
passerelle future avec AssembleurTriangles peut donc s'appuyer sur le couple
déjà disponible **point de base Lambert + azimut**, en conservant explicitement
la sémantique actuelle « azimut carte/image » jusqu'à validation métier.

## Tests existants et lacunes

Couverture réellement utile :

- `tests/test_geometrie_critique.py` teste `Ligne` (longueur, distance,
  projection, intersections, tolérance, azimut pixel), `Cercle`,
  intersections cercle/ligne et cercle/cercle, et l'inversibilité affine.
- `tests/test_sentinelle.py` teste la calibration des azimuts et le choix de
  ligne horaire, mais avec doubles de `Ligne`/points.
- Les tests de `AlgorithmeBaseCadran`, `AlgorithmeCadranFinal`,
  `AlgorithmeSegment`, `AlgorithmeStyletInitial` et
  `AlgorithmeLumiereStyletInitial` couvrent les règles de modules
  principalement avec géométrie fictive.
- Les fichiers `*_golden.py` de ces familles ancrent plusieurs sorties réelles :
  distances, azimuts et angles, mais pas des snapshots complets de géométrie ou
  de rendu.
- `test_map_data_config.py` couvre chargement ville et transformées de carte;
  `test_layer_manager.py` couvre le parcours de recalcul, pas la géométrie
  réelle de chaque sous-classe.

Lacunes dangereuses avant toute migration : aucune couverture directe des
constructeurs/recalculs/copies de `LigneGraphique` et de ses sous-classes;
aucun golden de `cropToImage`, `intersectionLigne`, `intersectionCercle`,
`projectionPointGraphique`, `pointsEquidistants`, `pointsLateraux`,
`parallelesDecalees`, `distanceLigne`, `distanceSegment`, ou `ArcOriente`;
aucun test de changement de carte qui compare les objets natifs inchangés et
les caches redérivés; aucun golden visuel. Les tests de représentation vérifient
souvent des objets fictifs ou le nombre d'objets, pas les coordonnées produites.

## Registre de risques

| Risque | Impact | Garde-fou requis |
|---|---|---|
| Confondre stockage Lambert et repère de calcul | changement silencieux de candidats, partitions, Sentinelle et angles | contrat de repère explicite par méthode, golden numérique avant migration |
| Remplacer direction image par direction Lambert | différence d'angle/orthogonalité sous calibration affine | validation métier + golden multi-cartes |
| Modifier le crop ou l'absence de `lignePixelImage` | intersections et visibilité changent, y compris hors image | golden de segments visibles/hors carte et cas tangents |
| Changer l'échelle locale px→m | seuils 20 km et positions équidistantes changent | jeux de référence autour de plusieurs villes/cartes |
| Traiter `LigneVerticale/Horizontale` comme Lambert | changement de sémantique non couvert | décision explicite ou conserver pixel-only |
| Faire une migration sans cache compatible | changement de carte ou UI de sélection se casse | test de régénération et maintien de `pointReference`/`lignePixelImage` dérivés |

## Découpage proposé des futurs tickets

### LAMBERT-NATIVE-002 — contrats et tests de non-régression

Sans changer de résultat, documenter/typer les repères dans les API existantes
et ajouter des tests de caractérisation : conversions, changement de carte,
crop, intersections/projections/décalages, angles Sentinelle/Segment et
sorties de `LigneHoraireFinal`. C'est un ticket préparatoire à risque faible,
mais les tests golden sont indispensables.

### LAMBERT-NATIVE-003 — stockage explicite des sous-classes déjà natives

Rendre explicite, sans supprimer les attributs pixels, que les données
Lambert de `PointGraphique`, `CercleGraphique`, `LigneEntreVilles`,
`LigneAzimut` et `SegmentEntreVilles` sont normatives et que
`pointReference`, `vecteur`, `distance` pixel et `lignePixelImage` sont des
caches redérivables. Préserver les signatures et les nombres. Risque modéré,
à protéger par les golden de -002.

### LAMBERT-NATIVE-004 — isoler `LigneGraphique` pixel-native

Conserver l'implémentation historique ou une façade de compatibilité pour
`LigneGraphique(point_px, vecteur_px)`, puis séparer conceptuellement le cache
pixel des sous-classes natives. Ne pas convertir `Ligne`, les orthogonales ou
les angles. Ticket structurel, risque modéré, sans appelant externe brut connu.

### LAMBERT-NATIVE-005 — passerelle `LigneHoraireFinal` / AssembleurTriangles

Exposer un contrat explicite « origine Lambert + azimut de carte » pour chaque
ligne horaire, et tester que la passerelle et le rendu héritent du même cache
pixel. Risque modéré; validation métier nécessaire seulement si l'assembleur
réclame une direction Lambert réelle.

### LAMBERT-NATIVE-006 — décision métier sur géométrie image

Uniquement après comparaison multi-cartes : décider séparément pour
Sentinelle, Segment/Planète, partitions, cercles à trois points, projections,
points équidistants/latéraux et candidats. Toute conversion vers Lambert ici
peut modifier les résultats numériques : validation métier et golden complets
obligatoires.

## Décisions à ne pas prendre dans cette série

- Ne pas supprimer `pointReference` ni `lignePixelImage` : ce sont des caches
  et supports légitimes de rendu/UI, et parfois le support volontaire d'un
  calcul image.
- Ne pas renommer une droite « Lambert » parce qu'elle est stockée avec un
  point Lambert : le repère de sa direction et de ses opérations doit rester
  déclaré séparément.
- Ne pas déduire que les angles pixel sont une dette : les commentaires, les
  conventions et les tests montrent au contraire des usages métier plausibles.
