# 650 — Lot 1 : référentiel astronomique des Sentinelles

## Périmètre et analyse préalable

Le lot ajoute un référentiel calculable et versionné, sans le raccorder aux
algorithmes consommateurs. `Sentinelle`, son CSV et ses interfaces restent
intacts, ainsi que Lampouy et les scénarios enregistrés.

L'examen préalable de `Sentinelle.py`, `calculAstronomique.py`,
`affichage_objets.py`, `carte_config.py`, du CSV historique et des trois suites
de tests astronomiques/Sentinelle montre les différences suivantes :

- `Sentinelle` charge `Azimut`, `AzimutGeant`, `Ville`, construit des objets
  graphiques puis calcule un `AzimutCalibre` dépendant de la carte. Son
  dictionnaire par note expose `HeureLocale`, `AzimutCalibre`, `AzimutGeant`.
- Son `azimutMidi` vient de Coëtquidan–Golfe-Juan en pixels. Il sert au dessin
  et aux recherches `surLigneHoraire`. Il ne doit pas être remplacé globalement.
- `MyJulianDate` interprète déjà 1066 dans le calendrier julien ;
  `positionSoleil` emploie `ts.ut1_jd`, une position apparente topocentrique et
  `altaz()` sans réfraction. Ces deux fonctions sont réutilisées.
- La conversion historique nommée `convertirHeureLocaleVersUTC` arrondit le
  décalage de longitude à la seconde et manipule des chaînes. Le nouveau
  contexte conserve le décalage exact et un JD UT1, sans modifier cette fonction.
- La recherche historique `calculHeurePourAzimutSoleil` ne convient pas à
  tous les nouveaux azimuts : à Carnac le 15/08/1066, la demande 255° peut
  intercepter 75° à cause du test de changement de signe modulo 180°.
  Le nouveau moteur cherche sur l'arc diurne croissant, du lever au coucher,
  avec les bornes des fonctions historiques `calculLeverSoleil` et
  `calculCoucherSoleil`. Il ne duplique pas le calcul astronomique de position.
- `heureSymetrique` fait une symétrie temporelle autour de 12:00. Elle reste
  utilisable par les anciens algorithmes, mais ne participe jamais au nouveau
  miroir angulaire.
- `LigneAzimut` attend un azimut **image**, pas un azimut astronomique ni une
  orientation Lambert. Aucune construction graphique n'est changée ici.

## Fichiers et API

- `data/sentinelles_reference_v1.json` : huit définitions, une seule grandeur
  faisant autorité par référence, provenance, statut et témoins de comparaison.
- `config/cadran_national_v1.json` : contexte de Carnac et axe national.
- `src/ReferentielSentinelles.py` : chargement, calcul et miroir astronomique.
- `tests/test_referentiel_sentinelles.py` : données, conventions, branches,
  comparaisons chiffrées et autonomie sans carte.

```python
from src.ReferentielSentinelles import (
    ReferentielSentinelles, symetrieAzimutSolaireAstronomique,
)

r = ReferentielSentinelles.charger()
s3 = r.get("S3")
s3.azimut_direct                 # degrés nord géographique, sens horaire
s3.heure_directe.secondes        # secondes TML non arrondies depuis minuit local
s3.heure_directe.toString()      # présentation HH:MM:SS, arrondie à la seconde
s3.heure_directe.toString("HH:MM")  # arrondi à la minute, présentation seulement
s3.azimut_miroir
s3.heure_miroir
s3.directe.branche               # "apres_midi"
s3.miroir.branche                # "matin"
r.cadran_national.centre         # "Coetquidan" : clé du point existant
r.cadran_national.orientation_midi  # 125.371

miroir = symetrieAzimutSolaireAstronomique(s3.azimut_direct, r.moteur)
miroir.azimut
miroir.heure_locale.secondes
miroir.branche
```

`DirectionSolaire` contient aussi le JD UT1 de l'instant. Le moteur refuse une
heure sous l'horizon ou un azimut inaccessible sur son arc diurne. Il est conçu
pour le site/date de référence ; ce n'est pas un solveur général des situations
polaires ou des journées où le Soleil passe au nord à midi.

Le module ne charge ni `data_loader`, ni `Sentinelle`, ni OpenCV, ni Tk, ni une
image ou calibration. Il réutilise le module astronomique du dépôt, donc exige
toujours Skyfield et `data/ephemeride/de406.bsp`. Comme les fonctions historiques,
il doit être exécuté depuis la racine du dépôt pour trouver cette éphéméride.
Le test d'autonomie interdit effectivement les imports graphiques et les accès
à `data/carto`, sans déplacer ni supprimer de fichiers.

## Conventions astronomiques

