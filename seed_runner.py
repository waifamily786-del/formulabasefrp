"""
FormulaBase Nexus - Manual Seed Runner
Run this script standalone to seed the database with demo data.
Usage: venv\Scripts\python.exe seed_runner.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

from database.db import create_all_tables, SessionLocal
from database.seed import seed_database

print("=" * 60)
print("FormulaBase Nexus - Database Setup & Seed")
print("=" * 60)

# Create all tables
print("\n[1/2] Creating database tables...")
create_all_tables()
print("      Tables created OK!")

# Seed demo data
print("\n[2/2] Seeding demo data...")
db = SessionLocal()
try:
    seeded = seed_database(db, force=False)
    if seeded:
        print("      Demo data seeded successfully!")
    else:
        print("      Database already has data - skipping seed.")
        print("      (Use force=True in code to re-seed)")
finally:
    db.close()

print("\n" + "=" * 60)
print("Setup complete! Run the server with:")
print("  cd backend")
print("  ..\venv\Scripts\python.exe -m uvicorn main:app --port 8765 --reload")
print("  API Docs: http://127.0.0.1:8765/api/docs")
print("=" * 60)
