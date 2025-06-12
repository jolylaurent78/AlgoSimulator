import cv2
import numpy as np
import threading
import sqlite3
import queue
import os
import tkinter as tk
import math
from tkinter import filedialog

# Base de données des villes
from src.data_loader import villes_dict

# Affichage des objects graphiques
from src.affichage_objets import ObjetGraphique, PointGraphique, COULEURS, SymboleWiki

# Gestion des coordonnées / projection
from src.carte_config import carteConfig

# Gestion des variables globales de l'affichge pan, zoom...'
from src.configGlobale import ConfigGlobale

# Gestion des layers graphiques
from src.layerManager import Layer, LayerManager


DISTANCE_SELECTION_PIXELS = 5





class ListePOIs:
    def __init__(self, canvas, chemin_bd: str, interface):
        self.chemin_bd = chemin_bd
        self.interface = interface

        # Lecture des paramètres depuis le fichier INI
        cfg = ConfigGlobale()
        self.nombre_max = cfg.getInt("Wikipedia", "nbMaxObjetsAffiche", 200)
        self.zoom_seuil_diagonale = cfg.getInt("Wikipedia", "zoomSeuilDiagonale", 300_000)
        self.icone_par_defaut = cfg.get("Wikipedia", "iconeParDefaut", "images/defaut.png")
        self.taille_symbole = cfg.getInt("Wikipedia", "tailleSymbole", 3)

        # Layer interne (non enregistré dans le layerManager)
        self.layer = Layer("POIs Wikipedia", couleur=(0, 128, 255), epaisseur = self.taille_symbole, visible=False)
        self.canvas = canvas

        self.queue_resultats = queue.Queue()
        self.thread_courant = None
        self.categories_visibles = set()


    def chargerAsync(self, bbox: tuple[float, float, float, float], zoom: float):
        """
        Lance un thread pour charger les POIs depuis la base, en fonction de la bbox affichée.
        """
        if self.thread_courant and self.thread_courant.is_alive():
            return  # Un thread est déjà actif : on ne relance pas

        xmin, ymin, xmax, ymax = bbox
        pertinence = (self.interface.varPOIPertinence.get() or "").lower()
        categorie = (self.interface.varPOICategorie.get() or "").lower()
        sujet = (self.interface.varPOISujet.get() or "").lower()

        def worker(pertinence: str, categorie: str, sujet: str, zoom_val: float):
            conn = sqlite3.connect(self.chemin_bd)
            cursor = conn.cursor()

            # Conditions dynamiques de filtrage
            conditions = ["lambert_x BETWEEN ? AND ?", "lambert_y BETWEEN ? AND ?"]
            params = [xmin, xmax, ymin, ymax]

            # condition dynamique si le filtrage par catégorie est actif
            if not ("toute" in categorie or "toutes" in categorie):
                conditions.append("P31Categorie.visible = 1")

            # Condition dynamique si le filtrage par sujet est actif
            if sujet and sujet != "tous":
                conditions.append("source_backlink = ?")
                params.append(self.interface.varPOISujet.get())

            # Si le zoom est trop large, on ne garde que les POIs croisés
            diagonale =((xmax - xmin) ** 2 + (ymax - ymin) ** 2) ** 0.5
            if diagonale > self.zoom_seuil_diagonale:
                conditions.append("crossReference = 2")
            elif diagonale > self.zoom_seuil_diagonale / 2:
                if pertinence == "elevée":
                    conditions.append("crossReference = 2")
                else:
                    conditions.append("crossReference IN (1,2)")
            else:
                if pertinence == "faible":
                    conditions.append("crossReference >= 0")
                elif pertinence == "moyenne":
                    conditions.append("crossReference >= 1")
                else:
                    conditions.append("crossReference = 2")


            sql = f"""
                SELECT qid, titre, source_backlink, summary, lambert_x, lambert_y, icone, url
                FROM EntreeHistorique
                JOIN P31Classification USING(p31)
                JOIN P31Categorie ON P31Classification.categorie = P31Categorie.nom
                WHERE {' AND '.join(conditions)}
                ORDER BY notoriete DESC
                LIMIT {self.nombre_max}
            """

            cursor.execute(sql, params)
            lignes = cursor.fetchall()
            conn.close()

            objets = []
            positions = []  # (x_l93, y_l93) des POIs retenus

            for qid, titre, source_backlink, summary, x_l93, y_l93, icone, url in lignes:
                # On regarde d'abord si le POI est déjà proche d'un autre
                px, py = carteConfig.lambert93_to_pixels(x_l93, y_l93)
                x2_l93, y2_l93 = carteConfig.pixels_to_lambert93(px + 1, py)
                metres_par_pixel = math.hypot(x2_l93 - x_l93, y2_l93 - y_l93)
                distance_seuil = metres_par_pixel * 16 / zoom_val

                skip = False
                for sx, sy in positions:
                    if math.hypot(x_l93 - sx, y_l93 - sy) < distance_seuil:
                        skip = True
                        break
                if skip:
                    continue

                tooltips = [source_backlink, url, summary]
                icone = icone if icone is not None else self.icone_par_defaut
                icone_path = os.path.join("images", icone)
                if not os.path.exists(icone_path):
                    icone_path = os.path.join("images", self.icone_par_defaut)
                objets.append(
                    SymboleWiki(
                        url,
                        x_l93,
                        y_l93,
                        icone_path=icone_path,
                        nom=titre,
                        layer=self.layer,
                        tooltips=tooltips,
                    )
                )
                positions.append((x_l93, y_l93))

            self.layer.supprimerTousObjets()
            self.layer.inclureObjetDansLayer(objets)
            self.canvas.after(0, self._afficherPOIs)

        self.thread_courant = threading.Thread(target=worker, args=(pertinence, categorie, sujet, zoom), daemon=True)
        self.thread_courant.start()

    def _afficherPOIs(self):
        self.interface._refresh_images(afficherPOIsUniquement = True )

