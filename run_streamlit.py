#!/usr/bin/env python3
"""
Life Care Plan Streamlit Application Launcher

This script starts the Streamlit web application for the Life Care Plan
Table Generator. The application provides an interactive browser interface
for creating, managing, and exporting life care plan cost projections.
"""

import subprocess
import sys
import os
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import streamlit
        import pandas
        import plotly
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("\n📦 Please install the required dependencies:")
        print("pip install -r streamlit_requirements.txt")
        return False

def main():
    """Launch the Streamlit application."""
    
    print("🏥 Life Care Plan Table Generator - Streamlit Application")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("streamlit_app.py"):
        print("❌ Error: streamlit_app.py not found in current directory")
        print("Please run this script from the project root directory.")
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    print("🚀 Starting Streamlit application...")
    print("📱 The application will open in your default web browser")
    print("🔗 URL: http://localhost:8501")
    print("\n💡 Tips:")
    print("   • Use Ctrl+C to stop the application")
    print("   • Refresh the browser page if you encounter any issues")
    print("   • Check the terminal for any error messages")
    print("\n" + "=" * 60)
    
    try:
        # Start Streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
            "--server.headless", "false",
            "--server.runOnSave", "true",
            "--browser.gatherUsageStats", "false"
        ])
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down Streamlit application...")
        print("Thank you for using Life Care Plan Table Generator!")
    except Exception as e:
        print(f"\n❌ Error starting Streamlit application: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure all dependencies are installed: pip install -r streamlit_requirements.txt")
        print("2. Check that port 8501 is not already in use")
        print("3. Ensure you have the necessary permissions")
        print("4. Try running directly: streamlit run streamlit_app.py")
        sys.exit(1)

if __name__ == "__main__":
    main()
