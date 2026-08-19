PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS device_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS brands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    UNIQUE(brand_id, name),
    FOREIGN KEY(brand_id) REFERENCES brands(id)
);

CREATE TABLE IF NOT EXISTS connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS statuses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS donor_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS engravers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS donors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS recipients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    national_id TEXT NOT NULL UNIQUE,
    name TEXT,
    surname TEXT,
    cns TEXT,
    nationality TEXT,
    ona_number TEXT
);

CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    internal_barcode TEXT NOT NULL UNIQUE,
    device_type_id INTEGER NOT NULL,
    brand_id INTEGER NOT NULL,
    model_id INTEGER NOT NULL,
    connection_id INTEGER NOT NULL,
    is_engraved INTEGER NOT NULL DEFAULT 0 CHECK(is_engraved IN (0,1)),
    engraving_date TEXT,
    engraver_id INTEGER,
    is_distributed INTEGER NOT NULL DEFAULT 0 CHECK(is_distributed IN (0,1)),
    recipient_id INTEGER,
    distribution_date TEXT,
    status_id INTEGER NOT NULL,
    place TEXT,
    capacity_gb INTEGER NOT NULL,
    os TEXT,
    serial_number TEXT,
    imei_1 TEXT,
    imei_2 TEXT,
    donor_type_id INTEGER NOT NULL,
    entry_date TEXT NOT NULL,
    donor_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(device_type_id) REFERENCES device_types(id),
    FOREIGN KEY(brand_id) REFERENCES brands(id),
    FOREIGN KEY(model_id) REFERENCES models(id),
    FOREIGN KEY(connection_id) REFERENCES connections(id),
    FOREIGN KEY(engraver_id) REFERENCES engravers(id),
    FOREIGN KEY(recipient_id) REFERENCES recipients(id),
    FOREIGN KEY(status_id) REFERENCES statuses(id),
    FOREIGN KEY(donor_type_id) REFERENCES donor_types(id),
    FOREIGN KEY(donor_id) REFERENCES donors(id)
);

CREATE TABLE IF NOT EXISTS accessories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    entity TEXT NOT NULL,
    entity_id INTEGER,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_devices_internal_barcode ON devices(internal_barcode);
CREATE INDEX IF NOT EXISTS idx_devices_distributed ON devices(is_distributed);
CREATE INDEX IF NOT EXISTS idx_devices_recipient ON devices(recipient_id);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status_id);
