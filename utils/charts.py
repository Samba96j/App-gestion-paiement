import matplotlib.pyplot as plt
from io import BytesIO
from PyQt5.QtGui import QImage, QPixmap
import numpy as np

class ChartGenerator:
    @staticmethod
    def generate_pie_chart(data, labels, title):
        plt.figure(figsize=(6, 6))
        plt.pie(data, labels=labels, autopct='%1.1f%%')
        plt.title(title)
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()
        
        buffer.seek(0)
        image = QImage()
        image.loadFromData(buffer.getvalue())
        
        return image