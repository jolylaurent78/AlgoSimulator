# Cadran Final — Calibration horaire de Lampouy

Correction sur `dev`, à partir de `e53b5cf`, avec la date corrigée demandée : **Lampouy, 19/08/1152 julien**. L’événement du **18/05/1152** identifie toujours la construction ; sa date et les scénarios sont inchangés et ne déterminent pas la date de calibration astronomique.

## Résultats DE406

Les deux heures TML sont résolues séparément par `MoteurSolaireSentinelles.directionPourAzimut()`, avec Skyfield/DE406 et les coordonnées de Lampouy dans `villes_dict` : latitude **48,29361111111112°**, longitude **−2,064722222222222°**.

| Paramètre | Branche directe AM | Branche miroir PM |
|---|---:|---:|
| Azimut cible | 138,5° | 221,5° |
| Azimut DE406 à l’instant résolu | 138,499995263819° | 221,499987095752° |
| Heure moyenne locale | **10:08:10,300735** | **13:53:40,141651** |
| Secondes TML internes | 36490,30073472659 | 50020,141651121776 |
| Label arrondi à la seconde | **10:08:10** | **13:53:40** |

La précision numérique de recherche reste celle du moteur existant : **0,01 seconde**, avec des écarts résiduels d’azimut sous 0,0001°. Les secondes fractionnaires sont conservées dans les calculs. Le test contrôle également le JD de minuit **2142056,5**, correspondant au 19 août 1152 julien.

Les valeurs approximatives Moshier fournies par l’utilisateur étaient 10:08:09 et 13:53:38. Les écarts DE406 sont respectivement **+1,300735 s** et **+2,141651 s** ; aucun calcul Moshier supplémentaire n’est réalisé, aucun ajustement n’est appliqué pour coïncider avec ces estimations.

La formule `86400 − heure AM` donnerait 13:51:49,699265, alors que le miroir astronomique calculé vaut **13:53:40,141651**. Elle n’est pas utilisée dans ce référentiel. L’azimut à **12:00 TML à Lampouy le 19 août** est **179,652826404881°** ; les lignes Lampouy utilisent ce midi de référence dans leurs formules existantes.

## Référence centralisée et identifiant compatible

`src/ReferentielLampouyFinal.py` définit une référence immuable regroupant le contexte, les deux directions solaires et l’azimut à 12:00 TML. Sa date centrale est explicitement **19/08/1152**. Elle ne reçoit ni la date d’événement `dateDataset`, ni une date d’observation du module : une modification de la ville d’observation ou de la date d’observation ne recalibre donc pas Lampouy.

La lumière et les lignes horaires du Cadran Final consomment cette même définition ; leurs champs d’heure, labels et infobulles découlent des valeurs calculées. Le choix sauvegardé **`10:09` demeure un identifiant historique**, proposé pour la construction du 18 mai comme auparavant. Il sélectionne la note L, mais ne remplace plus l’heure astronomique. Une sauvegarde/relecture temporaire confirme que cet identifiant est conservé sans migration et que les heures calculées sont restituées.

Le calcul physique de lumière au lieu et à la date d’observation continue d’utiliser le Soleil de ce lieu et de ce jour, à l’heure TML fixe calibrée à Lampouy. Les ombres Lampouy utilisent les azimuts et le midi du contexte de calibration ; leurs réflexions Endroit/Envers et l’axe du stylet restent traités par les mêmes formules.

Le Final n’appelle plus le Lampouy historique calculé à Carnac le 20/08/1152. Cette ancienne branche est conservée dans les autres algorithmes, conformément au périmètre : aucune modification de `Sentinelle`, `SentinelleNationale`, BaseCadran ou StyletInitial. Les huit références nationales, Joker compris, sont inchangées.

## Rejeu des projets existants

Les **38 scénarios** du projet courant sont chargés et recalculés en mémoire avant/après, sans sauvegarde sur les fichiers utilisateur. Les paramètres et l’empreinte du JSON sont identiques. Les huit références nationales sont comparées structurellement, ainsi que toutes leurs lignes horaires : aucune différence. Tous les centres des scénarios sans L sélectionné sont exactement identiques.

Bilan : **87 → 87 candidats** et **29 → 29 couvertures sur 33 références ponctuelles mesurables**. La transition sans bases reste sans géométrie. Aucun résultat de couverture n’est inventé pour les scénarios sans référence ponctuelle, notamment Zone.

