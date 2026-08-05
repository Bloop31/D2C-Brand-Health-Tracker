-- D2C Brand Health Tracker — PostgreSQL schema

CREATE TABLE IF NOT EXISTS brands (
    brand_id SERIAL PRIMARY KEY,
    brand_name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
    product_id SERIAL PRIMARY KEY,
    brand_id INT REFERENCES brands(brand_id),
    product_name TEXT,
    category TEXT,
    product_url TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id SERIAL PRIMARY KEY,
    product_id INT REFERENCES products(product_id),
    snapshot_date DATE,
    price NUMERIC,
    avg_rating NUMERIC,
    review_count INT
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id SERIAL PRIMARY KEY,
    product_id INT REFERENCES products(product_id),
    review_date DATE,
    review_text TEXT,
    review_rating INT,
    sentiment_score NUMERIC
);
