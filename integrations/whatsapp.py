import pywhatkit as wk
from typing import Optional
import logging
from datetime import datetime

class WhatsAppIntegration:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def send_alert(self, phone_number: str, message: str) -> bool:
        """Send inventory alert via WhatsApp"""
        try:
            # Remove any spaces or special characters
            phone_number = ''.join(c for c in phone_number if c.isdigit())
            
            if not phone_number.startswith('51'):
                phone_number = f'51{phone_number}'  # Default to Peru country code
            
            wk.sendwhatmsg_instantly(
                phone_no=f"+{phone_number}",
                message=message,
                wait_time=15,
                tab_close=True
            )
            return True
        except Exception as e:
            self.logger.error(f"Error sending WhatsApp alert: {e}")
            return False
    
    def send_order_to_supplier(self, supplier_phone: str, order_details: Dict) -> bool:
        """Send order to supplier via WhatsApp"""
        try:
            message = f"📦 *Pedido Dental*\n\n"
            message += f"📅 Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            message += "--------------------------------\n"
            
            for item in order_details['items']:
                message += f"▪ {item['nombre']} x{item['cantidad']} - S/{item['precio_unitario']:.2f}\n"
            
            message += "--------------------------------\n"
            message += f"💰 Total: S/{order_details['total']:.2f}\n\n"
            message += "Por favor confirmar disponibilidad. Gracias!"
            
            return self.send_alert(supplier_phone, message)
        except Exception as e:
            self.logger.error(f"Error sending order: {e}")
            return False
    def calcular_stock_acumulado(self, familia: str = None, subfamilia: str = None) -> Dict:
        """Calcula stock total agrupado por familia/subfamilia"""
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
        
        return self.db.execute_query(query, params)
    
    def actualizar_stock_familias(self, mes: int, anio: int):
        """Actualiza la tabla de stock acumulado por familia"""
        datos = self.calcular_stock_acumulado()
        
        for item in datos:
            self.db.execute_update("""
            INSERT OR REPLACE INTO stock_familias VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                item['familia'],
                item['subfamilia'],
                mes,
                anio,
                item['cantidad'],
                item['costo_total'],
                item['valor_total']
            ))
