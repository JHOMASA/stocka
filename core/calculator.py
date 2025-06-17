# core/calculator.py
from __future__ import annotations
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from database.db import InventoryDB  # Only for type checking


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
