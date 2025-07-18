@echo off
echo Lancement du scraper Windguru...
set WORKFLOW_START_TIME=%date:~-4%-%date:~3,2%-%date:~0,2% %time:~0,2%:%time:~3,2%:%time:~6,2% UTC
set WORKFLOW_TIMEZONE=Europe/Paris
python "Scripts_Python\windguru_csv_scraper.py"
python "Scripts_Python\csv_to_html_viewer.py" 
