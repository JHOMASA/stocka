from fpdf import FPDF
from datetime import datetime
import os
from typing import Dict  
import sys
import warnings

# PDF Engine Detection
PDF_ENGINE = None
FPDF = None

try:
    # First try standard import
    from fpdf import FPDF
    PDF_ENGINE = "fpdf2"
except ImportError:
    try:
        # Try absolute import path
        from fpdf.fpdf import FPDF
        PDF_ENGINE = "fpdf2-absolute"
    except ImportError:
        try:
            # Try legacy import
            import fpdf2
            from fpdf2 import FPDF
            PDF_ENGINE = "fpdf2-legacy"
        except ImportError:
            # Final fallback - mock FPDF class
            class FPDF:
                def __init__(self, *args, **kwargs):
                    raise RuntimeError(
                        "PDF functionality disabled. Required package not found.\n"
                        "Install with: pip install fpdf2"
                    )
            PDF_ENGINE = "none"
            warnings.warn(
                "PDF generation disabled. Install fpdf2 package.",
                RuntimeWarning,
                stacklevel=2
            )

# Export the FPDF class
if FPDF is None:
    FPDF = type('FPDF', (), {})
if not PDF_ENGINE:
    import warnings
    warnings.warn("PDF generation unavailable - install fpdf2")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFGenerator:
    """Handles PDF generation with multiple fallback options"""
    def __init__(self):
        self.pdf_engine = self._init_pdf_engine()
        self.output_dir = "facturas"
        os.makedirs(self.output_dir, exist_ok=True)

    def _init_pdf_engine(self) -> Tuple[str, object]:
        """Initialize the best available PDF engine"""
        engines = [
            ('fpdf2', self._try_fpdf2),
            ('reportlab', self._try_reportlab),
            ('pdfkit', self._try_pdfkit)
        ]

        for name, init_func in engines:
            engine = init_func()
            if engine:
                logger.info(f"Using PDF engine: {name}")
                return (name, engine)
        
        warnings.warn("No PDF library available - PDF generation disabled")
        return (None, None)

    def _try_fpdf2(self):
        """Try initializing fpdf2"""
        try:
            from fpdf import FPDF
            return FPDF
        except ImportError:
            return None

    def _try_reportlab(self):
        """Try initializing reportlab"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            return {'canvas': canvas, 'pagesize': letter}
        except ImportError:
            return None

    def _try_pdfkit(self):
        """Try initializing pdfkit (HTML to PDF)"""
        try:
            import pdfkit
            return pdfkit
        except ImportError:
            return None

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
       """Generate PDF using fpdf2 with complete invoice formatting"""
       pdf = self.pdf_engine[1]()
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
       pdf.set_font("Arial", 'B', 12)
       pdf.cell(200, 10, txt="DENTAL SUPPLY S.A.C.", ln=1)
       pdf.set_font("Arial", size=12)
       pdf.cell(200, 10, txt="RUC: 20601234567", ln=1)
       pdf.cell(200, 10, txt="Av. Dental 123, Lima", ln=1)
       pdf.cell(200, 10, txt="Tel: (01) 1234567", ln=1)
    
       # Customer information
       pdf.ln(10)
       pdf.set_font("Arial", 'B', 12)
       pdf.cell(200, 10, txt="DATOS DEL CLIENTE", ln=1)
       pdf.set_font("Arial", size=12)
       pdf.cell(200, 10, txt=f"Nombre: {factura_data['cliente']['nombre']}", ln=1)
       pdf.cell(200, 10, txt=f"Documento: {factura_data['cliente']['tipo_doc']} {factura_data['cliente']['numero_doc']}", ln=1)
       pdf.cell(200, 10, txt=f"Dirección: {factura_data['cliente']['direccion']}", ln=1)
    
       # Invoice details header
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
       for item in factura_data['items']:
         pdf.cell(20, 10, txt=str(item['cantidad']), border=1)
         pdf.cell(100, 10, txt=item['descripcion'], border=1)
         pdf.cell(30, 10, txt=f"S/. {item['precio_unitario']:.2f}", border=1)
         pdf.cell(30, 10, txt=f"S/. {item['total']:.2f}", border=1, ln=1)
    
       # Totals section
       pdf.ln(10)
       pdf.set_font("Arial", 'B', 12)
       pdf.cell(160, 10, txt="Subtotal:", ln=0)
       pdf.cell(30, 10, txt=f"S/. {factura_data['subtotal']:.2f}", ln=1)
       pdf.cell(160, 10, txt="IGV (18%):", ln=0)
       pdf.cell(30, 10, txt=f"S/. {factura_data['igv']:.2f}", ln=1)
       pdf.cell(160, 10, txt="TOTAL:", ln=0)
       pdf.cell(30, 10, txt=f"S/. {factura_data['total']:.2f}", ln=1)
    
       # Footer
       pdf.ln(20)
       pdf.set_font("Arial", 'I', 8)
       pdf.cell(200, 10, txt="Representación impresa de la factura electrónica", ln=1, align='C')
       pdf.cell(200, 10, txt=f"Fecha de emisión: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", ln=1, align='C')
    
       # Save file
       filename = f"factura_{factura_data['numero']}.pdf"
       filepath = os.path.join(self.output_dir, filename)
       pdf.output(filepath)
       return filepath

    def _create_with_reportlab(self, factura_data: Dict) -> str:
        """Generate PDF using reportlab with complete invoice formatting"""
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
    
        # Create story (content elements)
        story = []
    
        # Title
        story.append(Paragraph("FACTURA ELECTRÓNICA", styles['InvoiceTitle']))
        story.append(Paragraph(f"N° {factura_data['numero']}", styles['Heading2']))
    
        # Company info
        story.append(Paragraph("<b>DENTAL SUPPLY S.A.C.</b>", styles['Normal']))
        story.append(Paragraph("RUC: 20601234567", styles['Normal']))
        story.append(Paragraph("Av. Dental 123, Lima", styles['Normal']))
        story.append(Paragraph("Tel: (01) 1234567", styles['Normal']))
    
        # Customer info
        story.append(Paragraph("<b>DATOS DEL CLIENTE</b>", styles['Heading2']))
        story.append(Paragraph(f"Nombre: {factura_data['cliente']['nombre']}", styles['Normal']))
        story.append(Paragraph(f"Documento: {factura_data['cliente']['tipo_doc']} {factura_data['cliente']['numero_doc']}", styles['Normal']))
        story.append(Paragraph(f"Dirección: {factura_data['cliente']['direccion']}", styles['Normal']))
    
        # Invoice items table
        data = [
           ['Cant.', 'Descripción', 'P. Unit.', 'Total']
        ]
    
        for item in factura_data['items']:
          data.append([
            str(item['cantidad']),
            item['descripcion'],
            f"S/. {item['precio_unitario']:.2f}",
            f"S/. {item['total']:.2f}"
           ])
    
        # Add totals
        data.append(['', '', 'Subtotal:', f"S/. {factura_data['subtotal']:.2f}"])
        data.append(['', '', 'IGV (18%):', f"S/. {factura_data['igv']:.2f}"])
        data.append(['', '', '<b>TOTAL:</b>', f"<b>S/. {factura_data['total']:.2f}</b>"])
    
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
    
        story.append(table)
    
        # Footer
        story.append(Paragraph(
          f"<i>Representación impresa de la factura electrónica - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</i>",
          ParagraphStyle(name='Footer', fontSize=8, alignment=1)
        ))
    
        # Build PDF
        doc.build(story)
        return filepath

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
        # Implement your HTML invoice template here
        return f"""
        <html>
            <body>
                <h1>FACTURA ELECTRÓNICA</h1>
                <p>N° {factura_data['numero']}</p>
                <!-- Add other invoice elements -->
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
