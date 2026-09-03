import sqlite3
import os
from config import Config
from seed_data import seed_database

def reset_db_cleanly():
    print("Resetting database to pristine 3-category state with foreign-key safety...")
    seed_database(force_reset=True)
    print("✅ Database cleanly reset! All previous test registrations and orphaned records have been cleared.")

if __name__ == '__main__':
    reset_db_cleanly()
