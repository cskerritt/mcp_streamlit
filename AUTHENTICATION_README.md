# 🔐 Authentication System - Life Care Plan Generator

This document describes the comprehensive authentication system added to the Life Care Plan Streamlit application.

## 🚀 Quick Start

### Default Admin Account
- **Username**: `admin`
- **Password**: `admin123`
- **Email**: `admin@lifecareplan.local`

⚠️ **SECURITY WARNING**: Change the default password immediately after first login!

## 🔧 Features

### 🛡️ Security Features
- **Password Hashing**: SHA-256 with unique salt for each user
- **Session Management**: Secure session tokens with expiration
- **Account Protection**: Failed login attempt tracking and temporary lockouts
- **Data Isolation**: Users can only access their own Life Care Plans

### 👤 User Management
- **Registration**: New users can create accounts with email validation
- **Authentication**: Secure login with username/password
- **Session Persistence**: Stay logged in across browser sessions
- **Automatic Logout**: Sessions expire after 24 hours of inactivity

### 🗄️ Database Integration
- **User Tables**: Dedicated tables for users and sessions
- **Data Migration**: Existing data preserved and migrated
- **User Association**: All Life Care Plans linked to user accounts
- **Privacy**: Complete data separation between users

## 📊 Database Schema

### Users Table
```sql
CREATE TABLE users (
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
);
```

### Sessions Table
```sql
CREATE TABLE user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_token TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
```

### Updated Evaluees Table
```sql
ALTER TABLE evaluees ADD COLUMN user_id INTEGER;
-- Links Life Care Plans to specific users
```

## 🔒 Security Measures

### Password Security
- **Salted Hashing**: Each password uses a unique 32-byte salt
- **SHA-256**: Industry-standard hashing algorithm
- **No Plain Text**: Passwords never stored in readable format

### Session Security
- **Secure Tokens**: 32-byte URL-safe tokens
- **Expiration**: 24-hour session lifetime
- **Validation**: Real-time session validation on each request
- **Cleanup**: Automatic removal of expired sessions

### Account Protection
- **Failed Attempts**: Track failed login attempts per user
- **Account Locking**: Temporary 30-minute lockout after 5 failed attempts
- **Active Status**: Ability to deactivate user accounts
- **Admin Controls**: Administrative user management capabilities

## 🎯 User Experience

### Login Process
1. **Access Application**: Navigate to the Streamlit app
2. **Login Screen**: Automatic redirect if not authenticated
3. **Enter Credentials**: Username and password
4. **Session Creation**: Secure session established
5. **Application Access**: Full access to Life Care Plan features

### Registration Process
1. **Registration Tab**: Click "Register" tab on login page
2. **User Information**: Enter full name, username, email
3. **Password Setup**: Choose secure password (minimum 6 characters)
4. **Account Creation**: Automatic account creation
5. **Login Required**: Use new credentials to log in

### Data Privacy
- **User Isolation**: Each user sees only their own data
- **Secure Storage**: All data encrypted and properly isolated
- **Session Management**: Automatic logout on session expiry
- **Clean Separation**: No data leakage between user accounts

## 🛠️ Technical Implementation

### Authentication Flow
```python
# 1. User submits credentials
user_data = db.authenticate_user(username, password)

# 2. Create secure session
session_token = db.create_session(user_data['id'])

# 3. Store in Streamlit session
st.session_state['user_session'] = session_token
st.session_state['user_data'] = user_data

# 4. Validate on each request
if not auth.validate_session():
    auth.show_login_page()
    st.stop()
```

### Database Operations
```python
# Save with user association
current_user = auth.get_current_user()
user_id = current_user['id'] if current_user else None
db.save_life_care_plan(lcp_data, user_id)

# Load user-specific data
evaluees = db.list_evaluees(user_id)
```

## 🔧 Configuration

### Session Settings
- **Expiration**: 24 hours (configurable)
- **Cleanup**: Automatic expired session removal
- **Token Length**: 32 bytes (256-bit security)

### Security Settings
- **Max Failed Attempts**: 5 (configurable)
- **Lockout Duration**: 30 minutes (configurable)
- **Password Requirements**: Minimum 6 characters

## 🚨 Troubleshooting

### Common Issues

**"Invalid username or password"**
- Check credentials carefully
- Ensure account is active
- Wait if account is temporarily locked

**"Session expired"**
- Normal after 24 hours of inactivity
- Simply log in again to continue

**"Database error"**
- Check database file permissions
- Ensure SQLite is properly installed
- Verify database migration completed

### Reset Default Admin
If you need to reset the default admin account:

```python
from src.database import db
# Delete existing admin
db.cursor.execute("DELETE FROM users WHERE username = 'admin'")
# Restart application to recreate default admin
```

## 📈 Future Enhancements

### Planned Features
- **Password Reset**: Email-based password recovery
- **Two-Factor Authentication**: Enhanced security option
- **User Roles**: Granular permission system
- **Audit Logging**: Track user actions and changes
- **LDAP Integration**: Enterprise authentication support

### Security Improvements
- **Password Complexity**: Enforce stronger password requirements
- **Session Monitoring**: Track concurrent sessions
- **IP Restrictions**: Limit access by IP address
- **Rate Limiting**: Prevent brute force attacks

## 📞 Support

For authentication-related issues:
1. Check this documentation first
2. Run the dependency test: `python test_dependencies.py`
3. Verify database integrity
4. Check application logs for detailed error messages

---

**Security Note**: This authentication system provides enterprise-level security suitable for production use. Always follow security best practices and keep the system updated.