- Carnac : latitude 47°35′36″ N, longitude 3°04′47″ O, latitude positive et
  longitude est positive : **47,593333333333°, −3,079722222222°**.
- Date : **15 août 1066 julien**, origine numérique à 00:00 : **JD 2110640,5**.
  Cette origine est une date de calendrier avant correction de longitude,
  pas le JD UT1 physique du minuit local.
- Temps moyen local : **TML = UT1 + longitude × 240 secondes**.
  À Carnac, TML = UT1 − **739,133333… s**. On ajoute donc ce décalage positif
  pour passer de l'heure moyenne locale à UT1. Aucun fuseau légal moderne.
- Azimut apparent topocentrique, nord géographique = 0°, est = 90°, sud = 180°,
  sens horaire ; pas de réfraction atmosphérique demandée au calcul de position.
  Altitude Topos par défaut : 0 m, comme dans la fonction historique réutilisée.
- `A_miroir = (360 − A_direct) mod 360`, puis recherche de son instant réel
  dans la **même journée**. La branche matin/après-midi dépend de l'instant du
  passage au sud, pas du fait d'être avant/après 12:00 en TML.
- Éphéméride DE406 et modèle ΔT intégré à Skyfield (TT − UT1 ≈ 1349,958 s
  à la date de référence avec la version installée). Pas de substitution par
  une éphéméride exploratoire, pas d'ajustement des sorties aux témoins.

