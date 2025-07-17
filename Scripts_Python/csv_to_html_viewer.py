"""
CSV to HTML Viewer - Visualiseur de données Windguru pour Foil Report

Ce script lit les fichiers CSV générés par le scraper et crée une page HTML
interactive pour visualiser les données météorologiques dans Firefox.

Auteur: [Votre nom]
Version: 2.0.0
Date: 2024
"""

import os
import csv
import glob
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import webbrowser
import subprocess
from config import CSV_FOLDER, FIREFOX_PATH, SITES
from logger import init_logger, get_logger

# === Configuration des critères de vent par site ===
from config import SITE_CRITERIA


class CSVDataReader:
    """Classe pour lire et parser les fichiers CSV de Windguru."""
    
    def __init__(self, csv_folder: str):
        self.csv_folder = csv_folder
        self.data = {}
    
    def read_csv_file(self, filename: str) -> Optional[Dict]:
        """Lit un fichier CSV et retourne les données structurées."""
        logger = get_logger()
        filepath = os.path.join(self.csv_folder, filename)
        
        if not os.path.exists(filepath):
            logger.warning(f"Fichier non trouve: {filename}")
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile, delimiter=';')
                rows = list(reader)
            
            if len(rows) < 10:
                return None
            
            # Extraire l'ID du site et le nom
            site_id = rows[0][1] if len(rows[0]) > 1 else "Inconnu"
            site_name = rows[1][1] if len(rows) > 1 and len(rows[1]) > 1 else f"Site {site_id}"
            
            # Parser les données
            data = {
                'site_id': site_id,
                'site_name': site_name,
                'filename': filename,
                'models': {}
            }
            
            current_model = None
            current_data = {}
            
            for row in rows:
                if not row or not row[0]:
                    continue
                
                field = row[0].strip()
                
                if field == "Modele":
                    # Nouveau modèle
                    if current_model and current_data:
                        data['models'][current_model] = current_data
                    
                    current_model = row[1] if len(row) > 1 else "Inconnu"
                    current_data = {}
                
                elif field == "Heure mise a jour":
                    current_data['update_time'] = row[1] if len(row) > 1 else ""
                
                elif field == "Heures":
                    current_data['heures'] = row[1:] if len(row) > 1 else []
                
                elif field == "Vent (noeuds)":
                    current_data['vent'] = row[1:] if len(row) > 1 else []
                
                elif field == "Rafales (noeuds)":
                    current_data['rafales'] = row[1:] if len(row) > 1 else []
                
                elif field == "Direction du vent (degres)":
                    current_data['direction'] = row[1:] if len(row) > 1 else []
                
                elif field == "Temperature (C)":
                    current_data['temp'] = row[1:] if len(row) > 1 else []
                
                elif field == "Nuages Haut (%)":
                    current_data['nuages_haut'] = row[1:] if len(row) > 1 else []
                
                elif field == "Nuages Moyen (%)":
                    current_data['nuages_moyen'] = row[1:] if len(row) > 1 else []
                
                elif field == "Nuages Bas (%)":
                    current_data['nuages_bas'] = row[1:] if len(row) > 1 else []
                
                elif field == "Precipitations (mm/1h)":
                    current_data['pluie'] = row[1:] if len(row) > 1 else []
            
            # Ajouter le dernier modèle
            if current_model and current_data:
                data['models'][current_model] = current_data
            
            return data
            
        except Exception as e:
            return None
    
    def read_all_csv_files(self) -> Dict:
        """Lit tous les fichiers CSV du dossier."""
        logger = get_logger()
        csv_files = glob.glob(os.path.join(self.csv_folder, "Donnees_WG_*.csv"))
        
        logger.info(f"Fichiers CSV trouves: {len(csv_files)}")
        
        for csv_file in csv_files:
            filename = os.path.basename(csv_file)
            data = self.read_csv_file(filename)
            if data:
                self.data[data['site_id']] = data
                logger.success(f"Donnees chargees: {filename}")
        
        logger.data_loaded(len(self.data))
        return self.data


def merge_models(site_data: dict) -> dict:
    """
    Fusionne les données AROME et WG pour un site.
    Les heures sont en colonnes, sans doublons.
    On prend d'abord AROME, puis on complète avec WG.
    """
    models = site_data.get('models', {})
    arome = models.get('AROME 1.3km', {})
    wg = models.get('WG', {})

    heures_arome = arome.get('heures', [])
    heures_wg = wg.get('heures', [])

    # Fusion des heures (ordre : AROME puis WG sans doublons)
    heures = list(heures_arome)
    for h in heures_wg:
        if h not in heures:
            heures.append(h)

    # Pour chaque heure, choisir la source et les valeurs
    source = []
    def pick(field):
        vals_arome = arome.get(field, [])
        vals_wg = wg.get(field, [])
        res = []
        for i, h in enumerate(heures):
            if h in heures_arome:
                idx = heures_arome.index(h)
                v = vals_arome[idx] if idx < len(vals_arome) else ''
                res.append(v)
            elif h in heures_wg:
                idx = heures_wg.index(h)
                v = vals_wg[idx] if idx < len(vals_wg) else ''
                res.append(v)
            else:
                res.append('')
        return res

    for h in heures:
        if h in heures_arome:
            source.append('AROME')
        else:
            source.append('WG')

    merged = {
        'heures': heures,
        'source': source,
        'vent': pick('vent'),
        'rafales': pick('rafales'),
        'direction': pick('direction'),
        'temp': pick('temp'),
        'nuages_haut': pick('nuages_haut'),
        'nuages_moyen': pick('nuages_moyen'),
        'nuages_bas': pick('nuages_bas'),
        'pluie': pick('pluie'),
        'update_time_arome': arome.get('update_time', ''),
        'update_time_wg': wg.get('update_time', ''),
    }
    return merged


