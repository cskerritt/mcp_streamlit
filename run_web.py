#!/usr/bin/env python3
"""
Life Care Plan Web Application Launcher

This script starts the web-based GUI application for the Life Care Plan
Table Generator. The application provides an interactive browser interface
for creating, managing, and exporting life care plan cost projections.
"""

import uvicorn
import os
import sys
from pathlib import Path

def main():
    """Launch the web application."""
    
    print("🏥 Life Care Plan Table Generator - Web Application")
    print("=" * 55)
    print("Starting web server...")
    print()
    
    # Ensure required directories exist
    os.makedirs("static", exist_ok=True)
    os.makedirs("templates", exist_ok=True) 
    os.makedirs("temp_files", exist_ok=True)
    
    try:
        # Start the web server
        uvicorn.run(
            "web_app:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down web server...")
        print("Thank you for using Life Care Plan Table Generator!")
    except Exception as e:
        print(f"\n❌ Error starting web server: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure all dependencies are installed: pip install -r web_requirements.txt")
        print("2. Check that port 8000 is not already in use")
        print("3. Ensure you have write permissions in the current directory")
        sys.exit(1)

if __name__ == "__main__":
    main()