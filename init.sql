-- SmartBaku HoReCa ERP Database Schema & Seed Data
-- PostgreSQL 15

CREATE TABLE IF NOT EXISTS suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    voen VARCHAR(10) UNIQUE NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(100),
    address TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ingredients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE,
    unit VARCHAR(20) NOT NULL,
    quantity NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    min_stock NUMERIC(10,2) NOT NULL DEFAULT 0,
    unit_price NUMERIC(10,2) NOT NULL DEFAULT 0,
    supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS recipes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL,
    selling_price NUMERIC(10,2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS recipe_items (
    id SERIAL PRIMARY KEY,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE RESTRICT,
    quantity_needed NUMERIC(10,4) NOT NULL CHECK (quantity_needed > 0),
    UNIQUE(recipe_id, ingredient_id)
);

CREATE TABLE IF NOT EXISTS waybills (
    id SERIAL PRIMARY KEY,
    waybill_number VARCHAR(30) UNIQUE NOT NULL,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    subtotal NUMERIC(10,2) NOT NULL,
    edv_rate NUMERIC(5,2) NOT NULL DEFAULT 18.00,
    edv_amount NUMERIC(10,2) NOT NULL,
    total NUMERIC(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'AZN',
    exchange_rate NUMERIC(12,6) NOT NULL DEFAULT 1.000000,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS waybill_items (
    id SERIAL PRIMARY KEY,
    waybill_id INTEGER NOT NULL REFERENCES waybills(id) ON DELETE CASCADE,
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
    quantity NUMERIC(10,2) NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0),
    line_total NUMERIC(10,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS currency_rates (
    id SERIAL PRIMARY KEY,
    currency_code VARCHAR(3) NOT NULL,
    rate NUMERIC(12,6) NOT NULL,
    source VARCHAR(20) NOT NULL DEFAULT 'cbar.az',
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(currency_code, fetched_at)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ingredients_supplier  ON ingredients(supplier_id);
CREATE INDEX IF NOT EXISTS idx_ingredients_low_stock ON ingredients(quantity, min_stock);
CREATE INDEX IF NOT EXISTS idx_recipe_items_recipe   ON recipe_items(recipe_id);
CREATE INDEX IF NOT EXISTS idx_waybill_items_waybill ON waybill_items(waybill_id);
CREATE INDEX IF NOT EXISTS idx_waybills_supplier     ON waybills(supplier_id);
CREATE INDEX IF NOT EXISTS idx_waybills_created      ON waybills(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_currency_latest       ON currency_rates(currency_code, fetched_at DESC);

-- Seed Data: Suppliers
INSERT INTO suppliers (id, name, voen, phone, email, address) VALUES
(1, 'Azərsun Holding', '1400598371', '+994 12 404 99 00', 'b2b@azersun.az', 'Bakı şəh., Heydər Əliyev pr. 92A'),
(2, 'Atena MMC', '1700832456', '+994 50 211 33 44', 'sales@atena.az', 'Ağcabədi r., Hacılar kəndi'),
(3, 'Bravo Supermarket B2B', '1301245890', '+994 12 310 10 10', 'corporate@bravo.az', 'Bakı şəh., Əhməd Rəcəbli küç. 25')
ON CONFLICT (id) DO NOTHING;
SELECT setval('suppliers_id_seq', (SELECT MAX(id) FROM suppliers));

-- Seed Data: Ingredients
INSERT INTO ingredients (id, name, unit, quantity, min_stock, unit_price, supplier_id) VALUES
(1, 'Toyuq filesi', 'kq', 50.00, 10.00, 8.50, 1),
(2, 'Dana əti', 'kq', 30.00, 8.00, 16.00, 2),
(3, 'Düyü (kətan)', 'kq', 100.00, 20.00, 3.20, 3),
(4, 'Pomidor', 'kq', 40.00, 10.00, 2.50, 3),
(5, 'Soğan', 'kq', 60.00, 15.00, 1.20, 3),
(6, 'Kartof', 'kq', 80.00, 20.00, 1.00, 3),
(7, 'Kərə yağı', 'kq', 15.00, 5.00, 12.00, 1),
(8, 'Zeytun yağı', 'litr', 20.00, 5.00, 9.50, 2),
(9, 'Duz', 'kq', 25.00, 5.00, 0.80, 3),
(10, 'Qara istiot', 'kq', 3.00, 1.00, 25.00, 2),
(11, 'Zəfəran', 'qram', 100.00, 20.00, 0.40, 2),
(12, 'Limon', 'ədəd', 50.00, 15.00, 0.30, 3),
(13, 'Sarımsaq', 'kq', 5.00, 2.00, 4.00, 3),
(14, 'Badımcan', 'kq', 25.00, 8.00, 3.00, 3),
(15, 'Bibər (yaşıl)', 'kq', 20.00, 5.00, 3.50, 3),
(16, 'Un (buğda)', 'kq', 50.00, 15.00, 1.80, 1),
(17, 'Yumurta', 'ədəd', 200.00, 50.00, 0.15, 1),
(18, 'Süd', 'litr', 30.00, 10.00, 1.60, 1),
(19, 'Qaymaq', 'litr', 10.00, 3.00, 5.00, 1),
(20, 'Şəkər', 'kq', 40.00, 10.00, 1.50, 3),
(21, 'Qoz ləpəsi', 'kq', 5.00, 2.00, 20.00, 2),
(22, 'Nar', 'ədəd', 30.00, 10.00, 1.50, 3),
(23, 'Kişmiş', 'kq', 4.00, 1.00, 8.00, 2),
(24, 'Lavash (nazik)', 'ədəd', 100.00, 30.00, 0.40, 1),
(25, 'Coca-Cola 0.33L', 'ədəd', 120.00, 30.00, 0.60, 3)
ON CONFLICT (id) DO NOTHING;
SELECT setval('ingredients_id_seq', (SELECT MAX(id) FROM ingredients));

-- Seed Data: Recipes
INSERT INTO recipes (id, name, category, selling_price, is_active) VALUES
(1, 'Plov', 'Əsas yemək', 12.00, TRUE),
(2, 'Toyuq Kebab', 'Əsas yemək', 9.00, TRUE),
(3, 'Dovğa', 'Şorba', 5.00, TRUE),
(4, 'Badımcan dolması', 'Əsas yemək', 10.00, TRUE),
(5, 'Pak-baklava', 'Desert', 7.00, TRUE),
(6, 'Limonlu su', 'İçki', 3.00, TRUE)
ON CONFLICT (id) DO NOTHING;
SELECT setval('recipes_id_seq', (SELECT MAX(id) FROM recipes));

-- Seed Data: Recipe Items
INSERT INTO recipe_items (recipe_id, ingredient_id, quantity_needed) VALUES
-- Plov: Düyü 0.25kq, Dana əti 0.20kq, Kərə yağı 0.03kq, Soğan 0.08kq, Zəfəran 0.50qram, Duz 0.005kq
(1, 3, 0.2500),
(1, 2, 0.2000),
(1, 7, 0.0300),
(1, 5, 0.0800),
(1, 11, 0.5000),
(1, 9, 0.0050),
-- Toyuq Kebab: Toyuq filesi 0.25kq, Soğan 0.05kq, Bibər 0.05kq, Pomidor 0.08kq, Duz 0.003kq, Qara istiot 0.002kq
(2, 1, 0.2500),
(2, 5, 0.0500),
(2, 15, 0.0500),
(2, 4, 0.0800),
(2, 9, 0.0030),
(2, 10, 0.0020),
-- Dovğa: Süd 0.30litr, Düyü 0.03kq, Yumurta 1ədəd, Duz 0.005kq
(3, 18, 0.3000),
(3, 3, 0.0300),
(3, 17, 1.0000),
(3, 9, 0.0050),
-- Badımcan dolması: Badımcan 0.20kq, Dana əti 0.15kq, Düyü 0.05kq, Pomidor 0.10kq, Soğan 0.05kq
(4, 14, 0.2000),
(4, 2, 0.1500),
(4, 3, 0.0500),
(4, 4, 0.1000),
(4, 5, 0.0500),
-- Pak-baklava: Un 0.10kq, Kərə yağı 0.05kq, Şəkər 0.08kq, Yumurta 2ədəd, Qoz ləpəsi 0.04kq
(5, 16, 0.1000),
(5, 7, 0.0500),
(5, 20, 0.0800),
(5, 17, 2.0000),
(5, 21, 0.0400),
-- Limonlu su: Limon 2ədəd, Şəkər 0.03kq
(6, 12, 2.0000),
(6, 20, 0.0300)
ON CONFLICT (recipe_id, ingredient_id) DO NOTHING;

-- Seed Data: Initial Currency Rates
INSERT INTO currency_rates (currency_code, rate, source, fetched_at) VALUES
('USD', 1.700000, 'cbar.az', NOW()),
('EUR', 1.850000, 'cbar.az', NOW()),
('TRY', 0.049000, 'cbar.az', NOW()),
('RUB', 0.017500, 'cbar.az', NOW()),
('GEL', 0.620000, 'cbar.az', NOW())
ON CONFLICT (currency_code, fetched_at) DO NOTHING;
