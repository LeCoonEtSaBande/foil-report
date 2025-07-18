Windguru CSV Scraper & Foil Report
====================================

Description
-----------
Script Python pour récupérer les données météorologiques de Windguru et générer un visualiseur HTML moderne optimisé pour la pratique du foil.

Gestion centralisée des dates/heures
-----------------------------------
✅ Heure de lancement récupérée depuis GitHub Actions ou batch local
✅ Variables d'environnement WORKFLOW_START_TIME et WORKFLOW_TIMEZONE
✅ Heure écrite dans les CSV et lue par le visualiseur
✅ Suppression des doublons de calcul d'heure
✅ Format cohérent : dd/mm/yyyy à hh:mm

Fonctionnalités principales
--------------------------
✅ Scraping automatique des données Windguru (AROME 1.3km + WG)
✅ Fusion intelligente des modèles sans doublons
✅ Visualiseur HTML moderne avec design 16:9
✅ Système de notation intelligent (0-3 étoiles)
✅ Critères de vent configurables par site
✅ Interface responsive avec scroll horizontal

Structure du projet
------------------
Scraping/
├── Scripts_Python/
│   ├── windguru_csv_scraper.py  # Scraper principal
│   ├── csv_to_html_viewer.py    # Visualiseur Foil Report
│   ├── logger.py                # Système de logs
│   └── config.py                # Configuration + critères
├── Drivers/
│   └── geckodriver.exe          # Pilote Firefox
├── Donnees_Temporaires/
│   ├── Donnees_WG_*.csv         # Données source
│   └── HTML_from_csv_data_*.html # Rapports générés
└── WindScraper.bat              # Lanceur Windows

Prérequis
---------
- Python 3.x
- Firefox installé
- Geckodriver dans Drivers/
- Requirements (installé automatiquement via requirements.txt)

Installation
-----------
pip install -r requirements.txt

Configuration
------------
Modifiez Scripts_Python/config.py pour personnaliser les sites et critères :

### Sites à surveiller
```python
SITES = [
    72305,  # Le Grand Large Lyon
    314,    # Lac du Monteynard  
    179,    # Lac Léman
    # 67890,  # Nouveau site (décommentez pour ajouter)
]
```

### Critères de vent par site
Chaque site peut avoir des critères différents selon les saisons, exemples :

**Site 179 (Lac Léman)** - Toute l'année :
- Direction : 320°-40° (Nord-Ouest à Nord-Est)
- Vent moyen : 14 nœuds
- Vent bon : 17 nœuds  
- Vent très bon : 20 nœuds

**Site 314 (Lac du Monteynard)** - Saisonnier :
- Octobre-Mai : Direction 320°-40° OU 140°-220°, Vent 12/15/18 nœuds
- Juin-Septembre : Direction 320°-40° seulement, Vent 9/12/15 nœuds

**Site 72305 (Grand Large Lyon)** - Toute l'année :
- Direction : 320°-40° OU 140°-220°
- Vent moyen : 9 nœuds
- Vent bon : 11 nœuds
- Vent très bon : 15 nœuds

Utilisation
-----------
Méthode 1 : Double-clic sur WindScraper.bat

Méthode 2 : Ligne de commande
python Scripts_Python/windguru_csv_scraper.py
python Scripts_Python/csv_to_html_viewer.py

Fonctionnalités du visualiseur
-----------------------------
📊 Données affichées :
- Vent, Rafales avec échelle de couleur progressive
- Direction avec flèches rotatives
- Nuages avec symboles
- Température et Précipitations
- Note avec étoiles (⭐ à ⭐⭐⭐) selon critères

Système de notation
------------------
Note = A × B × C × D × E

**A = Note vent (basée sur vent ET rafales)** :
- 3 si vent ≥ vent_tres_bien
- 2 si vent ≥ vent_bien ET rafales ≥ vent_tres_bien
- 1 si (vent ≥ vent_moyen ET rafales > vent_bien) OU (vent ≥ vent_bien ET rafales < vent_tres_bien)
- 0 sinon

**B = Direction favorable** :
- 1 si direction dans les critères du site
- 0 sinon

**C = Période jour** :
- 1 si heure entre 7h30 et 20h
- 0 sinon (nuit)

**D = Pas de précipitations** :
- 1 si précipitations = 0
- 0 sinon

**E = Température favorable** :
- 1 si température > 5°C
- 0 sinon

**Résultat** : 0 à 3 étoiles empilées verticalement selon la qualité des conditions

🎨 Interface :
- Design 16:9 responsive
- Colonnes personnalisables (110px/20px)
- Bordures orange entre modèles
- Bordures grises entre jours
- En-têtes fixes

Système de logs
--------------
Symboles colorés pour le suivi :
🔵 Info | ✅ Succès | ❌ Erreur | ⚠️ Avertissement
⏳ Chargement | 🚀 Démarrage | 📊 Données | 💾 Fichier

Exemple :
[21:29:09] 🚀 Démarrage du scraping Windguru
[21:29:36] 📊 Site 72305: Données extraites (111 points)
[21:29:36] ✅ Fichier sauvegardé: Donnees_WG_72305.csv

Dépannage
---------
❌ "geckodriver not found" → Vérifiez Drivers/geckodriver.exe
❌ "Firefox not found" → Modifiez FIREFOX_PATH dans config.py
❌ Erreur de scraping → Vérifiez connexion internet
❌ Données AROME manquantes → Normal, WG utilisé en fallback

Ajout d'un nouveau site
----------------------
1. **Trouvez l'ID sur Windguru** :
   - Allez sur windguru.cz
   - Cherchez votre spot
   - L'ID est dans l'URL (ex: windguru.cz/station/72305)

2. **Ajoutez dans config.py** :
   ```python
   SITES = [
       72305,  # Site existant
       12345,  # Nouveau site
   ]
   ```

3. **Ajoutez les critères dans SITE_CRITERIA** :
   ```python
   12345: {
       "toute_annee": {
           "direction": [(315, 45)],  # Nord-Ouest à Nord-Est
           "vent_moyen": 10,
           "vent_bien": 13,
           "vent_tres_bien": 16
       }
   }
   ```

4. **Relancez le scraper** pour récupérer les nouvelles données

Personnalisation
---------------
- **Largeurs colonnes** : Modifiez width dans csv_to_html_viewer.py
- **Critères de vent** : Modifiez SITE_CRITERIA dans config.py (recommandé)
- **Périodes jour/nuit** : Modifiez is_night_time() dans csv_to_html_viewer.py
- **Design** : Modifiez les styles CSS dans generate_html()
- **Échelle de couleurs** : Modifiez get_wind_color_progressive() pour les couleurs du vent
- **Système de notation** : Modifiez calculate_note() pour changer la logique des étoiles

Support
-------
Vérifiez les logs pour identifier les problèmes.
Le script gère automatiquement les modèles disponibles. 
