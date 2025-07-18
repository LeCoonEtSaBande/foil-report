"""
Windguru CSV Scraper - Extracteur de données météorologiques Windguru

Ce script scrape les données météorologiques de Windguru pour les sites configurés
et les sauvegarde au format CSV. Il utilise Selenium avec Firefox pour extraire
les données des modèles AROME et WG (WeatherGuru).

FONCTIONNALITÉS PRINCIPALES :
- Scraping parallèle avec onglets multiples
- Extraction des données AROME et WG
- Gestion des timezones (GitHub Actions + local)
- Sauvegarde au format CSV européen
- Logging détaillé des opérations

ARCHITECTURE :
- Scraping parallèle avec ThreadPoolExecutor
- Extraction des tables HTML avec BeautifulSoup
- Gestion centralisée des dates/heures
- Synchronisation des threads avec verrous

Auteur: [Votre nom]
Version: 2.0.0
Date: 2024
"""

import os
import time
import csv
from datetime import datetime
import pytz
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup, Tag
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

# === Import de la configuration ===
from config import *
from logger import init_logger, get_logger

# === Verrou global pour synchroniser l'accès au driver ===
driver_lock = threading.Lock()

# === Options du navigateur ===
options = Options()
# Ne définir binary_location que si on n'utilise pas Selenium Manager
if DRIVER_PATH is not None:
    options.binary_location = FIREFOX_PATH
if HEADLESS_MODE:
    options.add_argument("--headless")

# Optimisations de performance pour Firefox
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-web-security")
options.add_argument("--disable-features=VizDisplayCompositor")

def extract_table_data(table, model_name, update_time):
    """
    Extrait les données d'une table de prévisions Windguru.
    
    Cette fonction parse une table HTML de Windguru et extrait :
    - Heures de prévision
    - Vitesse du vent et rafales
    - Direction du vent (avec correction d'angle)
    - Température
    - Couverture nuageuse (3 niveaux)
    - Précipitations
    
    ARGUMENTS :
    - table : Objet BeautifulSoup de la table
    - model_name : Nom du modèle (AROME/WG)
    - update_time : Heure de mise à jour
    
    RETOURNE :
    - Dict structuré avec toutes les données ou None si erreur
    """
    if not table or not isinstance(table, Tag):
        return None
    
    # Gestion d'une table vide ou anormale
    rows = table.find_all("tr")
    if len(rows) < 7:
        return None
    
    # Gestion d'une table contenant un modele de prevision de vague (3 lignes de plus entre direction et temperature)
    offset = 0
    if len(rows) >= 9:
        offset = 3
    
    # Extraction des données de base
    heures_raw = [td.get_text(strip=True) for td in rows[0].find_all("td")]  # type: ignore
    
    # Les heures sont déjà en heure locale sur Windguru, pas besoin de conversion
    heures = heures_raw
    vent = [td.text.strip() for td in rows[1].find_all("td")]  # type: ignore
    rafales = [td.text.strip() for td in rows[2].find_all("td")]  # type: ignore
    
    # Extraction de la direction avec correction pour AROME
    # Les flèches SVG sont orientées différemment selon le modèle
    direction = []
    for g in rows[3].find_all("g"):  # type: ignore
        transform = g.get("transform", "")  # type: ignore
        if transform and "rotate(" in transform:
            angle = transform.split("rotate(")[-1].split(",")[0]  # type: ignore
            try:
                corrected_angle = float(angle) - 180  # Correction d'orientation
                direction.append(str(int(corrected_angle)))
            except ValueError:
                direction.append(angle)
        else:
            direction.append("")
    
    # Extraction des autres données
    temp = [td.text.strip() for td in rows[4 + offset].find_all("td")]  # type: ignore
    cloud_cells = rows[5 + offset].find_all("td")  # type: ignore
    nuages_haut, nuages_moyen, nuages_bas = [], [], []
    
    # Extraction des 3 niveaux de nuages (haut, moyen, bas)
    for td in cloud_cells:
        divs = td.find_all("div", class_="clouds")  # type: ignore
        v_haut = divs[0].get_text(strip=True) if len(divs) > 0 else ""
        v_moyen = divs[1].get_text(strip=True) if len(divs) > 1 else ""
        v_bas = divs[2].get_text(strip=True) if len(divs) > 2 else ""
        nuages_haut.append(v_haut)
        nuages_moyen.append(v_moyen)
        nuages_bas.append(v_bas)
    
    pluie = [td.text.strip() for td in rows[6 + offset].find_all("td")]  # type: ignore
    
    return {
        "model": model_name,
        "update_time": update_time,
        "heures": heures,
        "vent": vent,
        "rafales": rafales,
        "direction": direction,
        "temp": temp,
        "nuages_haut": nuages_haut,
        "nuages_moyen": nuages_moyen,
        "nuages_bas": nuages_bas,
        "pluie": pluie
    }

