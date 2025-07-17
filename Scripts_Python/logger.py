"""
Logger avance pour le projet Windguru Scraper
Systeme de logs avec symboles colores et compteur de progression
"""

import sys
import time
from datetime import datetime
from typing import Optional

# === Symboles et messages de log ===
LOG_SYMBOLS = {
    'info': '🔵',      # Bleu pour les informations
    'success': '✅',    # Vert pour les succes
    'error': '❌',      # Rouge pour les erreurs
    'warning': '⚠️',    # Orange pour les avertissements
    'loading': '⏳',    # Sablier pour le chargement
    'start': '🚀',      # Fusee pour le demarrage
    'finish': '🏁',     # Drapeau pour la fin
    'data': '📊',       # Graphique pour les donnees
    'file': '💾',       # Disquette pour les fichiers
    'browser': '🌐',    # Globe pour le navigateur
    'site': '📍',       # Pin pour les sites
    'model': '📈',      # Graphique pour les modeles
    'progress': '📋'    # Presse-papiers pour le progres
}

LOG_MESSAGES = {
    'scraping_start': 'Demarrage du scraping Windguru',
    'scraping_finish': 'Scraping termine',
    'site_start': 'Traitement du site',
    'site_success': 'Site traite avec succes',
    'site_error': 'Erreur lors du traitement du site',
    'data_extracted': 'Donnees extraites',
    'file_saved': 'Fichier sauvegarde',
    'browser_start': 'Demarrage du navigateur',
    'browser_close': 'Fermeture du navigateur',
    'model_found': 'Modele trouve',
    'model_missing': 'Modele manquant',
    'loading_page': 'Chargement de la page',
    'waiting_data': 'Attente des donnees',
    'processing_data': 'Traitement des donnees',
    'saving_data': 'Sauvegarde des donnees',
    'viewer_start': 'Demarrage du visualiseur HTML',
    'viewer_finish': 'Visualiseur HTML termine',
    'no_data_found': 'Aucune donnee trouvee',
    'data_loaded': 'Donnees chargees',
    'html_generated': 'Page HTML generee',
    'firefox_opened': 'Firefox ouvert'
}

# === Couleurs ANSI pour le terminal ===
COLORS = {
    'reset': '\033[0m',
    'bold': '\033[1m',
    'red': '\033[91m',
    'green': '\033[92m',
    'yellow': '\033[93m',
    'blue': '\033[94m',
    'magenta': '\033[95m',
    'cyan': '\033[96m',
    'white': '\033[97m',
    'gray': '\033[90m'
}


