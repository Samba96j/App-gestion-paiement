from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

class PDFGenerator:
    @staticmethod
    def generate_receipt(paiement, output_path):
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        
        # En-tête
        elements.append(Paragraph("Reçu de Paiement", styles['Title']))
        
        # Données
        data = [
            ["Nom:", paiement['nom']],
            ["Prénom:", paiement['prenom']],
            ["Classe:", paiement['classe']],
            ["Montant:", f"{paiement['montant']} FCFA"],
            ["Date:", paiement['date_paiement']]
        ]
        
        t = Table(data)
        t.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(t)
        doc.build(elements)