Skyfield emploie par défaut le calendrier grégorien, même aux dates anciennes.
Il faut passer le JD julien construit par `MyJulianDate` à `ts.ut1_jd`, et non
appeler `ts.utc(1066, 8, 15, ...)` ou `ts.ut1(1066, 8, 15, ...)` sur les mêmes
chiffres : cette dernière date diffère ici de six jours.
Voir la [documentation des calendriers Skyfield](https://rhodesmill.org/skyfield/time.html#ancient-and-modern-dates)
et l'[API UT1](https://rhodesmill.org/skyfield/api-time.html).

## Tableau effectivement calculé

DE406, Skyfield 1.51. Les heures ci-dessous sont **présentées** à la seconde ;
les objets gardent leurs secondes fractionnaires. Les azimuts sont présentés
à 0,001°. M = matin ; PM = après-midi.

| Repère | Note | Azimut direct | Heure directe TML | Branche | Azimut miroir | Heure miroir TML | Branche |
| --- | --- | ---: | --- | --- | ---: | --- | --- |
| S1 | C | 128,818° | 09:43:00 | M | 231,182° | 14:21:11 | PM |
| S2 | D | 107,000° | 08:14:46 | M | 253,000° | 15:49:38 | PM |
| S3 | E | 255,000° | 15:59:05 | PM | 105,000° | 08:05:20 | M |
| S4 | F | 218,000° | 13:39:02 | PM | 142,000° | 10:25:04 | M |
| S5 | G | 179,150° | 12:00:00 | M | 180,850° | 12:04:01 | PM |
| S6 | A | 171,564° | 11:42:00 | M | 188,436° | 12:22:01 | PM |
| S7 | B | 166,869° | 11:30:42 | M | 193,131° | 12:33:19 | PM |
| Joker | J | 152,732° | 10:55:00 | M | 207,268° | 13:09:03 | PM |

Le midi solaire vrai calculé est à **12:02:00,446 TML**, soit **+2,446 s** par
rapport au témoin 12:01:58. À 12:00 TML, S5 est donc encore sur la branche du matin.

Écarts signés **calcul non arrondi − témoin fourni**, distances angulaires
circulaires en degrés, écarts temporels en secondes :

| Repère | Δ azimut direct (°) | Δ heure directe (s) | Δ azimut miroir (°) | Δ heure miroir (s) |
| --- | ---: | ---: | ---: | ---: |
| S1 | −0,010853 | +0,000000 | +0,010862 | +5,028297 |
| S2 | −0,000004 | +1,840204 | −0,000005 | +2,879135 |
| S3 | +0,000009 | +2,785575 | −0,000013 | +2,311507 |
| S4 | −0,000002 | +2,810513 | +0,000004 | +2,280033 |
| S5 | −0,017530 | +0,000000 | +0,017551 | +4,893377 |
| S6 | −0,016382 | +0,000000 | +0,016390 | +5,122078 |
| S7 | −0,016312 | +0,000000 | +0,016316 | +4,456842 |
| Joker | −0,015166 | +0,000000 | +0,015164 | +4,440827 |

La recherche numérique est bornée à **0,01 seconde**. Les autorités horaires
sont conservées exactement ; les autorités angulaires sont contrôlées à
**0,0001°**. L'involution du miroir est contrôlée à 0,0001° et 0,03 s.

Pour les seuls témoins d'investigation, les tests admettent **6 secondes** et
**0,025°** : ces marges couvrent les écarts mesurés (maxima 5,123 s et 0,017551°)
avec une petite réserve. Elles restent assez étroites pour détecter les erreurs
de calendrier, de longitude ou de branche observées lors de l'analyse.
Le moteur et le modèle ΔT ayant produit le tableau exploratoire ne sont pas
précisés ; l'origine exacte des quelques secondes d'écart n'est donc pas établie.
Ces tolérances ne constituent pas une estimation de l'incertitude physique de
1066. Toute évolution du moteur doit être diagnostiquée, pas compensée par une
correction ad hoc ni par l'élargissement automatique des seuils.

S1, S5, S6 restent des références structurantes ; S7 est affinée
géographiquement ; le Joker est une hypothèse ; S2/S3/S4 sont des mesures
provisoires. Les géographies ayant servi à calibrer ces heures ne sont **pas**
des validations indépendantes de ce même modèle. Les statuts et les témoins
n'interviennent jamais dans la formule solaire.

## Axe national et préparation du lot 2

`centre = "Coetquidan"` référence la clé déjà présente dans
`data/villes_database.csv`. Aucune seconde définition de ses coordonnées n'est
introduite. L'axe national vaut **125,371°**, statut **calibration provisoire**.

La convention précisée pour cette valeur est une **orientation de grille
Lambert-93 (EPSG:2154), sens horaire depuis le nord de la grille**, avec le
centre fixe Saint-Cyr–Coëtquidan. Elle est stockée explicitement, sans
recalibrage ni conversion dans le lot 1. Elle n'est ni l'azimut solaire
géographique (180° à midi solaire vrai), ni l'angle depuis le haut de l'image.
Le lot 2 effectuera la conversion affine existante avant `LigneAzimut`.

Pour convertir cette orientation de grille en orientation image au lot 2 :

```text
v_lambert = (sin(theta_grille), cos(theta_grille))
v_image = A @ v_lambert
theta_image = atan2(v_image.x, -v_image.y) modulo 360°
```

L'offset affine ne s'applique pas à un vecteur directeur. Il sert à transformer
le point d'ancrage, via `A @ point_lambert + offset`. Pour d'autres directions
dont le nord de départ serait géographique, il faudra d'abord tenir compte de
la convergence des méridiens au centre, par exemple avec une petite direction
géodésique projetée en Lambert. Cela ne concerne pas les 125,371° déjà définis
dans la grille.
Le sens de report des angles solaires relativement à l'axe national devra aussi
être explicité dans l'adaptateur du lot 2. Aucune de ces conversions n'est
injectée prématurément dans les anciens calculs graphiques.

## Interfaces à migrer aux lots 2 et 3

| Interface actuelle | Travail futur |
| --- | --- |
| `Sentinelle[note]["HeureLocale"]`, `getAzimut()` | Choisir explicitement directe/miroir et préserver les secondes jusqu'à la présentation. |
| `AzimutCalibre` | Distinguer solaire direct, solaire miroir et physique historique ; ne pas écraser `AzimutGeant`. |
| `azimutMidi`, `getOrigineStylet()`, `afficherLigneMidi()` | Ajouter le nouvel axe national et sa conversion de repère ; ne pas remplacer les axes propres aux stylets/segments. |
| `afficherLigneHoraire()` et `surLigneHoraire()` | Reporter les deux directions réelles, sans forcer directe = matin ; conserver le seuil de proximité pendant la migration. |
| `heureSymetrique()` dans Base, Lumière, Cadran et autres consommateurs | Remplacer les usages solaires concernés par le miroir astronomique, sans modifier les autres usages temporels. |
| `AlgorithmeStyletInitial.Candidats`, `SentinelleChemin` | Revoir sélection de branche et géométrie nationale dans l'adaptateur prévu. |
| `AlgorithmeSegment.PlaneteChemin` | Conserver l'emploi physique de `AzimutGeant` pour les planètes ; pas de substitution par le solaire. |
| Lampouy / Loudun | Migration séparée ; conserver note L, Carnac et date dédiée d'août 1152. |
| IHM et scénarios | Prévoir ultérieurement la présentation des nouvelles branches ; aucune migration automatique dans ce lot. |

## Reproduire les contrôles

Depuis la racine du dépôt, avec les dépendances et DE406 disponibles :

```text
python -m pytest tests/test_referentiel_sentinelles.py -q -s
python -m pytest -q
```

La première commande affiche les quatre écarts de chaque direction. La suite
historique conserve notamment les contrats de `Sentinelle`, la symétrie horaire
ancienne, le cas Lampouy et les solutions de référence des consommateurs.