def get_jour_complet(abreviation: str) -> str:
    """Convertit une abréviation de jour en nom complet français"""
    jours = {
        'Lu': 'Lundi',
        'Ma': 'Mardi', 
        'Me': 'Mercredi',
        'Je': 'Jeudi',
        'Ve': 'Vendredi',
        'Sa': 'Samedi',
        'Di': 'Dimanche',
        'Th': 'Jeudi',
        'Fr': 'Vendredi',
        'Sa': 'Samedi',
        'Su': 'Dimanche',
        'Mo': 'Lundi',
        'Tu': 'Mardi',
        'We': 'Mercredi'
    }
    return jours.get(abreviation, abreviation)


def parse_heure(heure_str: str) -> Tuple[str, str]:
    """Extrait le jour et l'heure d'une chaîne comme 'Lu14.03h' et convertit en français"""
    if not heure_str:
        return "", ""
    
    # Chercher le pattern jour + date + heure
    match = re.match(r'([A-Za-z]+)(\d+)\.(\d+)h', heure_str)
    if match:
        jour = match.group(1)
        date = match.group(2)
        heure = int(match.group(3))
        
        # Convertir le jour en français
        jour_fr = get_jour_complet(jour)
        
        return f"{jour_fr} {date}", f"{heure}"
    else:
        return heure_str, ""


def get_jour_from_heure(heure_str: str) -> str:
    """Extrait le jour complet d'une heure en français"""
    if not heure_str:
        return ""
    match = re.match(r'([A-Za-z]+)(\d+)\.(\d+)h', heure_str)
    if match:
        jour = match.group(1)
        date = match.group(2)
        jour_fr = get_jour_complet(jour)
        return f"{jour_fr} {date}"
    return ""


def is_night_time(heure_str: str) -> bool:
    """Détermine si c'est la nuit (20h-7h30)"""
    if not heure_str:
        return False
    
    match = re.match(r'[A-Za-z]+\d+\.(\d+)h', heure_str)
    if match:
        heure = int(match.group(1))
        return heure >= 20 or heure <= 7
    return False


def get_cloud_emojis(percentage_str: str, has_rain: bool = False, temperature: str = "") -> str:
    """Retourne les emojis de nuages selon le pourcentage, la présence de pluie et la température"""
    if not percentage_str:
        return ""
    
    try:
        percentage = int(percentage_str)
        
        # Déterminer le nombre de nuages selon le pourcentage
        if percentage < 6:
            return ""  # Pas de nuage pour 0-5%
        elif percentage <= 25:
            num_clouds = 1
        elif percentage <= 50:
            num_clouds = 2
        elif percentage <= 75:
            num_clouds = 3
        else:  # 76-100%
            num_clouds = 4
        
        # Vérifier la température pour la neige
        has_snow = False
        if temperature:
            try:
                temp_val = float(temperature)
                has_snow = temp_val < 2
            except ValueError:
                pass
        
        # Générer les nuages superposés
        clouds_html = ""
        for i in range(num_clouds):
            # Positionnement en carré : 2x2 pour 4 nuages max
            if i == 0:  # Premier nuage (haut-gauche)
                base_top_offset = -5
                left_offset = -4
            elif i == 1:  # Deuxième nuage (haut-droite)
                base_top_offset = -5
                left_offset = 3
            elif i == 2:  # Troisième nuage (bas-gauche)
                base_top_offset = 5
                left_offset = -4
            elif i == 3:  # Quatrième nuage (bas-droite)
                base_top_offset = 5
                left_offset = 3
            
            # Choisir le type de nuage
            if has_snow:
                cloud_emoji = "❄️"
                font_size = "10px"
                top_offset = base_top_offset + 2
            else:
                cloud_emoji = "☁️"
                font_size = "16px"
                top_offset = base_top_offset
            
            clouds_html += f'<span class="cloud-symbol" style="position: absolute; top: {top_offset}px; left: {left_offset}px; font-size: {font_size};">{cloud_emoji}</span>'
        
        # Ajouter la goutte de pluie au milieu si nécessaire
        if has_rain and not has_snow:
            clouds_html += f'<span class="cloud-symbol" style="position: absolute; top: 6px; left: 4px; font-size: 9px;">💧</span>'
        
        return f'<div style="position: relative; display: inline-block; width: 20px; height: 20px;">{clouds_html}</div>'
        
    except ValueError:
        return ""


def get_criteria_for_site_and_date(site_id: int, date_str: str) -> Optional[Dict]:
    """Retourne les critères appropriés pour un site et une date"""
    if site_id not in SITE_CRITERIA:
        return None
    
    # Utiliser le mois actuel du système
    current_month = datetime.now().month
    
    site_criteria = SITE_CRITERIA[site_id]
    
    if site_id == 179:
        if current_month in [6, 7, 8]:  # Juin à août
            return site_criteria.get("juin_aout")
        else:  # Septembre à mai
            return site_criteria.get("septembre_mai")
    
    elif site_id == 314:
        if current_month in [6, 7, 8, 9]:  # Juin à septembre
            return site_criteria.get("juin_septembre")
        else:  # Octobre à mai
            return site_criteria.get("octobre_mai")
    
    elif site_id == 72305:
        return site_criteria.get("toute_annee")
    
    return None


