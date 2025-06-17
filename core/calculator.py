from typing import Dict, List, Optional
from database.db import InventoryDB  

class InventoryCalculator:
    def __init__(self, db: InventoryDB):
        self.db = db
    
    def calcular_existencias_mes(self, producto_id: int, mes: int, anio: int, empresa_id: int = 1) -> Dict:
        """Calculate monthly inventory with monetary valuation"""
        prev_month, prev_year = self._get_previous_month(mes, anio)
        prev_data = self._obtener_datos_mes_anterior(producto_id, prev_month, prev_year, empresa_id)
        movimientos = self._obtener_movimientos_mes(producto_id, mes, anio, empresa_id)
        
        stock_inicial = prev_data['stock_final'] if prev_data else 0
        valor_inicial = prev_data['valor_final'] if prev_data else 0
        
        entradas = sum(m['cantidad'] for m in movimientos if m['tipo'] in ('entrada', 'ajuste_positivo'))
        salidas = sum(m['cantidad'] for m in movimientos if m['tipo'] in ('salida', 'ajuste_negativo'))
        
        valor_entradas = sum(m['precio_total'] for m in movimientos if m['tipo'] in ('entrada', 'ajuste_positivo'))
        valor_salidas = sum(m['precio_total'] for m in movimientos if m['tipo'] in ('salida', 'ajuste_negativo'))
        
        return {
            'producto_id': producto_id,
            'mes': mes,
            'anio': anio,
            'empresa_id': empresa_id,
            'stock_inicial': stock_inicial,
            'entradas': entradas,
            'salidas': salidas,
            'stock_final': stock_inicial + entradas - salidas,
            'valor_inicial': valor_inicial,
            'valor_entradas': valor_entradas,
            'valor_salidas': valor_salidas,
            'valor_final': valor_inicial + valor_entradas - valor_salidas
        }
    
    def _get_previous_month(self, mes: int, anio: int) -> tuple:
        """Get previous month and year"""
        if mes == 1: return 12, anio - 1
        return mes - 1, anio
    
    def _obtener_datos_mes_anterior(self, producto_id: int, mes: int, anio: int, empresa_id: int) -> Optional[Dict]:
        """Get data from previous month"""
        query = """
        SELECT stock_final, valor_final FROM existencias 
        WHERE producto_id = ? AND mes = ? AND anio = ? AND empresa_id = ?
        """
        result = self.db.execute_query(query, (producto_id, mes, anio, empresa_id))
        return result[0] if result else None
    
    def _obtener_movimientos_mes(self, producto_id: int, mes: int, anio: int, empresa_id: int) -> List[Dict]:
        """Get monthly movements"""
        query = """
        SELECT tipo, cantidad, precio_unitario, precio_total
        FROM movimientos
        WHERE producto_id = ? 
        AND strftime('%m', fecha_hora) = ?
        AND strftime('%Y', fecha_hora) = ?
        AND empresa_id = ?
        """
        return self.db.execute_query(query, (
            producto_id, 
            f"{mes:02d}", 
            str(anio), 
            empresa_id
        ))
    
    def calcular_stock_actual(self, producto_id: int) -> Dict:
        """Calculate current stock level"""
        query = """
        SELECT 
            p.nombre,
            p.stock,
            p.stock_minimo,
            COALESCE(SUM(CASE WHEN m.tipo IN ('entrada', 'ajuste_positivo') THEN m.cantidad ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN m.tipo IN ('salida', 'ajuste_negativo') THEN m.cantidad ELSE 0 END), 0) as stock_calculado
        FROM productos p
        LEFT JOIN movimientos m ON p.id = m.producto_id
        WHERE p.id = ?
        GROUP BY p.id
        """
        result = self.db.execute_query(query, (producto_id,))
        return result[0] if result else None
3. core/dental.py (Funcionalidades dentales)
python
from datetime import datetime, timedelta
from typing import Dict, List
from database.db import InventoryDB
from core.calculator import InventoryCalculator

class DentalInventoryManager:
    def __init__(self, db: InventoryDB):
        self.db = db
        self.calculator = InventoryCalculator(db)
    
    def verificar_vencimientos(self, dias_alerta: int = 30) -> List[Dict]:
        """Check for soon-to-expire lots"""
        hoy = datetime.now().date()
        fecha_limite = hoy + timedelta(days=dias_alerta)
        
        query = """
        SELECT 
            p.nombre as producto,
            l.numero_lote,
            l.fecha_vencimiento,
            l.cantidad,
            julianday(l.fecha_vencimiento) - julianday('now') as dias_restantes
        FROM lotes l
        JOIN productos p ON l.producto_id = p.id
        WHERE l.fecha_vencimiento BETWEEN ? AND ?
        AND p.activo = TRUE
        ORDER BY l.fecha_vencimiento
        """
        return self.db.execute_query(query, (hoy, fecha_limite))
    
    def generar_reporte_sunat(self, mes: int, anio: int) -> Dict:
        """Generate SUNAT-compliant monthly report"""
        productos = self.db.execute_query("SELECT id, nombre FROM productos WHERE activo = TRUE")
        
        reporte = {
            'mes': mes,
            'anio': anio,
            'productos': [],
            'total_valor_final': 0.0
        }
        
        for producto in productos:
            existencias = self.calculator.calcular_existencias_mes(
                producto['id'], mes, anio
            )
            reporte['productos'].append({
                'producto_id': producto['id'],
                'nombre': producto['nombre'],
                'stock_inicial': existencias['stock_inicial'],
                'entradas': existencias['entradas'],
                'salidas': existencias['salidas'],
                'stock_final': existencias['stock_final'],
                'valor_final': existencias['valor_final']
            })
            reporte['total_valor_final'] += existencias['valor_final']
        
        return reporte
    
    def sugerir_pedidos(self) -> List[Dict]:
        """Suggest orders based on stock levels and supplier lead time"""
        query = """
        SELECT 
            p.id,
            p.nombre,
            p.stock,
            p.stock_minimo,
            p.proveedor,
            p.dias_entrega,
            (p.stock_minimo - p.stock) as cantidad_sugerida
        FROM productos p
        WHERE p.stock < p.stock_minimo
        AND p.activo = TRUE
        """
        return self.db.execute_query(query)
    
    def registrar_movimiento_dental(self, producto_id: int, tipo: str, cantidad: int, 
                                 precio_unitario: float, documento: str = None) -> bool:
        """Register dental-specific movement"""
        query = """
        INSERT INTO movimientos (
            producto_id, tipo, cantidad, precio_unitario, documento
        ) VALUES (?, ?, ?, ?, ?)
        """
        try:
            affected = self.db.execute_update(query, 
                (producto_id, tipo, cantidad, precio_unitario, documento))
            
            # Update product stock
            if tipo in ('entrada', 'ajuste_positivo'):
                update_query = "UPDATE productos SET stock = stock + ? WHERE id = ?"
            else:
                update_query = "UPDATE productos SET stock = stock - ? WHERE id = ?"
            
            self.db.execute_update(update_query, (cantidad, producto_id))
            return affected > 0
        except Exception as e:
            print(f"Error registrando movimiento: {e}")
            return False
4. integrations/whatsapp.py (Integración WhatsApp)
python
import pywhatkit as wk
from typing import Optional
import logging

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
