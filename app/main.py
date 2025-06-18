import os
import sys
from pathlib import Path

# Add project root to path BEFORE any local imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Standard library imports
from datetime import datetime, timedelta

# Third-party imports
import pandas as pd
import streamlit as st
from integrations.sunat import PDF_ENGINE, FPDF

st.title("Dental Inventory System")

 Show Python version
st.write(f"Python version: {sys.version}")

if PDF_ENGINE != "none":
    st.success(f"✅ PDF generation ready (using {PDF_ENGINE})")
    try:
        pdf = FPDF()
        st.code("PDF test: FPDF() instantiated successfully")
    except Exception as e:
        st.error(f"PDF test failed: {str(e)}")
else:
    st.error("""
    ❌ Critical Error: PDF generation disabled
    
    Required actions:
    1. Verify setup.sh exists in repo root
    2. Confirm requirements.txt contains 'fpdf2==2.7.7'
    3. Check runtime.txt specifies python-3.10.13
    4. Contact Streamlit support with these logs
    """)
from importlib import util

if util.find_spec("fpdf"):
    st.success("✅ fpdf2 installed correctly!")
    st.code(str(util.find_spec("fpdf")))
else:
    st.error("❌ fpdf2 still missing - contact support")

# Local application imports
from database.db import InventoryDB
from core.calculator import InventoryCalculator
from core.dental import DentalInventoryManager
from integrations.whatsapp import WhatsAppIntegration
from integrations.sunat import SunatIntegration

# Debug paths
print("\n=== DEBUG INFO ===")
print("Current directory:", os.getcwd())
print("Parent directory contents:", os.listdir('..'))
print("Python path:", sys.path)

# Initialize app
st.set_page_config(
    page_title="Dental Inventory PRO",
    page_icon="🦷",
    layout="wide"
)

@st.cache_resource
def init_app():
    db = InventoryDB()
    return {
        'db': db,
        'calculator': InventoryCalculator(db),
        'dental_manager': DentalInventoryManager(db),
        'whatsapp': WhatsAppIntegration(),
        'sunat': SunatIntegration()
    }

app = init_app()


# Sidebar - Menú principal
st.sidebar.title("Menú Principal")
menu = st.sidebar.radio(
    "Seleccione módulo:",
    ["📊 Dashboard", "📦 Inventario", "📅 Lotes", "🧾 Facturación", "⚙️ Configuración"]
)

# Helper functions
def format_currency(value):
    return f"S/. {value:,.2f}"

# --- 📊 DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Dashboard de Gestión Dental")
    
    # Métricas clave
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Productos bajos en stock
        low_stock = db.conn.execute("""
            SELECT COUNT(*) FROM productos 
            WHERE stock < stock_minimo AND activo = TRUE
        """).fetchone()[0]
        st.metric("⚠️ Productos bajo mínimo", low_stock)
    
    with col2:
        # Valor total del inventario
        total_value = db.conn.execute("""
            SELECT SUM(stock * precio_unitario) 
            FROM productos WHERE activo = TRUE
        """).fetchone()[0] or 0
        st.metric("💰 Valor del inventario", format_currency(total_value))
    
    with col3:
        # Próximos vencimientos
        expiring = len(dental_manager.verificar_vencimientos(30))
        st.metric("⏳ Lotes por vencer (30 días)", expiring)
    
    # Gráfico de movimientos mensuales
    st.subheader("Movimientos Mensuales")
    movimientos = pd.read_sql("""
        SELECT strftime('%Y-%m', fecha_hora) as mes, 
               tipo, 
               SUM(cantidad) as cantidad,
               SUM(precio_total) as total
        FROM movimientos
        GROUP BY mes, tipo
        ORDER BY mes
    """, db.conn)
    
    if not movimientos.empty:
        pivot_mov = movimientos.pivot(index='mes', columns='tipo', values='total').fillna(0)
        st.bar_chart(pivot_mov)
    else:
        st.warning("No hay datos de movimientos disponibles")

