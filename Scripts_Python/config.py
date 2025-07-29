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
import re

# === Chemins relatifs ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# === Chemins des fichiers ===
DRIVER_PATH = os.path.join(PROJECT_ROOT, "Drivers", "geckodriver.exe")
CSV_FOLDER = os.path.join(PROJECT_ROOT, "Donnees_Temporaires")
# === Format des fichiers CSV ===
CSV_DELIMITER = ';'  # Séparateur de colonnes : '\t' (TSV), ',' (CSV), ';' (CSV européen)
CSV_ENCODING = 'utf-8'  # Encodage des fichiers

# === Configuration Firefox ===
FIREFOX_PATH = r"C:\Program Files\Mozilla Firefox\firefox.exe"

# === Configuration du scraping ===
HEADLESS_MODE = True  # True = mode sans interface, False = avec interface
WAIT_TIME = 8  # Temps d'attente en secondes pour le chargement des pages
JS_WAIT_TIME = 2  # Temps d'attente pour le JavaScript

# === SITES À SURVEILLER ===
# 
# Ajoutez ici les IDs des sites Windguru que vous voulez surveiller.
# Pour trouver l'ID d'un site :
# 1. Allez sur windguru.cz
# 2. Cherchez votre spot
# 3. L'ID est dans l'URL (ex: windguru.cz/station/72305)
#
# Pour chaque site, définissez :
# - "nom" : nom qui sera affiché
# - "direction" : plages de directions du vent favorables [(min1, max1), (min2, max2)]
# - "vent_moyen" : seuil minimum pour considérer le vent comme "moyen"
# - "vent_bien" : seuil pour considérer le vent comme "bon"
# - "vent_tres_bien" : seuil pour considérer le vent comme "très bon"
# - "balise_url"
# - "webcam_url"

SITES_CRITERIA = {
    72305: {  # Le Grand Large à Lyon
        "nom": "Le Grand Large",
        "direction": [(320, 40), (140, 220)],
        "vent_moyen": 9,
        "vent_bien": 11,
        "vent_tres_bien": 15,
        "balise_url": "https://m.winds-up.com/index.php?p=spot&id=138",
        "webcam_url": ""
    },
    193: {  # Chasse sur Rhône
        "nom": "Chasse sur Rhône",
        "direction": [(140, 220)],
        "vent_moyen": 12,
        "vent_bien": 15,
        "vent_tres_bien": 18,
        "balise_url": "",
        "webcam_url": ""
    },
    2020: {  # Porte les Valence
        "nom": "Porte les Valence",
        "direction": [(140, 220)],
        "vent_moyen": 12,
        "vent_bien": 15,
        "vent_tres_bien": 18,
        "balise_url": "",
        "webcam_url": ""
    },
    314: {  # Le Lac du Monteynard
        "nom": "Lac du Monteynard",
        "direction": [(320, 40), (140, 220)],
        "vent_moyen": 9,
        "vent_bien": 12,
        "vent_tres_bien": 15,
        "balise_url": "https://m.winds-up.com/index.php?p=spot&id=36",
        "webcam_url": "https://www.onekite.com/webcam-monteynard"
    },
    8248: {  # Lac de Laffrey
        "nom": "Lac de Laffrey",
        "direction": [(140, 220)],
        "vent_moyen": 12,
        "vent_bien": 15,
        "vent_tres_bien": 18,
        "balise_url": "",
        "webcam_url": ""
    },
    28061: {  # Le Lac du Bourget
        "nom": "Lac du Bourget",
        "direction": [(320, 40), (140, 220)],
        "vent_moyen": 12,
        "vent_bien": 15,
        "vent_tres_bien": 18,
        "balise_url": "https://balisemeteo.com/balise.php?idBalise=2456",
        "webcam_url": "https://www.skaping.com/grandlac/grandport"
    },
    179: {  # Le Lac Léman
        "nom": "Sciez/Excenevex",
        "direction": [(340, 60), (185, 265)],
        "vent_moyen": 14,
        "vent_bien": 17,
        "vent_tres_bien": 20,
        "balise_url": "http://meteo-sciez.fr/site/mesure_vent.php",
        "webcam_url": "https://www.skaping.com/excenevex/plage"
    },
    14: {  # L'Almanarre
        "nom": "L'Almanarre",
        "direction": [(50, 130), (230, 310)],
        "vent_moyen": 10,
        "vent_bien": 15,
        "vent_tres_bien": 20,
        "balise_url": "https://m.winds-up.com/index.php?p=spot&id=2",
        "webcam_url": "https://hyeres.fr/webcams/"
    }
    824: {  # Brutal beach
        "nom": "Six-Four brutal beach",
        "direction": [(225, 330)],
        "vent_moyen": 10,
        "vent_bien": 15,
        "vent_tres_bien": 20,
        "balise_url": "https://m.winds-up.com/index.php?p=spot&id=86",
        "webcam_url": "https://m.winds-up.com/index.php?p=spot&id=49&cat=webcam"
    }
}

def getSiteCriteria(site_id):
    return SITES_CRITERIA.get(site_id, None)

def getSitesID():
    return list(SITES_CRITERIA.keys())

def is_valid_url(url):
    return url == "" or re.match(r'^https?://', url)

def validate_sites_criteria():
    # site id sont des entiers?
    
    for site_id in SITES_CRITERIA.keys():
        if not isinstance(site_id, int) or site_id <= 0:
            raise ValueError(f"Clé invalide : {site_id}. Les identifiants doivent être des entiers strictement positifs.")

    for site_id, data in SITES_CRITERIA.items():
        # Vérification du nom
        nom = data.get("nom")
        if not isinstance(nom, str) or not nom.strip():
            raise ValueError(f"Site {site_id} : 'nom' invalide ou vide.")

        # Vérification des valeurs de vent
        for key in ["vent_moyen", "vent_bien", "vent_tres_bien"]:
            val = data.get(key)
            if not isinstance(val, int) or val <= 0:
                raise ValueError(f"Site {site_id} ({nom}) : '{key}' doit être un entier positif. Valeur : {val}")

        # Vérification des URLs
        for url_key in ["balise_url", "webcam_url"]:
            url_val = data.get(url_key)
            if not isinstance(url_val, str) or not is_valid_url(url_val):
                raise ValueError(f"Site {site_id} ({nom}) : '{url_key}' doit être une URL valide ou une chaîne vide.")

