# Adoption du Joker à 10:56:00 TML

La calibration officielle de travail passe de **10:55:00 à 10:56:00 TML**, sur `dev`, à partir du commit `ac9b11c`. Le référentiel persistant est désormais utilisé normalement par AlgoSimulator ; aucune modification d’algorithme n’est nécessaire.

## Justification et provenance

Les études historiques restent inchangées et disponibles : [comparatif 10:55 / 10:57](joker_1057_etude_globale.md), [validation 10:56](joker_1056_etude_globale.md). L’adoption à 10:56 retrouve Rouen tout en conservant Château-Gaillard, Bouvines et la sélection native d’Alise-Sainte-Reine. L’écart solaire au relevé de 153° diminue.

Dans `data/sentinelles_reference_v1.json`, l’entrée courante garde l’identifiant `Joker`, la note `J`, la nature `axe_rangee`, l’autorité `heure` et l’azimut physique historique **153.0**. Sa valeur devient `10:56:00`, son statut `calibration_de_travail_validee`, et ses témoins sont actualisés avec les résultats DE406.

Un historique daté du 30 octobre 2026 conserve **l’entrée précédente complète**, identique au JSON antérieur : heure 10:55, autorité, nature, statut, provenance Alise et anciens témoins. Il conserve séparément le calcul précédent DE406 : azimut direct **152,731833537028°**, miroir **207,268164106237°**, heure miroir **13:09:03,440827 TML** (47343,44082706372 s). Les anciens témoins approximatifs restent archivés comme tels, sans être confondus avec ces valeurs calculées.

Le motif enregistré est : « Ajustement de 10:55 à 10:56 TML, validé par étude globale DE406 : couverture simultanée de Rouen, Château-Gaillard et Bouvines, maintien de la sélection native d’Alise-Sainte-Reine et amélioration de l’accord avec l’azimut physique historique de 153°. » Les deux historiques S7 et les sept autres références sont conservés intégralement.

## Valeurs natives recalculées

Skyfield / DE406 ; Carnac, 15 août 1066 julien, temps moyen local converti en UT1. Les témoins JSON restent informatifs, jamais une autorité remplaçant le calcul.

| Paramètre | Résultat |
|---|---:|
| Joker AM | 10:56:00 |
| Azimut solaire direct | 153,109534102741° |
| Écart au relevé 153° | +0,109534102741° |
| Miroir astronomique | 13:08:03,364589 TML |
| Secondes miroir conservées | 47283,36458884875 |
| Azimut miroir | 206,890448385860° |
| Orientation miroir, grille Lambert-93 | 98,480551614140° |
| Distance réelle Alise–axe miroir | 17,179662566331 km |
| Sélection native Alise | vraie, Joker / J / miroir, distance entière 17 km |
| Joker PM des bases, symétrie TML | **13:04:00**, 47040 s |

L’axe national reste **125,371° depuis le nord de grille**, distinct du nord géographique des azimuts solaires. Le miroir astronomique du référentiel et du Cadran Final reste distinct de la symétrie TML des bases. Aucun de ces mécanismes n’est modifié. Le libellé `11:00` de l’interface reste inchangé.

## Rejeu réel des 16 bases

Le chargement normal de `projets/BaseCadran.json` est refait avec le référentiel enregistré, sans injection ni remplacement de la fabrique. Tous les paramètres locaux existants sont conservés. **Les résultats sont exactement identiques à l’hypothèse 10:56 validée**, y compris les listes de centres, diagnostics, partitions, heures et rayons. Aucune différence avec les valeurs témoins, hormis les arrondis de présentation.

| Base | Candidats pondérés | Meilleure distance (km) | Couverture à 20 km |
|---|---:|---:|---|
| Saint Amour | 1 | 8,012738 | Oui |
| Rocamadour | 1 | 16,076271 | Oui |
| Gergovie | 1 | 8,721513 | Oui |
| Carignan | 3 | 12,723583 | Oui |
| Ile d'Aix | 1 | 9,358809 | Oui |
| Rouen | 1 | 17,218031 | Oui |
| Metz | 1 | 689,542902 | Non |
| Chateau Gaillard | 2 | 1,647971 | Oui |
| Saint Cyr Coetquidan | 1 | 15,540208 | Oui |
| Domremy | 1 | 5,404876 | Oui |
| Reims | 1 | 10,210969 | Oui |
| Bouvines | 1 | 15,550449 | Oui |
| Chalus | 1 | 5,768251 | Oui |
| Fontevraud | 1 | 18,333633 | Oui |
| Le Goulet | 1 | 12,533544 | Oui |
| Pont de Noirmoutiers | 2 | 10,439013 | Oui |

