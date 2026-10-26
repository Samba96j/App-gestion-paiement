import sys
import os
import json 
import csv  
# Remplacez les imports PyQt6 par PyQt5
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QComboBox,
    QDateEdit, QTabWidget, QMessageBox, QFormLayout, QGroupBox, QTextEdit,
    QDialog, QInputDialog, QSpinBox, QCheckBox, QSystemTrayIcon,
    QScrollArea, QFrame, QBoxLayout, QHeaderView, QSizePolicy
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QIcon, QPixmap  # Ajoutez QPixmap ici

# Le reste du code reste identique, mais remplacez tous les 'PyQt6' par 'PyQt5'
import logging
import logging.config
from datetime import datetime, timedelta
from functools import partial
from collections import defaultdict  # Ajout nécessaire pour les statistiques

# Nouveaux imports
from models.database import Database
from utils.cache import Cache
from utils.pagination import Paginator
from utils.pdf_generator import PDFGenerator
from utils.charts import ChartGenerator
from utils.notifications import NotificationManager
from utils.config import LOGGING, DATABASE, CACHE, BASE_DIR

# Configuration du logging
logging.config.dictConfig(LOGGING)
logger = logging.getLogger(__name__)

# Constantes
STATUTS = ["payé", "impayé", "partiel", "remboursé"]
METHODES_PAIEMENT = ["Espèces", "Chèque", "Virement", "Carte bancaire", "Mobile Money"]
TEMPS_ACCES_DEFAUT = 24  # heures
DATA_DIR = os.path.join(BASE_DIR, "data")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
EXPORT_DIR = os.path.join(DATA_DIR, "exports")
FICHIER_UTILISATEURS = os.path.join(DATA_DIR, "utilisateurs.json")
FICHIER_DONNEES = os.path.join(DATA_DIR, "paiements.csv")
FICHIER_SAUVEGARDE = os.path.join(BACKUP_DIR, "paiements_{}.csv")
CHAMPS = ["id", "nom", "prenom", "classe", "montant", "mois", "methode_paiement", "statut", "date_paiement", "heure_paiement", "notes"]  # Ajout des champs
COLONNES_TABLEAU = ["id", "nom", "prenom", "classe", "montant", "mois", "statut", "date_paiement"]  # Ordre des colonnes affichées
ICON_DIR = os.path.join(BASE_DIR, "icons")
LARGEUR_BASCULE = 1180  # sous cette largeur, les formulaires passent sur une seule colonne


def icone(nom_fichier):
    return QIcon(os.path.join(ICON_DIR, nom_fichier))


def chemin_icone_css(nom_fichier):
    # Qt attend des séparateurs "/" dans les feuilles de style
    return os.path.join(ICON_DIR, nom_fichier).replace("\\", "/")


def formater_montant(valeur):
    return f"{valeur:,.0f} FCFA".replace(",", " ")

BUTTON_STYLE = """
QPushButton {
    background-color: #2196F3;
    color: white;
    font-size: 12px;
    font-weight: bold;
    border-radius: 8px;
    padding: 8px 16px;
    min-width: 110px;
    min-height: 30px;
}
QPushButton:hover {
    background-color: #1976D2;
}
QPushButton:pressed {
    background-color: #0D47A1;
}
QPushButton:disabled {
    background-color: #BDBDBD;
}

QPushButton#danger {
    background-color: #F44336;
}
QPushButton#danger:hover {
    background-color: #D32F2F;
}

QPushButton#success {
    background-color: #4CAF50;
}
QPushButton#success:hover {
    background-color: #388E3C;
}
"""

class Utilisateur:
    def __init__(self, username, password, is_admin=False, expiration=None):
        self.username = username
        self.password = password
        self.is_admin = is_admin
        self.expiration = expiration or (datetime.now() + timedelta(hours=TEMPS_ACCES_DEFAUT)).isoformat()
    
    def est_valide(self):
        try:
            return datetime.now() < datetime.fromisoformat(self.expiration)
        except (TypeError, ValueError):
            return False
    
    def to_dict(self):
        return {
            "username": self.username,
            "password": self.password,
            "is_admin": self.is_admin,
            "expiration": self.expiration
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            data["username"],
            data["password"],
            data.get("is_admin", False),
            data.get("expiration")
        )

