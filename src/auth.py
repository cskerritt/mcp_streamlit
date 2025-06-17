"""
Authentication module for Streamlit Life Care Plan Application
"""

import streamlit as st
from typing import Optional, Dict, Any
from .database import db
import logging

logger = logging.getLogger(__name__)

class StreamlitAuth:
    """Authentication handler for Streamlit application."""
    
    def __init__(self):
        self.session_key = 'user_session'
        self.user_key = 'user_data'
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        return self.session_key in st.session_state and self.user_key in st.session_state
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current authenticated user data."""
        if self.is_authenticated():
            return st.session_state[self.user_key]
        return None
    
    def login(self, username: str, password: str) -> bool:
        """Authenticate user and create session."""
        try:
            # Authenticate with database
            user_data = db.authenticate_user(username, password)
            if not user_data:
                return False
            
            # Create session
            session_token = db.create_session(user_data['id'])
            if not session_token:
                return False
            
            # Store in Streamlit session state
            st.session_state[self.session_key] = session_token
            st.session_state[self.user_key] = user_data
            
            logger.info(f"User '{username}' logged in successfully")
            return True
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    def logout(self):
        """Logout current user and clear session."""
        try:
            # Logout session in database
            if self.session_key in st.session_state:
                db.logout_session(st.session_state[self.session_key])
            
            # Clear Streamlit session state
            if self.session_key in st.session_state:
                del st.session_state[self.session_key]
            if self.user_key in st.session_state:
                del st.session_state[self.user_key]
            
            # Clear other app-specific session data
            keys_to_clear = ['lcp_data', 'current_table', 'page']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            
            logger.info("User logged out successfully")
            
        except Exception as e:
            logger.error(f"Logout error: {e}")
    
    def validate_session(self) -> bool:
        """Validate current session with database."""
        try:
            if not self.is_authenticated():
                return False
            
            session_token = st.session_state[self.session_key]
            user_data = db.validate_session(session_token)
            
            if not user_data:
                # Session invalid, clear local session
                self.logout()
                return False
            
            # Update user data in case it changed
            st.session_state[self.user_key] = user_data
            return True
            
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            self.logout()
            return False
    
    def register_user(self, username: str, email: str, password: str, full_name: str = None) -> bool:
        """Register a new user."""
        try:
            return db.create_user(username, email, password, full_name)
        except Exception as e:
            logger.error(f"User registration error: {e}")
            return False
    
    def require_auth(self):
        """Decorator-like function to require authentication for a page."""
        if not self.validate_session():
            self.show_login_page()
            st.stop()
    
    def show_login_page(self):
        """Display the login/registration page."""
        st.title("🏥 Life Care Plan - Login")
        
        # Create tabs for login and registration
        tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])
        
        with tab1:
            self._show_login_form()
        
        with tab2:
            self._show_registration_form()
    
    def _show_login_form(self):
        """Show the login form."""
        st.subheader("Login to Your Account")
        
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            col1, col2 = st.columns([1, 3])
            with col1:
                login_button = st.form_submit_button("Login", use_container_width=True)
            
            if login_button:
                if not username or not password:
                    st.error("Please enter both username and password")
                    return
                
                with st.spinner("Authenticating..."):
                    if self.login(username, password):
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password. Please try again.")
    
    def _show_registration_form(self):
        """Show the registration form."""
        st.subheader("Create New Account")
        
        with st.form("registration_form"):
            full_name = st.text_input("Full Name", placeholder="Enter your full name")
            username = st.text_input("Username", placeholder="Choose a username")
            email = st.text_input("Email", placeholder="Enter your email address")
            password = st.text_input("Password", type="password", placeholder="Choose a password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
            
            col1, col2 = st.columns([1, 3])
            with col1:
                register_button = st.form_submit_button("Register", use_container_width=True)
            
            if register_button:
                # Validation
                if not all([username, email, password, confirm_password]):
                    st.error("Please fill in all required fields")
                    return
                
                if password != confirm_password:
                    st.error("Passwords do not match")
                    return
                
                if len(password) < 6:
                    st.error("Password must be at least 6 characters long")
                    return
                
                if "@" not in email:
                    st.error("Please enter a valid email address")
                    return
                
                with st.spinner("Creating account..."):
                    if self.register_user(username, email, password, full_name):
                        st.success("Account created successfully! Please login with your new credentials.")
                    else:
                        st.error("Registration failed. Username or email may already exist.")

# Global authentication instance
auth = StreamlitAuth()
