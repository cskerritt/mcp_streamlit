#!/usr/bin/env python3
"""
Debug script to check and fix frequency_per_year column type
"""

import sqlite3
import os

# Database path
db_path = "lcp_data.db"

def check_database_schema():
    """Check the current database schema"""
    print("=== DATABASE SCHEMA CHECK ===")
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} does not exist!")
        return
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Check services table schema
        print("\nServices table schema:")
        cursor.execute("PRAGMA table_info(services)")
        columns = cursor.fetchall()
        
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            print(f"  {col_name}: {col_type}")
            
            if col_name == 'frequency_per_year':
                if 'INTEGER' in col_type.upper():
                    print(f"  ❌ PROBLEM: frequency_per_year is {col_type}, should be REAL")
                elif 'REAL' in col_type.upper():
                    print(f"  ✅ OK: frequency_per_year is {col_type}")
                else:
                    print(f"  ⚠️  UNKNOWN: frequency_per_year is {col_type}")

def check_existing_data():
    """Check existing frequency data"""
    print("\n=== EXISTING FREQUENCY DATA ===")
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT s.name, s.frequency_per_year, st.name as table_name
            FROM services s
            JOIN service_tables st ON s.table_id = st.id
            ORDER BY s.id
        """)
        
        services = cursor.fetchall()
        
        if not services:
            print("No services found in database")
            return
        
        print(f"Found {len(services)} services:")
        for service in services:
            name, frequency, table_name = service
            print(f"  {table_name}/{name}: frequency = {frequency} (type: {type(frequency)})")

def force_migration():
    """Force migration of frequency_per_year column"""
    print("\n=== FORCING MIGRATION ===")
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute("PRAGMA table_info(services)")
        columns = cursor.fetchall()
        
        frequency_col = None
        for col in columns:
            if col[1] == 'frequency_per_year':
                frequency_col = col
                break
        
        if not frequency_col:
            print("❌ frequency_per_year column not found!")
            return
        
        col_type = frequency_col[2]
        print(f"Current frequency_per_year type: {col_type}")
        
        if 'INTEGER' in col_type.upper():
            print("🔄 Migrating frequency_per_year from INTEGER to REAL...")
            
            # Create new table with correct schema
            cursor.execute('''
                CREATE TABLE services_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    inflation_rate REAL NOT NULL,
                    unit_cost REAL NOT NULL,
                    frequency_per_year REAL NOT NULL,
                    start_year INTEGER,
                    end_year INTEGER,
                    occurrence_years TEXT,
                    cost_range_low REAL,
                    cost_range_high REAL,
                    use_cost_range BOOLEAN DEFAULT 0,
                    is_one_time_cost BOOLEAN DEFAULT 0,
                    one_time_cost_year INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (table_id) REFERENCES service_tables (id) ON DELETE CASCADE
                )
            ''')
            
            # Copy data from old table to new table
            cursor.execute('''
                INSERT INTO services_new 
                SELECT * FROM services
            ''')
            
            # Drop old table and rename new table
            cursor.execute('DROP TABLE services')
            cursor.execute('ALTER TABLE services_new RENAME TO services')
            
            # Recreate index
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_services_table_id ON services (table_id)')
            
            conn.commit()
            print("✅ Migration completed successfully!")
            
        elif 'REAL' in col_type.upper():
            print("✅ Column is already REAL type, no migration needed")
        else:
            print(f"⚠️ Unknown column type: {col_type}")

def update_test_frequency():
    """Update a test frequency to decimal value"""
    print("\n=== UPDATING TEST FREQUENCY ===")
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Find first service
        cursor.execute("SELECT id, name, frequency_per_year FROM services LIMIT 1")
        service = cursor.fetchone()
        
        if not service:
            print("No services found to update")
            return
        
        service_id, name, current_freq = service
        print(f"Found service: {name} with frequency {current_freq}")
        
        # Update to 1.5
        new_frequency = 1.5
        cursor.execute("UPDATE services SET frequency_per_year = ? WHERE id = ?", (new_frequency, service_id))
        conn.commit()
        
        # Verify update
        cursor.execute("SELECT frequency_per_year FROM services WHERE id = ?", (service_id,))
        updated_freq = cursor.fetchone()[0]
        
        print(f"Updated frequency to: {updated_freq} (type: {type(updated_freq)})")
        
        if updated_freq == new_frequency:
            print("✅ Decimal frequency update successful!")
        else:
            print(f"❌ Update failed: expected {new_frequency}, got {updated_freq}")

if __name__ == "__main__":
    print("Life Care Plan Database Frequency Debug Tool")
    print("=" * 50)
    
    check_database_schema()
    check_existing_data()
    force_migration()
    check_database_schema()
    check_existing_data()
    update_test_frequency()
    check_existing_data()
    
    print("\n" + "=" * 50)
    print("Debug complete. Restart your application to see changes.")