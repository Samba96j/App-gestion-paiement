import os
from datetime import datetime

from PyQt5.QtWidgets import QSystemTrayIcon, QMenu
from PyQt5.QtGui import QIcon

from utils.config import BASE_DIR

class NotificationManager:
    def __init__(self):
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(QIcon(os.path.join(BASE_DIR, "icons", "school.png")))
        self.tray.show()
    
    def notify(self, title, message):
        self.tray.showMessage(title, message, QSystemTrayIcon.Information)
    
    def check_paiements_retard(self, paiements):
        aujourd_hui = datetime.now()
        for p in paiements:
            try:
                date_paiement = datetime.strptime(p.get('date_paiement', ''), "%d/%m/%Y")
            except (TypeError, ValueError):
                continue
            if (aujourd_hui - date_paiement).days > 30:
                self.notify(
                    "Paiement en retard",
                    f"L'élève {p.get('prenom', '')} {p.get('nom', '')} est en retard de paiement"
                )