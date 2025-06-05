import configparser
import os

class ConfigGlobale:
    def __init__(self, fichier="config/simulateurAlgo.ini"):
        self.config = configparser.ConfigParser()
        self.chemin = os.path.abspath(fichier)
        self.config.read(self.chemin)

    def getInt(self, section, clé, défaut=0):
        return self.config.getint(section, clé, fallback=défaut)

    def getFloat(self, section, clé, défaut=0.0):
        return self.config.getfloat(section, clé, fallback=défaut)

    def getBool(self, section, clé, défaut=False):
        return self.config.getboolean(section, clé, fallback=défaut)

    def get(self, section, clé, défaut=""):
        return self.config.get(section, clé, fallback=défaut)

    def set(self, section, clé, valeur):
        if section not in self.config:
            self.config[section] = {}
        self.config[section][clé] = str(valeur)

    def save(self):
        with open(self.chemin, "w") as f:
            self.config.write(f)
