CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    tipo_venta TEXT CHECK(tipo_venta IN ('con_receta', 'venta_libre', 'controlado')) NOT NULL,
    stock INTEGER DEFAULT 0,
    stock_minimo INTEGER DEFAULT 5,
    precio_compra REAL NOT NULL,
    precio_venta REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS lotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    numero_lote TEXT NOT NULL,
    fecha_fabricacion DATE NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    cantidad INTEGER NOT NULL,
    estado TEXT CHECK(estado IN ('vigente', 'vencido')) DEFAULT 'vigente',
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

CREATE TABLE IF NOT EXISTS certificados_sanitarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    numero_registro TEXT NOT NULL,
    autoridad_emisora TEXT,
    fecha_emision DATE,
    fecha_vencimiento DATE,
    estado TEXT CHECK(estado IN ('vigente', 'vencido')),
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

CREATE TABLE IF NOT EXISTS recetas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id INTEGER,
    odontologo_id INTEGER,
    fecha_emision DATE NOT NULL,
    fecha_vencimiento DATE
);

CREATE TABLE IF NOT EXISTS receta_detalle (
    receta_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    PRIMARY KEY (receta_id, producto_id),
    FOREIGN KEY (receta_id) REFERENCES recetas(id),
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auditoria_controlados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    accion TEXT,
    receta_id INTEGER,
    usuario_id INTEGER,
    fecha_hora DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS movimientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    tipo TEXT CHECK(tipo IN ('entrada', 'salida')) NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_unitario REAL,
    responsable TEXT,
    receta_id INTEGER,
    usuario_id INTEGER,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP
);
