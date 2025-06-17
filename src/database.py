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

                # Create default admin user if no users exist
                self._create_default_admin_if_needed()

        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

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
                        SET current_age = ?, birth_year = ?, discount_calculations = ?, user_id = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (lcp.evaluee.current_age, lcp.evaluee.birth_year, lcp.evaluee.discount_calculations, user_id, evaluee_id))
                    
                    # Delete existing projection settings and service tables (cascade will handle services)
                    cursor.execute('DELETE FROM projection_settings WHERE evaluee_id = ?', (evaluee_id,))
                    cursor.execute('DELETE FROM service_tables WHERE evaluee_id = ?', (evaluee_id,))
                else:
                    # Create new evaluee
                    cursor.execute('''
                        INSERT INTO evaluees (name, current_age, birth_year, discount_calculations, user_id)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (lcp.evaluee.name, lcp.evaluee.current_age, lcp.evaluee.birth_year, lcp.evaluee.discount_calculations, user_id))
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
                        # Handle occurrence_years JSON parsing safely
                        occurrence_years = None
                        if service_row[9] and isinstance(service_row[9], str):
                            try:
                                occurrence_years = json.loads(service_row[9])
                            except (json.JSONDecodeError, TypeError):
                                occurrence_years = None
                        
                        # Handle cost range values safely
                        use_cost_range = bool(service_row[12])
                        cost_range_low = service_row[10] if service_row[10] is not None else None
                        cost_range_high = service_row[11] if service_row[11] is not None else None

                        # If use_cost_range is True but values are None, disable cost range
                        if use_cost_range and (cost_range_low is None or cost_range_high is None):
                            use_cost_range = False
                            cost_range_low = None
                            cost_range_high = None

                        # Handle inflation rate - ensure it's stored as decimal
                        inflation_rate = service_row[3]
                        if inflation_rate > 1.0:  # Likely stored as percentage, convert to decimal
                            inflation_rate = inflation_rate / 100

                        service = Service(
                            name=service_row[2],
                            inflation_rate=inflation_rate,
                            unit_cost=service_row[4],
                            frequency_per_year=service_row[5],
                            start_year=service_row[6],
                            end_year=service_row[7],
                            occurrence_years=occurrence_years,
                            cost_range_low=cost_range_low,
                            cost_range_high=cost_range_high,
                            use_cost_range=use_cost_range,
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
    
    def list_evaluees(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get a list of all evaluees in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build query with optional user filter
                if user_id is not None:
                    cursor.execute('''
                        SELECT e.name, e.current_age, e.created_at, e.updated_at,
                               COUNT(st.id) as table_count,
                               COUNT(s.id) as service_count
                        FROM evaluees e
                        LEFT JOIN service_tables st ON e.id = st.evaluee_id
                        LEFT JOIN services s ON st.id = s.table_id
                        WHERE e.user_id = ? OR e.user_id IS NULL
                        GROUP BY e.id, e.name, e.current_age, e.created_at, e.updated_at
                        ORDER BY e.updated_at DESC
                    ''', (user_id,))
                else:
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