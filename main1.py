import sys
import csv
import datetime
import os
from collections import defaultdict
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QComboBox,
    QTextEdit, QDialog, QMessageBox, QFormLayout, QGroupBox, QTabWidget
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QIcon

# Configuration
FICHIER_DONNEES = "paiements_eleves.csv"
FICHIER_SAUVEGARDE = "sauvegarde_paiements_{}.csv"
CHAMPS = ["id", "nom", "prenom", "classe", "montant", "mois", "date_paiement",
          "heure_paiement", "methode_paiement", "statut", "notes"]
STATUTS = ["payé", "impayé", "partiel", "remboursé"]
METHODES_PAIEMENT = ["Espèces", "Chèque", "Virement", "Carte bancaire", "Mobile Money"]

class GestionPaiements:
    def __init__(self):
        self.paiements = []
        self.initialiser_fichier()
        self.charger_donnees()
        
    def initialiser_fichier(self):
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
        with open(FICHIER_DONNEES, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CHAMPS)
            writer.writeheader()
            writer.writerows(self.paiements)
        
        date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(FICHIER_SAUVEGARDE.format(date_str), mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CHAMPS)
            writer.writeheader()
            writer.writerows(self.paiements)
    
    def generer_id(self):
        ids = [int(p['id']) for p in self.paiements if 'id' in p and p['id'].isdigit()]
        return str(max(ids) + 1) if ids else "1"
    
    def ajouter_paiement(self, paiement):
        paiement['id'] = self.generer_id()
        maintenant = datetime.datetime.now()
        paiement['date_paiement'] = maintenant.strftime("%d/%m/%Y")
        paiement['heure_paiement'] = maintenant.strftime("%H:%M:%S")
        self.paiements.append(paiement)
        self.sauvegarder_donnees()
        return paiement['id']
    
    def modifier_paiement(self, id_paiement, nouvelles_valeurs):
        for i, paiement in enumerate(self.paiements):
            if paiement['id'] == id_paiement:
                maintenant = datetime.datetime.now()
                nouvelles_valeurs['date_paiement'] = maintenant.strftime("%d/%m/%Y")
                nouvelles_valeurs['heure_paiement'] = maintenant.strftime("%H:%M:%S")
                self.paiements[i] = {**paiement, **nouvelles_valeurs}
                self.sauvegarder_donnees()
                return True
        return False
    
    def rechercher_paiements(self, critere, valeur):
        if critere == "id":
            return [p for p in self.paiements if p['id'] == valeur]
        elif critere == "nom":
            return [p for p in self.paiements if p['nom'] == valeur.upper()]
        elif critere == "classe":
            return [p for p in self.paiements if p['classe'] == valeur.upper()]
        elif critere == "mois":
            return [p for p in self.paiements if p['mois'] == valeur]
        elif critere == "statut":
            return [p for p in self.paiements if p['statut'] == valeur]
        return []
    
    def get_statistiques(self):
        stats = {
            "total": len(self.paiements),
            "montant_total": sum(float(p['montant']) for p in self.paiements if p['statut'] == 'payé'),
            "par_classe": defaultdict(list),
            "par_statut": defaultdict(int)
        }
        
        for p in self.paiements:
            stats["par_classe"][p['classe']].append(float(p['montant']))
            stats["par_statut"][p['statut']] += 1
        
        return stats

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.gestion = GestionPaiements()
        self.setWindowTitle("Gestion des Paiements Scolaires")
        self.setWindowIcon(QIcon("school.png"))
        self.setGeometry(100, 100, 1000, 700)
        self.setup_ui()
    
    def setup_ui(self):
        # Style général
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QLabel {
                font-size: 12px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QLineEdit, QComboBox, QDateEdit, QTextEdit {
                padding: 6px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QTableWidget {
                gridline-color: #ddd;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #4CAF50;
                color: white;
                padding: 6px;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                background: white;
            }
            QTabBar::tab {
                background: #e1e1e1;
                padding: 8px;
                border: 1px solid #ddd;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: white;
                margin-bottom: -1px;
            }
            QGroupBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
        """)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Barre de titre
        title_label = QLabel("GESTION DES PAIEMENTS SCOLAIRES")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #2E7D32;
            padding: 10px;
            border-bottom: 2px solid #4CAF50;
        """)
        main_layout.addWidget(title_label)
        
        # Onglets
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # Onglet 1: Enregistrement
        tab1 = QWidget()
        tabs.addTab(tab1, "Nouveau Paiement")
        self.setup_enregistrement_tab(tab1)
        
        # Onglet 2: Recherche/Modification
        tab2 = QWidget()
        tabs.addTab(tab2, "Recherche/Modification")
        self.setup_recherche_tab(tab2)
        
        # Onglet 3: Statistiques
        tab3 = QWidget()
        tabs.addTab(tab3, "Statistiques")
        self.setup_statistiques_tab(tab3)
        
        # Onglet 4: Liste par classe
        tab4 = QWidget()
        tabs.addTab(tab4, "Liste par Classe")
        self.setup_classe_tab(tab4)
    
    def setup_enregistrement_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # Titre
        title_label = QLabel("NOUVEAU PAIEMENT")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #2E7D32;
            padding: 10px;
            border-bottom: 2px solid #4CAF50;
            margin-bottom: 15px;
        """)
        layout.addWidget(title_label)
        
        # Groupe formulaire
        form_group = QGroupBox("Informations de Paiement")
        form_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
            }
        """)
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(15)
        
        # Champs de formulaire
        self.nom_input = QLineEdit()
        self.prenom_input = QLineEdit()
        self.classe_input = QLineEdit()
        self.montant_input = QLineEdit()
        self.mois_input = QLineEdit()
        
        # ComboBox pour méthode et statut
        self.methode_combo = QComboBox()
        self.methode_combo.addItems(METHODES_PAIEMENT)
        self.statut_combo = QComboBox()
        self.statut_combo.addItems(STATUTS)
        self.statut_combo.setCurrentText("payé")
        
        # Zone de notes
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        
        # Style des champs
        for input_field in [self.nom_input, self.prenom_input, self.classe_input, 
                          self.montant_input, self.mois_input]:
            input_field.setStyleSheet("""
                QLineEdit {
                    padding: 8px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    min-width: 200px;
                }
            """)
        
        # Ajout des champs au formulaire
        form_layout.addRow("Nom:", self.nom_input)
        form_layout.addRow("Prénom:", self.prenom_input)
        form_layout.addRow("Classe:", self.classe_input)
        form_layout.addRow("Montant (FCFA):", self.montant_input)
        form_layout.addRow("Mois:", self.mois_input)
        form_layout.addRow("Méthode:", self.methode_combo)
        form_layout.addRow("Statut:", self.statut_combo)
        form_layout.addRow("Notes:", self.notes_input)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Boutons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)
        
        enregistrer_btn = QPushButton("Enregistrer")
        enregistrer_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        enregistrer_btn.clicked.connect(self.enregistrer_paiement)
        
        generer_recu_btn = QPushButton("Générer Reçu")
        generer_recu_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        generer_recu_btn.clicked.connect(self.generer_recu)
        
        btn_layout.addStretch()
        btn_layout.addWidget(enregistrer_btn)
        btn_layout.addWidget(generer_recu_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        layout.addStretch()
    
    def setup_recherche_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # Groupe recherche
        search_group = QGroupBox("Rechercher Paiements")
        search_layout = QFormLayout()
        
        self.search_critere_combo = QComboBox()
        self.search_critere_combo.addItems(["ID", "Nom", "Classe", "Mois", "Statut"])
        self.search_value_input = QLineEdit()
        self.search_btn = QPushButton("Rechercher")
        self.search_btn.clicked.connect(self.rechercher_paiements)
        
        search_layout.addRow("Critère:", self.search_critere_combo)
        search_layout.addRow("Valeur:", self.search_value_input)
        search_layout.addRow(self.search_btn)
        
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)
        
        # Tableau des résultats
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(8)
        self.result_table.setHorizontalHeaderLabels(["ID", "Nom", "Prénom", "Classe", "Montant", "Mois", "Statut", "Date"])
        self.result_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.result_table)
        
        # Boutons modification
        btn_layout = QHBoxLayout()
        modifier_btn = QPushButton("Modifier Sélection")
        modifier_btn.clicked.connect(self.modifier_paiement)
        modifier_btn.setStyleSheet("background-color: #2196F3;")
        
        exporter_btn = QPushButton("Exporter Données")
        exporter_btn.clicked.connect(self.exporter_donnees)
        exporter_btn.setStyleSheet("background-color: #607D8B;")
        
        btn_layout.addWidget(modifier_btn)
        btn_layout.addWidget(exporter_btn)
        layout.addLayout(btn_layout)
    
    def setup_statistiques_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # Bouton actualiser
        actualiser_btn = QPushButton("Actualiser les Statistiques")
        actualiser_btn.clicked.connect(self.afficher_statistiques)
        layout.addWidget(actualiser_btn)
        
        # Statistiques générales
        stats_group = QGroupBox("Statistiques Générales")
        stats_layout = QFormLayout()
        
        self.total_label = QLabel()
        self.montant_total_label = QLabel()
        
        stats_layout.addRow("Total paiements:", self.total_label)
        stats_layout.addRow("Montant total perçu:", self.montant_total_label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Par classe
        classe_group = QGroupBox("Par Classe")
        self.classe_text = QTextEdit()
        self.classe_text.setReadOnly(True)
        classe_layout = QVBoxLayout()
        classe_layout.addWidget(self.classe_text)
        classe_group.setLayout(classe_layout)
        layout.addWidget(classe_group)
        
        # Par statut
        statut_group = QGroupBox("Par Statut")
        self.statut_text = QTextEdit()
        self.statut_text.setReadOnly(True)
        statut_layout = QVBoxLayout()
        statut_layout.addWidget(self.statut_text)
        statut_group.setLayout(statut_layout)
        layout.addWidget(statut_group)
        
        self.afficher_statistiques()
    
    def setup_classe_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # Groupe recherche
        classe_group = QGroupBox("Liste des Élèves par Classe")
        classe_layout = QFormLayout()
        
        self.classe_input = QLineEdit()
        self.rechercher_classe_btn = QPushButton("Rechercher")
        self.rechercher_classe_btn.clicked.connect(self.lister_eleves_par_classe)
        
        classe_layout.addRow("Classe:", self.classe_input)
        classe_layout.addRow(self.rechercher_classe_btn)
        
        classe_group.setLayout(classe_layout)
        layout.addWidget(classe_group)
        
        # Résultats
        result_group = QGroupBox("Résultats")
        result_layout = QVBoxLayout()
        
        self.eleves_payes_text = QTextEdit()
        self.eleves_payes_text.setReadOnly(True)
        self.eleves_non_payes_text = QTextEdit()
        self.eleves_non_payes_text.setReadOnly(True)
        
        result_layout.addWidget(QLabel("Élèves ayant payé:"))
        result_layout.addWidget(self.eleves_payes_text)
        result_layout.addWidget(QLabel("Élèves n'ayant pas payé:"))
        result_layout.addWidget(self.eleves_non_payes_text)
        
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
    
    def enregistrer_paiement(self):
        # Vérification des champs obligatoires
        champs_obligatoires = {
            "Nom": self.nom_input.text().strip(),
            "Prénom": self.prenom_input.text().strip(),
            "Classe": self.classe_input.text().strip(),
            "Montant": self.montant_input.text().strip(),
            "Mois": self.mois_input.text().strip()
        }
        
        champs_vides = [nom for nom, valeur in champs_obligatoires.items() if not valeur]
        
        if champs_vides:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Champs manquants")
            msg.setText("Veuillez remplir tous les champs obligatoires:")
            msg.setDetailedText("\n".join(f"• {champ}" for champ in champs_vides))
            msg.setStyleSheet("""
                QMessageBox {
                    font-size: 12px;
                }
                QLabel#qt_msgbox_label {
                    margin-bottom: 10px;
                }
            """)
            msg.exec()
            return
        
        # Vérification du montant
        try:
            montant = float(self.montant_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Montant invalide", "Le montant doit être un nombre valide")
            return
        
        # Enregistrement du paiement
        paiement = {
            'nom': champs_obligatoires['Nom'].upper(),
            'prenom': champs_obligatoires['Prénom'].capitalize(),
            'classe': champs_obligatoires['Classe'].upper(),
            'montant': str(montant),
            'mois': champs_obligatoires['Mois'],
            'methode_paiement': self.methode_combo.currentText(),
            'statut': self.statut_combo.currentText(),
            'notes': self.notes_input.toPlainText().strip()
        }
        
        id_paiement = self.gestion.ajouter_paiement(paiement)
        
        # Message de confirmation
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Paiement enregistré")
        msg.setText(f"Paiement enregistré avec succès!\nID: {id_paiement}")
        msg.exec()
        
        # Réinitialisation du formulaire
        self.nom_input.clear()
        self.prenom_input.clear()
        self.classe_input.clear()
        self.montant_input.clear()
        self.mois_input.clear()
        self.notes_input.clear()
        self.statut_combo.setCurrentText("payé")
    
    def generer_recu(self):
        # Vérifier qu'un paiement est en cours
        if not all([
            self.nom_input.text().strip(),
            self.prenom_input.text().strip(),
            self.montant_input.text().strip()
        ]):
            QMessageBox.warning(self, "Impossible", "Veuillez d'abord remplir les informations du paiement")
            return
        
        # Créer un dialogue de confirmation
        reply = QMessageBox.question(
            self, 'Générer un reçu',
            "Voulez-vous générer un reçu pour ce paiement?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Générer le contenu du reçu
            contenu = f"""
            REÇU DE PAIEMENT SCOLAIRE
            {'='*40}
            Élève: {self.prenom_input.text()} {self.nom_input.text()}
            Classe: {self.classe_input.text()}
            Montant: {self.montant_input.text()} FCFA
            Mois: {self.mois_input.text()}
            Méthode: {self.methode_combo.currentText()}
            Date: {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}
            {'='*40}
            """
            
            # Afficher le reçu
            dialog = QDialog(self)
            dialog.setWindowTitle("Reçu de paiement")
            dialog.setMinimumWidth(400)
            
            layout = QVBoxLayout()
            text_edit = QTextEdit()
            text_edit.setPlainText(contenu)
            text_edit.setReadOnly(True)
            
            btn_save = QPushButton("Enregistrer le reçu")
            btn_close = QPushButton("Fermer")
            
            btn_layout = QHBoxLayout()
            btn_layout.addWidget(btn_save)
            btn_layout.addWidget(btn_close)
            
            layout.addWidget(text_edit)
            layout.addLayout(btn_layout)
            dialog.setLayout(layout)
            
            def save_receipt():
                # Implémenter la sauvegarde du reçu
                pass
            
            btn_save.clicked.connect(save_receipt)
            btn_close.clicked.connect(dialog.close)
            
            dialog.exec()
    
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
        # Implémentez l'export ici
        QMessageBox.information(self, "Export", "Fonctionnalité d'export à implémenter")
    
    def afficher_statistiques(self):
        stats = self.gestion.get_statistiques()
        
        self.total_label.setText(str(stats["total"]))
        self.montant_total_label.setText(f"{stats['montant_total']:.2f} FCFA")
        
        # Par classe
        classe_text = ""
        for classe, montants in sorted(stats["par_classe"].items()):
            classe_text += f"{classe}: {len(montants)} paiements, Total: {sum(montants):.2f} FCFA\n"
        self.classe_text.setPlainText(classe_text)
        
        # Par statut
        statut_text = ""
        for statut, count in stats["par_statut"].items():
            statut_text += f"{statut}: {count}\n"
        self.statut_text.setPlainText(statut_text)
    
    def lister_eleves_par_classe(self):
        classe = self.classe_input.text().strip().upper()
        if not classe:
            QMessageBox.warning(self, "Classe manquante", "Veuillez entrer une classe")
            return
        
        paiements_classe = [p for p in self.gestion.paiements if p['classe'] == classe]
        if not paiements_classe:
            QMessageBox.information(self, "Aucun résultat", f"Aucun élève trouvé pour la classe {classe}")
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Style global
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())