Le seul scénario sélectionnant L dans le projet courant est **Zone**, en ombre. Sa lumière reste C à 09:43:00. Ses ombres passent de 10:09 / 13:51 à **10:08:10 / 13:53:40**. Il conserve deux candidats, dont les centres évoluent :

| Centre | Avant (m Lambert-93) | Après (m Lambert-93) |
|---|---|---|
| 1 | (510442,485 ; 6736246,032) | (509539,224 ; 6734805,546) |
| 2 | (730731,656 ; 6804958,337) | (730148,849 ; 6805086,172) |

Les lignes L disponibles dans les autres scénarios du même événement affichent aussi les nouvelles heures, sans devenir candidates lorsque L n’est pas sélectionné. Le jeu courant ne contient pas de lumière sélectionnée L : ce chemin est couvert par les tests directs AM/PM, avec vérification heure/azimut à Lampouy et changement de lieu et de date d’observation.

## Tests

- **136 tests ciblés réussis en 57,49 s**, après correction au 19 août :

```text
python -m pytest tests/test_lampouy_final.py tests/test_cadran_final_midi_local.py tests/test_algorithme_cadran_final.py tests/test_cadran_national_lot2.py tests/test_sentinelle.py -q --tb=short
```

- **9 cas Lampouy réussis en 31,94 s**, après ajout du contrôle explicite du calendrier julien :

```text
python -m pytest tests/test_lampouy_final.py tests/test_cadrans_sentinelles_lot3.py -k lampouy -q --tb=short
```

- Les sept nouveaux cas vérifient l’alignement horaire/azimut AM et PM par recalcul direct, les secondes fractionnaires, l’absence de symétrie 24 h, la stabilité du référentiel fixe, la conservation des huit références nationales, l’indépendance à l’observation, les labels/infobulles et la sauvegarde/relecture temporaire du choix historique `10:09`.
- Les deux cas existants d’ombres Lampouy Endroit/Envers et les deux cas du lot 3 sont adaptés à la date corrigée. Les assertions du lot 3 concernant BaseCadran restent historiques et inchangées ; seules celles du Final consomment la nouvelle calibration.
- Les autres tests historiques de Lampouy restent inchangés et font partie des vérifications ciblées.

Suite complète sur la date corrigée : **1044 réussites, 2 échecs en 348,07 s**, commande `python -m pytest -q --tb=short`.

- `test_interface_propose_les_nouveaux_choix_sans_lancer_de_recherche` : erreur d’initialisation Tcl (`init.tcl`) dans le passage complet ; **rejeu isolé réussi en 3,16 s**, sans modification de Segment ou de l’interface.
- `test_bases_reelles_conservent_les_criteres_geometriques` : écart préexistant sur Carignan, deux candidats historiques contre zéro attendu. Le même écart est reproduit avec la fonction golden du commit de départ, les algorithmes Base et les données étant inchangés. Aucun golden sans rapport avec Lampouy n’est réécrit. La suite complète n’est donc pas annoncée intégralement verte.

## Fichiers et préservation

- `src/ReferentielLampouyFinal.py` : définition centrale réservée au Final, au 19 août 1152.
- `src/AlgorithmeCadranFinal.py` : consommation des références, identifiant compatible, labels et infobulles.
- `tests/test_lampouy_final.py` : sept nouveaux cas.
- `tests/test_cadran_final_midi_local.py` : deux cas existants adaptés.
- `tests/test_cadrans_sentinelles_lot3.py` : adaptation des deux cas Final, maintien des assertions BaseCadran.
- `docs/lampouy_final_calibration_horaire.md` : ce rapport.

Les modifications locales préexistantes sont conservées hors du commit : préférence `config/simulateurAlgo.ini` et ligne vide ajoutée avant `StyletLumiere` dans `src/AlgorithmeCadranFinal.py`. La version commitée du source exclut uniquement cette ligne vide utilisateur ; son code est identique au code testé. Les autres fichiers suivis sont contrôlés contre leurs empreintes initiales : aucun dataset, projet, calendrier musical, référentiel national, donnée historique, calibration cartographique ou autre algorithme n’est modifié. Aucun cache persistant n’est ajouté ou invalidé.
