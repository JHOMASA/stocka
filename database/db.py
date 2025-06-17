import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

class InventoryDB:
    def __init__(self, db_path: str = None):
        try:
            if db_path is None:
                db_path = Path(__file__).parent.parent / "data" / "dental_inventory.db"
                db_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.conn = sqlite3.connect(str(db_path))
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON")
            self._init_db()
        except Exception as e:
            raise RuntimeError(f"Database connection failed: {str(e)}")

    def _init_db(self):
        """Initialize dental-specific database schema"""
        cursor = self.conn.cursor()
        
        # Tabla de productos dentales
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            categoria TEXT CHECK(categoria IN ('resina', 'anestesia', 'instrumental', 'consumible')),
            stock INTEGER DEFAULT 0,
            stock_minimo INTEGER DEFAULT 5,
            precio_unitario DECIMAL(10,2) DEFAULT 0,
            proveedor TEXT DEFAULT 'DentalPerú',
            dias_entrega INTEGER DEFAULT 2,
            activo BOOLEAN DEFAULT TRUE,
            empresa_id INTEGER DEFAULT 1
        )
        """)
        
        # Tabla de movimientos (adaptada para dentales)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            tipo TEXT CHECK(tipo IN ('entrada', 'salida', 'ajuste_positivo', 'ajuste_negativo')),
            cantidad INTEGER NOT NULL,
            precio_unitario DECIMAL(10,2) NOT NULL,
            precio_total DECIMAL(10,2) GENERATED ALWAYS AS (cantidad * precio_unitario) STORED,
            fecha_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
            documento TEXT,
            notas TEXT,
            empresa_id INTEGER DEFAULT 1,
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        )
        """)
        
        # Tabla de existencias mensuales
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS existencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            mes INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
            anio INTEGER NOT NULL,
            stock_inicial INTEGER NOT NULL,
            entradas INTEGER NOT NULL DEFAULT 0,
            salidas INTEGER NOT NULL DEFAULT 0,
            stock_final INTEGER NOT NULL,
            valor_inicial DECIMAL(15,2) NOT NULL,
            valor_entradas DECIMAL(15,2) NOT NULL DEFAULT 0,
            valor_salidas DECIMAL(15,2) NOT NULL DEFAULT 0,
            valor_final DECIMAL(15,2) NOT NULL,
            empresa_id INTEGER DEFAULT 1,
            FOREIGN KEY (producto_id) REFERENCES productos(id),
            UNIQUE(producto_id, mes, anio, empresa_id)
        )
        """)
        
        # Tabla de lotes (específica para dentales)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS lotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            numero_lote TEXT NOT NULL,
            fecha_vencimiento DATE NOT NULL,
            cantidad INTEGER NOT NULL,
            empresa_id INTEGER DEFAULT 1,
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        )
        """)
        
        # Insertar datos iniciales de ejemplo
        cursor.execute("""
        INSERT OR IGNORE INTO productos (codigo, nombre, categoria, stock_minimo, precio_unitario) VALUES
            ('RES-001', 'Resina Flow', 'resina', 10, 85.50),
            ('ANE-002', 'Anestesia Lidocaína 2%', 'anestesia', 5, 12.80),
            ('GNT-003', 'Guantes de Nitrilo', 'consumible', 20, 1.20)
        """)
        
        self.conn.commit()

    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute a read query and return results as dictionaries"""
        cursor = self.conn.cursor()
        cursor.execute(query, params or ())
        return [dict(row) for row in cursor.fetchall()]

    def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute an update query and return affected rows"""
        cursor = self.conn.cursor()
        cursor.execute(query, params or ())
        self.conn.commit()
        return cursor.rowcount
