import os
import logging
from datetime import datetime
from typing import Dict, Optional
import warnings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhatsAppIntegration:
    def __init__(self, db_connection=None):
        """
        Initialize WhatsApp integration with optional DB connection
        Args:
            db_connection: Optional database connection for inventory methods
        """
        self.db = db_connection
        self.enabled = os.getenv('WHATSAPP_ENABLED', 'false').lower() == 'true'
        
        try:
            import pywhatkit as wk
            self.wk = wk
            self.has_whatsapp = True
        except ImportError:
            self.has_whatsapp = False
            warnings.warn("pywhatkit not installed - WhatsApp features will be mocked")

    def _format_order_message(self, order_details: Dict) -> str:
        """Helper method to format order messages"""
        message = [
            "📦 *Pedido Dental*",
            f"📅 Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            "--------------------------------"
        ]
        
        message.extend(
            f"▪ {item['nombre']} x{item['cantidad']} - S/{item['precio_unitario']:.2f}"
            for item in order_details['items']
        )
        
        message.extend([
            "--------------------------------",
            f"💰 Total: S/{order_details['total']:.2f}",
            "",
            "Por favor confirmar disponibilidad. Gracias!"
        ])
        
        return '\n'.join(message)

    def send_alert(self, number: str, message: str) -> bool:
        """
        Send WhatsApp alert
        Args:
            number: Phone number with country code (no +)
            message: Text message to send
        Returns:
            bool: True if successful
        """
        if not self.enabled:
            logger.info(f"WhatsApp disabled - would send to {number}: {message}")
            return False
            
        if not self.has_whatsapp:
            logger.warning(f"WhatsApp mock - would send to {number}: {message}")
            return False

        try:
            self.wk.sendwhatmsg_instantly(
                phone_no=f"+{number}",
                message=message,
                wait_time=15,
                tab_close=True,
                print_wait_time=True
            )
            logger.info(f"Sent WhatsApp to {number}")
            return True
        except Exception as e:
            logger.error(f"WhatsApp error to {number}: {str(e)}")
            return False

    def send_order_to_supplier(self, supplier_phone: str, order_details: Dict) -> bool:
        """Send formatted order to supplier via WhatsApp"""
        try:
            message = self._format_order_message(order_details)
            return self.send_alert(supplier_phone, message)
        except Exception as e:
            logger.error(f"Order sending failed: {str(e)}")
            return False

    # Inventory-related methods (only if DB connection provided)
    def calcular_stock_acumulado(self, familia: str = None, subfamilia: str = None) -> Optional[Dict]:
        """Calculate aggregated stock by family/subfamily"""
        if not self.db:
            logger.warning("DB connection not available for stock calculation")
            return None

        query = """
        SELECT 
            familia,
            subfamilia,
            SUM(stock) as cantidad,
            SUM(stock * costo_unitario) as costo_total,
            SUM(stock * precio_venta) as valor_total
        FROM productos
        WHERE activo = TRUE
        """
        
        params = []
        if familia:
            query += " AND familia = ?"
            params.append(familia)
        if subfamilia:
            query += " AND subfamilia = ?"
            params.append(subfamilia)
        
        query += " GROUP BY familia, subfamilia"
        
        try:
            return self.db.execute_query(query, params)
        except Exception as e:
            logger.error(f"Stock calculation failed: {str(e)}")
            return None

    def actualizar_stock_familias(self, mes: int, anio: int) -> bool:
        """Update family stock table"""
        if not self.db:
            logger.warning("DB connection not available for stock update")
            return False

        datos = self.calcular_stock_acumulado()
        if not datos:
            return False

        try:
            for item in datos:
                self.db.execute_update("""
                INSERT OR REPLACE INTO stock_familias 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    item['familia'],
                    item['subfamilia'],
                    mes,
                    anio,
                    item['cantidad'],
                    item['costo_total'],
                    item['valor_total']
                ))
            return True
        except Exception as e:
            logger.error(f"Stock update failed: {str(e)}")
            return False