class GestionUtilisateurs:
    def __init__(self):
        self.utilisateurs = []
        self.charger_utilisateurs()
        self.utilisateur_actuel = None
    
    def charger_utilisateurs(self):
        try:
            with open(FICHIER_UTILISATEURS, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.utilisateurs = [Utilisateur.from_dict(u) for u in data]
        except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError):
            self.utilisateurs = []
        self.garantir_admin_valide()
    
    def garantir_admin_valide(self):
        """Évite le verrouillage total : le compte admin est recréé ou renouvelé s'il a expiré."""
        admin = next((u for u in self.utilisateurs if u.username == "admin"), None)
        modifie = False
        if admin is None:
            admin = Utilisateur("admin", "admin123", True)
            self.utilisateurs.insert(0, admin)
            modifie = True
        elif not admin.est_valide():
            admin.expiration = (datetime.now() + timedelta(hours=TEMPS_ACCES_DEFAUT)).isoformat()
            modifie = True
        if modifie:
            self.sauvegarder_utilisateurs()
    
    def sauvegarder_utilisateurs(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(FICHIER_UTILISATEURS, "w", encoding="utf-8") as f:
            data = [u.to_dict() for u in self.utilisateurs]
            json.dump(data, f, indent=4, ensure_ascii=False)
    
    def authentifier(self, username, password):
        for user in self.utilisateurs:
            if user.username == username and user.password == password and user.est_valide():
                self.utilisateur_actuel = user
                return True
        return False
    
    def deconnecter(self):
        self.utilisateur_actuel = None
    
    def creer_utilisateur(self, username, password, is_admin=False, duree_heures=TEMPS_ACCES_DEFAUT):
        if any(u.username == username for u in self.utilisateurs):
            return False
        expiration = datetime.now() + timedelta(hours=duree_heures)
        nouvel_utilisateur = Utilisateur(username, password, is_admin, expiration.isoformat())
        self.utilisateurs.append(nouvel_utilisateur)
        self.sauvegarder_utilisateurs()
        return True
    
    def supprimer_utilisateur(self, username):
        if username == "admin":
            return False
        self.utilisateurs = [u for u in self.utilisateurs if u.username != username]
        self.sauvegarder_utilisateurs()
        return True
    
    def lister_utilisateurs(self):
        return [u for u in self.utilisateurs if u.username != "admin"]

class GestionPaiements:
    def __init__(self):
        self.paiements = []
        self.initialiser_fichier()
        self.charger_donnees()
    
    def initialiser_fichier(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)
        if not os.path.exists(FICHIER_DONNEES):
            with open(FICHIER_DONNEES, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=CHAMPS)
                writer.writeheader()
    
    def charger_donnees(self):
        try:
            with open(FICHIER_DONNEES, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.paiements = [row for row in reader]
        except FileNotFoundError:
            self.paiements = []
    
    def sauvegarder_donnees(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)
        with open(FICHIER_DONNEES, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CHAMPS, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.paiements)
        
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(FICHIER_SAUVEGARDE.format(date_str), mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CHAMPS, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.paiements)
    
    def generer_id(self):
        ids = [int(p['id']) for p in self.paiements if 'id' in p and p['id'].isdigit()]
        return str(max(ids) + 1) if ids else "1"
    
    def ajouter_paiement(self, paiement):
        paiement['id'] = self.generer_id()
        maintenant = datetime.now()
        paiement['date_paiement'] = maintenant.strftime("%d/%m/%Y")
        paiement['heure_paiement'] = maintenant.strftime("%H:%M:%S")
        self.paiements.append(paiement)
        self.sauvegarder_donnees()
        return paiement['id']
    
    def modifier_paiement(self, id_paiement, nouvelles_valeurs):
        for i, paiement in enumerate(self.paiements):
            if paiement['id'] == id_paiement:
                maintenant = datetime.now()
                nouvelles_valeurs['date_paiement'] = maintenant.strftime("%d/%m/%Y")
                nouvelles_valeurs['heure_paiement'] = maintenant.strftime("%H:%M:%S")
                self.paiements[i] = {**paiement, **nouvelles_valeurs}
                self.sauvegarder_donnees()
                return True
        return False
    
    def rechercher_paiements(self, critere, valeur):
        valeur = valeur.strip().lower()
        if critere == "id":
            return [p for p in self.paiements if p['id'] == valeur]
        elif critere == "nom":
            return [p for p in self.paiements if p['nom'].lower() == valeur]
        elif critere == "classe":
            return [p for p in self.paiements if p['classe'].lower() == valeur]
        elif critere == "mois":
            return [p for p in self.paiements if p['mois'].lower() == valeur]
        elif critere == "statut":
            return [p for p in self.paiements if p['statut'].lower() == valeur]
        return []
    
    @staticmethod
    def _montant_numerique(paiement):
        try:
            return float(str(paiement.get('montant', '')).replace(',', '.').replace(' ', ''))
        except (TypeError, ValueError):
            return 0.0
    
    def get_statistiques(self):
        stats = {
            "total": len(self.paiements),
            "montant_total": sum(self._montant_numerique(p) for p in self.paiements if p.get('statut') == 'payé'),
            "par_classe": defaultdict(list),
            "par_statut": defaultdict(int)
        }
        for p in self.paiements:
            stats["par_classe"][p.get('classe') or "Non renseignée"].append(self._montant_numerique(p))
            stats["par_statut"][p.get('statut') or "impayé"] += 1
        return stats

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialisation des nouvelles fonctionnalités
        self.db = Database()
        self.cache = Cache()
        self.notification_manager = NotificationManager()
        self.chart_generator = ChartGenerator()
        self.pdf_generator = PDFGenerator()
        self.paginator = None
        self.current_page = 1
        self.items_per_page = CACHE['max_size']
        
        # Initialisation existante
        self.gestion_utilisateurs = GestionUtilisateurs()
        self.gestion = GestionPaiements()
        
        # Configuration de l'interface
        if not self.authentifier_utilisateur():
            sys.exit()
            
        # Configuration de la fenêtre
        self.setWindowTitle("Gestion des Paiements Scolaires")
        self.conteneurs_responsives = []
        self.mode_etroit = None
        
        # Initialisation de l'interface
        self.init_ui()
        self.adapter_a_ecran()
        logger.info("Application démarrée avec succès")
    
    def adapter_a_ecran(self):
        """Dimensionne la fenêtre selon l'écran disponible (petit portable, grand moniteur, haute résolution)."""
        ecran = QApplication.primaryScreen()
        if ecran is None:
            self.resize(1200, 800)
            return
        zone = ecran.availableGeometry()
        largeur = max(720, min(int(zone.width() * 0.92), 1500))
        hauteur = max(520, min(int(zone.height() * 0.92), 980))
        self.resize(largeur, hauteur)
        self.setMinimumSize(min(720, zone.width()), min(520, zone.height()))
        self.rafraichir_onglets()
    
    def ecran_etroit(self):
        ecran = QApplication.primaryScreen()
        if ecran is None:
            return False
        zone = ecran.availableGeometry()
        return zone.width() < 1500 or zone.height() < 900
    
    def taille_dialogue(self, largeur, hauteur):
        """Réduit la taille d'une boîte de dialogue si l'écran est plus petit."""
        ecran = QApplication.primaryScreen()
        if ecran is None:
            return largeur, hauteur
        zone = ecran.availableGeometry()
        return (min(largeur, int(zone.width() * 0.9)), min(hauteur, int(zone.height() * 0.9)))
    
    def creer_onglet_defilable(self, titre):
        """Onglet dont le contenu défile : indispensable sur les écrans peu hauts."""
        contenu = QWidget()
        zone = QScrollArea()
        zone.setWidgetResizable(True)
        zone.setFrameShape(QFrame.NoFrame)
        zone.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        zone.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        zone.setWidget(contenu)
        self.tabs.addTab(zone, titre)
        return contenu
    
    def enregistrer_conteneur_responsive(self, conteneur):
        self.conteneurs_responsives.append(conteneur)
    
    def rendre_tableau_adaptatif(self, table, mode=None):
        """Les colonnes occupent toute la largeur disponible et les lignes restent lisibles."""
        entete = table.horizontalHeader()
        entete.setSectionResizeMode(QHeaderView.Stretch if mode is None else mode)
        entete.setMinimumSectionSize(70)
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        table.setMinimumHeight(180)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adapter_disposition()
    
    def adapter_disposition(self):
        """Bascule les formulaires à deux colonnes en une colonne sur écran étroit."""
        if not self.conteneurs_responsives:
            return
        etroit = self.width() < LARGEUR_BASCULE
        if etroit == self.mode_etroit:
            return
        self.mode_etroit = etroit
        direction = QBoxLayout.TopToBottom if etroit else QBoxLayout.LeftToRight
        for conteneur in self.conteneurs_responsives:
            conteneur.setDirection(direction)
            conteneur.invalidate()
        self.rafraichir_onglets()
    
    def rafraichir_onglets(self):
        """Force le recalcul de la hauteur des contenus défilables après un changement de disposition."""
        for index in range(self.tabs.count()):
            onglet = self.tabs.widget(index)
            if isinstance(onglet, QScrollArea) and onglet.widget() is not None:
                disposition = onglet.widget().layout()
                if disposition is not None:
                    disposition.activate()

    def update_table(self, data):
        # La signature évite de réafficher des données périmées après ajout/modification
        signature = hash(tuple(
            (p.get('id'), p.get('montant'), p.get('statut'), p.get('date_paiement'), p.get('heure_paiement'))
            for p in data
        ))
        cache_key = f"table_data_page_{self.current_page}_{signature}"
        cached_data = self.cache.get(cache_key)
        
        if cached_data:
            logger.debug("Utilisation des données en cache")
            paginated_data = cached_data
        else:
            logger.debug("Génération de nouvelles données paginées")
            self.paginator = Paginator(data, self.items_per_page)
            paginated_data = self.paginator.get_page(self.current_page)
            self.cache.set(cache_key, paginated_data)
        
        # Mise à jour du tableau
        self.result_table.setRowCount(0)
        for row, item in enumerate(paginated_data):
            self.result_table.insertRow(row)
            for col, champ in enumerate(COLONNES_TABLEAU):
                self.result_table.setItem(row, col, QTableWidgetItem(str(item.get(champ, ""))))
        
        # Mise à jour des contrôles de pagination
        self.update_pagination_controls()
        
        # Vérification des paiements en retard
        self.notification_manager.check_paiements_retard(data)

    def export_pdf(self):
        try:
            selected_items = self.result_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "Attention", "Veuillez sélectionner un paiement")
                return
            
            row = selected_items[0].row()
            paiement = self.get_row_data(row)
            
            output_path = f"recu_{paiement['id']}.pdf"
            self.pdf_generator.generate_receipt(paiement, output_path)
            
            QMessageBox.information(self, "Succès", f"Le reçu PDF a été généré: {output_path}")
            logger.info(f"Reçu PDF généré: {output_path}")
        except Exception as e:
            logger.error(f"Erreur lors de la génération du PDF: {e}")
            QMessageBox.critical(self, "Erreur", "Impossible de générer le PDF")

    def show_statistics_chart(self):
        try:
            stats = self.gestion.get_statistiques()
            
            # Génération du graphique circulaire
            data = [stats['par_statut'][status] for status in STATUTS]
            chart_data = self.chart_generator.generate_pie_chart(
                data=data,
                labels=STATUTS,
                title="Répartition des Paiements par Statut"
            )
            
            # Affichage du graphique dans une nouvelle fenêtre
            chart_dialog = QDialog(self)
            chart_dialog.setWindowTitle("Statistiques")
            layout = QVBoxLayout()
            chart_label = QLabel()
            chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            largeur, hauteur = self.taille_dialogue(600, 600)
            chart_label.setPixmap(
                QPixmap.fromImage(chart_data).scaled(
                    largeur, hauteur, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
            layout.addWidget(chart_label)
            chart_dialog.setLayout(layout)
            chart_dialog.exec()
            
            logger.info("Graphique statistique généré avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de la génération du graphique: {e}")
            QMessageBox.critical(self, "Erreur", "Impossible de générer le graphique")

    def authentifier_utilisateur(self):
        while True:
            username, ok1 = QInputDialog.getText(
                self, "Connexion", "Nom d'utilisateur:"
            )
            if not ok1:
                return False
            password, ok2 = QInputDialog.getText(
                self, "Connexion", "Mot de passe:", QLineEdit.EchoMode.Password
            )
            if not ok2:
                return False
            if self.gestion_utilisateurs.authentifier(username, password):
                QMessageBox.information(self, "Succès", "Connexion réussie!")
                return True
            else:
                QMessageBox.warning(self, "Erreur", "Identifiants incorrects ou compte expiré")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(12, 8, 12, 8)

        # Titre principal
        title_label = QLabel("GESTION DES PAIEMENTS SCOLAIRES")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #1976D2;
            padding: 12px 0 10px 0;
            border-bottom: 3px solid #1976D2;
            letter-spacing: 1px;
        """)
        self.main_layout.addWidget(title_label)

        # Icône
        icon_label = QLabel()
        icon_label.setPixmap(QPixmap(os.path.join(ICON_DIR, "school.png")).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(icon_label)

        # Création des onglets
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        barre_onglets = self.tabs.tabBar()
        barre_onglets.setExpanding(False)          # chaque onglet prend la largeur de son libellé
        barre_onglets.setElideMode(Qt.ElideNone)   # jamais de "..." dans les noms d'onglets
        barre_onglets.setUsesScrollButtons(True)
        self.main_layout.addWidget(self.tabs, 1)

        # Onglet 1 : Nouveau Paiement
        tab1 = self.creer_onglet_defilable("Nouveau Paiement")
        self.setup_enregistrement_tab(tab1)

        # Onglet 2 : Recherche/Modification
        tab2 = self.creer_onglet_defilable("Recherche/Modification")
        self.setup_recherche_tab(tab2)

        # Onglet 3 : Statistiques
        tab3 = self.creer_onglet_defilable("Statistiques")
        self.setup_statistiques_tab(tab3)

        # Onglet 4 : Liste par Classe
        tab4 = self.creer_onglet_defilable("Liste par Classe")
        self.setup_liste_classe_tab(tab4)

        # Onglet admin si admin connecté
        if self.gestion_utilisateurs.utilisateur_actuel and self.gestion_utilisateurs.utilisateur_actuel.is_admin:
            self.setup_admin_tab()

    def setup_enregistrement_tab(self, tab):
        layout = QVBoxLayout(tab)

        # Titre avec style amélioré
        title = QLabel("NOUVEAU PAIEMENT")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 17px;
            font-weight: bold;
            color: white;
            background: #1976D2;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0 20px 0;
        """)
        layout.addWidget(title)

        # Container principal avec deux colonnes (une seule si la fenêtre est étroite)
        main_container = QBoxLayout(QBoxLayout.LeftToRight)
        self.enregistrer_conteneur_responsive(main_container)

        # Colonne gauche - Informations obligatoires
        left_column = QVBoxLayout()
        form_group = QGroupBox("Informations de l'élève")
        form_group.setStyleSheet("""
            QGroupBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                      stop:0 #E3F2FD, stop:1 #FFFFFF);
                border: 2px solid #1976D2;
                border-radius: 10px;
                margin-top: 15px;
                padding: 20px;
                font-size: 13px;
            }
            QGroupBox::title {
                color: #1976D2;
                font-size: 14px;
                font-weight: bold;
                subcontrol-position: top center;
                padding: 5px 30px;
                background-color: white;
            }
        """)

        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setVerticalSpacing(20)

        # Champs de saisie avec style amélioré
        input_style = """
            QLineEdit {
                padding: 12px;
                border: 2px solid #90CAF9;
                border-radius: 6px;
                font-size: 13px;
                min-width: 250px;
                background: white;
            }
            QLineEdit:focus {
                border-color: #1976D2;
            }
        """

        self.nom_input = QLineEdit()
        self.nom_input.setPlaceholderText("Entrez le nom")
        self.nom_input.setStyleSheet(input_style)

        self.prenom_input = QLineEdit()
        self.prenom_input.setPlaceholderText("Entrez le prénom")
        self.prenom_input.setStyleSheet(input_style)

        self.classe_input = QLineEdit()
        self.classe_input.setPlaceholderText("Ex: 6E, 5E, 4E...")
        self.classe_input.setStyleSheet(input_style)

        self.montant_input = QLineEdit()
        self.montant_input.setPlaceholderText("Montant en FCFA")
        self.montant_input.setStyleSheet(input_style)

        self.mois_input = QLineEdit()
        self.mois_input.setPlaceholderText("Ex: Janvier, Février...")
        self.mois_input.setStyleSheet(input_style)

        # Labels avec style
        label_style = "QLabel { color: #1976D2; font-weight: bold; font-size: 12px; }"
        for row, (label, widget) in enumerate([
            ("Nom *", self.nom_input),
            ("Prénom *", self.prenom_input),
            ("Classe *", self.classe_input),
            ("Montant (FCFA) *", self.montant_input),
            ("Mois *", self.mois_input)
        ]):
            lbl = QLabel(label)
            lbl.setStyleSheet(label_style)
            form_layout.addRow(lbl, widget)

        form_group.setLayout(form_layout)
        left_column.addWidget(form_group)
        main_container.addLayout(left_column)

        # Colonne droite - Options supplémentaires
        right_column = QVBoxLayout()
        option_group = QGroupBox("Options de paiement")
        option_group.setStyleSheet("""
            QGroupBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                      stop:0 #F3E5F5, stop:1 #FFFFFF);
                border: 2px solid #7B1FA2;
                border-radius: 10px;
                margin-top: 15px;
                padding: 20px;
                font-size: 13px;
            }
            QGroupBox::title {
                color: #7B1FA2;
                font-size: 14px;
                font-weight: bold;
                subcontrol-position: top center;
                padding: 5px 30px;
                background-color: white;
            }
        """)

        option_layout = QFormLayout()
        option_layout.setSpacing(15)

        # Style pour les ComboBox
        combo_style = """
            QComboBox {
                padding: 12px;
                border: 2px solid #CE93D8;
                border-radius: 6px;
                font-size: 13px;
                min-width: 250px;
                background: white;
            }
            QComboBox::drop-down {
                border: none;
            }
        """

        self.methode_combo = QComboBox()
        self.methode_combo.addItems(METHODES_PAIEMENT)
        self.methode_combo.setStyleSheet(combo_style)

        self.statut_combo = QComboBox()
        self.statut_combo.addItems(STATUTS)
        self.statut_combo.setCurrentText("payé")
        self.statut_combo.setStyleSheet(combo_style)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Ajoutez des notes supplémentaires...")
        self.notes_input.setMaximumHeight(100)
        self.notes_input.setStyleSheet("""
            QTextEdit {
                padding: 12px;
                border: 2px solid #CE93D8;
                border-radius: 6px;
                font-size: 13px;
                background: white;
            }
        """)

        option_layout.addRow(QLabel("Méthode de paiement :"), self.methode_combo)
        option_layout.addRow(QLabel("Statut :"), self.statut_combo)
        option_layout.addRow(QLabel("Notes :"), self.notes_input)

        option_group.setLayout(option_layout)
        right_column.addWidget(option_group)
        main_container.addLayout(right_column)

        # Ajouter le container principal au layout
        layout.addLayout(main_container)

        # Boutons d'action
        buttons_container = QHBoxLayout()
        buttons_container.addStretch()

        save_btn = QPushButton(icone("save.png"), "Enregistrer")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 13px;
                font-weight: bold;
                border-radius: 8px;
                padding: 12px 30px;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self.enregistrer_paiement)

        receipt_btn = QPushButton(icone("print.png"), "Générer Reçu")
        receipt_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 13px;
                font-weight: bold;
                border-radius: 8px;
                padding: 12px 30px;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        receipt_btn.setCursor(Qt.PointingHandCursor)
        receipt_btn.clicked.connect(self.generer_recu)

        buttons_container.addWidget(save_btn)
        buttons_container.addSpacing(20)
        buttons_container.addWidget(receipt_btn)
        buttons_container.addStretch()

        layout.addSpacing(20)
        layout.addLayout(buttons_container)
        layout.addStretch()
    
    def setup_recherche_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # Groupe recherche
        search_group = QGroupBox("Rechercher Paiements")
        search_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #1976D2;
                border: 2px solid #90CAF9;
                border-radius: 8px;
                margin-top: 22px;
                padding: 14px 12px 12px 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                padding: 0 6px;
                background-color: #F5F5F5;
            }
        """)
        search_layout = QFormLayout()
        search_layout.setVerticalSpacing(14)
        
        self.search_critere_combo = QComboBox()
        self.search_critere_combo.addItems(["ID", "Nom", "Classe", "Mois", "Statut"])
        self.search_critere_combo.setStyleSheet("font-size: 13px; padding: 6px;")
        self.search_value_input = QLineEdit()
        self.search_value_input.setStyleSheet("font-size: 13px; padding: 6px;")
        search_btn = QPushButton(icone("search.png"), "Rechercher")
        search_btn.setStyleSheet(BUTTON_STYLE)
        search_btn.setMinimumWidth(100)  # Agrandi
        search_btn.setMinimumHeight(30)  # Agrandi
        search_btn.setCursor(Qt.PointingHandCursor)
        search_btn.clicked.connect(self.rechercher_paiements)
        
        search_layout.addRow("Critère:", self.search_critere_combo)
        search_layout.addRow("Valeur:", self.search_value_input)
        search_layout.addRow(search_btn)
        
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # Tableau des résultats
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(8)
        self.result_table.setHorizontalHeaderLabels(
            ["ID", "Nom", "Prénom", "Classe", "Montant", "Mois", "Statut", "Date"]
        )
        self.result_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.rendre_tableau_adaptatif(self.result_table)
        self.result_table.setStyleSheet("""
            QTableWidget {
                font-size: 13px;
                selection-background-color: #BBDEFB;
            }
            QHeaderView::section {
                font-size: 13px;
                background: #1976D2;
                color: white;
            }
        """)
        layout.addWidget(self.result_table)
        
        # Boutons modification
        btn_layout = QHBoxLayout()
        modifier_btn = QPushButton(icone("edit.png"), "Modifier")
        modifier_btn.setStyleSheet(BUTTON_STYLE)
        modifier_btn.setMinimumWidth(220)  # Agrandi
        modifier_btn.setMinimumHeight(44)  # Agrandi
        modifier_btn.clicked.connect(self.modifier_paiement)
        exporter_btn = QPushButton("Exporter\nDonnées")
        exporter_btn.clicked.connect(self.exporter_donnees)
        exporter_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                font-size: 13px;
                font-weight: bold;
                border-radius: 5px;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
        """)
        btn_layout.addWidget(modifier_btn)
        btn_layout.addWidget(exporter_btn)
        layout.addLayout(btn_layout)
        
        # Pagination (rattachée à l'onglet des résultats)
        self.setup_pagination_controls(layout)
    
    def setup_statistiques_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # Titre
        title = QLabel("STATISTIQUES DES PAIEMENTS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: white;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                        stop:0 #1565C0, stop:0.5 #1976D2, stop:1 #42A5F5);
            padding: 14px;
            border-radius: 8px;
            margin: 6px 0 18px 0;
        """)
        layout.addWidget(title)
        
        # Container pour les statistiques générales (utilisation de QHBoxLayout)
        stats_container = QBoxLayout(QBoxLayout.LeftToRight)
        self.enregistrer_conteneur_responsive(stats_container)
        
        # Statistiques générales (côté gauche)
        stats_group = QGroupBox("Vue d'ensemble")
        stats_group.setStyleSheet("""
            QGroupBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                      stop:0 #E3F2FD, stop:1 #FFFFFF);
                border: 2px solid #1976D2;
                border-radius: 10px;
                margin-top: 15px;
                padding: 15px;
                font-size: 13px;
                min-width: 300px;
            }
            QGroupBox::title {
                color: #1976D2;
                font-size: 14px;
                font-weight: bold;
                subcontrol-position: top center;
                padding: 5px 30px;
                background-color: white;
            }
            QLabel {
                padding: 10px;
                margin: 5px 0;
                border-radius: 5px;
            }
        """)
        
        stats_layout = QVBoxLayout()
        total_container = QWidget()
        total_layout = QVBoxLayout(total_container)
        
        total_titre = QLabel("Nombre total de paiements")
        total_titre.setStyleSheet("font-weight: bold; color: #1976D2;")
        self.total_label = QLabel()
        self.total_label.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: #1976D2;
            background: rgba(255, 255, 255, 0.7);
            padding: 15px;
            border-radius: 8px;
            qproperty-alignment: AlignCenter;
        """)
        
        montant_titre = QLabel("Montant total perçu")
        montant_titre.setStyleSheet("font-weight: bold; color: #2E7D32; margin-top: 10px;")
        self.montant_total_label = QLabel()
        self.montant_total_label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #2E7D32;
            background: rgba(255, 255, 255, 0.7);
            padding: 15px;
            border-radius: 8px;
            qproperty-alignment: AlignCenter;
        """)
        
        total_layout.addWidget(total_titre)
        total_layout.addWidget(self.total_label)
        total_layout.addWidget(montant_titre)
        total_layout.addWidget(self.montant_total_label)
        stats_layout.addWidget(total_container)
        stats_group.setLayout(stats_layout)
        stats_container.addWidget(stats_group)
        
        # Container droit pour les tableaux
        tables_container = QVBoxLayout()
        
        # Statistiques par classe
        classe_group = QGroupBox("Répartition par Classe")
        classe_group.setStyleSheet("""
            QGroupBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                      stop:0 #F1F8E9, stop:1 #FFFFFF);
                border: 2px solid #43A047;
                border-radius: 10px;
                padding: 15px;
                font-size: 13px;
            }
            QGroupBox::title {
                color: #2E7D32;
                font-size: 14px;
                font-weight: bold;
                subcontrol-position: top center;
                padding: 5px 30px;
                background-color: white;
            }
        """)
        
        self.classe_table = QTableWidget()
        self.classe_table.setColumnCount(2)
        self.classe_table.setHorizontalHeaderLabels(["Classe", "Montant total (FCFA)"])
        self.rendre_tableau_adaptatif(self.classe_table)
        self.classe_table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                border: none;
            }
            QHeaderView::section {
                background-color: #43A047;
                color: white;
                font-weight: bold;
                padding: 8px;
                border: none;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        classe_layout = QVBoxLayout()
        classe_layout.addWidget(self.classe_table)
        classe_group.setLayout(classe_layout)
        tables_container.addWidget(classe_group)
        
        # Statistiques par statut
        statut_group = QGroupBox("Répartition par Statut")
        statut_group.setStyleSheet("""
            QGroupBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                      stop:0 #FFF3E0, stop:1 #FFFFFF);
                border: 2px solid #FF9800;
                border-radius: 10px;
                padding: 15px;
                font-size: 13px;
            }
            QGroupBox::title {
                color: #F57C00;
                font-size: 14px;
                font-weight: bold;
                subcontrol-position: top center;
                padding: 5px 30px;
                background-color: white;
            }
        """)
        
        self.statut_table = QTableWidget()
        self.statut_table.setColumnCount(2)
        self.statut_table.setHorizontalHeaderLabels(["Statut", "Nombre"])
        self.rendre_tableau_adaptatif(self.statut_table)
        self.statut_table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                border: none;
            }
            QHeaderView::section {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 8px;
                border: none;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        statut_layout = QVBoxLayout()
        statut_layout.addWidget(self.statut_table)
        statut_group.setLayout(statut_layout)
        tables_container.addWidget(statut_group)
        
        # Ajouter les containers au layout principal
        stats_container.addLayout(tables_container)
        layout.addLayout(stats_container)
        
        # Créer un conteneur horizontal pour les boutons
        buttons_layout = QHBoxLayout()

        # Bouton Actualiser
        btn_refresh = QPushButton("Actualiser")
        btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #43A047;
                color: white;
                font-size: 13px;
                font-weight: bold;
                border-radius: 5px;
                padding: 12px 24px;
                margin-top: 20px;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self.afficher_statistiques)

        # Bouton Graphique
        btn_stats = QPushButton(icone("chart.png"), "Afficher le graphique")
        btn_stats.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                font-size: 13px;
                font-weight: bold;
                border-radius: 5px;
                padding: 12px 24px;
                margin-top: 20px;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
        """)
        btn_stats.setCursor(Qt.PointingHandCursor)
        btn_stats.clicked.connect(self.afficher_graphique_statistiques)

        # Ajouter les boutons au layout horizontal
        buttons_layout.addWidget(btn_refresh, alignment=Qt.AlignmentFlag.AlignCenter)
        buttons_layout.addWidget(btn_stats, alignment=Qt.AlignmentFlag.AlignCenter)

        # Ajouter le layout des boutons au layout principal
        layout.addLayout(buttons_layout)

    def setup_liste_classe_tab(self, tab):
        layout = QVBoxLayout(tab)

        # Titre
        title = QLabel("Liste des élèves par classe")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #1976D2;
            margin-bottom: 18px;
        """)
        layout.addWidget(title)

        # Barre de recherche par classe
        search_layout = QHBoxLayout()
        search_label = QLabel("Filtrer par classe :")
        search_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #1976D2;")
        self.classe_filter_input = QLineEdit()
        self.classe_filter_input.setPlaceholderText("Ex : T, 2ND, 6E, etc.")
        self.classe_filter_input.setStyleSheet("font-size: 13px; padding: 6px; min-width: 120px;")
        self.classe_filter_input.textChanged.connect(self.remplir_liste_eleves_table)
        search_btn = QPushButton("Rechercher")
        search_btn.setStyleSheet(BUTTON_STYLE)
        search_btn.setMinimumHeight(36)
        search_btn.setCursor(Qt.PointingHandCursor)
        search_btn.clicked.connect(self.remplir_liste_eleves_table)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.classe_filter_input)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        # Tableau des résultats
        self.eleves_table = QTableWidget()
        self.eleves_table.setColumnCount(4)
        self.eleves_table.setHorizontalHeaderLabels(["Classe", "Nom", "Prénom", "Statut"])
        self.eleves_table.horizontalHeader().setStretchLastSection(True)
        self.rendre_tableau_adaptatif(self.eleves_table)
        self.eleves_table.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.eleves_table)

        # Remplir la table au chargement
        self.remplir_liste_eleves_table()

    def remplir_liste_eleves_table(self):
        filtre = self.classe_filter_input.text().strip().upper()
        paiements = self.gestion.paiements
        if filtre:
            paiements = [p for p in paiements if p['classe'].upper().startswith(filtre)]
        # Tri par classe puis nom
        paiements = sorted(paiements, key=lambda p: (p['classe'], p['nom'], p['prenom']))
        self.eleves_table.setRowCount(len(paiements))
        for row, eleve in enumerate(paiements):
            self.eleves_table.setItem(row, 0, QTableWidgetItem(eleve['classe']))
            self.eleves_table.setItem(row, 1, QTableWidgetItem(eleve['nom']))
            self.eleves_table.setItem(row, 2, QTableWidgetItem(eleve['prenom']))
            self.eleves_table.setItem(row, 3, QTableWidgetItem(eleve['statut']))

    def setup_admin_tab(self):
        tab_admin = self.creer_onglet_defilable("Administration")
        layout = QVBoxLayout(tab_admin)

        # Conteneur principal avec deux colonnes (une seule si la fenêtre est étroite)
        main_container = QBoxLayout(QBoxLayout.LeftToRight)
        self.enregistrer_conteneur_responsive(main_container)

        # Colonne gauche - Création d'utilisateur
        left_column = QVBoxLayout()
        form_group = QGroupBox("Créer un nouvel utilisateur")
        form_group.setStyleSheet("""
            QGroupBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                      stop:0 #E3F2FD, stop:1 #FFFFFF);
                border: 2px solid #1976D2;
                border-radius: 10px;
                margin-top: 15px;
                padding: 20px;
                font-size: 13px;
            }
            QGroupBox::title {
                color: #1976D2;
                font-size: 14px;
                font-weight: bold;
                subcontrol-position: top center;
                padding: 5px 30px;
                background-color: white;
            }
        """)

        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setVerticalSpacing(20)

        # Style pour les champs de saisie
        input_style = """
            QLineEdit, QSpinBox {
                padding: 12px;
                border: 2px solid #90CAF9;
                border-radius: 6px;
                font-size: 13px;
                min-width: 280px;
                background: white;
            }
            QLineEdit:focus, QSpinBox:focus {
                border-color: #1976D2;
            }
        """

        self.nouvel_user_input = QLineEdit()
        self.nouvel_user_input.setPlaceholderText("Entrez le nom d'utilisateur")
        self.nouvel_user_input.setStyleSheet(input_style)

        self.nouvel_pass_input = QLineEdit()
        self.nouvel_pass_input.setPlaceholderText("Entrez le mot de passe")
        self.nouvel_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.nouvel_pass_input.setStyleSheet(input_style)

        self.duree_acces_spin = QSpinBox()
        self.duree_acces_spin.setRange(1, 720)
        self.duree_acces_spin.setValue(TEMPS_ACCES_DEFAUT)
        self.duree_acces_spin.setStyleSheet(input_style)

        self.admin_checkbox = QCheckBox("Administrateur")
        self.admin_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 13px;
                color: #1976D2;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
        """)

        # Labels avec style
        label_style = """
            QLabel {
                color: #1976D2;
                font-weight: bold;
                font-size: 12px;
                padding: 5px;
            }
        """
        
        for label, widget in [
            ("Nom d'utilisateur :", self.nouvel_user_input),
            ("Mot de passe :", self.nouvel_pass_input),
            ("Durée d'accès (heures) :", self.duree_acces_spin),
            ("", self.admin_checkbox)
        ]:
            if label:
                lbl = QLabel(label)
                lbl.setStyleSheet(label_style)
                form_layout.addRow(lbl, widget)
            else:
                form_layout.addRow(widget)

        form_group.setLayout(form_layout)

        # Bouton créer utilisateur avec style amélioré
        btn_creer = QPushButton(icone("add.png"), "Créer Utilisateur")
        btn_creer.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 13px;
                font-weight: bold;
                border-radius: 8px;
                padding: 12px 30px;
                min-width: 280px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        btn_creer.setCursor(Qt.PointingHandCursor)
        btn_creer.clicked.connect(self.creer_utilisateur)

        left_column.addWidget(form_group)
        left_column.addWidget(btn_creer, alignment=Qt.AlignmentFlag.AlignCenter)
        left_column.addStretch()
        main_container.addLayout(left_column)

        # Colonne droite - Liste des utilisateurs
        right_column = QVBoxLayout()
        users_group = QGroupBox("Utilisateurs existants")
        users_group.setStyleSheet("""
            QGroupBox {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                      stop:0 #F1F8E9, stop:1 #FFFFFF);
                border: 2px solid #43A047;
                border-radius: 10px;
                margin-top: 15px;
                padding: 20px;
                font-size: 13px;
            }
            QGroupBox::title {
                color: #2E7D32;
                font-size: 14px;
                font-weight: bold;
                subcontrol-position: top center;
                padding: 5px 30px;
                background-color: white;
            }
        """)

        users_layout = QVBoxLayout()
        self.liste_users = QTableWidget()
        self.liste_users.setColumnCount(4)
        self.liste_users.setHorizontalHeaderLabels(["Utilisateur", "Admin", "Expiration", "Actions"])
        self.rendre_tableau_adaptatif(self.liste_users)
        entete_users = self.liste_users.horizontalHeader()
        entete_users.setStretchLastSection(False)
        entete_users.setSectionResizeMode(3, QHeaderView.Interactive)
        self.liste_users.setColumnWidth(3, 170)
        self.liste_users.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                border: none;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #43A047;
                color: white;
                font-weight: bold;
                padding: 4px;
                border: none;
            }
            QTableWidget::item {
                padding: 2px;
                height: 24px;
            }
        """)
        users_layout.addWidget(self.liste_users)
        users_group.setLayout(users_layout)

        right_column.addWidget(users_group)
        main_container.addLayout(right_column)

        # Ajout du conteneur principal au layout
        layout.addLayout(main_container)

        # Actualiser la liste
        self.actualiser_liste_utilisateurs()

    def creer_utilisateur(self):
        username = self.nouvel_user_input.text().strip()
        password = self.nouvel_pass_input.text().strip()
        duree = self.duree_acces_spin.value()
        is_admin = self.admin_checkbox.isChecked()
        if not username or not password:
            QMessageBox.warning(self, "Erreur", "Veuillez remplir tous les champs")
            return
        if self.gestion_utilisateurs.creer_utilisateur(username, password, is_admin, duree):
            QMessageBox.information(self, "Succès", f"Utilisateur {username} créé avec succès!")
            self.actualiser_liste_utilisateurs()
            self.nouvel_user_input.clear()
            self.nouvel_pass_input.clear()
        else:
            QMessageBox.warning(self, "Erreur", "Ce nom d'utilisateur existe déjà")

    def supprimer_utilisateur(self, username):
        if self.gestion_utilisateurs.supprimer_utilisateur(username):
            QMessageBox.information(self, "Succès", f"Utilisateur {username} supprimé")
            self.actualiser_liste_utilisateurs()
        else:
            QMessageBox.warning(self, "Erreur", "Impossible de supprimer cet utilisateur")

    def actualiser_liste_utilisateurs(self):
        self.liste_users.setRowCount(0)

        for i, user in enumerate(self.gestion_utilisateurs.lister_utilisateurs()):
            self.liste_users.insertRow(i)

            item_user = QTableWidgetItem(user.username)
            item_user.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.liste_users.setItem(i, 0, item_user)

            item_admin = QTableWidgetItem("✔" if user.is_admin else "")
            item_admin.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_admin.setForeground(Qt.green if user.is_admin else Qt.gray)
            self.liste_users.setItem(i, 1, item_admin)

            expiration = datetime.fromisoformat(user.expiration)
            item_exp = QTableWidgetItem(expiration.strftime("%d/%m/%Y %H:%M"))
            item_exp.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.liste_users.setItem(i, 2, item_exp)

            btn_supprimer = QPushButton(icone("delete.png"), "Supprimer")
            btn_supprimer.setStyleSheet(BUTTON_STYLE)
            btn_supprimer.setObjectName("danger")
            btn_supprimer.setMinimumWidth(100)
            btn_supprimer.setCursor(Qt.PointingHandCursor)
            btn_supprimer.clicked.connect(partial(self.supprimer_utilisateur, user.username))
            self.liste_users.setCellWidget(i, 3, btn_supprimer)

        self.liste_users.resizeRowsToContents()

    def enregistrer_paiement(self):
        if not self.gestion_utilisateurs.utilisateur_actuel:
            QMessageBox.warning(self, "Non autorisé", "Vous devez être connecté")
            return
        champs_obligatoires = {
            "Nom": self.nom_input.text().strip(),
            "Prénom": self.prenom_input.text().strip(),
            "Classe": self.classe_input.text().strip(),
            "Montant": self.montant_input.text().strip(),
            "Mois": self.mois_input.text().strip()
        }
        champs_vides = [nom for nom, valeur in champs_obligatoires.items() if not valeur]
        if champs_vides:
            QMessageBox.warning(self, "Champs manquants", "Veuillez remplir tous les champs obligatoires:\n" + "\n".join(champs_vides))
            return
        try:
            montant = float(champs_obligatoires["Montant"])
            if montant <= 0:
                raise ValueError("Le montant doit être positif.")
        except ValueError:
            QMessageBox.warning(self, "Montant invalide", "Le montant doit être un nombre positif.")
            return
        paiement = {
            'nom': champs_obligatoires['Nom'].upper(),
            'prenom': champs_obligatoires['Prénom'].capitalize(),
            'classe': champs_obligatoires['Classe'].upper(),
            'montant': champs_obligatoires['Montant'],
            'mois': champs_obligatoires['Mois'],
            'methode_paiement': self.methode_combo.currentText(),
            'statut': self.statut_combo.currentText(),
            'notes': self.notes_input.toPlainText().strip()
        }
        id_paiement = self.gestion.ajouter_paiement(paiement)
        QMessageBox.information(self, "Succès", f"Paiement enregistré avec succès (ID: {id_paiement}).")
        self.nom_input.clear()
        self.prenom_input.clear()
        self.classe_input.clear()
        self.montant_input.clear()
        self.mois_input.clear()
        self.notes_input.clear()
        self.statut_combo.setCurrentText("payé")

    def generer_recu(self):
        if not all([
            self.nom_input.text().strip(),
            self.prenom_input.text().strip(),
            self.montant_input.text().strip()
        ]):
            QMessageBox.warning(self, "Impossible", "Veuillez d'abord remplir les informations du paiement")
            return
        contenu = f"""
        REÇU DE PAIEMENT SCOLAIRE
        {'='*40}
        Élève: {self.prenom_input.text()} {self.nom_input.text()}
        Classe: {self.classe_input.text()}
        Montant: {self.montant_input.text()} FCFA
        Mois: {self.mois_input.text()}
        Méthode: {self.methode_combo.currentText()}
        Date: {datetime.now().strftime("%d/%m/%Y %H:%M")}
        {'='*40}
        """
        nom_fichier = f"recu_{self.nom_input.text()}_{self.prenom_input.text()}.txt"
        try:
            with open(nom_fichier, 'w', encoding='utf-8') as f:
                f.write(contenu)
            QMessageBox.information(self, "Succès", f"Reçu enregistré sous : {nom_fichier}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible d'enregistrer le reçu : {e}")

    def rechercher_paiements(self):
        critere = self.search_critere_combo.currentText().lower()
        valeur = self.search_value_input.text().strip()
        if not valeur:
            QMessageBox.warning(self, "Valeur manquante", "Veuillez entrer une valeur de recherche")
            return
        
        resultats = self.gestion.rechercher_paiements(critere, valeur)
        self.result_table.setRowCount(len(resultats))
        for row, paiement in enumerate(resultats):
            self.result_table.setItem(row, 0, QTableWidgetItem(paiement['id']))
            self.result_table.setItem(row, 1, QTableWidgetItem(paiement['nom']))
            self.result_table.setItem(row, 2, QTableWidgetItem(paiement['prenom']))
            self.result_table.setItem(row, 3, QTableWidgetItem(paiement['classe']))
            self.result_table.setItem(row, 4, QTableWidgetItem(paiement['montant']))
            self.result_table.setItem(row, 5, QTableWidgetItem(paiement['mois']))
            self.result_table.setItem(row, 6, QTableWidgetItem(paiement['statut']))
            self.result_table.setItem(row, 7, QTableWidgetItem(paiement['date_paiement']))

    def modifier_paiement(self):
        selected = self.result_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Aucune sélection", "Veuillez sélectionner un paiement à modifier")
            return
            
        id_paiement = self.result_table.item(selected[0].row(), 0).text()
        # Créer une boîte de dialogue de modification
        dialog = QDialog(self)
        dialog.setWindowTitle("Modifier Paiement")
        dialog.setModal(True)
        layout = QFormLayout(dialog)
        
        # Trouver le paiement
        paiement = None
        for p in self.gestion.paiements:
            if p['id'] == id_paiement:
                paiement = p
                break
        
        if not paiement:
            QMessageBox.warning(self, "Erreur", "Paiement introuvable")
            return
        
        # Créer les champs de formulaire
        nom_input = QLineEdit(paiement['nom'])
        prenom_input = QLineEdit(paiement['prenom'])
        classe_input = QLineEdit(paiement['classe'])
        montant_input = QLineEdit(paiement['montant'])
        mois_input = QLineEdit(paiement['mois'])
        methode_combo = QComboBox()
        methode_combo.addItems(METHODES_PAIEMENT)
        methode_combo.setCurrentText(paiement['methode_paiement'])
        statut_combo = QComboBox()
        statut_combo.addItems(STATUTS)
        statut_combo.setCurrentText(paiement['statut'])
        notes_input = QTextEdit(paiement['notes'])
        
        layout.addRow("Nom:", nom_input)
        layout.addRow("Prénom:", prenom_input)
        layout.addRow("Classe:", classe_input)
        layout.addRow("Montant:", montant_input)
        layout.addRow("Mois:", mois_input)
        layout.addRow("Méthode:", methode_combo)
        layout.addRow("Statut:", statut_combo)
        layout.addRow("Notes:", notes_input)
        
        # Boutons
        btn_layout = QHBoxLayout()
        sauvegarder_btn = QPushButton("Sauvegarder")
        annuler_btn = QPushButton("Annuler")
        
        btn_layout.addWidget(sauvegarder_btn)
        btn_layout.addWidget(annuler_btn)
        layout.addRow(btn_layout)
        
        def sauvegarder():
            nouvelles_valeurs = {
                'nom': nom_input.text().strip().upper(),
                'prenom': prenom_input.text().strip().capitalize(),
                'classe': classe_input.text().strip().upper(),
                'montant': montant_input.text().strip(),
                'mois': mois_input.text().strip(),
                'methode_paiement': methode_combo.currentText(),
                'statut': statut_combo.currentText(),
                'notes': notes_input.toPlainText().strip()
            }
            
            if self.gestion.modifier_paiement(id_paiement, nouvelles_valeurs):
                QMessageBox.information(self, "Succès", "Paiement modifié avec succès")
                dialog.close()
                self.rechercher_paiements()
            else:
                QMessageBox.warning(self, "Erreur", "Échec de la modification")
        
        sauvegarder_btn.clicked.connect(sauvegarder)
        annuler_btn.clicked.connect(dialog.close)
        
        dialog.exec()
    
    def exporter_donnees(self):
        if not self.gestion.paiements:
            QMessageBox.information(self, "Export", "Aucun paiement à exporter")
            return
        try:
            os.makedirs(EXPORT_DIR, exist_ok=True)
            nom_fichier = os.path.join(
                EXPORT_DIR,
                f"export_paiements_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            with open(nom_fichier, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=CHAMPS, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(self.gestion.paiements)
            logger.info(f"Données exportées: {nom_fichier}")
            QMessageBox.information(self, "Export réussi", f"Données exportées dans:\n{nom_fichier}")
        except OSError as e:
            logger.error(f"Erreur lors de l'export: {e}")
            QMessageBox.critical(self, "Erreur", f"Impossible d'exporter les données:\n{e}")
    
    def afficher_statistiques(self):
        stats = self.gestion.get_statistiques()
        # Générales
        self.total_label.setText(str(stats["total"]))
        self.montant_total_label.setText(formater_montant(stats['montant_total']))
        # Par classe
        self.classe_table.setRowCount(0)
        for i, (classe, montants) in enumerate(stats["par_classe"].items()):
            self.classe_table.insertRow(i)
            self.classe_table.setItem(i, 0, QTableWidgetItem(str(classe)))
            self.classe_table.setItem(i, 1, QTableWidgetItem(formater_montant(sum(montants))))
        # Par statut
        self.statut_table.setRowCount(0)
        for i, statut in enumerate(STATUTS):
            self.statut_table.insertRow(i)
            self.statut_table.setItem(i, 0, QTableWidgetItem(statut.capitalize()))
            self.statut_table.setItem(i, 1, QTableWidgetItem(str(stats["par_statut"].get(statut, 0))))

    def afficher_graphique_statistiques(self):
        try:
            stats = self.gestion.get_statistiques()
            valeurs = [stats["par_statut"].get(s, 0) for s in STATUTS]
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Tableau de Bord - Statistiques")
            dialog.resize(*self.taille_dialogue(1000, 700))
            
            layout = QVBoxLayout(dialog)
            
            # En-tête
            header = QLabel("TABLEAU DE BORD DES PAIEMENTS")
            header.setStyleSheet("""
                font-size: 17px;
                font-weight: bold;
                color: white;
                background: #1976D2;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
            """)
            header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(header)

            # Conteneur principal
            main_content = QHBoxLayout()

            # Colonne gauche - Graphiques
            charts_container = QVBoxLayout()
            
            # Graphique circulaire
            pie_group = QGroupBox("Répartition par Statut")
            pie_layout = QVBoxLayout()
            image = self.chart_generator.generate_pie_chart(valeurs, STATUTS, "")
            chart_label = QLabel()
            chart_label.setPixmap(QPixmap.fromImage(image).scaled(
                400, 400, 
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
            pie_layout.addWidget(chart_label)
            pie_group.setLayout(pie_layout)
            charts_container.addWidget(pie_group)
            
            main_content.addLayout(charts_container)

            # Colonne droite - Statistiques détaillées
            stats_container = QVBoxLayout()
            
            # Vue d'ensemble
            overview_group = QGroupBox("Vue d'ensemble")
            overview_group.setStyleSheet("""
                QGroupBox {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                      stop:0 #E3F2FD, stop:1 #FFFFFF);
                    border: 2px solid #1976D2;
                    border-radius: 8px;
                    padding: 15px;
                }
                QGroupBox::title {
                    color: #1976D2;
                    font-weight: bold;
                    font-size: 13px;
                }
                QLabel {
                    font-size: 12px;
                    padding: 5px;
                }
            """)
            overview_layout = QVBoxLayout()
            
            # Statistiques principales
            total_paiements = QLabel(f"📊 Nombre total de paiements : {stats['total']}")
            montant_total = QLabel(f"💰 Montant total perçu : {stats['montant_total']:,} FCFA")
            montant_total.setStyleSheet("font-weight: bold; color: #2E7D32; font-size: 13px;")
            
            # Moyenne des paiements
            moy_paiement = stats['montant_total'] / stats['total'] if stats['total'] > 0 else 0
            moyenne = QLabel(f"📈 Moyenne par paiement : {moy_paiement:,.0f} FCFA")
            
            overview_layout.addWidget(total_paiements)
            overview_layout.addWidget(montant_total)
            overview_layout.addWidget(moyenne)
            overview_group.setLayout(overview_layout)
            stats_container.addWidget(overview_group)
            
            # Détails par statut
            details_group = QGroupBox("Détails par Statut")
            details_group.setStyleSheet("""
                QGroupBox {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                      stop:0 #F1F8E9, stop:1 #FFFFFF);
                    border: 2px solid #43A047;
                    border-radius: 8px;
                    padding: 15px;
                }
                QGroupBox::title {
                    color: #2E7D32;
                    font-weight: bold;
                    font-size: 13px;
                }
            """)
            details_layout = QVBoxLayout()
            
            # Table des statuts
            status_table = QTableWidget()
            status_table.setColumnCount(3)
            status_table.setHorizontalHeaderLabels(["Statut", "Nombre", "Pourcentage"])
            status_table.horizontalHeader().setStretchLastSection(True)
            status_table.setStyleSheet("""
                QTableWidget {
                    border: none;
                    background-color: transparent;
                }
                QHeaderView::section {
                    background-color: #43A047;
                    color: white;
                    font-weight: bold;
                    padding: 6px;
                }
            """)
            
            status_table.setRowCount(len(STATUTS))
            for i, statut in enumerate(STATUTS):
                count = stats["par_statut"].get(statut, 0)
                percentage = (count / stats["total"] * 100) if stats["total"] > 0 else 0
                
                status_table.setItem(i, 0, QTableWidgetItem(statut.capitalize()))
                status_table.setItem(i, 1, QTableWidgetItem(str(count)))
                status_table.setItem(i, 2, QTableWidgetItem(f"{percentage:.1f}%"))
                
            details_layout.addWidget(status_table)
            details_group.setLayout(details_layout)
            stats_container.addWidget(details_group)
            
            # Top des classes
            classes_group = QGroupBox("Top 5 des Classes")
            classes_group.setStyleSheet("""
                QGroupBox {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                      stop:0 #FFF3E0, stop:1 #FFFFFF);
                    border: 2px solid #FF9800;
                    border-radius: 8px;
                    padding: 15px;
                }
                QGroupBox::title {
                    color: #F57C00;
                    font-weight: bold;
                    font-size: 13px;
                }
            """)
            classes_layout = QVBoxLayout()
            
            # Table des classes
            sorted_classes = sorted(
                stats["par_classe"].items(),
                key=lambda x: sum(x[1]),
                reverse=True
            )[:5]
            
            class_table = QTableWidget()
            class_table.setColumnCount(2)
            class_table.setHorizontalHeaderLabels(["Classe", "Montant total"])
            class_table.horizontalHeader().setStretchLastSection(True)
            class_table.setStyleSheet("""
                QTableWidget {
                    border: none;
                    background-color: transparent;
                }
                QHeaderView::section {
                    background-color: #FF9800;
                    color: white;
                    font-weight: bold;
                    padding: 6px;
                }
            """)
            
            class_table.setRowCount(len(sorted_classes))
            for i, (classe, montants) in enumerate(sorted_classes):
                class_table.setItem(i, 0, QTableWidgetItem(classe))
                class_table.setItem(i, 1, QTableWidgetItem(formater_montant(sum(montants))))
                
            classes_layout.addWidget(class_table)
            classes_group.setLayout(classes_layout)
            stats_container.addWidget(classes_group)
            
            main_content.addLayout(stats_container)
            layout.addLayout(main_content)
            
            # Bouton de fermeture
            close_btn = QPushButton("Fermer")
            close_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1976D2;
                    color: white;
                    font-size: 12px;
                    font-weight: bold;
                    border-radius: 5px;
                    padding: 8px 15px;
                    min-width: 100px;
                    margin-top: 15px;
                }
                QPushButton:hover {
                    background-color: #1565C0;
                }
            """)
            close_btn.clicked.connect(dialog.close)
            layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
            
            dialog.exec()
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du graphique: {e}")
            QMessageBox.critical(self, "Erreur", "Impossible de générer le graphique")

    def lister_eleves_par_classe(self):
        classe = self.classe_search_input.text().strip().upper()
        if not classe:
            QMessageBox.warning(self, "Classe manquante", "Veuillez entrer une classe")
            return
        
        paiements_classe = [p for p in self.gestion.paiements if p['classe'] == classe]
        if not paiements_classe:
            QMessageBox.information(self, "Aucun résultat", f"Aucun élève trouvé pour la classe {classe}")
            self.eleves_payes_text.clear()
            self.eleves_non_payes_text.clear()
            return
        
        eleves_payes = [p for p in paiements_classe if p['statut'] == "payé"]
        eleves_non_payes = [p for p in paiements_classe if p['statut'] != "payé"]
        
        # Afficher les élèves ayant payé
        payes_text = ""
        for eleve in eleves_payes:
            payes_text += f"- {eleve['prenom']} {eleve['nom']} (Montant: {eleve['montant']} FCFA, Mois: {eleve['mois']})\n"
        self.eleves_payes_text.setPlainText(payes_text if payes_text else "Aucun élève n'a payé.")
        
        # Afficher les élèves n'ayant pas payé
        non_payes_text = ""
        for eleve in eleves_non_payes:
            non_payes_text += f"- {eleve['prenom']} {eleve['nom']} (Statut: {eleve['statut']}, Mois: {eleve['mois']})\n"
        self.eleves_non_payes_text.setPlainText(non_payes_text if non_payes_text else "Tous les élèves ont payé.")

    def setup_pagination_controls(self, layout):
        self.pagination_widget = QWidget()
        pagination_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("Précédent")
        self.next_button = QPushButton("Suivant")
        self.page_label = QLabel()
        
        self.prev_button.clicked.connect(self.previous_page)
        self.next_button.clicked.connect(self.next_page)
        
        pagination_layout.addWidget(self.prev_button)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_button)
        
        self.pagination_widget.setLayout(pagination_layout)
        layout.addWidget(self.pagination_widget)

    def update_pagination_controls(self):
        if self.paginator:
            total_pages = self.paginator.total_pages
            self.page_label.setText(f"Page {self.current_page}/{total_pages}")
            self.prev_button.setEnabled(self.current_page > 1)
            self.next_button.setEnabled(self.current_page < total_pages)

    def previous_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_table(self.gestion.paiements)

    def next_page(self):
        if self.paginator and self.current_page < self.paginator.total_pages:
            self.current_page += 1
            self.update_table(self.gestion.paiements)

    def show_success_message(self, title, message):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: white;
            }
            QPushButton {
                padding: 6px 12px;
                background-color: #2196F3;
                color: white;
                border-radius: 4px;
                min-width: 80px;
            }
        """)
        msg.exec_()

if __name__ == "__main__":
    # Rendu net sur les écrans haute résolution (4K, Retina, mise à l'échelle 125-200 %)
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    # Style global
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 9))
    # Palette moderne
    palette = app.palette()
    palette.setColor(palette.Window, Qt.white)
    palette.setColor(palette.Base, Qt.white)
    palette.setColor(palette.AlternateBase, Qt.lightGray)
    palette.setColor(palette.Button, Qt.white)
    palette.setColor(palette.ButtonText, Qt.black)
    palette.setColor(palette.Text, Qt.black)
    palette.setColor(palette.Highlight, Qt.cyan)
    palette.setColor(palette.HighlightedText, Qt.black)
    app.setPalette(palette)
    # Feuille de style globale
    app.setStyleSheet("""
    QMainWindow {
        background-color: #F5F5F5;
    }
    
    QTabWidget::pane {
        border: 2px solid #1976D2;
        border-radius: 8px;
        background: white;
    }
    
    QTabBar::tab {
        background: #E3F2FD;
        border: 1px solid #90CAF9;
        border-radius: 6px;
        padding: 4px 9px;
        margin: 2px;
        font-size: 11px;
        min-width: 0px;
    }
    
    QScrollArea {
        border: none;
        background: transparent;
    }
    
    QScrollArea > QWidget > QWidget {
        background: transparent;
    }
    
    QTabBar::tab:selected {
        background: #1976D2;
        color: white;
    }
    
    QGroupBox {
        font-size: 12px;
        font-weight: bold;
        border: 2px solid #90CAF9;
        border-radius: 8px;
        margin-top: 12px;
        padding: 10px;
    }
    
    QLineEdit, QTextEdit, QComboBox {
        padding: 8px;
        border: 1px solid #BDBDBD;
        border-radius: 4px;
        background: white;
    }
    
    QTableWidget {
        border: 1px solid #BDBDBD;
        border-radius: 4px;
        background: white;
        gridline-color: #E0E0E0;
    }
    
    QTableWidget QHeaderView::section {
        background: #1976D2;
        color: white;
        font-weight: bold;
        padding: 4px;          /* Réduit de 8px à 4px */
        border: none;
        font-size: 12px;
    }
    
    QTableWidget::item {
        padding: 2px;          /* Réduit de 5px à 2px */
    }
    
    QHeaderView::section:horizontal {
        height: 28px;          /* Hauteur de l'en-tête */
    }
    
    QHeaderView::section:vertical {
        width: 30px;           /* Largeur de l'en-tête vertical */
    }
    
    QTableWidget::item:selected {
        background-color: #E3F2FD;
        color: black;
    }
""")
    window = MainWindow()
    if window.ecran_etroit():
        window.showMaximized()
    else:
        window.show()
    sys.exit(app.exec())