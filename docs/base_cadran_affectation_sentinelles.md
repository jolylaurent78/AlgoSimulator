# Base Cadran — Affectation explicite des Sentinelles aux stylets

Mission sur `dev`, révision de départ `a49a56c`. Les affectations définissent l’identité nationale et sa branche ; elles ne sont plus déduites d’une recherche du voisin le plus proche. Les périodes AM/PM, substitutions, calendriers, constructions et seuils restent indépendants et inchangés.

## Affectations retenues

Les codes hors S1–S7 et S1M–S7M sont refusés par `ValueError`, sans repli silencieux. Les sept cellules renseignées fixent les identités historiques/géométriques ci-dessous, avec la correction S6M expressément demandée pour 1431. Les relevés géométriques ont été faits avant modification, sur les mêmes villes et la même calibration.

| Événement | Stylet | SentinelleStylet | Note / branche | Justification et validation |
|---|---|---|---|---|
| 15 Aout 778 : Bataille de Roncevaux | Roncevaux | `S1` | C / directe | Référence de construction S1 et relevé géométrique actuel concordants. |
| 20 Mars 1815 : Début des 100 jours | Golfe-Juan | `S5M` | G / miroir | S5 miroir déjà documentée dans `referentiel_sentinelles_lot3.md`, et retrouvée géométriquement. |
| 30 Mai 1431 : Mort de Jeanne d’Arc | Sainte-Catherine-de-Fierbois | `S6M` | A / miroir | S6M imposé par la mission ; la dérive automatique vers S7M est explicitement écartée. |
| 12 Avril 1365 : Traité de Guérande | Alise-Sainte-Reine | **vide** | Joker / miroir (relevé automatique) | À définir : Joker n’appartient pas aux codes autorisés. Cellule vide, aucun S1–S7 inventé. |
| 27 Juillet 1214 : Bataille des Bouvines | Vouneuil-sur-Vienne | `S5` | G / directe | Note G déjà documentée ; direction directe identifiée par le relevé géométrique existant. |
| 15 Juin 1066 : Guillaume le conquérant | Nouaillé-Maupertuis | `S6` | A / directe | Note A déjà documentée ; direction directe identifiée par le relevé géométrique existant. |
| 19 Juillet 933 : Hommage de Guillaume Longue Epée | Saint-Valentin | `S7M` | B / miroir | S7 miroir documentée dans les rapports de calibration S7 ; relevé concordant. |
| 28 Septembre 1066: Débarquement de Guillaume le Conquérant | 3RDV | **vide** | non affecté | Événement de transition : cellule vide. Relevé automatique hors sélection, donc non retenu. |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Loudun | `S5M` | G / miroir | Note G déjà documentée ; branche miroir du relevé géométrique actuel figée explicitement. |

Les notes proviennent du référentiel existant, pas d’un nouveau tableau de correspondance dans le calcul. Pour les affectations fondées sur la géométrie, la validation historique indépendante peut encore être complétée ; les identités indiquées ne sont pas recalculées si la calibration évolue. Les justifications antérieures des notes figurent notamment dans `s7_169_symetrie_horaire_bases.md` et `s7_169_5_mesures.md`.

**Restent sans affectation explicite : Alise-Sainte-Reine et 3RDV.** Alise conserve temporairement le comportement de compatibilité, avec diagnostic explicite ; aucun code Joker non autorisé n’est introduit. La transition du 28 septembre n’a pas de scénario parmi les 16 bases contrôlées.

## Chargement, compatibilité et persistance

- La colonne est placée immédiatement après `Stylet`. Les autres cellules du CSV et ses fins de ligne sont conservées ; aucune date, base, note ou coordonnée n’est remplacée.
- `ListeSegmentsDataSet` expose `sentinelleStylet`. Une ancienne colonne absente, ou un ancien snapshot dépourvu du champ, donne une valeur vide compatible.
- Le loader enrichit **uniquement les anciens projets BaseCadran**, **uniquement si la clé manque**, et **uniquement par identifiant exact d’événement**. Il lit la seule colonne nouvelle du CSV ; toutes les autres valeurs embarquées restent autoritaires.
- Une affectation déjà présente, même explicitement vide, est conservée. Une affectation invalide n’est jamais remplacée automatiquement. Un événement sans correspondance exacte conserve son absence d’affectation et un diagnostic de repli.
- Un CSV manquant laisse l’ancien projet chargeable avec un avertissement. Le repli est également signalé par `diagnosticAffectation` et le logger de `CercleHoraire` : « recherche automatique de compatibilité ». Les autres erreurs de lecture ou les codes invalides ne sont pas masqués.
- La sauvegarde conserve la nouvelle information dans le snapshot. Un snapshot complet est ensuite autonome : le rechargement n’a plus besoin de lire le CSV métier.
- Les anciens projets Cadran Final, Segment, Stylet Initial et Lumière Initiale ne reçoivent aucun enrichissement depuis le CSV. Le code du Cadran Final n’est pas modifié.