class WindguruLogger:
    """Classe de logging avancee avec symboles colores et compteur de progression."""
    
    def __init__(self, total_sites: int = 0):
        self.total_sites = total_sites
        self.current_site = 0
        self.start_time = None
        
    def _print_log(self, symbol: str, message: str, color: str = 'white', bold: bool = False):
        """Affiche un message de log avec symbole et couleur."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        color_code = COLORS.get(color, '')
        bold_code = COLORS.get('bold', '') if bold else ''
        reset_code = COLORS.get('reset', '')
        
        log_line = f"{color_code}{bold_code}[{timestamp}] {symbol} {message}{reset_code}"
        print(log_line)
        sys.stdout.flush()  # Force l'affichage immediat
    
    def start_scraping(self):
        """Log du demarrage du scraping."""
        self.start_time = time.time()
        self._print_log(
            LOG_SYMBOLS['start'],
            LOG_MESSAGES['scraping_start'],
            'cyan',
            True
        )
    
    def finish_scraping(self):
        """Log de la fin du scraping."""
        if self.start_time:
            duration = time.time() - self.start_time
            self._print_log(
                LOG_SYMBOLS['finish'],
                f"{LOG_MESSAGES['scraping_finish']} ({duration:.1f}s)",
                'green',
                True
            )
    
    def start_site(self, site_id: int, site_name: str = ""):
        """Log du debut du traitement d'un site."""
        self.current_site += 1
        site_info = f"Site {site_id}"
        if site_name and site_name != f"Site {site_id}":
            site_info += f" ({site_name})"
        
        self._print_log(
            LOG_SYMBOLS['site'],
            f"{self.current_site}/{self.total_sites} - {LOG_MESSAGES['site_start']}: {site_info}",
            'blue',
            True
        )
    
    def site_success(self, site_id: int, models_found: list):
        """Log du succes du traitement d'un site."""
        models_str = ", ".join(models_found) if models_found else "aucun"
        self._print_log(
            LOG_SYMBOLS['success'],
            f"Site {site_id}: {LOG_MESSAGES['site_success']} - Modeles: {models_str}",
            'green'
        )
    
    def site_error(self, site_id: int, error_msg: str = ""):
        """Log d'erreur lors du traitement d'un site."""
        error_info = f" - {error_msg}" if error_msg else ""
        self._print_log(
            LOG_SYMBOLS['error'],
            f"Site {site_id}: {LOG_MESSAGES['site_error']}{error_info}",
            'red'
        )
    
    def browser_start(self):
        """Log du demarrage du navigateur."""
        self._print_log(
            LOG_SYMBOLS['browser'],
            LOG_MESSAGES['browser_start'],
            'cyan'
        )
    
    def browser_close(self):
        """Log de la fermeture du navigateur."""
        self._print_log(
            LOG_SYMBOLS['browser'],
            LOG_MESSAGES['browser_close'],
            'gray'
        )
    
    def loading_page(self, site_id: int, current_site: int = 0, total_sites: int = 0):
        """Log du chargement d'une page."""
        progress = f"{current_site}/{total_sites} - " if current_site > 0 and total_sites > 0 else ""
        self._print_log(
            LOG_SYMBOLS['loading'],
            f"{progress}Site {site_id}: {LOG_MESSAGES['loading_page']}",
            'yellow'
        )
    
    def waiting_data(self, site_id: int, current_site: int = 0, total_sites: int = 0):
        """Log de l'attente des donnees."""
        progress = f"{current_site}/{total_sites} - " if current_site > 0 and total_sites > 0 else ""
        self._print_log(
            LOG_SYMBOLS['loading'],
            f"{progress}Site {site_id}: {LOG_MESSAGES['waiting_data']}",
            'yellow'
        )
    
    def model_found(self, site_id: int, model_name: str):
        """Log de la decouverte d'un modele."""
        self._print_log(
            LOG_SYMBOLS['model'],
            f"Site {site_id}: {LOG_MESSAGES['model_found']} - {model_name}",
            'green'
        )
    
    def model_missing(self, site_id: int, model_name: str):
        """Log d'un modele manquant."""
        self._print_log(
            LOG_SYMBOLS['warning'],
            f"Site {site_id}: {LOG_MESSAGES['model_missing']} - {model_name}",
            'yellow'
        )
    
    def data_extracted(self, site_id: int, data_count: int):
        """Log de l'extraction des donnees."""
        self._print_log(
            LOG_SYMBOLS['data'],
            f"Site {site_id}: {LOG_MESSAGES['data_extracted']} ({data_count} points)",
            'cyan'
        )
    
    def saving_data(self, site_id: int):
        """Log de la sauvegarde des donnees."""
        self._print_log(
            LOG_SYMBOLS['file'],
            f"Site {site_id}: {LOG_MESSAGES['saving_data']}",
            'magenta'
        )
    
    def file_saved(self, filename: str):
        """Log de la sauvegarde reussie d'un fichier."""
        self._print_log(
            LOG_SYMBOLS['success'],
            f"{LOG_MESSAGES['file_saved']}: {filename}",
            'green'
        )
    
    def viewer_start(self):
        """Log du demarrage du visualiseur HTML."""
        self._print_log(
            LOG_SYMBOLS['data'],
            LOG_MESSAGES['viewer_start'],
            'cyan',
            True
        )
    
    def viewer_finish(self):
        """Log de la fin du visualiseur HTML."""
        self._print_log(
            LOG_SYMBOLS['finish'],
            LOG_MESSAGES['viewer_finish'],
            'green'
        )
    
    def no_data_found(self):
        """Log quand aucune donnee n'est trouvee."""
        self._print_log(
            LOG_SYMBOLS['warning'],
            LOG_MESSAGES['no_data_found'],
            'yellow'
        )
    
    def data_loaded(self, site_count: int):
        """Log du chargement des donnees."""
        self._print_log(
            LOG_SYMBOLS['data'],
            f"{LOG_MESSAGES['data_loaded']} ({site_count} sites)",
            'cyan'
        )
    
    def html_generated(self, filename: str):
        """Log de la generation de la page HTML."""
        self._print_log(
            LOG_SYMBOLS['file'],
            f"{LOG_MESSAGES['html_generated']}: {filename}",
            'green'
        )
    
    def firefox_opened(self, filename: str):
        """Log de l'ouverture de Firefox."""
        self._print_log(
            LOG_SYMBOLS['browser'],
            f"{LOG_MESSAGES['firefox_opened']}: {filename}",
            'green'
        )
    
    def info(self, message: str):
        """Log d'information generale."""
        self._print_log(
            LOG_SYMBOLS['info'],
            message,
            'blue'
        )
    
    def warning(self, message: str):
        """Log d'avertissement."""
        self._print_log(
            LOG_SYMBOLS['warning'],
            message,
            'yellow'
        )
    
    def error(self, message: str):
        """Log d'erreur."""
        self._print_log(
            LOG_SYMBOLS['error'],
            message,
            'red'
        )
    
    def success(self, message: str):
        """Log de succes."""
        self._print_log(
            LOG_SYMBOLS['success'],
            message,
            'green'
        )


# Instance globale du logger
logger = None


def init_logger(total_sites: int = 0):
    """Initialise le logger global."""
    global logger
    logger = WindguruLogger(total_sites)
    return logger


def get_logger() -> WindguruLogger:
    """Retourne l'instance du logger global."""
    global logger
    if logger is None:
        logger = WindguruLogger()
    return logger 