Bilan : **20 candidats, 15 bases couvertes sur 16**. Metz reste non couverte, sans recherche supplémentaire. Les treize bases autres que Rouen, Château-Gaillard et Bouvines conservent exactement leurs centres et nombres par rapport à l’ancienne calibration.

- **Rouen** : cas 2 pondéré, AB imposé = **28,814260 km**, candidat à **17,218031 km**. PM = 13:04:00. Les trois écarts sont **0,055675 / 9,465372 / 15,790979 km**.
- **Château-Gaillard** : cas 1, **deux candidats**, meilleur à **1,647971 km**.
- **Bouvines** : cas 1, un candidat à **15,550449 km**. Le rayon distance est recalculé à 10:56 : **340,454985 km**, contre 341,341544 km à 10:55.

Aucun seuil 30/20 km, formule de cercle, partition, substitution ou paramètre de scénario n’est modifié.

## Rejeu réel des 38 scénarios Final

Le projet local `projets/CadranFinal_Solutions.json` est chargé normalement avec la calibration persistée, puis les modules sont recalculés explicitement par événement et scénario. Les listes de centres, heures, directions et résultats sont **exactement identiques** à l’étude 10:56.

**87 candidats**, **29 couvertures sur 33 références ponctuelles mesurables**, aucune perte de couverture. Les 38 scénarios sont contrôlés ; la transition sans bases reste sans géométrie. Les 11 scénarios ayant une lumière ou une ombre Joker utilisent les nouvelles directions ; les autres conservent exactement leurs centres. Le tableau détaillé des 38 scénarios de [l’étude 10:56](joker_1056_etude_globale.md) s’applique donc sans différence.

| Contrôle prioritaire | Meilleure distance (km) | Couvert |
|---|---:|---|
| Jumièges | 7,830431 | Oui |
| Donon | 12,922930 | Oui |
| Quiberon | 3,801047 | Oui |
| Solesmes | 2,591807 | Oui |
| Pic du Midi | 17,798722 | Oui |
| Montmirail | 15,086739 | Oui |

Pic du Midi conserve **2,201278 km de marge**. Les ombres Joker emploient 10:56 AM et le miroir réel 13:08:03,364589 PM. Les scénarios Frontiere Sud Bretagne, Le Bec, Dover, Zone et Scénario par défaut n’ont pas de référence ponctuelle vérifiable : leurs nombres de candidats sont contrôlés, mais aucune couverture n’est inventée. Montmirail utilise seulement en mémoire le point déjà fourni par l’utilisateur, 48,10° N / 0,769° E.

## Tests et limites

- **221 tests ciblés réussis en 59,49 s** : nouveau fichier d’adoption, référentiel, géométrie nationale lot 2, modules Base et Final, clefs Base.
- Complément : **11 tests réussis en 6,57 s** (`tests/test_s7_symetrie_bases.py` et le test d’interface des clefs Final). Le test d’archive S7 sélectionne désormais explicitement les historiques S7, au lieu de supposer que le dernier historique global lui appartient. Toutes ses assertions de valeurs sont conservées.
- Les tests temporels lot 3 ont également été exécutés : leurs attentes Joker sont actualisées ; le golden sur les paramètres locaux conserve son écart préexistant à Carignan (deux candidats historiques contre zéro attendu). Cet écart n’est pas masqué en modifiant le projet ou des attentes indépendantes du Joker.
- Quatre nouveaux tests vérifient l’entrée enregistrée et son archive, le calcul solaire et les secondes fractionnaires du miroir, la distinction avec la symétrie TML, la sélection native d’Alise et le fait que des témoins JSON volontairement faux ne remplacent jamais les calculs.
- Les heures des sentinelles fictives de `test_algorithme_lumiere_stylet_initial.py` sont volontairement conservées : ces tests isolent le comportement des modules et ne consultent pas le référentiel enregistré. Les autres attentes temporelles sans lien avec le Joker restent intactes.

