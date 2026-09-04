import sqlite3
import os
from config import Config
from seed_data import seed_database

def reset_db_cleanly():
    print("Resetting database to pristine state with foreign-key safety...")
    db_path = Config.DATABASE
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print("Removed existing database file to recreate clean schema.")
        except Exception as e:
            print(f"Notice: {e}")
    seed_database(force_reset=True)
    print("✅ Database cleanly reset! All previous test registrations and orphaned records have been cleared.")

if __name__ == '__main__':
    reset_db_cleanly()
