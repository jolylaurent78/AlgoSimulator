# Projections pour la recherche des années Segment

Dans **Recherche de l'année**, choisir la projection et la tolérance puis
cliquer sur **Rechercher les années**. Les nouveaux calculs utilisent par défaut
**Écliptique J2000** et **2,5°**. Les tolérances proposées sont **2,5°** et **5°** ;
le choix **Équatorial** conserve l'ancienne projection. Le tableau des années
candidates garde ses colonnes.

## Calcul

- **Équatorial** : calcul historique Skyfield `sun.at(t).observe(astre)`, projeté
  sur le plan XY équatorial ICRF, conservé y compris son temps de lumière.
- **Écliptique J2000** : vecteur géométrique `(astre - sun).at(t)` au même instant,
  transformé par `frame_xyz(ecliptic_J2000_frame)` puis projeté sur XY.
  Ce repère est fixe : `ecliptic_frame`, qui dépend de la date, n'est pas utilisé.

Dans chaque projection, l'origine 0° est la direction projetée Soleil–Terre à
l'équinoxe de printemps de l'année examinée. La détermination annuelle existante
de l'équinoxe et la convention de temps UT1 sont conservées. Le plan reste J2000
même si l'origine angulaire est redéfinie chaque année.

La même projection sert à rechercher le passage terrestre et à calculer l'azimut
planétaire. Les directions terrestres directe/opposée et les deux orientations
de l'angle du segment sont conservées. Comparaisons, recherche de date et erreur
affichée utilisent la distance angulaire circulaire.

Les fonctions astronomiques gardent par défaut le mode équatorial pour leurs
autres appelants. `azimutHeliocentriqueJ2000()` reste le calcul équatorial absolu
historique ; son nom ne désigne pas une projection écliptique.

Références Skyfield : [repères](https://rhodesmill.org/skyfield/api-framelib.html),
[positions et transformations](https://rhodesmill.org/skyfield/api-position.html).

## Contrôle ponctuel DE406 / Skyfield 1.51

Géométrie de la fixture de Guérande, année 1365, Uranus, angle complémentaire,
direction terrestre opposée 53,24° :

| Projection | Date terrestre (calendrier du projet, UT1) | Azimut Uranus | Erreur |
| --- | --- | --- | --- |
| Équatorial | 07/05/1365 15:00 | 283,22° | 3,51° |
| Écliptique J2000 | 06/05/1365 03:00 | 280,79° | 1,07° |

Avec 2,5°, seule la seconde ligne est candidate ; avec l'ancien réglage
équatorial/4°, la première est conservée. Ces dates utilisent la précision
historique de recherche de six heures. Le contrôle n'altère ni la fixture ni
les scénarios. Les résultats exploratoires Swiss Ephemeris/Moshier n'étant pas
fournis, aucune correspondance chiffrée avec eux n'est affirmée.

Aucun recalcul global, migration ou mécanisme d'invalidation des caches n'est
ajouté. Les listes existantes restent affichées jusqu'à une recherche manuelle.
Le recalcul des projets et la mise à jour des scénarios restent à la charge
de l'utilisateur.
