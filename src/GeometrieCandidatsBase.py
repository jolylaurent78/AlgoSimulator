"""Candidats des bases : calculs euclidiens en mètres Lambert-93, distances en km."""
from dataclasses import dataclass
from math import atan2, degrees, hypot, isfinite, sqrt


TOL_METRES = 1e-6
TOL_PARALLELES = 1e-12  # Déterminant de directions unitaires, sans seuil géographique.
DEDUP_METRES = .001


def distance(a, b):
    return hypot(a[0]-b[0], a[1]-b[1])


def croix(a, b):
    return a[0]*b[1]-a[1]*b[0]


def soustraire(a, b):
    return a[0]-b[0], a[1]-b[1]


def unitaire(v):
    norme = hypot(*v)
    if not isfinite(norme) or norme == 0:
        raise ValueError("Direction métrique invalide")
    return v[0]/norme, v[1]/norme


@dataclass(frozen=True)
class CercleMetrique:
    centre: tuple
    rayon: float  # mètres

    def __post_init__(self):
        if not all(isfinite(x) for x in (*self.centre, self.rayon)) or self.rayon < 0:
            raise ValueError("Cercle métrique invalide")

    def ecart(self, p):
        return abs(distance(p, self.centre)-self.rayon)/1000


def intersectionsDroiteCercle(origine, direction, cercle):
    if not all(isfinite(x) for x in origine):
        raise ValueError("Origine métrique invalide")
    u = unitaire(direction)
    delta = soustraire(cercle.centre, origine)
    along = delta[0]*u[0]+delta[1]*u[1]
    hauteur = abs(croix(delta, u))
    if hauteur > cercle.rayon + TOL_METRES:
        return []
    pied = (origine[0]+along*u[0], origine[1]+along*u[1])
    racine = sqrt(max(0., (cercle.rayon-hauteur)*(cercle.rayon+hauteur)))
    if racine <= TOL_METRES:
        return [pied]
    return [(pied[0]+s*racine*u[0], pied[1]+s*racine*u[1]) for s in (-1, 1)]


@dataclass
class ResultatCandidatBase:
    a: tuple | None = None
    b: tuple | None = None
    c: tuple | None = None
    ab: float | None = None
    ac: float | None = None
    bc: float | None = None
    segment: str | None = None
    d_min: float | None = None
    m: tuple | None = None
    g: tuple | None = None
    p: tuple | None = None
    angle: float | None = None
    poids: float = 0.
    methode: str = "ponderee"
    contraintes: tuple | None = None
    rejet: str = ""
    partition: int | None = None
    traitement: str = "ponderee"
    cercle_non_secant: str | None = None
    q: tuple | None = None
    distance_aq: float | None = None

    @property
    def accepte(self):
        return self.p is not None and not self.rejet


def pondererTriangleBase(a, b, c=None):
    """Présélection et centre ; aucune exigence d'inclusion des sommets dans 20 km."""
    r = ResultatCandidatBase(a=a, b=b, c=c)
    if not all(isfinite(x) for p in (a,b,c) if p is not None for x in p):
        r.rejet = "coordonnées non finies"
        return r
    r.ab = distance(a,b)/1000
    segments = [(r.ab, 'AB', a, b, c)]
    if c is not None:
        r.ac, r.bc = distance(a,c)/1000, distance(b,c)/1000
        segments += [(r.ac,'AC',a,c,b), (r.bc,'BC',b,c,a)]
    # min() conserve la première occurrence : AB, puis AC, puis BC.
    r.d_min, r.segment, debut, fin, oppose = min(segments, key=lambda s:s[0])
    if r.d_min > 30 + TOL_METRES/1000:
        r.rejet = "distance minimale > 30 km"
        return r
    r.m = tuple((debut[i]+fin[i])/2 for i in (0,1))
    if c is None:
        r.methode = "milieu AB (tangentes indéterminées)"
        r.p = r.m
        return r
    r.g = tuple(a[i]+((b[i]-a[i])+(c[i]-a[i]))/3 for i in (0,1))
    v, w = soustraire(debut,oppose), soustraire(fin,oppose)
    if hypot(*v) <= TOL_METRES or hypot(*w) <= TOL_METRES:
        r.angle = 0.
    else:
        v,w = unitaire(v),unitaire(w)
        r.angle = degrees(atan2(abs(croix(v,w)), v[0]*w[0]+v[1]*w[1]))
    r.poids = min(1., (r.angle/45)**2)
    r.p = tuple(r.m[i]+r.poids*(r.g[i]-r.m[i]) for i in (0,1))
    if not all(isfinite(x) for x in (*r.g,*r.p)):
        r.rejet = "centre non fini"
    return r


