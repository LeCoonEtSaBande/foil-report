# === Configuration du projet Windguru Scraper ===
# 
# Ce fichier permet de configurer facilement :
# 1. Les sites à surveiller
# 2. Les critères de vent pour chaque site
# 3. Les paramètres de scraping
#
# Pour ajouter un nouveau site :
# 1. Ajoutez son ID dans la liste SITES
# 2. Ajoutez ses critères dans SITE_CRITERIA
# 3. Relancez le scraper

import os

# === Chemins relatifs ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# === Chemins des fichiers ===
DRIVER_PATH = os.path.join(PROJECT_ROOT, "Drivers", "geckodriver.exe")
CSV_FOLDER = os.path.join(PROJECT_ROOT, "Donnees_Temporaires")

# === Configuration Firefox ===
FIREFOX_PATH = r"C:\Program Files\Mozilla Firefox\firefox.exe"

# === Configuration du scraping ===
HEADLESS_MODE = True  # True = mode sans interface, False = avec interface
WAIT_TIME = 5  # Temps d'attente en secondes pour le chargement des pages
PAUSE_BETWEEN_SITES = 1  # Pause entre les sites en secondes
JS_WAIT_TIME = 0.5  # Temps d'attente pour le JavaScript

# === SITES À SURVEILLER ===
# 
# Ajoutez ici les IDs des sites Windguru que vous voulez surveiller.
# Pour trouver l'ID d'un site :
# 1. Allez sur windguru.cz
# 2. Cherchez votre spot
# 3. L'ID est dans l'URL (ex: windguru.cz/station/72305)
#
SITES = [
    72305,  # Le Grand Large à Lyon
    193,    # Chasse sur Rhône
    314,    # Le Lac du Monteynard
    28061,  # Le Lac du Bourget
    179,    # Le Lac Leman
    14,     # L'Almanarre
]

# === CRITÈRES DE VENT PAR SITE ===
#
# Pour chaque site, définissez :
# - "direction" : plages de directions favorables [(min1, max1), (min2, max2)]
# - "vent_moyen" : seuil minimum pour considérer le vent comme "moyen"
# - "vent_bien" : seuil pour considérer le vent comme "bon"
# - "vent_tres_bien" : seuil pour considérer le vent comme "très bon"
#
SITE_CRITERIA = {
    # === SITE 72305 - Le Grand Large à Lyon ===
    72305: {
        "direction": [(320, 40), (140, 220)],  # Nord-Ouest à Nord-Est OU Sud-Est à Sud-Ouest
        "vent_moyen": 9,
        "vent_bien": 11,
        "vent_tres_bien": 15
    },
    # === SITE 193 - Chasse sur Rhône ===
    193: {
        "direction": [ (140, 220)],  # Sud-Est à Sud-Ouest
        "vent_moyen": 12,
        "vent_bien": 15,
        "vent_tres_bien": 18
    },
        # === SITE 314 - Le Lac du Monteynard ===
    314: {
        "direction": [(320, 40), (140, 220)],  # Nord-Ouest à Nord-Est OU Sud-Est à Sud-Ouest
        "vent_moyen": 9,
        "vent_bien": 12,
        "vent_tres_bien": 15
    },
    # === SITE 28061 - Le Lac du Bourget ===
    28061: {
        "direction": [(320, 40), (140, 220)],  # Nord-Ouest à Nord-Est OU Sud-Est à Sud-Ouest
        "vent_moyen": 12,
        "vent_bien": 15,
        "vent_tres_bien": 18
    },
    # === SITE 179 - Le Lac Leman ===
    179: {
        "direction": [(320, 40)],  # Nord-Ouest à Nord-Est
        "vent_moyen": 14,           # 14 nœuds minimum
        "vent_bien": 17,            # 17 nœuds pour "bon"
        "vent_tres_bien": 20        # 20 nœuds pour "très bon"
    },
    # === SITE 14 - L'Almanarre ===
    14: {
        "direction": [(50, 130), (230, 310)],  # Vent d'Est ou vent d'Ouest
        "vent_moyen": 9,
        "vent_bien": 11,
        "vent_tres_bien": 15
    },
}

# === Format des fichiers CSV ===
CSV_DELIMITER = ';'  # Séparateur de colonnes : '\t' (TSV), ',' (CSV), ';' (CSV européen)
CSV_ENCODING = 'utf-8'  # Encodage des fichiers