def write_model_data_to_csv(writer, model_data, max_cols):
    """
    Écrit les données d'un modèle dans le fichier CSV.
    
    Cette fonction formate et écrit les données météo dans le CSV
    avec le format standard : en-tête + valeurs par colonne.
    
    ARGUMENTS :
    - writer : Writer CSV
    - model_data : Données du modèle à écrire
    - max_cols : Nombre maximum de colonnes pour l'alignement
    """
    if not model_data:
        # Si pas de données, écrire des lignes vides
        writer.writerow(["Modele", model_data.get("model", "Inconnu")] + [""] * (max_cols - 1))
        writer.writerow(["Heure mise a jour", ""] + [""] * (max_cols - 1))
        for field in ["Heures", "Vent (noeuds)", "Rafales (noeuds)", "Direction du vent (degres)", 
                     "Temperature (C)", "Nuages Haut (%)", "Nuages Moyen (%)", "Nuages Bas (%)", 
                     "Precipitations (mm/1h)"]:
            writer.writerow([field] + [""] * max_cols)
        writer.writerow(["Note Windguru"] + [""] * max_cols)
        return
    
    # Écriture des données du modèle
    writer.writerow(["Modele", model_data["model"]] + [""] * (max_cols - 1))
    writer.writerow(["Heure mise a jour", model_data["update_time"]] + [""] * (max_cols - 1))
    writer.writerow(["Heures"] + model_data["heures"])
    writer.writerow(["Vent (noeuds)"] + model_data["vent"])
    writer.writerow(["Rafales (noeuds)"] + model_data["rafales"])
    writer.writerow(["Direction du vent (degres)"] + model_data["direction"])
    writer.writerow(["Temperature (C)"] + model_data["temp"])
    writer.writerow(["Nuages Haut (%)"] + model_data["nuages_haut"])
    writer.writerow(["Nuages Moyen (%)"] + model_data["nuages_moyen"])
    writer.writerow(["Nuages Bas (%)"] + model_data["nuages_bas"])
    writer.writerow(["Precipitations (mm/1h)"] + model_data["pluie"])
    writer.writerow(["Note Windguru"] + [""] * (max_cols - 1))