# --- 📦 INVENTARIO ---
elif menu == "📦 Inventario":
    st.title("Gestión de Inventario")
    
    tab1, tab2, tab3 = st.tabs(["📝 Registrar Movimiento", "📋 Productos", "📈 Análisis"])
    
    with tab1:
        with st.form("movimiento_form"):
            # Obtener productos activos
            productos = pd.read_sql("""
                SELECT id, nombre, stock FROM productos 
                WHERE activo = TRUE ORDER BY nombre
            """, db.conn)
            
            col1, col2 = st.columns(2)
            
            with col1:
                producto_id = st.selectbox(
                    "Producto",
                    productos['id'],
                    format_func=lambda x: productos.loc[productos['id'] == x, 'nombre'].iloc[0]
                )
                tipo = st.radio("Tipo de movimiento", ["entrada", "salida", "ajuste"])
                
            with col2:
                cantidad = st.number_input("Cantidad", min_value=1, step=1)
                precio = st.number_input("Precio unitario", min_value=0.0, value=0.0)
                responsable = st.text_input("Responsable")
            
            submitted = st.form_submit_button("Registrar Movimiento")
            
            if submitted:
                try:
                    precio_total = cantidad * precio
                    db.conn.execute("""
                        INSERT INTO movimientos (
                            producto_id, tipo, cantidad, 
                            precio_unitario, precio_total, responsable
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (producto_id, tipo, cantidad, precio, precio_total, responsable))
                    
                    # Actualizar stock
                    if tipo == "entrada":
                        db.conn.execute("""
                            UPDATE productos SET stock = stock + ? 
                            WHERE id = ?
                        """, (cantidad, producto_id))
                    else:
                        db.conn.execute("""
                            UPDATE productos SET stock = stock - ? 
                            WHERE id = ?
                        """, (cantidad, producto_id))
                    
                    db.conn.commit()
                    st.success("Movimiento registrado exitosamente!")
                    
                    # Verificar si el stock está bajo mínimo
                    current_stock = db.conn.execute("""
                        SELECT stock, stock_minimo FROM productos 
                        WHERE id = ?
                    """, (producto_id,)).fetchone()
                    
                    if current_stock['stock'] < current_stock['stock_minimo']:
                        whatsapp.send_alert(
                            "51987654321",  # Número del administrador
                            f"⚠️ ALERTA: Stock de {productos.loc[productos['id'] == producto_id, 'nombre'].iloc[0]} "
                            f"bajo mínimo ({current_stock['stock']} unidades)"
                        )
                        
                except Exception as e:
                    db.conn.rollback()
                    st.error(f"Error al registrar movimiento: {str(e)}")
    
    with tab2:
        st.subheader("Lista de Productos")
        productos = pd.read_sql("""
            SELECT id, codigo, nombre, categoria, stock, 
                   stock_minimo, precio_unitario 
            FROM productos WHERE activo = TRUE
            ORDER BY nombre
        """, db.conn)
        
        # Resaltar productos bajo mínimo
        def highlight_low_stock(row):
            color = 'red' if row['stock'] < row['stock_minimo'] else ''
            return [f'background-color: {color}' for _ in row]
        
        st.dataframe(
            productos.style.apply(highlight_low_stock, axis=1),
            use_container_width=True
        )
        
        # Agregar nuevo producto
        with st.expander("➕ Agregar nuevo producto"):
            with st.form("nuevo_producto"):
                col1, col2 = st.columns(2)
                
                with col1:
                    codigo = st.text_input("Código")
                    nombre = st.text_input("Nombre")
                    categoria = st.selectbox(
                        "Categoría",
                        ["resina", "anestesia", "instrumental", "consumible"]
                    )
                
                with col2:
                    stock_minimo = st.number_input("Stock mínimo", min_value=1, value=5)
                    precio = st.number_input("Precio unitario", min_value=0.0)
                    proveedor = st.text_input("Proveedor principal", "DentalPerú")
                
                submitted = st.form_submit_button("Guardar Producto")
                
                if submitted:
                    try:
                        db.conn.execute("""
                            INSERT INTO productos (
                                codigo, nombre, categoria, stock_minimo,
                                precio_unitario, proveedor
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (codigo, nombre, categoria, stock_minimo, precio, proveedor))
                        db.conn.commit()
                        st.success("Producto agregado exitosamente!")
                    except Exception as e:
                        st.error(f"Error al agregar producto: {str(e)}")

# --- 📅 LOTES ---
elif menu == "📅 Lotes":
    st.title("Gestión de Lotes")
    
    tab1, tab2 = st.tabs(["📝 Registrar Lote", "📋 Lotes Activos"])
    
    with tab1:
        with st.form("lote_form"):
            # Obtener productos activos
            productos = pd.read_sql("""
                SELECT id, nombre FROM productos 
                WHERE activo = TRUE ORDER BY nombre
            """, db.conn)
            
            col1, col2 = st.columns(2)
            
            with col1:
                producto_id = st.selectbox(
                    "Producto",
                    productos['id'],
                    format_func=lambda x: productos.loc[productos['id'] == x, 'nombre'].iloc[0]
                )
                numero_lote = st.text_input("Número de lote")
                
            with col2:
                fecha_vencimiento = st.date_input("Fecha de vencimiento", 
                                                min_value=datetime.now().date())
                cantidad = st.number_input("Cantidad", min_value=1, step=1)
            
            submitted = st.form_submit_button("Registrar Lote")
            
            if submitted:
                try:
                    db.conn.execute("""
                        INSERT INTO lotes (
                            producto_id, numero_lote, 
                            fecha_vencimiento, cantidad
                        ) VALUES (?, ?, ?, ?)
                    """, (producto_id, numero_lote, fecha_vencimiento, cantidad))
                    
                    # Actualizar stock del producto
                    db.conn.execute("""
                        UPDATE productos SET stock = stock + ? 
                        WHERE id = ?
                    """, (cantidad, producto_id))
                    
                    db.conn.commit()
                    st.success("Lote registrado exitosamente!")
                except Exception as e:
                    db.conn.rollback()
                    st.error(f"Error al registrar lote: {str(e)}")
    
    with tab2:
        st.subheader("Lotes Activos")
        
        # Filtros
        col1, col2 = st.columns(2)
        
        with col1:
            dias_vencimiento = st.slider(
                "Mostrar lotes que vencen en (días):",
                1, 180, 30
            )
        
        with col2:
            show_expired = st.checkbox("Mostrar vencidos")
        
        # Consulta de lotes
        hoy = datetime.now().date()
        fecha_limite = hoy + timedelta(days=dias_vencimiento)
        
        query = """
            SELECT p.nombre, l.numero_lote, l.fecha_vencimiento, 
                   l.cantidad, julianday(l.fecha_vencimiento) - julianday('now') as dias_restantes
            FROM lotes l
            JOIN productos p ON l.producto_id = p.id
            WHERE p.activo = TRUE
        """
        
        if not show_expired:
            query += " AND l.fecha_vencimiento >= date('now')"
        
        query += " ORDER BY l.fecha_vencimiento"
        
        lotes = pd.read_sql(query, db.conn)
        
        if not lotes.empty:
            # Resaltar vencimientos próximos
            def highlight_expiring(row):
                if row['dias_restantes'] < 0:
                    color = 'red'
                elif row['dias_restantes'] < 30:
                    color = 'orange'
                else:
                    color = ''
                return [f'background-color: {color}' for _ in row]
            
            st.dataframe(
                lotes.style.apply(highlight_expiring, axis=1),
                use_container_width=True
            )
            
            # Botón para exportar
            csv = lotes.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📤 Exportar a CSV",
                data=csv,
                file_name="lotes_activos.csv",
                mime="text/csv"
            )
        else:
            st.info("No hay lotes activos registrados")

