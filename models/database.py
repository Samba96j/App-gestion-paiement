import sqlite3
import logging
from utils.config import DATABASE
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.db_path = DATABASE['name']
        self.init_db()
    
    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Création des tables
            cursor.executescript('''
                CREATE TABLE IF NOT EXISTS paiements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nom TEXT NOT NULL,
                    prenom TEXT NOT NULL,
                    classe TEXT NOT NULL,
                    montant REAL NOT NULL,
                    mois TEXT NOT NULL,
                    date_paiement TEXT NOT NULL,
                    heure_paiement TEXT NOT NULL,
                    methode_paiement TEXT NOT NULL,
                    statut TEXT NOT NULL,
                    notes TEXT
                );
                
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    is_admin BOOLEAN NOT NULL DEFAULT 0,
                    expiration TEXT NOT NULL
                );
            ''')
            conn.commit()
            logger.info("Base de données initialisée avec succès")