def scrape_site_in_tab(driver, site_id, tab_index, total_sites):
    """
    Scrape un site dans un onglet spécifique avec synchronisation.
    
    Cette fonction gère le scraping d'un site dans un onglet dédié
    avec gestion des erreurs et logging détaillé.
    
    ARGUMENTS :
    - driver : Instance WebDriver Firefox
    - site_id : ID du site Windguru
    - tab_index : Index de l'onglet (0-based)
    - total_sites : Nombre total de sites pour le logging
    
    RETOURNE :
    - Tuple (site_id, wg_data, arome_data, site_name)
    """
    logger = get_logger()
    current_site = tab_index + 1
    
    try:
        with driver_lock:
            # Basculer vers l'onglet avec vérification
            driver.switch_to.window(driver.window_handles[tab_index])
            
            # Vérifier qu'on est bien sur le bon onglet
            current_url = driver.current_url
            if f"/{site_id}" not in current_url:
                driver.get(f"https://www.windguru.cz/{site_id}")
            
            url = f"https://www.windguru.cz/{site_id}"
            driver.get(url)
            
            # Attendre seulement les éléments essentiels avec timeout optimisé
            logger.loading_page(site_id, current_site, total_sites)
            WebDriverWait(driver, WAIT_TIME).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.tabulka"))
            )
            
            # Attendre juste 0.5 seconde pour le JavaScript (optimisé)
            logger.waiting_data(site_id, current_site, total_sites)
            time.sleep(JS_WAIT_TIME)
            
            # Récupération du nom du site (sélecteur .spot-name)
            site_name = f"Site {site_id}"
            try:
                spot_elem = driver.find_element(By.CSS_SELECTOR, ".spot-name")
                site_name = spot_elem.text.strip()
            except Exception as e:
                pass
            
            # Récupérer l'heure de lancement depuis les variables d'environnement ou calculer localement
            workflow_start_time = os.environ.get('WORKFLOW_START_TIME')
            workflow_timezone = os.environ.get('WORKFLOW_TIMEZONE', 'Europe/Paris')
            
            if workflow_start_time:
                # Utiliser l'heure de GitHub Actions
                try:
                    # Parser l'heure UTC de GitHub Actions
                    utc_time = datetime.strptime(workflow_start_time, '%Y-%m-%d %H:%M:%S UTC')
                    # Convertir en heure locale française
                    tz = pytz.timezone(workflow_timezone)
                    local_time = utc_time.replace(tzinfo=pytz.UTC).astimezone(tz)
                    update_time = local_time.strftime("%d.%m. %H:%M")
                except Exception:
                    # Fallback si erreur de parsing
                    utc_now = datetime.now()
                    france_time = utc_now.replace(hour=(utc_now.hour + 2) % 24)
                    update_time = france_time.strftime("%d.%m. %H:%M")
            else:
                # Utiliser l'heure locale (lancement local)
                utc_now = datetime.now()
                france_time = utc_now.replace(hour=(utc_now.hour + 2) % 24)
                update_time = france_time.strftime("%d.%m. %H:%M")
            
            # Analyse du HTML pour trouver toutes les tables de prévisions
            soup = BeautifulSoup(driver.page_source, "html.parser")
            legends = soup.find_all("div", class_="nadlegend")
            
            # Extraction des données pour les deux modèles
            wg_data = None
            arome_data = None
            
            for legend in legends:
                legend_text = legend.get_text(strip=True).lower()
                
                # Extraction WG
                if "wg" in legend_text and not wg_data:
                    wg_table = legend.find_next("table", class_="tabulka")
                    wg_data = extract_table_data(wg_table, "WG", update_time)
                    if wg_data:
                        logger.model_found(site_id, "WG")
                
                # Extraction AROME
                elif "arome" in legend_text and not arome_data:
                    arome_table = legend.find_next("table", class_="tabulka")
                    arome_data = extract_table_data(arome_table, "AROME 1.3km", update_time)
                    if arome_data:
                        logger.model_found(site_id, "AROME 1.3km")
            
            # Log des modèles manquants
            if not wg_data:
                logger.model_missing(site_id, "WG")
            if not arome_data:
                logger.model_missing(site_id, "AROME 1.3km")
            
            if not wg_data:
                return site_id, None, None, site_name
            
            return site_id, wg_data, arome_data, site_name
        
    except Exception as e:
        logger.site_error(site_id, str(e))
        return site_id, None, None, f"Site {site_id}"

def scrape_windguru_parallel():
    """
    Scrape tous les sites en parallèle avec des onglets.
    
    Cette fonction orchestre le scraping parallèle en créant
    un onglet par site et en lançant les threads de scraping.
    
    RETOURNE :
    - Dict des résultats par site_id
    """
    logger = get_logger()
    
    # Utiliser Selenium Manager si DRIVER_PATH est None, sinon utiliser le chemin spécifié
    if DRIVER_PATH is None:
        driver = webdriver.Firefox(options=options)
    else:
        driver = webdriver.Firefox(service=Service(DRIVER_PATH), options=options)
    results = {}
    total_sites = len(SITES)
    
    logger.browser_start()
    
    try:
        # Créer un onglet pour chaque site
        for i, site_id in enumerate(SITES):
            if i == 0:
                # Le premier onglet existe déjà
                pass
            else:
                # Créer un nouvel onglet
                driver.execute_script("window.open('');")
        
        # Traiter tous les sites en parallèle
        threads = []
        for i, site_id in enumerate(SITES):
            thread = threading.Thread(
                target=lambda site_id=site_id, i=i: results.update({site_id: scrape_site_in_tab(driver, site_id, i, total_sites)})
            )
            threads.append(thread)
            thread.start()
        
        # Attendre que tous les threads se terminent
        for thread in threads:
            thread.join()
        
        return results
        
    finally:
        logger.browser_close()
        driver.quit()