## Identité du stylet et heure de construction

`S6M` sélectionne la note A/S6, branche miroir, directement dans `SentinelleNationale` / `ReferentielSentinelles`. Aucune recherche automatique n’est appelée pour ce code. La direction assignée et son heure nationale restent dans `selectionHoraire` / `heureStylet`. Le diagnostic de distance à cette direction ne change jamais l’affectation explicite.

Le calcul du cercle conserve ensuite sa logique : choix du calendrier, substitutions `=`, `+2`, `−2` ou Joker, heure **AM** de la note finale, puis éventuellement **(86400 − heure_AM) % 86400** pour la période PM. La branche assignée ne modifie ni `heureAMPM` ni `cercleAMPM`. S3 et S4 directes PM sont couvertes par les tests pour vérifier cette indépendance. Lampouy conserve sa substitution angulaire historique et sa gestion de signe.

### Écart constaté sur le témoin miroir S6

La mission cite **12:21:56** pour le miroir astronomique S6 ; cette valeur figure comme témoin dans `sentinelles_reference_v1.json`. Le référentiel **DE406 actuel**, déjà utilisé avant cette modification, donne **12:22:01,122077934 TML** (44521,122077934 secondes). Il est conservé sans aucun ajustement de calibration. Cette différence d’environ cinq secondes ne concerne pas la construction des bases : **11:42:00 AM et 12:18:00 PM** restent exactes. La calibration S7 reste à **169,5°**.

## Saint Cyr Coetquidan — contrôles en mémoire

Le scénario enregistré reste **Standard / −2 / AM**, avec son choix de cercle inchangé. Avec S7M automatique, B −2 donnait G à 12:00 ; avec S6M explicite, A −2 donne **F à 10:25:04**. Ses deux candidats disparaissent : les cercles horaire et distance n’ont plus d’intersection, et aucun secours de partition ne converge. Aucun seuil ni réglage n’est ajusté pour les récupérer.

Le cas obligatoire `=` est testé séparément en mémoire, sans sauvegarde ni modification du scénario. Le côté du cercle est celui du scénario enregistré.

| Période | Heure de construction | Heure nationale du stylet S6M | Angle positif | Troisième point (L93 m) | Centre du cercle horaire (L93 m) | Rayon horaire (km) | Candidats recalculés |
|---|---|---|---:|---|---|---:|---|
| AM | **11:42:00** | 12:22:01 | 8,538170° | (662455.372 ; 7552719.909) | (625188.301 ; 7109018.735) | 446,201650 | aucun |
| PM | **12:18:00** | 12:22:01 | 11,143693° | (645050.870 ; 7345502.183) | (616422.676 ; 7004655.345) | 342,767679 | (310211.606 ; 6862780.256) |

Le rayon ci-dessus est celui de la construction horaire, recalculé par la formule existante. Les **cercles candidats conservent leur rayon de 20 km**. L’unique candidat du contrôle PM n’est pas imposé : il résulte du pipeline inchangé. Aucun passage à S7, 11:37:03 ou 12:26:58 n’intervient dans l’affectation S6M.

## Vérification des 16 scénarios enregistrés

Deux calculs en mémoire sont comparés : avant le correctif, puis après enrichissement du seul champ nouveau. Tous les paramètres, dates, notes embarquées, octaves, périodes, substitutions et côtés de cercle sont conservés.

