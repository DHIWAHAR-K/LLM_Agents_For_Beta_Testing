#!/usr/bin/env python3
"""Clear all data from the experiments database."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "results" / "experiments.db"

def clear_database():
    """Clear all data from the experiments database."""
    # Ensure results directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    if not DB_PATH.exists():
        print(f"Database file not found at {DB_PATH}")
        print("Nothing to clear.")
        return
    
    print(f"Connecting to database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    
    if not tables:
        print("No tables found in database.")
        conn.close()
        return
    
    print(f"Found {len(tables)} tables to clear:")
    for table in tables:
        print(f"  - {table}")
    
    # Disable foreign key constraints temporarily
    cursor.execute("PRAGMA foreign_keys = OFF")
    
    # Clear all tables
    for table in tables:
        cursor.execute(f"DELETE FROM {table}")
        count = cursor.rowcount
        print(f"  Cleared {count} rows from {table}")
    
    # Reset auto-increment counters
    for table in tables:
        cursor.execute(f"DELETE FROM sqlite_sequence WHERE name = '{table}'")
    
    # Re-enable foreign key constraints
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Commit changes
    conn.commit()
    
    # Verify tables are empty
    print("\nVerifying tables are empty:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        if count == 0:
            print(f"  ✓ {table}: empty")
        else:
            print(f"  ✗ {table}: {count} rows remaining")
    
    conn.close()
    print(f"\n✓ Database cleared successfully!")

if __name__ == "__main__":
    clear_database()

