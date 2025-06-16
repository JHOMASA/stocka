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