### Golden historique : deux changements réellement dépendants du Joker

Le golden `test_bases_reelles_conservent_les_criteres_geometriques` utilise **la méthode historique et les paramètres du projet versionné**, qui diffèrent des paramètres locaux de l’étude pondérée. Une copie temporaire de ce projet est calculée à 10:55 puis à 10:56, avec les mêmes paramètres :

| Base du projet versionné, mode historique | 10:55 | 10:56 |
|---|---|---|
| Château-Gaillard | aucun candidat | 1 centre : (576904,964799 ; 6902698,291993) m |
| Bouvines | 1 centre : (709697,984416 ; 7039227,428647) m | aucun candidat |

**Seules ces deux attentes géométriques sont actualisées** ; les quatorze autres restent inchangées. Les constructions sont contrôlées par les assertions géométriques existantes du golden, qui réussit pour les 16 scénarios sur le projet versionné avec ces deux mises à jour. La perte du candidat historique de Bouvines est explicitement signalée : l’adoption ne garantit pas la conservation des résultats de toutes les anciennes combinaisons de paramètres ou de toutes les méthodes. Elle ne constitue pas une perte dans le jeu pondéré local demandé, où Bouvines reste couvert à 15,550449 km.

Premier passage complet : **1036 réussites, 3 échecs en 308,11 s**. L’hypothèse d’ordre du test S7 ci-dessus est corrigée ; l’erreur d’initialisation Tcl du test d’interface des clefs passe au rejeu ciblé sans modification de l’interface ; l’écart golden Carignan sur le projet local reste préexistant.

**Passage complet final : 1038 réussites, 1 échec en 299,50 s**, commande `python -m pytest -q --tb=short`. Le seul échec restant est `test_bases_reelles_conservent_les_criteres_geometriques`, sur les paramètres locaux de Carignan (deux candidats historiques contre zéro attendu). La suite n’est donc pas intégralement verte dans cet état de travail local. Les tests d’interface et d’archive S7 réussissent dans ce passage final. Le même golden passe sur les 16 scénarios du projet versionné avec les seules mises à jour Joker démontrées ci-dessus. Les projets locaux ne sont ni remplacés ni modifiés pour masquer l’écart.

## Fichiers livrés et préservation

- `data/sentinelles_reference_v1.json` : heure officielle, provenance, historique et témoins Joker.
- `tests/test_referentiel_sentinelles.py` : valeur, statut et branches Joker.
- `tests/test_algorithme_base_cadran.py` : attente horaire Joker réelle.
- `tests/test_algorithme_cadran_final.py` : attente horaire Joker réelle.
- `tests/test_base_cadran_clefs.py` : heure Joker conservée par les substitutions.
- `tests/test_cadrans_sentinelles_lot3.py` : nouvelles heures/angle Joker et les deux attentes historiques démontrées ci-dessus.
- `tests/test_joker_1056_adoption.py` : quatre tests ciblés d’adoption.
- `tests/test_s7_symetrie_bases.py` : sélection explicite des archives S7 après ajout d’un historique Joker.
- `docs/joker_1056_adoption.md` : ce document.

Les projets locaux déjà modifiés sont préservés et exclus du commit. Une préférence locale est modifiée pendant l’exécution : `config/simulateurAlgo.ini`, `last_project_path`, passe de `BaseCadran.json` à `StyletInitial_solutions.json`. Elle est conservée hors commit ; le chemin de carte reste identique. Cette préférence ne participe pas aux chargements géométriques, qui utilisent les chemins explicites des projets.

Tous les autres fichiers suivis hors de la liste livrée sont comparés à leurs empreintes avant adoption : code des algorithmes, configuration nationale, dataset, villes, carte, anciens rapports et projets restent inchangés. L’entrée précédente du Joker et les historiques S7 sont comparés structurellement à la copie avant modification ; les sept autres références sont identiques dans le JSON et dans le calcul solaire.
