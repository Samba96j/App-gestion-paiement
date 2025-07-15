import csv
import datetime
import os
import sys
from typing import List, Dict, Optional
from collections import defaultdict

# Configuration
FICHIER_DONNEES = "paiements_eleves.csv"
FICHIER_SAUVEGARDE = "sauvegarde_paiements_{}.csv"
CHAMPS = ["id", "nom", "prenom", "classe", "montant", "mois", "date_paiement", 
          "heure_paiement", "methode_paiement", "statut", "notes"]
STATUTS = ["payé", "impayé", "partiel", "remboursé"]

class GestionPaiements:
    def __init__(self):
        self.paiements = []
        self.initialiser_fichier()
        self.charger_donnees()
        
    def initialiser_fichier(self) -> None:
        """Initialise le fichier CSV avec les en-têtes si nécessaire"""
        if not os.path.exists(FICHIER_DONNEES):
            with open(FICHIER_DONNEES, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=CHAMPS)
                writer.writeheader()
    
    def charger_donnees(self) -> None:
        """Charge les données depuis le fichier CSV"""
        try:
            with open(FICHIER_DONNEES, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.paiements = [row for row in reader]
        except FileNotFoundError:
            self.paiements = []
    
    def sauvegarder_donnees(self) -> None:
        """Sauvegarde les données dans le fichier CSV"""
        with open(FICHIER_DONNEES, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CHAMPS)
            writer.writeheader()
            writer.writerows(self.paiements)
        
        # Créer une sauvegarde datée
        date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(FICHIER_SAUVEGARDE.format(date_str), mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CHAMPS)
            writer.writeheader()
            writer.writerows(self.paiements)
    
    def generer_id(self) -> str:
        """Génère un ID unique pour un nouveau paiement"""
        ids = [int(p['id']) for p in self.paiements if 'id' in p and p['id'].isdigit()]
        return str(max(ids) + 1) if ids else "1"
    
    def enregistrer_paiement(self) -> None:
        """Enregistre un nouveau paiement"""
        print("\n--- NOUVEAU PAIEMENT ---")
        
        paiement = {
            'id': self.generer_id(),
            'nom': input("Nom de l'élève: ").strip().upper(),
            'prenom': input("Prénom de l'élève: ").strip().capitalize(),
            'classe': input("Classe: ").strip().upper(),
            'montant': input("Montant payé: ").strip(),
            'mois': input("Mois concerné (ex: Septembre 2023): ").strip(),
            'methode_paiement': self.choisir_methode_paiement(),
            'statut': "payé",
            'notes': input("Notes supplémentaires (facultatif): ").strip()
        }
        
        maintenant = datetime.datetime.now()
        paiement['date_paiement'] = maintenant.strftime("%d/%m/%Y")
        paiement['heure_paiement'] = maintenant.strftime("%H:%M:%S")
        
        self.paiements.append(paiement)
        self.sauvegarder_donnees()
        
        print(f"\n✅ Paiement enregistré (ID: {paiement['id']})")
        self.generer_recu(paiement)
    
    def choisir_methode_paiement(self) -> str:
        """Affiche un menu pour choisir la méthode de paiement"""
        methodes = ["Espèces", "Chèque", "Virement", "Carte bancaire", "Mobile Money"]
        print("\nMéthodes de paiement disponibles:")
        for i, methode in enumerate(methodes, 1):
            print(f"{i}. {methode}")
        
        while True:
            choix = input("Choix (1-5): ").strip()
            if choix.isdigit() and 1 <= int(choix) <= 5:
                return methodes[int(choix)-1]
            print("Choix invalide. Veuillez entrer un nombre entre 1 et 5.")
    
    def modifier_paiement(self) -> None:
        """Modifie un paiement existant"""
        print("\n--- MODIFICATION PAIEMENT ---")
        id_paiement = input("ID du paiement à modifier: ").strip()
        
        for i, paiement in enumerate(self.paiements):
            if 'id' in paiement and paiement['id'] == id_paiement:
                print("\nPaiement trouvé:")
                self.afficher_paiement_detail(paiement)
                
                print("\nEntrez les nouvelles valeurs (laissez vide pour ne pas modifier):")
                nouvelles_valeurs = {
                    'nom': input(f"Nom ({paiement['nom']}): ").strip() or paiement['nom'],
                    'prenom': input(f"Prénom ({paiement['prenom']}): ").strip() or paiement['prenom'],
                    'classe': input(f"Classe ({paiement['classe']}): ").strip() or paiement['classe'],
                    'montant': input(f"Montant ({paiement['montant']}): ").strip() or paiement['montant'],
                    'mois': input(f"Mois ({paiement['mois']}): ").strip() or paiement['mois'],
                    'methode_paiement': input(f"Méthode ({paiement['methode_paiement']}): ").strip() or paiement['methode_paiement'],
                    'statut': self.choisir_statut(paiement['statut']),
                    'notes': input(f"Notes ({paiement['notes']}): ").strip() or paiement['notes']
                }
                
                # Mise à jour de la date/heure de modification
                maintenant = datetime.datetime.now()
                nouvelles_valeurs['date_paiement'] = maintenant.strftime("%d/%m/%Y")
                nouvelles_valeurs['heure_paiement'] = maintenant.strftime("%H:%M:%S")
                
                self.paiements[i] = {**paiement, **nouvelles_valeurs}
                self.sauvegarder_donnees()
                print("\n✅ Paiement modifié avec succès")
                return
        
        print("\n❌ Aucun paiement trouvé avec cet ID")
    
    def choisir_statut(self, statut_actuel: str) -> str:
        """Permet de choisir un statut parmi les options valides"""
        print(f"\nStatut actuel: {statut_actuel}")
        print("Nouveau statut:")
        for i, statut in enumerate(STATUTS, 1):
            print(f"{i}. {statut}")
        
        while True:
            choix = input("Choix (1-4, laissez vide pour garder actuel): ").strip()
            if not choix:
                return statut_actuel
            if choix.isdigit() and 1 <= int(choix) <= 4:
                return STATUTS[int(choix)-1]
            print("Choix invalide. Veuillez entrer un nombre entre 1 et 4.")
    
    def rechercher_paiements(self) -> None:
        """Recherche des paiements selon différents critères"""
        print("\n--- RECHERCHE PAIEMENTS ---")
        print("1. Par ID")
        print("2. Par élève (nom/prénom)")
        print("3. Par classe")
        print("4. Par mois")
        print("5. Par statut")
        choix = input("Votre choix (1-5): ").strip()
        
        if choix == '1':
            id_paiement = input("ID du paiement: ").strip()
            resultats = [p for p in self.paiements if p['id'] == id_paiement]
        elif choix == '2':
            nom = input("Nom: ").strip().upper()
            prenom = input("Prénom: ").strip().capitalize()
            resultats = [p for p in self.paiements if p['nom'] == nom and p['prenom'] == prenom]
        elif choix == '3':
            classe = input("Classe: ").strip().upper()
            resultats = [p for p in self.paiements if p['classe'] == classe]
        elif choix == '4':
            mois = input("Mois (ex: Septembre 2023): ").strip()
            resultats = [p for p in self.paiements if p['mois'] == mois]
        elif choix == '5':
            print("\nStatuts disponibles:")
            for i, statut in enumerate(STATUTS, 1):
                print(f"{i}. {statut}")
            choix_statut = input("Choix (1-4): ").strip()
            if choix_statut.isdigit() and 1 <= int(choix_statut) <= 4:
                resultats = [p for p in self.paiements if p['statut'] == STATUTS[int(choix_statut)-1]]
            else:
                print("Choix invalide")
                return
        else:
            print("Choix invalide")
            return
        
        if not resultats:
            print("\nAucun paiement trouvé")
        else:
            print(f"\n{len(resultats)} paiement(s) trouvé(s):")
            for paiement in resultats:
                self.afficher_paiement_resume(paiement)
    
    def afficher_paiement_resume(self, paiement: Dict) -> None:
        """Affiche un résumé du paiement"""
        print(f"\nID: {paiement['id']} | {paiement['prenom']} {paiement['nom']} ({paiement['classe']})")
        print(f"Montant: {paiement['montant']} FCFA | Mois: {paiement['mois']}")
        print(f"Statut: {paiement['statut']} | Méthode: {paiement['methode_paiement']}")
        print(f"Date: {paiement['date_paiement']} à {paiement['heure_paiement']}")
    
    def afficher_paiement_detail(self, paiement: Dict) -> None:
        """Affiche les détails complets d'un paiement"""
        self.afficher_paiement_resume(paiement)
        if paiement['notes']:
            print(f"\nNotes: {paiement['notes']}")
        print("-" * 40)
    
    def generer_recu(self, paiement: Dict) -> None:
        """Génère un reçu pour un paiement"""
        print("\n--- REÇU DE PAIEMENT ---")
        self.afficher_paiement_detail(paiement)
        
        choix = input("\nVoulez-vous sauvegarder ce reçu? (O/N): ").strip().upper()
        if choix == 'O':
            nom_fichier = f"recu_{paiement['id']}_{paiement['nom']}_{paiement['prenom']}.txt"
            with open(nom_fichier, 'w', encoding='utf-8') as f:
                f.write("ÉCOLE SECONDAIRE - REÇU DE PAIEMENT\n")
                f.write("="*40 + "\n")
                f.write(f"ID: {paiement['id']}\n")
                f.write(f"Élève: {paiement['prenom']} {paiement['nom']}\n")
                f.write(f"Classe: {paiement['classe']}\n")
                f.write(f"Montant: {paiement['montant']} FCFA\n")
                f.write(f"Mois: {paiement['mois']}\n")
                f.write(f"Statut: {paiement['statut']}\n")
                f.write(f"Méthode: {paiement['methode_paiement']}\n")
                f.write(f"Date: {paiement['date_paiement']} à {paiement['heure_paiement']}\n")
                if paiement['notes']:
                    f.write(f"\nNotes: {paiement['notes']}\n")
                f.write("\nMerci pour votre confiance!\n")
                f.write("="*40 + "\n")
            
            print(f"Reçu sauvegardé sous: {nom_fichier}")
    
    def statistiques(self) -> None:
        """Affiche des statistiques sur les paiements"""
        if not self.paiements:
            print("\nAucun paiement enregistré")
            return
        
        total_paiements = len(self.paiements)
        total_montant = sum(float(p['montant']) for p in self.paiements if p['statut'] == 'payé')
        
        # Par classe
        classes = defaultdict(list)
        for p in self.paiements:
            classes[p['classe']].append(float(p['montant']))
        
        # Par statut
        statuts = defaultdict(int)
        for p in self.paiements:
            statuts[p['statut']] += 1
        
        print("\n--- STATISTIQUES ---")
        print(f"Total paiements: {total_paiements}")
        print(f"Montant total perçu: {total_montant:.2f} FCFA")
        
        print("\nPar classe:")
        for classe, montants in sorted(classes.items()):
            print(f"- {classe}: {len(montants)} paiements, Total: {sum(montants):.2f} FCFA")
        
        print("\nPar statut:")
        for statut, count in statuts.items():
            print(f"- {statut}: {count}")
        
        print("\nDerniers paiements:")
        derniers = sorted(self.paiements, key=lambda x: (
            datetime.datetime.strptime(x['date_paiement'], "%d/%m/%Y"),
            datetime.datetime.strptime(x['heure_paiement'], "%H:%M:%S")
        ), reverse=True)[:5]
        
        for p in derniers:
            print(f"{p['date_paiement']} - {p['prenom']} {p['nom']}: {p['montant']} FCFA ({p['statut']})")
    
    def exporter_donnees(self) -> None:
        """Exporte les données dans un format externe"""
        print("\n--- EXPORT DONNÉES ---")
        print("1. Format CSV (Excel)")
        print("2. Format Texte")
        choix = input("Choix (1-2): ").strip()
        
        date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if choix == '1':
            nom_fichier = f"export_paiements_{date_str}.csv"
            with open(nom_fichier, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=CHAMPS)
                writer.writeheader()
                writer.writerows(self.paiements)
            print(f"Données exportées dans {nom_fichier}")
        
        elif choix == '2':
            nom_fichier = f"export_paiements_{date_str}.txt"
            with open(nom_fichier, 'w', encoding='utf-8') as f:
                f.write("LISTE DES PAIEMENTS\n")
                f.write("="*50 + "\n")
                for p in self.paiements:
                    f.write(f"ID: {p['id']}\n")
                    f.write(f"Élève: {p['prenom']} {p['nom']} ({p['classe']})\n")
                    f.write(f"Montant: {p['montant']} FCFA | Mois: {p['mois']}\n")
                    f.write(f"Statut: {p['statut']} | Méthode: {p['methode_paiement']}\n")
                    f.write(f"Date: {p['date_paiement']} à {p['heure_paiement']}\n")
                    if p['notes']:
                        f.write(f"Notes: {p['notes']}\n")
                    f.write("-"*50 + "\n")
            print(f"Données exportées dans {nom_fichier}")
        
        else:
            print("Choix invalide")
    
    def lister_eleves_par_classe(self) -> None:
        """Liste les élèves d'une classe spécifiée et les sépare en deux groupes : payés et non payés"""
        classe = input("Entrez la classe à rechercher : ").strip().upper()
        
        if not classe:
            print("\n❌ Classe invalide.")
            return
        
        # Filtrer les paiements par classe
        paiements_classe = [p for p in self.paiements if p['classe'] == classe]
        
        if not paiements_classe:
            print(f"\n❌ Aucun élève trouvé pour la classe {classe}.")
            return
        
        # Séparer les élèves en deux groupes : payés et non payés
        eleves_payes = [p for p in paiements_classe if p['statut'] == "payé"]
        eleves_non_payes = [p for p in paiements_classe if p['statut'] != "payé"]
        
        print(f"\n=== Liste des élèves de la classe {classe} ===")
        
        print("\n✅ Élèves ayant payé :")
        if eleves_payes:
            for eleve in eleves_payes:
                print(f"- {eleve['prenom']} {eleve['nom']} (Montant : {eleve['montant']} FCFA, Mois : {eleve['mois']})")
        else:
            print("Aucun élève n'a payé.")
        
        print("\n❌ Élèves n'ayant pas payé :")
        if eleves_non_payes:
            for eleve in eleves_non_payes:
                print(f"- {eleve['prenom']} {eleve['nom']} (Statut : {eleve['statut']}, Mois : {eleve['mois']})")
        else:
            print("Tous les élèves ont payé.")

def menu_principal():
    """Affiche le menu principal"""
    gestion = GestionPaiements()
    
    while True:
        print("\n=== GESTION DES PAIEMENTS ===")
        print("1. Nouveau paiement")
        print("2. Modifier paiement")
        print("3. Rechercher paiements")
        print("4. Statistiques")
        print("5. Exporter données")
        print("6. Lister élèves par classe")
        print("7. Quitter")
        
        choix = input("\nVotre choix (1-7): ").strip()
        
        if choix == '1':
            gestion.enregistrer_paiement()
        elif choix == '2':
            gestion.modifier_paiement()
        elif choix == '3':
            gestion.rechercher_paiements()
        elif choix == '4':
            gestion.statistiques()
        elif choix == '5':
            gestion.exporter_donnees()
        elif choix == '6':
            gestion.lister_eleves_par_classe()
        elif choix == '7':
            print("\nMerci d'avoir utilisé le système de gestion des paiements. Au revoir!")
            break
        else:
            print("\nChoix invalide. Veuillez sélectionner une option entre 1 et 7.")

if __name__ == "__main__":
    menu_principal()