| Événement | Scénario | Calendrier / substitution / période / cercle | Affectation avant → après | Heure de construction avant → après | Candidats avant → après |
|---|---|---|---|---|---:|
| 15 Aout 778 : Bataille de Roncevaux | Saint Amour | Standard / = / AM / PM | S1 → S1 | 09:43:00 → 09:43:00 | 1 → 1 |
| 15 Aout 778 : Bataille de Roncevaux | Rocamadour | Déclinaison / = / AM / AM | S1 → S1 | 10:25:04 → 10:25:04 | 1 → 1 |
| 15 Juin 1066 : Guillaume le conquérant | Gergovie | Déclinaison / = / AM / PM | S6 → S6 | 10:25:04 → 10:25:04 | 1 → 1 |
| 15 Juin 1066 : Guillaume le conquérant | Carignan | Déclinaison / +2 / AM / AM | S6 → S6 | 11:42:00 → 11:42:00 | 0 → 0 |
| 20 Mars 1815 : Début des 100 jours | Ile d'Aix | Déclinaison / -2 / AM / AM | S5M → S5M | 09:43:00 → 09:43:00 | 2 → 2 |
| 20 Mars 1815 : Début des 100 jours | Rouen | Standard / 11:00 / PM / PM | S5M → S5M | 13:05:00 → 13:05:00 | 0 → 0 |
| 27 Juillet 1214 : Bataille des Bouvines | Metz | Déclinaison / -2 / PM / AM | S5 → S5 | 12:22:57 → 12:22:57 | 0 → 0 |
| 27 Juillet 1214 : Bataille des Bouvines | Chateau Gaillard | Standard / 11:00 / AM / AM | S5 → S5 | 10:55:00 → 10:55:00 | 0 → 0 |
| 30 Mai 1431 : Mort de Jeanne d’Arc | Saint Cyr Coetquidan | Standard / -2 / AM / AM | S7M → S6M | 12:00:00 → 10:25:04 | 2 → 0 |
| 30 Mai 1431 : Mort de Jeanne d’Arc | Domremy | Déclinaison / = / PM / AM | S7M → S6M | 12:18:00 → 12:18:00 | 1 → 1 |
| 12 Avril 1365 : Traité de Guérande | Reims | Déclinaison / +2 / AM / PM | JokerM → JokerM | 10:25:04 → 10:25:04 | 1 → 1 |
| 12 Avril 1365 : Traité de Guérande | Bouvines | Standard / 11:00 / AM / PM | JokerM → JokerM | 10:55:00 → 10:55:00 | 1 → 1 |
| 19 Juillet 933 : Hommage de Guillaume Longue Epée | Chalus | Standard / = / PM / PM | S7M → S7M | 12:22:57 → 12:22:57 | 1 → 1 |
| 19 Juillet 933 : Hommage de Guillaume Longue Epée | Fontevraud | Standard / = / PM / AM | S7M → S7M | 12:22:57 → 12:22:57 | 1 → 1 |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Pont de Noirmoutiers | Standard / = / AM / PM | S5M → S5M | 12:00:00 → 12:00:00 | 2 → 2 |
| 18 Mai 1152 : Mariage d’Aliénor d’Aquitaine | Le Goulet | Standard / 138.5° / AM / AM | S5M → S5M | 12:00:00 → 12:00:00 | 1 → 1 |

Bilan : **15 → 13 candidats**. **15 constructions horaires et listes de candidats restent identiques** (heures en secondes, angle, troisième point et coordonnées des candidats). Seul Saint Cyr change sa géométrie. Domremy change également son identité de stylet S7M → S6M, mais conserve sa construction de calendrier Déclinaison et ses résultats.

Les coordonnées de tous les candidats restants sont vérifiées par reconstruction indépendante des cercles : leurs intersections et projections sur les partitions donnent les mêmes milieux, avec le seuil strict historique de 20 km. Le test golden réel couvre maintenant les **16 scénarios présents**, au lieu d’attentes devenues partielles après les mises à jour du projet ; aucune fixture JSON ni solution enregistrée n’est modifiée.

| Scénario | Intersections des cercles | Plus petit écart de convergence mesuré (km) | Candidats |
|---|---:|---:|---:|
| Saint Amour | 2 | 6,912155 | 1 |
| Rocamadour | 2 | 2,512418 | 1 |
| Gergovie | 2 | 10,276297 | 1 |
| Carignan | 2 | 39,614784 | 0 |
| Ile d'Aix | 2 | 1,366941 | 2 |
| Rouen | 2 | 25,191784 | 0 |
| Metz | 2 | 22,964517 | 0 |
| Chateau Gaillard | 2 | 25,030631 | 0 |
| Saint Cyr Coetquidan | 0 | aucune paire disponible | 0 |
| Domremy | 2 | 7,836056 | 1 |
| Reims | 2 | 10,069160 | 1 |
| Bouvines | 2 | 16,590554 | 1 |
| Chalus | 2 | 1,651598 | 1 |
| Fontevraud | 2 | 12,309234 | 1 |
| Pont de Noirmoutiers | 2 | 4,055618 | 2 |
| Le Goulet | 2 | 9,087789 | 1 |

## Tests et périmètre

- Tests ciblés rejoués : `python -m pytest tests/test_affectation_sentinelle_stylet.py tests/test_cadrans_sentinelles_lot3.py::test_bases_reelles_conservent_les_criteres_geometriques -q --tb=short` — **62 réussites en 22,04 s**.
- Une passe plus large a vérifié les tests Base Cadran, le lot 3 et les contrats/roundtrips de persistance : 222 réussites ; la seule assertion ancienne de Saint Cyr (deux candidats S7) a été mise à jour après vérification géométrique, puis rejouée dans les 62 tests ci-dessus.
- Suite complète : `python -m pytest -q --tb=short` — **958 réussites en 284,53 s**.
- Les 61 nouveaux cas couvrent tous les codes et les deux périodes, les substitutions et calendriers, les codes invalides, les diagnostics de compatibilité, Lampouy et le choix du côté, les anciens CSV, l’enrichissement exact et limité à BaseCadran, la priorité aux affectations embarquées, la persistance autonome et le CSV absent.
- Aucune formule de cercle ou de convergence, aucun rayon candidat, aucune calibration, aucun algorithme Cadran Final et aucun projet JSON n’est modifié. Seul `SentinelleStylet` est ajouté aux données métier et à la compatibilité des anciens projets BaseCadran.
