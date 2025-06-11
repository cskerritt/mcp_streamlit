#!/usr/bin/env python3
"""
Dependency Update Script for Life Care Plan Table Generator

This script helps update all dependencies to their latest compatible versions
and checks for any issues.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and return success status."""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr.strip()}")
        return False

def check_python_version():
    """Check if Python version is compatible."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} is not compatible")
        print("   Requires Python 3.8 or higher")
        return False

def main():
    """Main update process."""
    print("🏥 Life Care Plan Table Generator - Dependency Update")
    print("=" * 55)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check if we're in the right directory
    if not Path("web_requirements.txt").exists():
        print("❌ web_requirements.txt not found. Please run this script from the project root directory.")
        sys.exit(1)
    
    success = True
    
    # Update pip first
    success &= run_command(
        f"{sys.executable} -m pip install --upgrade pip",
        "Updating pip to latest version"
    )
    
    # Install/update web requirements
    success &= run_command(
        f"{sys.executable} -m pip install -r web_requirements.txt --upgrade",
        "Installing/updating web dependencies"
    )
    
    # Install/update core requirements if they exist
    if Path("requirements.txt").exists():
        success &= run_command(
            f"{sys.executable} -m pip install -r requirements.txt --upgrade",
            "Installing/updating core dependencies"
        )
    
    # Check for potential issues
    print("\n🔍 Checking for potential dependency conflicts...")
    result = subprocess.run(
        f"{sys.executable} -m pip check",
        shell=True,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ No dependency conflicts found")
    else:
        print("⚠️  Potential dependency conflicts detected:")
        print(result.stdout)
        success = False
    
    # Test imports
    print("\n🧪 Testing critical imports...")
    test_imports = [
        ("fastapi", "FastAPI web framework"),
        ("uvicorn", "ASGI web server"),
        ("pandas", "Data manipulation"),
        ("plotly", "Chart generation"),
        ("pydantic", "Data validation"),
        ("openpyxl", "Excel file handling"),
        ("docx", "Word document generation"),
        ("reportlab", "PDF generation")
    ]
    
    for module, description in test_imports:
        try:
            __import__(module)
            print(f"✅ {module:12} - {description}")
        except ImportError as e:
            print(f"❌ {module:12} - Failed to import: {e}")
            success = False
    
    print("\n" + "=" * 55)
    if success:
        print("🎉 All dependencies updated successfully!")
        print("\nYou can now run the application:")
        print("   python run_web.py")
        print("\nOr for development mode:")
        print("   uvicorn web_app:app --reload --host 0.0.0.0 --port 8000")
    else:
        print("⚠️  Some issues were detected. Please review the output above.")
        print("\nYou may need to:")
        print("1. Create a fresh virtual environment")
        print("2. Install dependencies manually")
        print("3. Check Python version compatibility")
    
    print(f"\n📝 Log: All output saved to console")

if __name__ == "__main__":
    main()