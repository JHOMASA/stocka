from fpdf import FPDF
from datetime import datetime
import os
from typing import Dict

class SunatIntegration:
    def __init__(self):
        self.output_dir = "facturas"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generar_factura(self, factura_data: Dict) -> str:
        """Generate SUNAT-compliant invoice PDF"""
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # Encabezado
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="FACTURA ELECTRÓNICA", ln=1, align='C')
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"N° {factura_data['numero']}", ln=1, align='C')
        
        # Datos del emisor
        pdf.cell(200, 10, txt="DENTAL SUPPLY S.A.C.", ln=1)
        pdf.cell(200, 10, txt="RUC: 20601234567", ln=1)
        pdf.cell(200, 10, txt="Av. Dental 123, Lima", ln=1)
        
        # Datos del cliente
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="DATOS DEL CLIENTE", ln=1)
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"{factura_data['cliente']['nombre']}", ln=1)
        pdf.cell(200, 10, txt=f"{factura_data['cliente']['tipo_doc']}: {factura_data['cliente']['numero_doc']}", ln=1)
        
        # Detalle de la factura
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="DETALLE DE PRODUCTOS", ln=1)
        pdf.set_font("Arial", size=10)
        
        # Cabecera de tabla
        pdf.cell(100, 10, txt="Descripción", border=1)
        pdf.cell(30, 10, txt="Cantidad", border=1)
        pdf.cell(30, 10, txt="P. Unit.", border=1)
        pdf.cell(30, 10, txt="Total", border=1, ln=1)
        
        # Items
        for item in factura_data['items']:
            pdf.cell(100, 10, txt=item['descripcion'], border=1)
            pdf.cell(30, 10, txt=str(item['cantidad']), border=1)
            pdf.cell(30, 10, txt=f"S/. {item['precio_unitario']:.2f}", border=1)
            pdf.cell(30, 10, txt=f"S/. {item['total']:.2f}", border=1, ln=1)
        
        # Totales
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt=f"OP. GRAVADA: S/. {factura_data['subtotal']:.2f}", ln=1)
        pdf.cell(200, 10, txt=f"IGV (18%): S/. {factura_data['igv']:.2f}", ln=1)
        pdf.cell(200, 10, txt=f"TOTAL: S/. {factura_data['total']:.2f}", ln=1)
        
        # Pie de página
        pdf.ln(20)
        pdf.set_font("Arial", 'I', 8)
        pdf.cell(200, 10, txt="Representación impresa de la factura electrónica", ln=1, align='C')
        pdf.cell(200, 10, txt=f"Fecha de emisión: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", ln=1, align='C')
        
        # Guardar archivo
        filename = f"factura_{factura_data['numero']}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        pdf.output(filepath)
        
        return filepath