def calculate_note(site_id: int, vent: str, rafales: str, direction: str, 
                   jour_str: str, heure_str: str, pluie: str, temp: str) -> str:
    """
    Calcule la note avec étoiles selon la formule : Note = A x B x C x D x E
    
    A = note vent (1, 2, ou 3 selon les seuils)
    B = direction favorable (1 ou 0)
    C = période jour (1 ou 0)
    D = pas de précipitations (1 ou 0)
    E = température > 5°C (1 ou 0)
    """
    criteria = get_criteria_for_site_and_date(site_id, jour_str)
    if not criteria:
        return ""
    
    try:
        vent_val = float(vent) if vent else 0
        rafales_val = float(rafales) if rafales else 0
        direction_val = float(direction) if direction else 0
        temp_val = float(temp) if temp else 0
        pluie_val = float(pluie) if pluie else 0
    except ValueError:
        return ""
    
    vent_moyen = criteria["vent_moyen"]
    vent_bien = criteria["vent_bien"]
    vent_tres_bien = criteria["vent_tres_bien"]
    
    # A - Note vent selon nouvelle logique
    if vent_val >= vent_tres_bien:
        A = 3
    elif vent_val >= vent_bien and rafales_val >= vent_tres_bien:
        A = 2
    elif (vent_val >= vent_moyen and rafales_val > vent_bien) or (vent_val >= vent_bien and rafales_val < vent_tres_bien):
        A = 1
    else:
        A = 0
    
    # B - Direction favorable
    B = 0
    for dir_min, dir_max in criteria["direction"]:
        if dir_min <= dir_max:  # Cas normal (ex: 135-225)
            if dir_min <= direction_val <= dir_max:
                B = 1
                break
        else:  # Cas qui traverse 0° (ex: 315-45)
            if direction_val >= dir_min or direction_val <= dir_max:
                B = 1
                break
    
    # C - Période jour
    C = 1 if not is_night_time(heure_str) else 0
    
    # D - Pas de précipitations
    D = 1 if pluie_val == 0 else 0
    
    # E - Température > 5°C
    E = 1 if temp_val >= 5 else 0
    
    # Calcul de la note finale
    note = A * B * C * D * E
    
    # Génération des étoiles empilées verticalement
    if note == 0:
        return ""
    elif note == 1:
        return '<div class="note-stars" style="display: flex; flex-direction: column; align-items: center; line-height: 0.8;">⭐</div>'
    elif note == 2:
        return '<div class="note-stars" style="display: flex; flex-direction: column; align-items: center; line-height: 0.8;">⭐<br>⭐</div>'
    elif note == 3:
        return '<div class="note-stars" style="display: flex; flex-direction: column; align-items: center; line-height: 0.8;">⭐<br>⭐<br>⭐</div>'
    else:
        return '<div class="note-stars" style="display: flex; flex-direction: column; align-items: center; line-height: 0.8;">⭐<br>⭐<br>⭐</div>'  # Maximum 3 étoiles


def get_wind_color_progressive(site_id: int, wind_value: float, check_type: str = "vent") -> str:
    """
    Calcule la couleur progressive pour le vent selon la nouvelle échelle :
    - 2 nœuds avant moyen : bleu très clair
    - Moyen : bleu clair
    - De moyen à bien : progressivement vert
    - Bien : vert
    - De bien à très bien : progressivement orange
    - Très bien : orange
    - Puis progressivement rouge
    - +10 nœuds par rapport à bien : rouge et reste rouge
    """
    criteria = get_criteria_for_site_and_date(site_id, "")
    if not criteria:
        return ""
    
    vent_moyen = criteria["vent_moyen"]
    vent_bien = criteria["vent_bien"]
    vent_tres_bien = criteria["vent_tres_bien"]
    
    # Calculer les seuils
    seuil_bleu_tres_clair = vent_moyen - 2
    seuil_rouge = vent_bien + 10
    
    # Déterminer la couleur selon la valeur
    if wind_value < seuil_bleu_tres_clair:
        return ""  # Pas de couleur pour les valeurs très faibles
    
    elif wind_value < vent_moyen:
        # Bleu très clair à bleu clair (progression linéaire)
        ratio = (wind_value - seuil_bleu_tres_clair) / (vent_moyen - seuil_bleu_tres_clair)
        # Interpolation entre bleu très clair et bleu clair
        red = int(173 + ratio * (173 - 173))  # 173 -> 173 (reste constant)
        green = int(216 + ratio * (216 - 216))  # 216 -> 216 (reste constant)
        blue = int(230 + ratio * (230 - 230))  # 230 -> 230 (reste constant)
        alpha = 0.3 + ratio * 0.4  # Opacité progressive
        return f"background-color: rgba({red}, {green}, {blue}, {alpha:.2f});"
    
    elif wind_value < vent_bien:
        # Bleu clair à vert (progression linéaire)
        ratio = (wind_value - vent_moyen) / (vent_bien - vent_moyen)
        # Interpolation entre bleu clair et vert
        red = int(173 + ratio * (50 - 173))  # 173 -> 50
        green = int(216 + ratio * (205 - 216))  # 216 -> 205
        blue = int(230 + ratio * (50 - 230))  # 230 -> 50
        return f"background-color: rgb({red}, {green}, {blue});"
    
    elif wind_value < vent_tres_bien:
        # Vert à orange (progression linéaire)
        ratio = (wind_value - vent_bien) / (vent_tres_bien - vent_bien)
        # Interpolation entre vert et orange
        red = int(50 + ratio * (255 - 50))  # 50 -> 255
        green = int(205 + ratio * (165 - 205))  # 205 -> 165
        blue = int(50 + ratio * (0 - 50))  # 50 -> 0
        return f"background-color: rgb({red}, {green}, {blue});"
    
    elif wind_value < seuil_rouge:
        # Orange à rouge (progression linéaire)
        ratio = (wind_value - vent_tres_bien) / (seuil_rouge - vent_tres_bien)
        # Interpolation entre orange et rouge
        red = int(255 + ratio * (255 - 255))  # 255 -> 255 (reste max)
        green = int(165 + ratio * (0 - 165))  # 165 -> 0
        blue = int(0 + ratio * (0 - 0))  # 0 -> 0
        return f"background-color: rgb({red}, {green}, {blue});"
    
    else:
        # Rouge pour les valeurs élevées
        return "background-color: rgb(255, 0, 0);"


