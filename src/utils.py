import os
import sys

def cheminRelatif(relatif):
    """
    Renvoie le chemin absolu vers un fichier/dossier embarqué,
    compatible avec PyInstaller (--onefile).
    """
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS  # mode exécutable packagé
    else:
        base = os.path.abspath(".")  # mode script standard
    return os.path.join(base, relatif)