def distancesContraintesBase(p, horaire, cercle_distance, origine, direction):
    u = unitaire(direction)
    return (horaire.ecart(p), cercle_distance.ecart(p),
            abs(croix(soustraire(p,origine),u))/1000)


def calculerCandidatBasePondere(a, b, horaire, cercle_distance, origine, direction):
    """Tangentes aux points partition/cercle, puis contrôle des trois contraintes."""
    c = None
    na, nb = soustraire(a,horaire.centre), soustraire(b,cercle_distance.centre)
    if hypot(*na) > TOL_METRES and hypot(*nb) > TOL_METRES:
        na,nb = unitaire(na),unitaire(nb)
        u,v = (-na[1],na[0]),(-nb[1],nb[0])
        det = croix(u,v)
        if abs(det) > TOL_PARALLELES:
            s = croix(soustraire(b,a),v)/det
            possible = (a[0]+s*u[0], a[1]+s*u[1])
            if all(isfinite(x) for x in possible):
                # Vérification des équations des deux tangentes, pas de limite de carte.
                residus = [abs(sum((possible[i]-p[i])*n[i] for i in (0,1)))
                           for p,n in ((a,na),(b,nb))]
                if max(residus) <= TOL_METRES:
                    c = possible
    r = pondererTriangleBase(a,b,c)
    if not r.accepte:
        return r
    r.contraintes = distancesContraintesBase(r.p,horaire,cercle_distance,origine,direction)
    if not all(isfinite(d) and d <= 20 + TOL_METRES/1000 for d in r.contraintes):
        r.rejet = "contrainte finale > 20 km"
    return r


def ecartDroiteCercle(origine, direction, cercle):
    """Distance minimale droite/cercle en km, nulle si la droite est sécante."""
    u = unitaire(direction)
    return max(0.,abs(croix(soustraire(cercle.centre,origine),u))-cercle.rayon)/1000


def calculerSecoursNonSecant(cercle, nom, horaire, cercle_distance, origine, direction):
    """Milieu du plus court trajet cercle/partition, sans tangentes ni sommet C."""
    u = unitaire(direction)
    n = (-u[1],u[0])
    delta = soustraire(cercle.centre,origine)
    signe = delta[0]*n[0]+delta[1]*n[1]
    q = tuple(cercle.centre[i]-signe*n[i] for i in (0,1))
    r = ResultatCandidatBase(methode="secours_non_secant",traitement="secours_non_secant",
                            cercle_non_secant=nom,q=q,segment="AQ")
    if abs(signe) <= cercle.rayon + TOL_METRES:
        r.rejet = "cercle sécant : secours non applicable"
        return r
    a = tuple(cercle.centre[i]-(1 if signe>0 else -1)*cercle.rayon*n[i] for i in (0,1))
    r.a = a
    r.distance_aq = r.d_min = (abs(signe)-cercle.rayon)/1000
    if r.distance_aq > 30 + TOL_METRES/1000:
        r.rejet = "écart AQ > 30 km"
        return r
    r.m = r.p = tuple((a[i]+q[i])/2 for i in (0,1))
    r.contraintes = distancesContraintesBase(r.p,horaire,cercle_distance,origine,direction)
    if not all(isfinite(d) and d <= 20 + TOL_METRES/1000 for d in r.contraintes):
        r.rejet = "contrainte finale > 20 km"
    return r


def chercherCandidatsBasePonderes(horaire, cercle_distance, partitions):
    """Toutes les combinaisons ; diagnostics conservés, doublons retirés du rendu."""
    retenus, diagnostics = [], []

    def enregistrer(r,index):
        r.partition = index
        if r.accepte:
            if any(distance(r.p,g.p) <= DEDUP_METRES for g in retenus):
                r.rejet = "doublon à 1 mm"
            else:
                retenus.append(r)
        diagnostics.append(r)

    for index,(origine,direction) in enumerate(partitions):
        points_a = intersectionsDroiteCercle(origine,direction,horaire)
        points_b = intersectionsDroiteCercle(origine,direction,cercle_distance)
        if not points_a or not points_b:
            for cercle,nom,points in ((horaire,"horaire",points_a),(cercle_distance,"distance",points_b)):
                if not points:
                    enregistrer(calculerSecoursNonSecant(cercle,nom,horaire,cercle_distance,origine,direction),index)
            continue
        for a in points_a:
            for b in points_b:
                r = calculerCandidatBasePondere(a,b,horaire,cercle_distance,origine,direction)
                enregistrer(r,index)
    return retenus,diagnostics