def save_to_csv_raw(site_id, wg_data, arome_data=None, site_name=""):
    """
    Sauvegarde les données brutes dans un fichier CSV.
    
    Cette fonction crée un fichier CSV structuré avec les données
    des modèles AROME et WG pour un site donné.
    
    ARGUMENTS :
    - site_id : ID du site Windguru
    - wg_data : Données du modèle WG
    - arome_data : Données du modèle AROME (optionnel)
    - site_name : Nom du site
    """
    logger = get_logger()
    filename = os.path.join(CSV_FOLDER, f"Donnees_WG_{site_id}.csv")
    
    # Déterminer le nombre maximum de colonnes
    max_cols = len(wg_data["heures"]) if wg_data else 0
    if arome_data and len(arome_data["heures"]) > max_cols:
        max_cols = len(arome_data["heures"])
    
    logger.saving_data(site_id)
    
    with open(filename, 'w', newline='', encoding=CSV_ENCODING) as csvfile:
        writer = csv.writer(csvfile, delimiter=CSV_DELIMITER)
        
        # En-tête avec ID du site et nom
        header = ["ID Site", site_id] + [""] * (max_cols - 1)
        writer.writerow(header)
        writer.writerow(["Nom Site", site_name] + [""] * (max_cols - 1))
        writer.writerow([])  # Ligne vide
        
        # Données du modèle WG
        write_model_data_to_csv(writer, wg_data, max_cols)
        writer.writerow([])  # Ligne vide
        
        # Données du modèle AROME
        write_model_data_to_csv(writer, arome_data, max_cols)
    
    logger.file_saved(os.path.basename(filename))

def main():
    """
    Fonction principale avec parallélisation.
    
    Cette fonction orchestre l'ensemble du processus de scraping :
    1. Initialisation du logging
    2. Affichage de l'heure locale
    3. Scraping parallèle des sites
    4. Sauvegarde des résultats en CSV
    5. Logging des statistiques finales
    """
    total_sites = len(SITES)
    logger = init_logger(total_sites)
    
    # Afficher l'heure locale française
    workflow_start_time = os.environ.get('WORKFLOW_START_TIME')
    workflow_timezone = os.environ.get('WORKFLOW_TIMEZONE', 'Europe/Paris')
    
    if workflow_start_time:
        try:
            utc_time = datetime.strptime(workflow_start_time, '%Y-%m-%d %H:%M:%S UTC')
            tz = pytz.timezone(workflow_timezone)
            local_time = utc_time.replace(tzinfo=pytz.UTC).astimezone(tz)
            current_time = local_time.strftime("%d/%m/%Y à %H:%M:%S")
        except Exception:
            utc_now = datetime.now()
            france_time = utc_now.replace(hour=(utc_now.hour + 2) % 24)
            current_time = france_time.strftime("%d/%m/%Y à %H:%M:%S")
    else:
        utc_now = datetime.now()
        france_time = utc_now.replace(hour=(utc_now.hour + 2) % 24)
        current_time = france_time.strftime("%d/%m/%Y à %H:%M:%S")
    
    print(f"🕐 Heure locale française: {current_time}")
    
    logger.start_scraping()
    
    # Scraping parallèle
    results = scrape_windguru_parallel()
    
    # Sauvegarde des résultats
    success_count = 0
    for i, (site_id, (_, wg_data, arome_data, site_name)) in enumerate(results.items(), 1):
        logger.start_site(site_id, site_name)
        
        if wg_data:
            # Compter les données extraites
            data_count = len(wg_data.get('heures', []))
            logger.data_extracted(site_id, data_count)
            
            save_to_csv_raw(site_id, wg_data, arome_data, site_name)
            success_count += 1
            
            # Log des modèles trouvés
            models_found = []
            if wg_data:
                models_found.append("WG")
            if arome_data:
                models_found.append("AROME")
            logger.site_success(site_id, models_found)
        else:
            logger.site_error(site_id, "Aucune donnee extraite")
    
    logger.finish_scraping()

if __name__ == "__main__":
    main() 
