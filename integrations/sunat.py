import os
import sys
import logging
import warnings
from io import BytesIO
from datetime import datetime
from typing import Dict, Optional, Tuple, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFGenerator:
    """Handles PDF generation with multiple fallback options"""
    def __init__(self):
        self.output_dir = "facturas"
        os.makedirs(self.output_dir, exist_ok=True)
        self.pdf_engine = self._init_pdf_engine()
        
    def _init_pdf_engine(self) -> Tuple[str, Any]:
        """Initialize the best available PDF engine"""
        engines = [
            ('fpdf2', self._try_fpdf2),
            ('reportlab', self._try_reportlab),
            ('pdfkit', self._try_pdfkit)
        ]

        for name, init_func in engines:
            try:
                engine = init_func()
                if engine:
                    logger.info(f"Using PDF engine: {name}")
                    return (name, engine)
            except ImportError:
                continue
        
        logger.warning("No PDF library available - PDF generation disabled")
        return (None, None)

    def _try_fpdf2(self):
        """Initialize fpdf2 engine"""
        from fpdf import FPDF
        return FPDF

    def _try_reportlab(self):
    """Initialize reportlab engine"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        return {'canvas': canvas, 'pagesize': letter}
    except ImportError:
        return None

    def _try_pdfkit(self):
        """Initialize pdfkit engine"""
        import pdfkit
        return pdfkit

    def create_invoice(self, factura_data: Dict) -> Optional[str]:
        """Create invoice using available PDF engine"""
        if not self.pdf_engine[0]:
            return None

        try:
            if self.pdf_engine[0] == 'fpdf2':
                return self._create_with_fpdf(factura_data)
            elif self.pdf_engine[0] == 'reportlab':
                return self._create_with_reportlab(factura_data)
            elif self.pdf_engine[0] == 'pdfkit':
                return self._create_with_pdfkit(factura_data)
        except Exception as e:
            logger.error(f"PDF generation failed: {str(e)}")
            return None

    def _create_with_fpdf(self, factura_data: Dict) -> str:
        """Generate PDF using fpdf2"""
        FPDF = self.pdf_engine[1]
        pdf = FPDF()
        pdf.add_page()
        
        # Set document properties
        pdf.set_title(f"Factura {factura_data['numero']}")
        pdf.set_author("Dental Supply S.A.C.")
        
        # Header
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="FACTURA ELECTRÓNICA", ln=1, align='C')
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"N° {factura_data['numero']}", ln=1, align='C')
        
        # Company information
        self._add_company_info(pdf)
        
        # Customer information
        self._add_customer_info(pdf, factura_data['cliente'])
        
        # Invoice items
        self._add_invoice_items(pdf, factura_data['items'])
        
        # Totals
        self._add_totals(pdf, factura_data)
        
        # Footer
        self._add_footer(pdf)
        
        # Save file
        filename = f"factura_{factura_data['numero']}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        pdf.output(filepath)
        return filepath

    def _add_company_info(self, pdf):
        """Add company information to PDF"""
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="DENTAL SUPPLY S.A.C.", ln=1)
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="RUC: 20601234567", ln=1)
        pdf.cell(200, 10, txt="Av. Dental 123, Lima", ln=1)
        pdf.cell(200, 10, txt="Tel: (01) 1234567", ln=1)

    def _add_customer_info(self, pdf, cliente: Dict):
        """Add customer information to PDF"""
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="DATOS DEL CLIENTE", ln=1)
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Nombre: {cliente['nombre']}", ln=1)
        pdf.cell(200, 10, txt=f"Documento: {cliente['tipo_doc']} {cliente['numero_doc']}", ln=1)
        pdf.cell(200, 10, txt=f"Dirección: {cliente['direccion']}", ln=1)

    def _add_invoice_items(self, pdf, items: list):
        """Add invoice items to PDF"""
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="DETALLE DE FACTURA", ln=1)
        
        # Table header
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(20, 10, txt="Cant.", border=1)
        pdf.cell(100, 10, txt="Descripción", border=1)
        pdf.cell(30, 10, txt="P. Unit.", border=1)
        pdf.cell(30, 10, txt="Total", border=1, ln=1)
        
        # Table rows
        pdf.set_font("Arial", size=10)
        for item in items:
            pdf.cell(20, 10, txt=str(item['cantidad']), border=1)
            pdf.cell(100, 10, txt=item['descripcion'], border=1)
            pdf.cell(30, 10, txt=f"S/. {item['precio_unitario']:.2f}", border=1)
            pdf.cell(30, 10, txt=f"S/. {item['total']:.2f}", border=1, ln=1)

    def _add_totals(self, pdf, factura_data: Dict):
        """Add totals to PDF"""
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(160, 10, txt="Subtotal:", ln=0)
        pdf.cell(30, 10, txt=f"S/. {factura_data['subtotal']:.2f}", ln=1)
        pdf.cell(160, 10, txt="IGV (18%):", ln=0)
        pdf.cell(30, 10, txt=f"S/. {factura_data['igv']:.2f}", ln=1)
        pdf.cell(160, 10, txt="TOTAL:", ln=0)
        pdf.cell(30, 10, txt=f"S/. {factura_data['total']:.2f}", ln=1)

    def _add_footer(self, pdf):
        """Add footer to PDF"""
        pdf.ln(20)
        pdf.set_font("Arial", 'I', 8)
        pdf.cell(200, 10, txt="Representación impresa de la factura electrónica", ln=1, align='C')
        pdf.cell(200, 10, txt=f"Fecha de emisión: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", ln=1, align='C')

    def _create_with_reportlab(self, factura_data: Dict) -> str:
        """Generate PDF using reportlab"""
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle

        filename = f"factura_{factura_data['numero']}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        doc = SimpleDocTemplate(filepath, pagesize=self.pdf_engine[1]['pagesize'])
        styles = getSampleStyleSheet()

        # Custom styles
        styles.add(ParagraphStyle(
            name='InvoiceTitle',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=1  # Center
        ))

        # Create story elements
        story = []
        
        # Add title and company info
        story.extend(self._create_reportlab_header(styles, factura_data))
        
        # Add customer info
        story.extend(self._create_reportlab_customer_info(styles, factura_data['cliente']))
        
        # Add invoice items
        story.append(self._create_reportlab_items_table(factura_data['items']))
        
        # Add totals
        story.extend(self._create_reportlab_totals(factura_data))
        
        # Add footer
        story.append(self._create_reportlab_footer(styles))
        
        # Build PDF
        doc.build(story)
        return filepath

    def _create_reportlab_header(self, styles, factura_data: Dict) -> list:
        """Create header elements for reportlab"""
        elements = []
        elements.append(Paragraph("FACTURA ELECTRÓNICA", styles['InvoiceTitle']))
        elements.append(Paragraph(f"N° {factura_data['numero']}", styles['Heading2']))
        elements.append(Paragraph("<b>DENTAL SUPPLY S.A.C.</b>", styles['Normal']))
        elements.append(Paragraph("RUC: 20601234567", styles['Normal']))
        elements.append(Paragraph("Av. Dental 123, Lima", styles['Normal']))
        elements.append(Paragraph("Tel: (01) 1234567", styles['Normal']))
        return elements

    def _create_reportlab_customer_info(self, styles, cliente: Dict) -> list:
        """Create customer info elements for reportlab"""
        elements = []
        elements.append(Paragraph("<b>DATOS DEL CLIENTE</b>", styles['Heading2']))
        elements.append(Paragraph(f"Nombre: {cliente['nombre']}", styles['Normal']))
        elements.append(Paragraph(f"Documento: {cliente['tipo_doc']} {cliente['numero_doc']}", styles['Normal']))
        elements.append(Paragraph(f"Dirección: {cliente['direccion']}", styles['Normal']))
        return elements

    def _create_reportlab_items_table(self, items: list) -> Table:
       """Create items table for reportlab"""
       from reportlab.platypus import Table  # Move import here if needed
       from reportlab.lib import colors
    
       data = [['Cant.', 'Descripción', 'P. Unit.', 'Total']]
    
       for item in items:
          data.append([
            str(item['cantidad']),
            item['descripcion'],
            f"S/. {item['precio_unitario']:.2f}",
            f"S/. {item['total']:.2f}"
        ])
        
        table = Table(data, colWidths=[30, 200, 60, 60])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -4), colors.beige),
            ('GRID', (0, 0), (-1, -4), 1, colors.grey),
            ('GRID', (2, -3), (-1, -1), 1, colors.grey),
            ('SPAN', (0, -3), (1, -3)),
            ('SPAN', (0, -2), (1, -2)),
            ('SPAN', (0, -1), (1, -1)),
        ]))
        return table

    def _create_reportlab_totals(self, factura_data: Dict) -> list:
        """Create totals elements for reportlab"""
        data = [
            ['', '', 'Subtotal:', f"S/. {factura_data['subtotal']:.2f}"],
            ['', '', 'IGV (18%):', f"S/. {factura_data['igv']:.2f}"],
            ['', '', '<b>TOTAL:</b>', f"<b>S/. {factura_data['total']:.2f}</b>"]
        ]
        
        table = Table(data, colWidths=[30, 200, 60, 60])
        table.setStyle(TableStyle([
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (3, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (2, 0), (-1, -1), 1, colors.grey)
        ]))
        
        return [table]

    def _create_reportlab_footer(self, styles) -> Paragraph:
        """Create footer for reportlab"""
        return Paragraph(
            f"<i>Representación impresa de la factura electrónica - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</i>",
            ParagraphStyle(name='Footer', fontSize=8, alignment=1)
        )

    def _create_with_pdfkit(self, factura_data: Dict) -> str:
        """Generate PDF from HTML using pdfkit"""
        html_content = self._generate_invoice_html(factura_data)
        filepath = os.path.join(self.output_dir, f"factura_{factura_data['numero']}.pdf")
        
        self.pdf_engine[1].from_string(
            html_content,
            filepath,
            options={'encoding': 'UTF-8'}
        )
        return filepath

    def _generate_invoice_html(self, factura_data: Dict) -> str:
        """Generate HTML template for pdfkit"""
        items_html = "".join(
            f"<tr><td>{item['cantidad']}</td>"
            f"<td>{item['descripcion']}</td>"
            f"<td>S/. {item['precio_unitario']:.2f}</td>"
            f"<td>S/. {item['total']:.2f}</td></tr>"
            for item in factura_data['items']
        )
        
        return f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial; margin: 40px; }}
                    table {{ width: 100%; border-collapse: collapse; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .total-row {{ font-weight: bold; }}
                    .footer {{ font-size: 0.8em; text-align: center; margin-top: 40px; }}
                </style>
            </head>
            <body>
                <h1 style="text-align: center;">FACTURA ELECTRÓNICA</h1>
                <h2 style="text-align: center;">N° {factura_data['numero']}</h2>
                
                <div>
                    <h3>DENTAL SUPPLY S.A.C.</h3>
                    <p>RUC: 20601234567</p>
                    <p>Av. Dental 123, Lima</p>
                    <p>Tel: (01) 1234567</p>
                </div>
                
                <div style="margin-top: 20px;">
                    <h3>DATOS DEL CLIENTE</h3>
                    <p>Nombre: {factura_data['cliente']['nombre']}</p>
                    <p>Documento: {factura_data['cliente']['tipo_doc']} {factura_data['cliente']['numero_doc']}</p>
                    <p>Dirección: {factura_data['cliente']['direccion']}</p>
                </div>
                
                <h3 style="margin-top: 20px;">DETALLE DE FACTURA</h3>
                <table>
                    <tr>
                        <th>Cant.</th>
                        <th>Descripción</th>
                        <th>P. Unit.</th>
                        <th>Total</th>
                    </tr>
                    {items_html}
                    <tr class="total-row">
                        <td colspan="3">Subtotal:</td>
                        <td>S/. {factura_data['subtotal']:.2f}</td>
                    </tr>
                    <tr class="total-row">
                        <td colspan="3">IGV (18%):</td>
                        <td>S/. {factura_data['igv']:.2f}</td>
                    </tr>
                    <tr class="total-row">
                        <td colspan="3">TOTAL:</td>
                        <td>S/. {factura_data['total']:.2f}</td>
                    </tr>
                </table>
                
                <div class="footer">
                    <p>Representación impresa de la factura electrónica</p>
                    <p>Fecha de emisión: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                </div>
            </body>
        </html>
        """

class SunatIntegration:
    """Main SUNAT integration class"""
    def __init__(self):
        self.pdf = PDFGenerator()
        logger.info("SUNAT integration initialized")

    def generar_factura(self, factura_data: Dict) -> Optional[str]:
        """
        Generate SUNAT-compliant invoice
        Args:
            factura_data: Dictionary containing invoice data
        Returns:
            str: Path to generated PDF, or None if failed
        """
        try:
            if not self.pdf.pdf_engine[0]:
                logger.warning("PDF generation unavailable - no engine found")
                return None
                
            return self.pdf.create_invoice(factura_data)
        except Exception as e:
            logger.error(f"Invoice generation failed: {str(e)}")
            return None

# Export for compatibility
PDF_ENGINE = "fpdf2" if PDFGenerator().pdf_engine[0] == 'fpdf2' else "reportlab" if PDFGenerator().pdf_engine[0] == 'reportlab' else "pdfkit" if PDFGenerator().pdf_engine[0] == 'pdfkit' else "none"
FPDF = PDFGenerator().pdf_engine[1] if PDFGenerator().pdf_engine[0] else None

def verify_pdf_support() -> bool:
    """Check if PDF generation is available"""
    return PDF_ENGINE != "none"
