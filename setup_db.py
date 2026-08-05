"""
Run once to create the tables in your Postgres database.
Before running: open pgAdmin, create a database called d2c_tracker
(right-click Databases -> Create -> Database), then update db_config.py
with your username/password.

Usage: python setup_db.py
"""
import psycopg2
from db_config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

with open("schema.sql", "r") as f:
    cur.execute(f.read())

conn.commit()
cur.close()
conn.close()

print("Tables created in d2c_tracker: brands, products, snapshots, reviews")
print("Refresh the database in pgAdmin (right-click -> Refresh) to see them.")