def clamp_pan(crop_w, crop_h):
    global pan_x, pan_y

    (w_img, h_img) = carteConfig.image_size
    pan_x = min(max(pan_x, 0), w_img - crop_w)
    pan_y = min(max(pan_y, 0), h_img - crop_h)


def set_globals(pan_x_val=None, pan_y_val=None, zoom_factor_val=None):
    global pan_x, pan_y, zoom_factor
    if zoom_factor_val is not None:
        zoom_factor = max(min(zoom_factor_val, max_zoom), min_zoom)
    if pan_x_val is not None:
        pan_x = int(pan_x_val)
    if pan_y_val is not None:
        pan_y = int(pan_y_val)


def transformer_affichage_pixel(px, py):
    """
    Transforme les coordonnées (px, py) d’un point en pixels image absolus
    en coordonnées (x, y) en pixels écran (dans la fenêtre d’affichage),
    en tenant compte du zoom, du pan, du centrage (bord gris éventuel),
    et du ratio d’aspect.
    """

    (w_img, h_img) = carteConfig.image_size
    # Taille de l’image affichée en pixels image (après zoom, mais limitée à l’image réelle)
    souhaiteAfficher_w = frame_width / zoom_factor
    souhaiteAfficher_h = frame_height / zoom_factor

    tailleImageRelative_w = min(w_img, souhaiteAfficher_w)
    tailleImageRelative_h = min(h_img, souhaiteAfficher_h)

    # Position absolue (image) du coin haut gauche de la portion affichée
    x0 = min(max(0, pan_x), max(0, w_img - tailleImageRelative_w))
    y0 = min(max(0, pan_y), max(0, h_img - tailleImageRelative_h))

    # Position relative du point dans la zone affichée
    rel_x = (px - x0) / tailleImageRelative_w
    rel_y = (py - y0) / tailleImageRelative_h

    # Taille réelle de l’image affichée dans la fenêtre (en pixels écran)
    tailleImageAffichee_w = int(tailleImageRelative_w * zoom_factor)
    tailleImageAffichee_h = int(tailleImageRelative_h * zoom_factor)

    # Décalage (centrage éventuel) dans la fenêtre
    origineImageDansFenetre_x = max((frame_width - tailleImageAffichee_w) // 2, 0)
    origineImageDansFenetre_y = max((frame_height - tailleImageAffichee_h) // 2, 0)

    # Position finale du point à l’écran
    final_x = int(rel_x * tailleImageAffichee_w + origineImageDansFenetre_x)
    final_y = int(rel_y * tailleImageAffichee_h + origineImageDansFenetre_y)

    return final_x, final_y


def transformer_pixel_affichage_vers_image(x_ecran, y_ecran):
    """
    Transforme les coordonnées (x, y) écran (fenêtre affichée)
    en coordonnées image absolues (pixels de l’image source),
    en tenant compte du zoom, pan, centrage, bords gris, etc.
    """
    (w_img, h_img) = carteConfig.image_size

    # Taille de l’image affichée en pixels image (après zoom)
    souhaiteAfficher_w = frame_width / zoom_factor
    souhaiteAfficher_h = frame_height / zoom_factor

    tailleImageRelative_w = min(w_img, souhaiteAfficher_w)
    tailleImageRelative_h = min(h_img, souhaiteAfficher_h)

    # Taille réelle de l’image affichée dans la fenêtre (en pixels écran)
    tailleImageAffichee_w = int(tailleImageRelative_w * zoom_factor)
    tailleImageAffichee_h = int(tailleImageRelative_h * zoom_factor)

    # Décalage (centrage éventuel) dans la fenêtre
    origineImageDansFenetre_x = max((frame_width - tailleImageAffichee_w) // 2, 0)
    origineImageDansFenetre_y = max((frame_height - tailleImageAffichee_h) // 2, 0)

    # Position relative dans l’image affichée (0..1)
    rel_x = (x_ecran - origineImageDansFenetre_x) / tailleImageAffichee_w
    rel_y = (y_ecran - origineImageDansFenetre_y) / tailleImageAffichee_h

    if not (0 <= rel_x <= 1 and 0 <= rel_y <= 1):
        return None, None  # hors zone affichée

    # Coordonnées pixels absolues dans l’image source
    tailleImageRelative_w = min(w_img, souhaiteAfficher_w)
    tailleImageRelative_h = min(h_img, souhaiteAfficher_h)

    x0 = min(max(0, pan_x), max(0, w_img - tailleImageRelative_w))
    y0 = min(max(0, pan_y), max(0, h_img - tailleImageRelative_h))

    px = x0 + rel_x * tailleImageRelative_w
    py = y0 + rel_y * tailleImageRelative_h

    return px, py


def display(layerManager:LayerManager, listePOIs:ListePOIs, retourner_image=False, afficherPOIsUniquement=False):
    global pan_x, pan_y, zoom_factor, canvasDisplay


    # Dans le cas de base, on crée un canvas.. mais pour afficher les POIs, on le réutilise
    if not afficherPOIsUniquement:
        w_img, h_img = carteConfig.image_size
        crop_w = int(frame_width / zoom_factor)
        crop_h = int(frame_height / zoom_factor)

        pan_x = min(max(pan_x, 0), max(0, w_img - crop_w))
        pan_y = min(max(pan_y, 0), max(0, h_img - crop_h))

        x1 = max(0, pan_x)
        y1 = max(0, pan_y)
        x2 = min(pan_x + crop_w, w_img)
        y2 = min(pan_y + crop_h, h_img)

        cropped = carteConfig.img[y1:y2, x1:x2]
        target_w = int((x2 - x1) * zoom_factor)
        target_h = int((y2 - y1) * zoom_factor)
        resized = cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_AREA)

        canvas = np.full((frame_height, frame_width, 3), 230, dtype=np.uint8)
        offset_x = max(0, (frame_width - target_w) // 2)
        offset_y = max(0, (frame_height - target_h) // 2)
        canvas[offset_y:offset_y + target_h, offset_x:offset_x + target_w] = resized

        canvasDisplay = canvas  # ← stocké globalement

        # On lance un thread pour calculer en parallèle la liste des POIs à afficher
        if (listePOIs.layer.estVisible() == True):
            x1_l93, y1_l93 = carteConfig.pixels_to_lambert93(x1, y1)
            x2_l93, y2_l93 = carteConfig.pixels_to_lambert93(x2, y2)
            # Correction du sens Y (axe inversé écran vs Lambert)
            xmin = min(x1_l93, x2_l93)
            xmax = max(x1_l93, x2_l93)
            ymin = min(y1_l93, y2_l93)
            ymax = max(y1_l93, y2_l93)
            bbox = (xmin, ymin, xmax, ymax)
            listePOIs.chargerAsync(bbox, zoom=zoom_factor)

    #On affiche la liste des objets graphiques associés aux Algorithmes dans
    if afficherPOIsUniquement == False:
        for obj in layerManager.getListeObjetsGraphiquesVisible():
            obj.afficher(canvas, transformer_affichage_pixel)
    else:
    # On affiche les POIs si dispo sur le canvas déjà initialisé.
        for obj in listePOIs.layer.getListeObjetsGraphiques():
            obj.afficher(canvasDisplay, transformer_affichage_pixel)

    if retourner_image:
        return canvasDisplay
    else:
        cv2.imshow("Carte", canvasDisplay)


def get_distance_selection_pixels():
    """
    Distance de sélection tolérée, en pixels image absolus.
    Elle dépend du niveau de zoom : plus on est dézoomé, plus la tolérance est grande.
    """
    base_distance_ecran = 5  # en pixels écran, fixe

    # Convertit cette distance en pixels image
    return base_distance_ecran / zoom_factor



def selectionVille(x_pix: float, y_pix: float) -> PointGraphique | None:
    """
    Recherche la ville la plus proche du clic (en pixels image),
    et retourne un PointGraphique si une ville est trouvée dans la tolérance.

    :param x_pix: position X du clic (pixels image)
    :param y_pix: position Y du clic (pixels image)
    :param layerManager: inutilisé ici mais cohérent avec selectionObjet
    :return: PointGraphique correspondant à une ville, ou None
    """
    tolérance = get_distance_selection_pixels()
    candidats = []

    for ville in villes_dict.values():
        pointVille = PointGraphique(ville.nom, *ville.coordonneesLambert())
        d = pointVille.distanceDepuis(x_pix, y_pix)
        if d <= tolérance:
            candidats.append((d, pointVille))

    if not candidats:
        return None

    candidats.sort(key=lambda t: t[0])
    return candidats[0][1]


def selectionObjet(x_pix: float, y_pix: float, layerManager:LayerManager, typeObjetCible = None, layerPOIs = None) -> "ObjetGraphique | None":
    tolérance = get_distance_selection_pixels()
    candidats = []

    for obj in layerManager.getListeObjetsGraphiquesVisible():
        if typeObjetCible and not isinstance(obj, typeObjetCible):
            continue  # ⛔ Exclu car type différent

        try:
            d = obj.distanceDepuis(x_pix, y_pix)
            if d <= tolérance:
                candidats.append((d, obj))
        except NotImplementedError:
            continue

    if layerPOIs is not None:
         for obj in layerPOIs.getListeObjetsGraphiques():
            d = obj.distanceDepuis(x_pix, y_pix)
            if d <= tolérance:
                candidats.append((d, obj))

    if not candidats:
        return None

    candidats.sort(key=lambda t: t[0])
    return candidats[0][1]



def sauvegarder_carte_complete(filepath="sauvegarde.png"):

    # Copie de l'image complète d’origine
    carte_complete = carteConfig.img.copy()

    # Fonction d'affichage sans zoom ni pan (pixels bruts)
    def transformer_complet(x, y):
        return x, y

    # Dessin des objets
    for obj in layerManager.getListeObjetsGraphiques():
        obj.afficher(carte_complete, transformer_complet)

    # Enregistrement
    success = cv2.imwrite(filepath, carte_complete)
    if success:
        print(f"✅ Carte complète enregistrée dans : {filepath}")
    else:
        print("❌ Échec de la sauvegarde.")


# === Chargement carte et initialisation ===
zoom_factor = 1.0
min_zoom = 0.2
max_zoom = 10.0
pan_x, pan_y = 0, 0
dragging = False
prev_mouse = None
canvasDisplay = None
frame_width, frame_height = 1920, 1080


mode_actif = None
