#!/usr/bin/env python3
"""
Data migration script to fix inflation rates that might be stored as percentages
instead of decimals in the database.
"""

import sqlite3
import sys
import os

def fix_inflation_rates(db_path="lcp_data.db"):
    """Fix inflation rates in the database."""
    print("🔧 Fixing inflation rates in database...")
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Get all services with their inflation rates
            cursor.execute('SELECT id, name, inflation_rate FROM services')
            services = cursor.fetchall()
            
            fixed_count = 0
            
            for service_id, service_name, inflation_rate in services:
                if inflation_rate > 1.0:  # Likely stored as percentage
                    new_rate = inflation_rate / 100
                    cursor.execute(
                        'UPDATE services SET inflation_rate = ? WHERE id = ?',
                        (new_rate, service_id)
                    )
                    print(f"  ✅ Fixed '{service_name}': {inflation_rate}% → {new_rate}")
                    fixed_count += 1
            
            # Also fix default inflation rates in service tables
            cursor.execute('SELECT id, name, default_inflation_rate FROM service_tables')
            tables = cursor.fetchall()
            
            for table_id, table_name, default_rate in tables:
                if default_rate and default_rate > 1.0:  # Likely stored as percentage
                    new_rate = default_rate / 100
                    cursor.execute(
                        'UPDATE service_tables SET default_inflation_rate = ? WHERE id = ?',
                        (new_rate, table_id)
                    )
                    print(f"  ✅ Fixed table '{table_name}' default rate: {default_rate}% → {new_rate}")
                    fixed_count += 1
            
            conn.commit()
            
            if fixed_count > 0:
                print(f"\n🎉 Fixed {fixed_count} inflation rate(s) in the database!")
            else:
                print("\n✅ No inflation rates needed fixing - database is already correct!")
                
            return True
            
    except Exception as e:
        print(f"\n❌ Error fixing inflation rates: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "lcp_data.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database file '{db_path}' not found!")
        sys.exit(1)
    
    success = fix_inflation_rates(db_path)
    sys.exit(0 if success else 1)