# --- 🧾 FACTURACIÓN ---
elif menu == "🧾 Facturación":
    st.title("Facturación Electrónica")
    
    tab1, tab2 = st.tabs(["🧾 Generar Factura", "📊 Reportes SUNAT"])
    
    with tab1:
        with st.form("factura_form"):
            # Datos del cliente
            st.subheader("Datos del Cliente")
            col1, col2 = st.columns(2)
            
            with col1:
                cliente_tipo = st.radio("Tipo de documento", ["DNI", "RUC"])
                cliente_numero = st.text_input("Número de documento")
            
            with col2:
                cliente_nombre = st.text_input("Nombre/Razón Social")
                cliente_direccion = st.text_input("Dirección")
            
            # Productos
            st.subheader("Productos")
            productos = pd.read_sql("""
                SELECT id, nombre, precio_unitario FROM productos 
                WHERE activo = TRUE ORDER BY nombre
            """, db.conn)
            
            items = []
            for i in range(3):  # Permitir hasta 3 items por factura
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        producto_id = st.selectbox(
                            f"Producto {i+1}",
                            productos['id'],
                            format_func=lambda x: productos.loc[productos['id'] == x, 'nombre'].iloc[0],
                            key=f"prod_{i}"
                        )
                    
                    with col2:
                        cantidad = st.number_input(
                            "Cantidad", 
                            min_value=1, 
                            value=1,
                            key=f"cant_{i}"
                        )
                    
                    with col3:
                        precio = st.number_input(
                            "Precio", 
                            min_value=0.0,
                            value=float(productos.loc[productos['id'] == producto_id, 'precio_unitario'].iloc[0]),
                            key=f"precio_{i}"
                        )
                    
                    if producto_id:
                        items.append({
                            "producto_id": producto_id,
                            "cantidad": cantidad,
                            "precio": precio
                        })
            
            submitted = st.form_submit_button("Generar Factura")
            
            if submitted and items:
                try:
                    # Generar PDF de factura
                    factura_data = {
                        "cliente": {
                            "tipo": cliente_tipo,
                            "numero": cliente_numero,
                            "nombre": cliente_nombre,
                            "direccion": cliente_direccion
                        },
                        "items": [{
                            "nombre": productos.loc[productos['id'] == item['producto_id'], 'nombre'].iloc[0],
                            "cantidad": item['cantidad'],
                            "precio": item['precio'],
                            "total": item['cantidad'] * item['precio']
                        } for item in items],
                        "total": sum(item['cantidad'] * item['precio'] for item in items),
                        "igv": sum(item['cantidad'] * item['precio'] for item in items) * 0.18
                    }
                    
                    pdf_path = sunat.generar_factura(factura_data)
                    
                    # Registrar movimientos de salida
                    for item in items:
                        db.conn.execute("""
                            INSERT INTO movimientos (
                                producto_id, tipo, cantidad,
                                precio_unitario, precio_total,
                                documento
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            item['producto_id'], 
                            "salida",
                            item['cantidad'],
                            item['precio'],
                            item['cantidad'] * item['precio'],
                            f"Factura-{datetime.now().strftime('%Y%m%d')}"
                        ))
                        
                        # Actualizar stock
                        db.conn.execute("""
                            UPDATE productos SET stock = stock - ? 
                            WHERE id = ?
                        """, (item['cantidad'], item['producto_id']))
                    
                    db.conn.commit()
                    
                    # Mostrar PDF
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            "⬇️ Descargar Factura",
                            data=f,
                            file_name=f"factura_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf"
                        )
                    
                    st.success("Factura generada y movimientos registrados!")
                
                except Exception as e:
                    db.conn.rollback()
                    st.error(f"Error al generar factura: {str(e)}")
    
    with tab2:
        st.subheader("Reportes para SUNAT")
        
        col1, col2 = st.columns(2)
        
        with col1:
            mes = st.selectbox("Mes", range(1, 13), format_func=lambda x: datetime(2023, x, 1).strftime('%B'))
        
        with col2:
            anio = st.number_input("Año", min_value=2020, max_value=2030, value=datetime.now().year)
        
        if st.button("Generar Reporte Mensual"):
            reporte = dental_manager.generar_reporte_sunat(mes, anio)
            
            st.subheader(f"Reporte {mes}/{anio}")
            st.write(f"**Total valor final:** {format_currency(reporte['total_valor_final'])}")
            
            # Mostrar tabla de productos
            st.dataframe(
                pd.DataFrame(reporte['productos']),
                use_container_width=True
            )
            
            # Exportar a Excel
            df = pd.DataFrame(reporte['productos'])
            excel = df.to_excel(index=False)
            st.download_button(
                "📊 Exportar a Excel",
                data=excel,
                file_name=f"reporte_sunat_{mes}_{anio}.xlsx",
                mime="application/vnd.ms-excel"
            )

# --- ⚙️ CONFIGURACIÓN ---
elif menu == "⚙️ Configuración":
    st.title("Configuración del Sistema")
    
    tab1, tab2 = st.tabs(["🔧 Parámetros", "📲 Integraciones"])
    
    with tab1:
        st.subheader("Configuración General")
        
        with st.form("config_form"):
            empresa_nombre = st.text_input("Nombre de la empresa", "Mi Farmacia Dental")
            moneda = st.selectbox("Moneda", ["PEN (S/.)", "USD ($)"])
            dias_alerta_stock = st.number_input("Días de alerta para vencimientos", min_value=1, value=30)
            
            submitted = st.form_submit_button("Guardar Configuración")
            if submitted:
                st.success("Configuración guardada exitosamente!")
    
    with tab2:
        st.subheader("Configuración de WhatsApp")
        
        with st.form("whatsapp_form"):
            whatsapp_numero = st.text_input("Número para alertas", "+51987654321")
            whatsapp_api_key = st.text_input("API Key (opcional)", type="password")
            
            # Probar conexión
            if st.form_submit_button("Probar Conexión"):
                if whatsapp.send_alert(whatsapp_numero, "✅ Prueba de conexión exitosa"):
                    st.success("Conexión exitosa con WhatsApp!")
                else:
                    st.error("Error al conectar con WhatsApp")
