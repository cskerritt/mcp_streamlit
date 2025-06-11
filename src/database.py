import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from .models import LifeCarePlan, Evaluee, ProjectionSettings, ServiceTable, Service
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LCPDatabase:
    """Database manager for Life Care Plan data persistence."""
    
    def __init__(self, db_path: str = "lcp_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create evaluees table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS evaluees (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        current_age REAL NOT NULL,
                        birth_year INTEGER,
                        discount_calculations BOOLEAN NOT NULL DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create projection_settings table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS projection_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        evaluee_id INTEGER NOT NULL,
                        base_year INTEGER NOT NULL,
                        projection_years REAL NOT NULL,
                        discount_rate REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (evaluee_id) REFERENCES evaluees (id) ON DELETE CASCADE
                    )
                ''')
                
                # Create service_tables table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS service_tables (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        evaluee_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        default_inflation_rate REAL DEFAULT 3.5,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (evaluee_id) REFERENCES evaluees (id) ON DELETE CASCADE
                    )
                ''')
                
                # Create services table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS services (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        table_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        inflation_rate REAL NOT NULL,
                        unit_cost REAL NOT NULL,
                        frequency_per_year INTEGER NOT NULL,
                        start_year INTEGER,
                        end_year INTEGER,
                        occurrence_years TEXT,  -- JSON array
                        cost_range_low REAL,
                        cost_range_high REAL,
                        use_cost_range BOOLEAN DEFAULT 0,
                        is_one_time_cost BOOLEAN DEFAULT 0,
                        one_time_cost_year INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (table_id) REFERENCES service_tables (id) ON DELETE CASCADE
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_evaluees_name ON evaluees (name)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_services_table_id ON services (table_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_service_tables_evaluee_id ON service_tables (evaluee_id)')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def save_life_care_plan(self, lcp: LifeCarePlan) -> int:
        """Save a complete life care plan to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if evaluee already exists (by name)
                cursor.execute('SELECT id FROM evaluees WHERE name = ?', (lcp.evaluee.name,))
                evaluee_row = cursor.fetchone()
                
                if evaluee_row:
                    # Update existing evaluee
                    evaluee_id = evaluee_row[0]
                    cursor.execute('''
                        UPDATE evaluees 
                        SET current_age = ?, birth_year = ?, discount_calculations = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (lcp.evaluee.current_age, lcp.evaluee.birth_year, lcp.evaluee.discount_calculations, evaluee_id))
                    
                    # Delete existing projection settings and service tables (cascade will handle services)
                    cursor.execute('DELETE FROM projection_settings WHERE evaluee_id = ?', (evaluee_id,))
                    cursor.execute('DELETE FROM service_tables WHERE evaluee_id = ?', (evaluee_id,))
                else:
                    # Create new evaluee
                    cursor.execute('''
                        INSERT INTO evaluees (name, current_age, birth_year, discount_calculations)
                        VALUES (?, ?, ?, ?)
                    ''', (lcp.evaluee.name, lcp.evaluee.current_age, lcp.evaluee.birth_year, lcp.evaluee.discount_calculations))
                    evaluee_id = cursor.lastrowid
                
                # Save projection settings
                cursor.execute('''
                    INSERT INTO projection_settings (evaluee_id, base_year, projection_years, discount_rate)
                    VALUES (?, ?, ?, ?)
                ''', (evaluee_id, lcp.settings.base_year, lcp.settings.projection_years, lcp.settings.discount_rate))
                
                # Save service tables and services
                for table_name, table in lcp.tables.items():
                    cursor.execute('''
                        INSERT INTO service_tables (evaluee_id, name, default_inflation_rate)
                        VALUES (?, ?, ?)
                    ''', (evaluee_id, table_name, getattr(table, 'default_inflation_rate', 3.5)))
                    table_id = cursor.lastrowid
                    
                    # Save services for this table
                    for service in table.services:
                        occurrence_years_json = json.dumps(service.occurrence_years) if service.occurrence_years else None
                        
                        cursor.execute('''
                            INSERT INTO services (
                                table_id, name, inflation_rate, unit_cost, frequency_per_year,
                                start_year, end_year, occurrence_years, cost_range_low, cost_range_high,
                                use_cost_range, is_one_time_cost, one_time_cost_year
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            table_id, service.name, service.inflation_rate, service.unit_cost,
                            service.frequency_per_year, service.start_year, service.end_year,
                            occurrence_years_json, service.cost_range_low, service.cost_range_high,
                            service.use_cost_range, service.is_one_time_cost, service.one_time_cost_year
                        ))
                
                conn.commit()
                logger.info(f"Life care plan saved successfully for evaluee: {lcp.evaluee.name}")
                return evaluee_id
                
        except Exception as e:
            logger.error(f"Error saving life care plan: {e}")
            raise
    
    def load_life_care_plan(self, evaluee_name: str) -> Optional[LifeCarePlan]:
        """Load a life care plan from the database by evaluee name."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get evaluee
                cursor.execute('SELECT * FROM evaluees WHERE name = ?', (evaluee_name,))
                evaluee_row = cursor.fetchone()
                
                if not evaluee_row:
                    return None
                
                evaluee_id = evaluee_row[0]
                evaluee = Evaluee(
                    name=evaluee_row[1],
                    current_age=evaluee_row[2],
                    birth_year=evaluee_row[3],
                    discount_calculations=bool(evaluee_row[4])
                )
                
                # Get projection settings
                cursor.execute('SELECT * FROM projection_settings WHERE evaluee_id = ?', (evaluee_id,))
                settings_row = cursor.fetchone()
                
                if not settings_row:
                    logger.error(f"No projection settings found for evaluee: {evaluee_name}")
                    return None
                
                settings = ProjectionSettings(
                    base_year=settings_row[2],
                    projection_years=settings_row[3],
                    discount_rate=settings_row[4]
                )
                
                # Get service tables
                cursor.execute('SELECT * FROM service_tables WHERE evaluee_id = ?', (evaluee_id,))
                table_rows = cursor.fetchall()
                
                tables = {}
                for table_row in table_rows:
                    table_id = table_row[0]
                    table_name = table_row[2]
                    
                    table = ServiceTable(name=table_name)
                    table.default_inflation_rate = table_row[3]
                    
                    # Get services for this table
                    cursor.execute('SELECT * FROM services WHERE table_id = ?', (table_id,))
                    service_rows = cursor.fetchall()
                    
                    for service_row in service_rows:
                        occurrence_years = json.loads(service_row[9]) if service_row[9] else None
                        
                        service = Service(
                            name=service_row[2],
                            inflation_rate=service_row[3],
                            unit_cost=service_row[4],
                            frequency_per_year=service_row[5],
                            start_year=service_row[6],
                            end_year=service_row[7],
                            occurrence_years=occurrence_years,
                            cost_range_low=service_row[10],
                            cost_range_high=service_row[11],
                            use_cost_range=bool(service_row[12]),
                            is_one_time_cost=bool(service_row[13]),
                            one_time_cost_year=service_row[14]
                        )
                        
                        table.add_service(service)
                    
                    tables[table_name] = table
                
                lcp = LifeCarePlan(evaluee=evaluee, settings=settings)
                for table_name, table in tables.items():
                    lcp.add_table(table)
                
                logger.info(f"Life care plan loaded successfully for evaluee: {evaluee_name}")
                return lcp
                
        except Exception as e:
            logger.error(f"Error loading life care plan: {e}")
            return None
    
    def list_evaluees(self) -> List[Dict[str, Any]]:
        """Get a list of all evaluees in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT e.name, e.current_age, e.created_at, e.updated_at,
                           COUNT(st.id) as table_count,
                           COUNT(s.id) as service_count
                    FROM evaluees e
                    LEFT JOIN service_tables st ON e.id = st.evaluee_id
                    LEFT JOIN services s ON st.id = s.table_id
                    GROUP BY e.id, e.name, e.current_age, e.created_at, e.updated_at
                    ORDER BY e.updated_at DESC
                ''')
                
                rows = cursor.fetchall()
                evaluees = []
                
                for row in rows:
                    evaluees.append({
                        'name': row[0],
                        'age': row[1],
                        'created_at': row[2],
                        'updated_at': row[3],
                        'table_count': row[4],
                        'service_count': row[5]
                    })
                
                return evaluees
                
        except Exception as e:
            logger.error(f"Error listing evaluees: {e}")
            return []
    
    def delete_evaluee(self, evaluee_name: str) -> bool:
        """Delete an evaluee and all associated data."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM evaluees WHERE name = ?', (evaluee_name,))
                deleted_rows = cursor.rowcount
                
                conn.commit()
                
                if deleted_rows > 0:
                    logger.info(f"Evaluee '{evaluee_name}' deleted successfully")
                    return True
                else:
                    logger.warning(f"No evaluee found with name: {evaluee_name}")
                    return False
                
        except Exception as e:
            logger.error(f"Error deleting evaluee: {e}")
            return False

# Global database instance
db = LCPDatabase()