def get_wind_background_class(site_id: int, vent: str, rafales: str, direction: str, 
                             jour_str: str, heure_str: str, pluie: str, check_type: str = "both") -> str:
    """
    Détermine la classe CSS pour le fond selon les conditions de vent
    check_type: "vent", "rafales", "direction", ou "both"
    """
    criteria = get_criteria_for_site_and_date(site_id, jour_str)
    if not criteria:
        return ""
    
    try:
        vent_val = float(vent) if vent else 0
        rafales_val = float(rafales) if rafales else 0
        direction_val = float(direction) if direction else 0
    except ValueError:
        return ""
    
    # Vérifier la direction
    direction_ok = False
    for dir_min, dir_max in criteria["direction"]:
        if dir_min <= dir_max:  # Cas normal (ex: 135-225)
            if direction_val >= dir_min or direction_val <= dir_max:
                direction_ok = True
                break
        else:  # Cas qui traverse 0° (ex: 315-45)
            if direction_val >= dir_min or direction_val <= dir_max:
                direction_ok = True
                break
    
    if not direction_ok:
        return ""
    
    # Utiliser la nouvelle échelle de couleur progressive
    if check_type == "vent":
        return get_wind_color_progressive(site_id, vent_val, "vent")
    elif check_type == "rafales":
        return get_wind_color_progressive(site_id, rafales_val, "rafales")
    elif check_type == "direction":
        # Vérifier seulement la direction (toujours favorable si on arrive ici)
        return "background-color: #c3e6cb;"  # Vert clair pour direction favorable
    else:
        # Pour "both", on utilise la moyenne des deux valeurs
        avg_val = (vent_val + rafales_val) / 2
        return get_wind_color_progressive(site_id, avg_val, "both")


def get_temperature_color(temp_str: str) -> str:
    """Retourne la couleur de la température selon l'échelle définie"""
    if not temp_str:
        return "#000000"  # Noir par défaut
    
    try:
        temp_val = float(temp_str)
        
        if temp_val < 1:
            return "#8B008B"  # Violet
        elif temp_val < 10:
            return "#0000FF"  # Bleu
        elif temp_val < 20:
            return "#87CEEB"  # Bleu clair
        elif temp_val < 25:
            return "#32CD32"  # Vert
        elif temp_val < 30:
            return "#FFA500"  # Orange
        elif temp_val < 35:
            return "#FF8C00"  # Orange foncé
        else:
            return "#FF0000"  # Rouge
    except ValueError:
        return "#000000"  # Noir par défaut


