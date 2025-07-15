from datetime import datetime
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu
from PyQt5.QtGui import QIcon

class NotificationManager:
    def __init__(self):
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(QIcon("icons/school.png"))
        self.tray.show()
    
    def notify(self, title, message):
        self.tray.showMessage(title, message, QSystemTrayIcon.Information)
    
    def check_paiements_retard(self, paiements):
        aujourd_hui = datetime.now()
        for p in paiements:
            date_paiement = datetime.strptime(p['date_paiement'], "%d/%m/%Y")
            if (aujourd_hui - date_paiement).days > 30:
                self.notify(
                    "Paiement en retard",
                    f"L'élève {p['prenom']} {p['nom']} est en retard de paiement"
                )