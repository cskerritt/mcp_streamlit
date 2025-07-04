import sqlite3
import json
import hashlib
import secrets
from datetime import datetime, timedelta
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

                # Create users table for authentication
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        full_name TEXT,
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        is_admin BOOLEAN NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP,
                        failed_login_attempts INTEGER DEFAULT 0,
                        locked_until TIMESTAMP
                    )
                ''')

                # Create sessions table for session management
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        session_token TEXT UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')

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

                # Add user_id column to evaluees table if it doesn't exist (migration)
                try:
                    cursor.execute('ALTER TABLE evaluees ADD COLUMN user_id INTEGER')
                    logger.info("Added user_id column to evaluees table")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        pass  # Column already exists
                    else:
                        raise
                
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
                
                # Create scenarios table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS scenarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        evaluee_id INTEGER NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT DEFAULT '',
                        is_baseline BOOLEAN NOT NULL DEFAULT 0,
                        base_year INTEGER NOT NULL,
                        projection_years REAL NOT NULL,
                        discount_rate REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (evaluee_id) REFERENCES evaluees (id) ON DELETE CASCADE,
                        UNIQUE(evaluee_id, name)
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
                        frequency_per_year REAL NOT NULL,
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
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users (username)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions (session_token)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions (user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_evaluees_name ON evaluees (name)')

                # Create user_id index only if column exists
                try:
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_evaluees_user_id ON evaluees (user_id)')
                except sqlite3.OperationalError:
                    pass  # Column doesn't exist yet

                cursor.execute('CREATE INDEX IF NOT EXISTS idx_services_table_id ON services (table_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_service_tables_evaluee_id ON service_tables (evaluee_id)')
                
                conn.commit()
                logger.info("Database initialized successfully")

                # Run database migrations
                self._run_migrations()
                
                # Create default admin user if no users exist
                self._create_default_admin_if_needed()

        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def _run_migrations(self):
        """Run database migrations to update schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Migration 1: Change frequency_per_year from INTEGER to REAL
                # Check if the column is currently INTEGER
                cursor.execute("PRAGMA table_info(services)")
                columns = cursor.fetchall()
                
                frequency_col = None
                for col in columns:
                    if col[1] == 'frequency_per_year':
                        frequency_col = col
                        break
                
                if frequency_col and 'INTEGER' in str(frequency_col[2]).upper():
                    logger.info("Migrating frequency_per_year column from INTEGER to REAL")
                    
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
                    logger.info("Successfully migrated frequency_per_year column to REAL type")
                
                # Migration 2: Add scenario_id column to service_tables
                try:
                    cursor.execute("PRAGMA table_info(service_tables)")
                    columns = cursor.fetchall()
                    column_names = [col[1] for col in columns]
                    
                    if 'scenario_id' not in column_names:
                        logger.info("Adding scenario_id column to service_tables")
                        cursor.execute('ALTER TABLE service_tables ADD COLUMN scenario_id INTEGER')
                        
                        # Create index for the new column
                        cursor.execute('CREATE INDEX IF NOT EXISTS idx_service_tables_scenario_id ON service_tables (scenario_id)')
                        
                        conn.commit()
                        logger.info("Successfully added scenario_id column to service_tables")
                        
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e).lower():
                        logger.warning(f"Migration warning: {e}")
                    
        except Exception as e:
            logger.error(f"Error running migrations: {e}")
            # Don't raise - migrations should be non-breaking

    def _create_default_admin_if_needed(self):
        """Create a default admin user if no users exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check if any users exist
                cursor.execute('SELECT COUNT(*) FROM users')
                user_count = cursor.fetchone()[0]

                if user_count == 0:
                    # Create default admin user
                    default_username = "admin"
                    default_email = "admin@lifecareplan.local"
                    default_password = "admin123"  # Should be changed on first login

                    salt = self._generate_salt()
                    password_hash = self._hash_password(default_password, salt)

                    cursor.execute('''
                        INSERT INTO users (username, email, password_hash, salt, full_name, is_admin)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (default_username, default_email, password_hash, salt, "Default Administrator", True))

                    conn.commit()
                    logger.info("Default admin user created: username='admin', password='admin123'")
                    logger.warning("SECURITY: Please change the default admin password immediately!")

        except Exception as e:
            logger.error(f"Error creating default admin user: {e}")
    
    def save_life_care_plan(self, lcp: LifeCarePlan, user_id: Optional[int] = None) -> int:
        """Save a complete life care plan with scenarios to the database."""
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
                        SET current_age = ?, birth_year = ?, discount_calculations = ?, user_id = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (lcp.evaluee.current_age, lcp.evaluee.birth_year, lcp.evaluee.discount_calculations, user_id, evaluee_id))
                    
                    # Delete existing data (scenarios and their tables/services will cascade)
                    cursor.execute('DELETE FROM projection_settings WHERE evaluee_id = ?', (evaluee_id,))
                    cursor.execute('DELETE FROM scenarios WHERE evaluee_id = ?', (evaluee_id,))
                    cursor.execute('DELETE FROM service_tables WHERE evaluee_id = ? AND scenario_id IS NULL', (evaluee_id,))
                else:
                    # Create new evaluee
                    cursor.execute('''
                        INSERT INTO evaluees (name, current_age, birth_year, discount_calculations, user_id)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (lcp.evaluee.name, lcp.evaluee.current_age, lcp.evaluee.birth_year, lcp.evaluee.discount_calculations, user_id))
                    evaluee_id = cursor.lastrowid
                
                # Save baseline projection settings (for backward compatibility)
                cursor.execute('''
                    INSERT INTO projection_settings (evaluee_id, base_year, projection_years, discount_rate)
                    VALUES (?, ?, ?, ?)
                ''', (evaluee_id, lcp.settings.base_year, lcp.settings.projection_years, lcp.settings.discount_rate))
                
                # Save scenarios if they exist
                if hasattr(lcp, 'scenarios') and lcp.scenarios:
                    for scenario_name, scenario in lcp.scenarios.items():
                        # Save scenario
                        scenario_settings = scenario.settings if scenario.settings else lcp.settings
                        cursor.execute('''
                            INSERT INTO scenarios (evaluee_id, name, description, is_baseline, base_year, projection_years, discount_rate)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (evaluee_id, scenario.name, scenario.description, scenario.is_baseline,
                              scenario_settings.base_year, scenario_settings.projection_years, scenario_settings.discount_rate))
                        scenario_id = cursor.lastrowid
                        
                        # Save service tables and services for this scenario
                        for table_name, table in scenario.tables.items():
                            cursor.execute('''
                                INSERT INTO service_tables (evaluee_id, scenario_id, name, default_inflation_rate)
                                VALUES (?, ?, ?, ?)
                            ''', (evaluee_id, scenario_id, table_name, getattr(table, 'default_inflation_rate', 3.5)))
                            table_id = cursor.lastrowid
                            
                            # Save services for this table
                            for service in table.services:
                                self._save_service(cursor, table_id, service)
                else:
                    # Backward compatibility: save tables directly (no scenarios)
                    for table_name, table in lcp.tables.items():
                        cursor.execute('''
                            INSERT INTO service_tables (evaluee_id, name, default_inflation_rate)
                            VALUES (?, ?, ?)
                        ''', (evaluee_id, table_name, getattr(table, 'default_inflation_rate', 3.5)))
                        table_id = cursor.lastrowid
                        
                        # Save services for this table
                        for service in table.services:
                            self._save_service(cursor, table_id, service)
                
                conn.commit()
                logger.info(f"Successfully saved life care plan: {lcp.evaluee.name}")
                return evaluee_id
                
        except Exception as e:
            logger.error(f"Error saving life care plan: {e}")
            raise
    
    def _save_service(self, cursor, table_id: int, service):
        """Helper method to save a service to the database."""
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
    
    def load_life_care_plan(self, evaluee_name: str) -> Optional[LifeCarePlan]:
        """Load a life care plan with scenarios from the database by evaluee name."""
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
                
                # Get baseline projection settings
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
                
                # Check if scenarios exist
                cursor.execute('SELECT * FROM scenarios WHERE evaluee_id = ? ORDER BY is_baseline DESC, name', (evaluee_id,))
                scenario_rows = cursor.fetchall()
                
                scenarios = {}
                active_scenario = None
                
                if scenario_rows:
                    # Load scenarios
                    for scenario_row in scenario_rows:
                        scenario_id = scenario_row[0]
                        scenario_name = scenario_row[2]
                        scenario_description = scenario_row[3]
                        is_baseline = bool(scenario_row[4])
                        
                        scenario_settings = ProjectionSettings(
                            base_year=scenario_row[5],
                            projection_years=scenario_row[6],
                            discount_rate=scenario_row[7]
                        )
                        
                        # Load tables for this scenario
                        scenario_tables = self._load_tables_for_scenario(cursor, evaluee_id, scenario_id)
                        
                        from src.models import Scenario
                        scenario = Scenario(
                            name=scenario_name,
                            description=scenario_description,
                            settings=scenario_settings,
                            tables=scenario_tables,
                            is_baseline=is_baseline,
                            created_at=datetime.fromisoformat(scenario_row[8]) if scenario_row[8] else datetime.now()
                        )
                        
                        scenarios[scenario_name] = scenario
                        
                        if is_baseline or active_scenario is None:
                            active_scenario = scenario_name
                    
                    # Create LCP with scenarios
                    lcp = LifeCarePlan(
                        evaluee=evaluee,
                        settings=settings,
                        _tables={},  # Empty, data is in scenarios
                        scenarios=scenarios,
                        active_scenario=active_scenario
                    )
                else:
                    # Backward compatibility: load tables directly (no scenarios)
                    tables = self._load_tables_for_scenario(cursor, evaluee_id, None)
                    
                    lcp = LifeCarePlan(
                        evaluee=evaluee,
                        settings=settings,
                        _tables=tables
                    )
                    # Initialize baseline scenario
                    lcp.__post_init__()
                
                logger.info(f"Successfully loaded life care plan: {evaluee_name}")
                return lcp
                
        except Exception as e:
            logger.error(f"Error loading life care plan: {e}")
            return None
    
    def _load_tables_for_scenario(self, cursor, evaluee_id: int, scenario_id: Optional[int]) -> Dict[str, 'ServiceTable']:
        """Load service tables for a specific scenario (or baseline if scenario_id is None)."""
        tables = {}
        
        # Build WHERE clause based on whether we're loading for a scenario or baseline
        if scenario_id is not None:
            cursor.execute('SELECT * FROM service_tables WHERE evaluee_id = ? AND scenario_id = ?', (evaluee_id, scenario_id))
        else:
            cursor.execute('SELECT * FROM service_tables WHERE evaluee_id = ? AND (scenario_id IS NULL OR scenario_id = ?)', (evaluee_id, scenario_id))
        
        table_rows = cursor.fetchall()
        
        for table_row in table_rows:
            table_id = table_row[0]
            table_name = table_row[2]
            
            from src.models import ServiceTable
            table = ServiceTable(name=table_name)
            table.default_inflation_rate = table_row[3]
            
            # Get services for this table
            cursor.execute('SELECT * FROM services WHERE table_id = ?', (table_id,))
            service_rows = cursor.fetchall()
            
            for service_row in service_rows:
                # Handle occurrence_years JSON parsing safely
                occurrence_years = None
                if service_row[8]:  # occurrence_years column (index 8)
                    try:
                        occurrence_years = json.loads(service_row[8])
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in occurrence_years for service: {service_row[2]}")
                
                from src.models import Service
                service = Service(
                    name=service_row[2],
                    inflation_rate=service_row[3],
                    unit_cost=service_row[4],
                    frequency_per_year=service_row[5],
                    start_year=service_row[6],
                    end_year=service_row[7],
                    occurrence_years=occurrence_years,
                    cost_range_low=service_row[9],
                    cost_range_high=service_row[10],
                    use_cost_range=bool(service_row[11]),
                    is_one_time_cost=bool(service_row[12]),
                    one_time_cost_year=service_row[13]
                )
                table.add_service(service)
            
            tables[table_name] = table
        
        return tables
    
    def list_evaluees(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get a list of all evaluees in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build query with optional user filter
                if user_id is not None:
                    cursor.execute('''
                        SELECT e.name, e.current_age, e.birth_year, e.created_at, e.updated_at,
                               COUNT(st.id) as table_count,
                               COUNT(s.id) as service_count
                        FROM evaluees e
                        LEFT JOIN service_tables st ON e.id = st.evaluee_id
                        LEFT JOIN services s ON st.id = s.table_id
                        WHERE e.user_id = ? OR e.user_id IS NULL
                        GROUP BY e.id, e.name, e.current_age, e.birth_year, e.created_at, e.updated_at
                        ORDER BY e.updated_at DESC
                    ''', (user_id,))
                else:
                    cursor.execute('''
                        SELECT e.name, e.current_age, e.birth_year, e.created_at, e.updated_at,
                               COUNT(st.id) as table_count,
                               COUNT(s.id) as service_count
                        FROM evaluees e
                        LEFT JOIN service_tables st ON e.id = st.evaluee_id
                        LEFT JOIN services s ON st.id = s.table_id
                        GROUP BY e.id, e.name, e.current_age, e.birth_year, e.created_at, e.updated_at
                        ORDER BY e.updated_at DESC
                    ''')
                
                rows = cursor.fetchall()
                evaluees = []
                
                for row in rows:
                    evaluees.append({
                        'name': row[0],
                        'current_age': row[1],
                        'birth_year': row[2],
                        'created_at': row[3],
                        'updated_at': row[4],
                        'table_count': row[5],
                        'service_count': row[6]
                    })
                
                return evaluees
                
        except Exception as e:
            logger.error(f"Error listing evaluees: {e}")
            return []
    
    def copy_life_care_plan(self, source_name: str, new_name: str, user_id: Optional[int] = None) -> bool:
        """Copy a life care plan to a new name.
        
        Args:
            source_name: Name of the evaluee/plan to copy
            new_name: New name for the copied plan
            user_id: User ID for ownership (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load the source plan
            source_lcp = self.load_life_care_plan(source_name)
            if not source_lcp:
                logger.error(f"Source plan '{source_name}' not found")
                return False
            
            # Check if new name already exists
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM evaluees WHERE name = ?', (new_name,))
                if cursor.fetchone():
                    logger.error(f"Plan with name '{new_name}' already exists")
                    return False
            
            # Create a copy with the new name
            new_lcp = source_lcp.copy(new_name)
            
            # Save the copy to database
            self.save_life_care_plan(new_lcp, user_id)
            
            logger.info(f"Successfully copied plan '{source_name}' to '{new_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Error copying life care plan: {e}")
            return False
    
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

    # User Authentication Methods

    def _hash_password(self, password: str, salt: str) -> str:
        """Hash a password with salt using SHA-256."""
        return hashlib.sha256((password + salt).encode()).hexdigest()

    def _generate_salt(self) -> str:
        """Generate a random salt for password hashing."""
        return secrets.token_hex(32)

    def _generate_session_token(self) -> str:
        """Generate a secure session token."""
        return secrets.token_urlsafe(32)

    def create_user(self, username: str, email: str, password: str, full_name: str = None, is_admin: bool = False) -> bool:
        """Create a new user account."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check if username or email already exists
                cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
                if cursor.fetchone():
                    logger.warning(f"User creation failed: username '{username}' or email '{email}' already exists")
                    return False

                # Generate salt and hash password
                salt = self._generate_salt()
                password_hash = self._hash_password(password, salt)

                # Insert new user
                cursor.execute('''
                    INSERT INTO users (username, email, password_hash, salt, full_name, is_admin)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (username, email, password_hash, salt, full_name, is_admin))

                conn.commit()
                logger.info(f"User '{username}' created successfully")
                return True

        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate a user and return user info if successful."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get user data
                cursor.execute('''
                    SELECT id, username, email, password_hash, salt, full_name, is_active, is_admin,
                           failed_login_attempts, locked_until
                    FROM users WHERE username = ?
                ''', (username,))

                user_row = cursor.fetchone()
                if not user_row:
                    logger.warning(f"Authentication failed: user '{username}' not found")
                    return None

                user_id, username, email, stored_hash, salt, full_name, is_active, is_admin, failed_attempts, locked_until = user_row

                # Check if account is active
                if not is_active:
                    logger.warning(f"Authentication failed: user '{username}' account is inactive")
                    return None

                # Check if account is locked
                if locked_until:
                    locked_until_dt = datetime.fromisoformat(locked_until)
                    if datetime.now() < locked_until_dt:
                        logger.warning(f"Authentication failed: user '{username}' account is locked until {locked_until}")
                        return None
                    else:
                        # Unlock account
                        cursor.execute('UPDATE users SET locked_until = NULL, failed_login_attempts = 0 WHERE id = ?', (user_id,))

                # Verify password
                password_hash = self._hash_password(password, salt)
                if password_hash != stored_hash:
                    # Increment failed login attempts
                    failed_attempts += 1
                    cursor.execute('UPDATE users SET failed_login_attempts = ? WHERE id = ?', (failed_attempts, user_id))

                    # Lock account after 5 failed attempts for 30 minutes
                    if failed_attempts >= 5:
                        lock_until = datetime.now() + timedelta(minutes=30)
                        cursor.execute('UPDATE users SET locked_until = ? WHERE id = ?', (lock_until.isoformat(), user_id))
                        logger.warning(f"User '{username}' account locked due to too many failed login attempts")

                    conn.commit()
                    logger.warning(f"Authentication failed: invalid password for user '{username}'")
                    return None

                # Successful login - reset failed attempts and update last login
                cursor.execute('''
                    UPDATE users
                    SET failed_login_attempts = 0, locked_until = NULL, last_login = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (user_id,))

                conn.commit()

                logger.info(f"User '{username}' authenticated successfully")
                return {
                    'id': user_id,
                    'username': username,
                    'email': email,
                    'full_name': full_name,
                    'is_admin': bool(is_admin)
                }

        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None

    def create_session(self, user_id: int, expires_hours: int = 24) -> Optional[str]:
        """Create a new session for a user."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Generate session token
                session_token = self._generate_session_token()
                expires_at = datetime.now() + timedelta(hours=expires_hours)

                # Insert session
                cursor.execute('''
                    INSERT INTO user_sessions (user_id, session_token, expires_at)
                    VALUES (?, ?, ?)
                ''', (user_id, session_token, expires_at.isoformat()))

                conn.commit()
                logger.info(f"Session created for user ID {user_id}")
                return session_token

        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None

    def validate_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Validate a session token and return user info if valid."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get session and user data
                cursor.execute('''
                    SELECT s.user_id, s.expires_at, u.username, u.email, u.full_name, u.is_admin, u.is_active
                    FROM user_sessions s
                    JOIN users u ON s.user_id = u.id
                    WHERE s.session_token = ? AND s.is_active = 1
                ''', (session_token,))

                session_row = cursor.fetchone()
                if not session_row:
                    return None

                user_id, expires_at, username, email, full_name, is_admin, is_active = session_row

                # Check if user is still active
                if not is_active:
                    return None

                # Check if session has expired
                expires_at_dt = datetime.fromisoformat(expires_at)
                if datetime.now() > expires_at_dt:
                    # Deactivate expired session
                    cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE session_token = ?', (session_token,))
                    conn.commit()
                    return None

                return {
                    'id': user_id,
                    'username': username,
                    'email': email,
                    'full_name': full_name,
                    'is_admin': bool(is_admin)
                }

        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return None

    def logout_session(self, session_token: str) -> bool:
        """Logout a session by deactivating it."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE session_token = ?', (session_token,))
                conn.commit()

                return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Error logging out session: {e}")
            return False

    def cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE expires_at < ?', (datetime.now().isoformat(),))
                conn.commit()

                logger.info(f"Cleaned up {cursor.rowcount} expired sessions")

        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")

# Global database instance
db = LCPDatabase()