class HTMLGenerator:
    """Classe pour générer la page HTML de visualisation."""
    
    def __init__(self, data: Dict):
        self.data = data
    
    def generate_html(self) -> str:
        """Génère le contenu HTML complet."""
        # Convertir l'heure UTC de GitHub en heure locale française
        # GitHub affiche UTC mais dit que c'est CEST, donc on ajoute +2h en été
        utc_now = datetime.now()
        # En juillet, on est en heure d'été (CEST = UTC+2)
        france_time = utc_now.replace(hour=(utc_now.hour + 2) % 24)
        current_time = france_time.strftime('%d/%m/%Y à %H:%M')
        
        html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Foil Report {current_time}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 10px;
        }}
        
        .container {{
            /* max-width: 95vw; */
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
            aspect-ratio: 16/9;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-shrink: 0;
        }}
        
        .header h1 {{
            font-size: 2em;
            margin: 0;
        }}
        
        .content {{
            flex: 1;
            overflow: auto;
            padding: 20px;
            background: linear-gradient(135deg, #4a5f8a 0%, #5a3d7a 100%);
        }}
        
        .site-card {{
            background: #e8e9ea;
            border-radius: 10px;
            margin-bottom: 20px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        
        .site-header {{
            background: #343a40;
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .site-header h2 {{
            font-size: 1.3em;
            margin: 0;
        }}
        
        .site-header .update-time {{
            opacity: 0.8;
            font-size: 0.9em;
        }}
        
        .data-table {{
            width: max-content;
            border-collapse: collapse;
            font-size: 0.8em;
            table-layout: fixed;
        }}
        
        .data-table th {{
            background: #e9ecef;
            padding: 2px 1px;
            text-align: center;
            font-weight: 600;
            border-bottom: 2px solid #dee2e6;
            font-size: 0.9em;
            position: sticky;
            top: 0;
            z-index: 10;
            width: 25px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .data-table td {{
            padding: 2px 1px;
            text-align: center;
            border-bottom: 1px solid #dee2e6;
            font-size: 0.9em;
            vertical-align: middle;
            width: 25px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        

        
        .data-table tr:hover {{
            background: #e3f2fd;
        }}
        
        .wind-direction {{
            display: inline-block;
            font-size: 1.2em;
        }}
        
        .cloud-symbol {{
            cursor: help;
            font-size: 1.2em;
        }}
        

        
        .note-stars {{
            color: #ffc107;
            font-size: 1.2em;
        }}
        
        .no-data {{
            text-align: center;
            padding: 40px;
            color: #6c757d;
            font-style: italic;
        }}
        
        .footer {{
            background: #343a40;
            color: white;
            text-align: center;
            padding: 15px;
            font-size: 0.9em;
            flex-shrink: 0;
        }}
        
        .data-table td:first-child {{
            color: #222 !important;
            font-weight: bold !important;
            background: #b8babb !important;
            position: sticky;
            left: 0;
            z-index: 5;
            width: 110px;
        }}
        
        .data-table th:first-child {{
            background: #b8babb !important;
            position: sticky;
            left: 0;
            z-index: 15;
            width: 110px;
        }}
        
        .data-table tr:nth-child(2) th:nth-child(even) {{
            background: #d1d3d4;
        }}
        
        .data-table tr:nth-child(2) th:nth-child(odd) {{
            background: #b8babb;
        }}
        
        .data-table tr:nth-child(1) th {{
            background: #b8babb !important;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                margin: 5px;
                border-radius: 10px;
                max-width: 98vw;
                aspect-ratio: auto;
                min-height: 100vh;
            }}
            
            .header {{
                padding: 15px 20px;
            }}
            
            .header h1 {{
                font-size: 1.3em;
            }}
            
            .content {{
                padding: 10px;
            }}
            
            .site-header {{
                padding: 10px 15px;
                flex-direction: column;
                gap: 5px;
            }}
            
            .site-header h2 {{
                font-size: 1.1em;
            }}
            
            .site-header .update-time {{
                font-size: 0.8em;
                text-align: center;
            }}
            
            .data-table {{
                font-size: 0.65em;
                min-width: auto;
                width: 100%;
            }}
            
            .data-table th,
            .data-table td {{
                padding: 2px 1px;
                min-width: 20px;
                max-width: 25px;
                width: 20px;
                font-size: 0.7em;
                word-wrap: break-word;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            
            .data-table td:first-child,
            .data-table th:first-child {{
                width: 80px;
                min-width: 80px;
                max-width: 80px;
                font-size: 0.7em;
            }}
            
            /* Réduire la taille des flèches de direction */
            .wind-direction {{
                font-size: 1em;
            }}
            
            /* Réduire la taille des étoiles */
            .note-stars {{
                font-size: 0.9em;
            }}
            
            /* Optimiser l'affichage des nuages */
            .cloud-symbol {{
                font-size: 0.8em;
            }}
        }}
        
        @media (max-width: 480px) {{
            .container {{
                margin: 2px;
                border-radius: 8px;
            }}
            
            .header {{
                padding: 10px 15px;
            }}
            
            .header h1 {{
                font-size: 1.1em;
            }}
            
            .content {{
                padding: 5px;
            }}
            
            .site-card {{
                margin-bottom: 15px;
            }}
            
            .site-header {{
                padding: 8px 12px;
            }}
            
            .site-header h2 {{
                font-size: 1em;
            }}
            
            .site-header .update-time {{
                font-size: 0.7em;
            }}
            
            .data-table {{
                font-size: 0.6em;
            }}
            
            .data-table th,
            .data-table td {{
                padding: 1px 1px;
                min-width: 18px;
                max-width: 22px;
                width: 18px;
                font-size: 0.65em;
            }}
            
            .data-table td:first-child,
            .data-table th:first-child {{
                width: 70px;
                min-width: 70px;
                max-width: 70px;
                font-size: 0.65em;
            }}
            
            .wind-direction {{
                font-size: 0.9em;
            }}
            
            .note-stars {{
                font-size: 0.8em;
            }}
            
            .cloud-symbol {{
                font-size: 0.7em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌊 Foil Report {current_time}</h1>
        </div>
        
        <div class="content">
"""
        
        if not self.data:
            html += """
            <div class="no-data">
                <h2>📁 Aucune donnée trouvée</h2>
                <p>Aucun fichier CSV n'a été trouvé dans le dossier Donnees_Temporaires.</p>
                <p>Exécutez d'abord le scraper pour générer des données.</p>
            </div>
"""
        else:
            for site_id in SITES:
                site_id_str = str(site_id)
                if site_id_str in self.data:
                    site_data = self.data[site_id_str]
                    merged = merge_models(site_data)
                    html += self._generate_site_html(site_id, site_data, merged)
        
        html += """
        </div>
        
        <div class="footer">
            <p>Généré automatiquement par WCSVS</p>
        </div>
    </div>
    
    <script>
        // Fonction pour formater les données après chargement
        document.addEventListener('DOMContentLoaded', function() {
            // Formatage des directions du vent
            document.querySelectorAll('.dir-cell').forEach(cell => {
                const angle = cell.textContent;
                if (angle && !isNaN(parseFloat(angle))) {
                    const cssAngle = parseFloat(angle) + 180;
                    cell.innerHTML = `<span style="transform: rotate(${cssAngle}deg); display: inline-block; font-size: 2em;">↑</span>`;
                }
            });
        });
    </script>
</body>
</html>
"""
        return html
    
    def _generate_site_html(self, site_id: int, site_data: Dict, merged: Dict) -> str:
        """Génère le HTML pour un site spécifique."""
        site_name = site_data.get('site_name', f"Site {site_id}")
        update_time_arome = merged.get('update_time_arome', '')
        update_time_wg = merged.get('update_time_wg', '')
        
        html = f"""
            <div class="site-card">
                <div class="site-header">
                    <h2>📍 {site_name}</h2>
                    <span class="update-time">AROME: {update_time_arome} | WG: {update_time_wg}</span>
                </div>
                <div style="overflow-x: auto; -webkit-overflow-scrolling: touch;">
        """
        html += self._generate_merged_table_html(site_id, merged)
        html += """
                </div>
            </div>
        """
        return html

    def _generate_synthetic_cloud_row(self, label: str, clouds_h: list, clouds_m: list, clouds_b: list, rain_data: list, temp_data: list, heures: list, get_border_style_func) -> str:
        """Génère une ligne de nuages synthétisée (maximum des 3 niveaux)"""
        html = f'<tr><td><b>{label}</b></td>'
        
        for i, (cloud_h, cloud_m, cloud_b, rain_val, temp_val, heure) in enumerate(zip(clouds_h, clouds_m, clouds_b, rain_data, temp_data, heures)):
            # Déterminer le fond jour/nuit
            bg_color = "#ffeaa7" if not is_night_time(heure) else "#a2c6f7"
            
            # Vérifier s'il y a de la pluie
            has_rain = rain_val and float(rain_val) > 0
            
            # Calculer le maximum des 3 niveaux de nuages
            max_cloud = 0
            try:
                cloud_h_val = int(cloud_h) if cloud_h else 0
                cloud_m_val = int(cloud_m) if cloud_m else 0
                cloud_b_val = int(cloud_b) if cloud_b else 0
                max_cloud = max(cloud_h_val, cloud_m_val, cloud_b_val)
            except ValueError:
                pass
            
            # Obtenir les emojis de nuage synthétisés
            cloud_emojis = get_cloud_emojis(str(max_cloud), has_rain, temp_val)
            
            # Générer le contenu de la cellule
            if cloud_emojis:
                cell_content = cloud_emojis
            else:
                cell_content = ""  # Pas d'affichage pour les valeurs < 6%
            
            # Ajouter les bordures si nécessaire
            border_style = get_border_style_func(i)
            style_attr = f' style="background-color: {bg_color}; {border_style}"' if border_style else f' style="background-color: {bg_color};"'
            
            html += f'<td{style_attr}>{cell_content}</td>'
        
        html += '</tr>'
        return html

    def _generate_temperature_row(self, label: str, temp_data: list, get_border_style_func) -> str:
        """Génère une ligne de température avec échelle de couleur"""
        html = f'<tr><td><b>{label}</b></td>'
        
        for i, temp_val in enumerate(temp_data):
            # Obtenir la couleur selon la température
            color = get_temperature_color(temp_val)
            
            # Style pour la température avec couleur
            border_style = get_border_style_func(i)
            style_attr = f' style="color: {color}; font-weight: bold; {border_style}"' if border_style else f' style="color: {color}; font-weight: bold;"'
            
            # Contenu de la cellule
            cell_content = temp_val if temp_val else ""
            
            html += f'<td{style_attr}>{cell_content}</td>'
        
        html += '</tr>'
        return html

    def _generate_wind_row(self, label: str, wind_data: list, bg_styles: list, get_border_style_func) -> str:
        """Génère une ligne de vent/rafales avec couleurs progressives"""
        html = f'<tr><td><b>{label}</b></td>'
        
        for i, (wind_val, bg_style) in enumerate(zip(wind_data, bg_styles)):
            border_style = get_border_style_func(i)
            
            # Combiner les styles
            if border_style:
                if bg_style:
                    style_attr = f' style="{bg_style} font-weight: bold; {border_style}"'
                else:
                    style_attr = f' style="font-weight: bold; {border_style}"'
            else:
                if bg_style:
                    style_attr = f' style="{bg_style} font-weight: bold;"'
                else:
                    style_attr = ' style="font-weight: bold;"'
            
            # Contenu de la cellule
            cell_content = wind_val if wind_val else ""
            
            html += f'<td{style_attr}>{cell_content}</td>'
        
        html += '</tr>'
        return html

    def _generate_rain_row(self, label: str, rain_data: list, get_border_style_func) -> str:
        """Génère une ligne de précipitations en bleu"""
        html = f'<tr><td><b>{label}</b></td>'
        
        for i, rain_val in enumerate(rain_data):
            # Style pour les précipitations en bleu
            border_style = get_border_style_func(i)
            style_attr = f' style="color: #0066cc; font-weight: bold; {border_style}"' if border_style else ' style="color: #0066cc; font-weight: bold;"'
            
            # Contenu de la cellule
            cell_content = rain_val if rain_val else ""
            
            html += f'<td{style_attr}>{cell_content}</td>'
        
        html += '</tr>'
        return html

    def _get_border_style(self, i: int, heures: list) -> str:
        """Génère le style de bordure pour une colonne"""
        if i == 0:
            return ""
        
        # Barre séparative entre les jours
        current_jour = get_jour_from_heure(heures[i])
        prev_jour = get_jour_from_heure(heures[i-1])
        if current_jour != prev_jour and current_jour and prev_jour:
            return 'border-left: 2px solid #6c757d;'
        
        return ""

    def _generate_merged_table_html(self, site_id: int, merged: dict) -> str:
        heures = merged['heures']
        source = merged['source']
        vent = merged['vent']
        rafales = merged['rafales']
        direction = merged['direction']
        temp = merged['temp']
        nuages_haut = merged['nuages_haut']
        nuages_moyen = merged['nuages_moyen']
        nuages_bas = merged['nuages_bas']
        pluie = merged['pluie']

        # Trouver la limite entre AROME et WG
        try:
            limite = source.index('WG')
        except ValueError:
            limite = len(source)  # tout AROME

        # Fonction pour générer les bordures
        def get_border_style(i):
            border = ""
            # Barre orange entre les modèles (priorité)
            if i == limite:
                border = 'border-left: 3px solid #ff6b35;'
            # Barre séparative entre les jours (plus foncée)
            elif i > 0:
                current_jour = get_jour_from_heure(heures[i])
                prev_jour = get_jour_from_heure(heures[i-1])
                if current_jour != prev_jour and current_jour and prev_jour:
                    border = 'border-left: 2px solid #6c757d;'
            return border

        html = f"""
                <table class="data-table">
                    <thead>
                        <tr>
                            <th style="font-weight: bold;"></th>
        """
        
        # Première ligne : jours fusionnés
        current_jour = None
        current_jour_count = 0
        jour_cells = []
        
        for i, h in enumerate(heures):
            jour, _ = parse_heure(h)
            # Convertir l'abréviation en nom complet
            jour_complet = get_jour_complet(jour.split()[0]) + " " + jour.split()[1] if jour else jour
            color = "#d1451f" if source[i] == 'AROME' else "#000000"
            border_style = get_border_style(i)
            
            if jour != current_jour:
                # Fermer la cellule précédente si elle existe
                if current_jour is not None:
                    current_jour_complet = get_jour_complet(current_jour.split()[0]) + " " + current_jour.split()[1] if current_jour else current_jour
                    style_attr = f' style="color: {color}; font-weight: bold; {border_style}"' if border_style else f' style="color: {color}; font-weight: bold;"'
                    colspan_attr = f' colspan="{current_jour_count}"' if current_jour_count > 1 else ''
                    jour_cells.append(f'<th{style_attr}{colspan_attr}>{current_jour_complet}</th>')
                
                # Commencer une nouvelle cellule
                current_jour = jour
                current_jour_count = 1
            else:
                # Continuer la cellule actuelle
                current_jour_count += 1
        
        # Fermer la dernière cellule
        if current_jour is not None:
            # Déterminer la couleur selon le modèle dominant dans cette période
            dominant_source = 'AROME' if any(source[i] == 'AROME' for i in range(len(source) - current_jour_count, len(source))) else 'WG'
            color = "#d1451f" if dominant_source == 'AROME' else "#000000"
            current_jour_complet = get_jour_complet(current_jour.split()[0]) + " " + current_jour.split()[1] if current_jour else current_jour
            style_attr = f' style="color: {color}; font-weight: bold;"'
            colspan_attr = f' colspan="{current_jour_count}"' if current_jour_count > 1 else ''
            jour_cells.append(f'<th{style_attr}{colspan_attr}>{current_jour_complet}</th>')
        
        # Ajouter toutes les cellules de jour
        html += ''.join(jour_cells)
        
        html += """
                        </tr>
                        <tr>
                            <th style="font-weight: bold;">Heures</th>
        """
        for i, h in enumerate(heures):
            _, heure = parse_heure(h)
            color = "#d1451f" if source[i] == 'AROME' else "#000000"
            border_style = get_border_style(i)
            style_attr = f' style="color: {color}; font-weight: bold; {border_style}"' if border_style else f' style="color: {color}; font-weight: bold;"'
            html += f'<th{style_attr}>{heure}</th>'
        html += """
                </tr>
            </thead>
            <tbody>
        """
        
        def row(label, vals, cell_class="", is_bold=False, bg_classes=None):
            r = f'<tr><td><b>{label}</b></td>'
            for i, v in enumerate(vals):
                border_style = get_border_style(i)
                bg_class = bg_classes[i] if bg_classes and i < len(bg_classes) else ""
                
                # Combiner les classes CSS
                all_classes = f"{cell_class} {bg_class}".strip()
                
                if border_style:
                    if is_bold:
                        style_attr = f' style="{border_style}; font-weight: bold;"'
                    else:
                        style_attr = f' style="{border_style}"'
                else:
                    if is_bold:
                        style_attr = ' style="font-weight: bold;"'
                    else:
                        style_attr = ''
                
                class_attr = f' class="{all_classes}"' if all_classes else ""
                r += f'<td{class_attr}{style_attr}>{v}</td>'
            r += '</tr>'
            return r

        # Calculer les styles de fond pour chaque heure (séparément pour vent et rafales)
        vent_bg_styles = []
        rafales_bg_styles = []
        direction_is_good = []
        for i, (v, r, d, p, h) in enumerate(zip(vent, rafales, direction, pluie, heures)):
            jour_str = get_jour_from_heure(h)
            vent_bg_style = get_wind_background_class(site_id, v, r, d, jour_str, h, p, "vent")
            rafales_bg_style = get_wind_background_class(site_id, v, r, d, jour_str, h, p, "rafales")
            # Vérification direction favorable
            criteria = get_criteria_for_site_and_date(site_id, jour_str)
            is_good = False
            if criteria:
                try:
                    direction_val = float(d) if d else 0
                    for dir_min, dir_max in criteria["direction"]:
                        if dir_min <= dir_max:
                            if dir_min <= direction_val <= dir_max:
                                is_good = True
                                break
                        else:
                            if direction_val >= dir_min or direction_val <= dir_max:
                                is_good = True
                                break
                except ValueError:
                    pass
            vent_bg_styles.append(vent_bg_style)
            rafales_bg_styles.append(rafales_bg_style)
            direction_is_good.append(is_good)
        
        # Vent (en gras avec couleurs progressives)
        html += self._generate_wind_row('Vent (Nds)', vent, vent_bg_styles, get_border_style)
        
        # Rafales (en gras avec couleurs progressives)
        html += self._generate_wind_row('Rafales (Nds)', rafales, rafales_bg_styles, get_border_style)
        
        # Direction (flèches colorées)
        direction_cells = []
        for i, d in enumerate(direction):
            try:
                angle = float(d)
                css_angle = angle + 180
                color = "#32CD32" if direction_is_good[i] else "#222"
                direction_html = f'<span class="wind-direction" style="transform: rotate({css_angle}deg); display: inline-block; font-size: 1.7em; color: {color};">↑</span>'
            except (ValueError, TypeError):
                direction_html = d if d else ""
            direction_cells.append(direction_html)
        html += row('Direction', direction_cells, 'dir-cell')
        
        # Nuages synthétisés (maximum des 3 niveaux)
        html += self._generate_synthetic_cloud_row('Nuages', nuages_haut, nuages_moyen, nuages_bas, pluie, temp, heures, get_border_style)
        
        # Précipitations en bleu
        html += self._generate_rain_row('Précipitations', pluie, get_border_style)
        
        # Température avec échelle de couleur
        html += self._generate_temperature_row('Température', temp, get_border_style)
        
        # Calculer les notes avec étoiles
        notes = []
        for i, (v, r, d, p, h, t) in enumerate(zip(vent, rafales, direction, pluie, heures, temp)):
            jour_str = get_jour_from_heure(h)
            note = calculate_note(site_id, v, r, d, jour_str, h, p, t)
            notes.append(note)
        
        # Note avec étoiles
        html += row('Note', notes)
        html += """
            </tbody>
        </table>
        """
        return html


def open_in_firefox(html_file: str) -> None:
    """Ouvre le fichier HTML dans Firefox."""
    logger = get_logger()
    try:
        # Essayer d'ouvrir avec Firefox spécifique avec paramètre pour forcer le rechargement
        subprocess.Popen([FIREFOX_PATH, html_file, "--new-tab"])
        logger.firefox_opened(os.path.basename(html_file))
    except Exception as e:
        try:
            # Fallback: ouvrir avec le navigateur par défaut
            webbrowser.open(f"file://{os.path.abspath(html_file)}")
            logger.firefox_opened(os.path.basename(html_file))
        except Exception as e2:
            logger.error(f"Impossible d'ouvrir Firefox: {str(e)}")


def main() -> None:
    """Fonction principale."""
    logger = init_logger()
    
    logger.viewer_start()
    
    # Lire les données CSV
    reader = CSVDataReader(CSV_FOLDER)
    data = reader.read_all_csv_files()
    
    if not data:
        logger.no_data_found()
        return
    
    # Trier les données selon l'ordre des sites dans config.py
    sorted_data = {}
    for site_id in SITES:
        site_id_str = str(site_id)
        if site_id_str in data:
            sorted_data[site_id_str] = data[site_id_str]
    
    # Ajouter les sites non présents dans la config à la fin
    for site_id, site_data in data.items():
        if site_id not in sorted_data:
            sorted_data[site_id] = site_data
    
    # Générer la page HTML
    generator = HTMLGenerator(sorted_data)
    html_content = generator.generate_html()
    
    # Supprimer les anciens fichiers HTML pour forcer le rechargement du cache
    for old_file in glob.glob(os.path.join(CSV_FOLDER, "FR_*.html")):
        try:
            os.remove(old_file)
            logger.info(f"Ancien fichier HTML supprimé: {os.path.basename(old_file)}")
        except Exception as e:
            logger.warning(f"Impossible de supprimer l'ancien fichier {os.path.basename(old_file)}: {str(e)}")
    
    # Générer le nom du fichier avec la date et l'heure
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M")
    html_filename = f"FR_{date_str}_{time_str}.html"
    html_file = os.path.join(CSV_FOLDER, html_filename)
    
    try:
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.html_generated(os.path.basename(html_file))
        
        # Ouvrir dans Firefox
        open_in_firefox(html_file)
        
        logger.viewer_finish()
        
    except Exception as e:
        logger.error(f"Erreur lors de la generation HTML: {str(e)}")


if __name__ == "__main__":
    main() 
