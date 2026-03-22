#!/usr/bin/env python3
"""
Setup script for Finance Tracker
Guides user through initial configuration
"""
import os
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path.home() / "finance-tracker"


def check_python_version():
    """Ensure Python 3.9+"""
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")
    return True


def install_dependencies():
    """Install required Python packages."""
    print("\n📦 Installing dependencies...")
    req_file = BASE_DIR / "requirements.txt"
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("✅ Dependencies installed")
        return True
    else:
        print(f"❌ Failed to install dependencies: {result.stderr}")
        return False


def check_anthropic_key():
    """Check for Anthropic API key."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        print(f"✅ Anthropic API key found (starts with {key[:10]}...)")
        return True
    else:
        print("⚠️  ANTHROPIC_API_KEY not set")
        print("   Add to your ~/.zshrc or ~/.bash_profile:")
        print("   export ANTHROPIC_API_KEY='your-key-here'")
        return False


def check_google_credentials():
    """Check for Google Sheets credentials."""
    creds_file = BASE_DIR / "credentials.json"
    if creds_file.exists():
        print(f"✅ Google credentials found at {creds_file}")
        return True
    else:
        print(f"⚠️  Google credentials not found")
        print(f"   Place credentials.json at: {creds_file}")
        print("   See README for instructions on getting credentials")
        return False


def setup_launchd():
    """Install launchd plist for folder watching."""
    plist_src = BASE_DIR / "com.finance-tracker.watcher.plist"
    plist_dest = Path.home() / "Library" / "LaunchAgents" / "com.finance-tracker.watcher.plist"

    if not plist_src.exists():
        print("❌ Plist file not found")
        return False

    # Create LaunchAgents dir if needed
    plist_dest.parent.mkdir(parents=True, exist_ok=True)

    # Update plist with correct Python path
    import shutil
    shutil.copy(plist_src, plist_dest)

    print(f"✅ Launchd plist installed at {plist_dest}")
    print("   To start the watcher, run:")
    print(f"   launchctl load {plist_dest}")
    print("   To stop:")
    print(f"   launchctl unload {plist_dest}")

    return True


def test_sheets_connection():
    """Test Google Sheets connection."""
    try:
        sys.path.insert(0, str(BASE_DIR))
        from src.sheets_sync import get_sheets_client, get_or_create_spreadsheet

        print("\n🔗 Testing Google Sheets connection...")
        client = get_sheets_client()
        spreadsheet = get_or_create_spreadsheet(client)
        print(f"✅ Connected to spreadsheet: {spreadsheet.title}")
        print(f"   URL: {spreadsheet.url}")
        return True
    except Exception as e:
        print(f"❌ Sheets connection failed: {e}")
        return False


def main():
    print("=" * 50)
    print("    FINANCE TRACKER SETUP")
    print("=" * 50)

    results = []

    # Check Python
    results.append(("Python version", check_python_version()))

    # Install dependencies
    results.append(("Dependencies", install_dependencies()))

    # Check API keys
    results.append(("Anthropic API key", check_anthropic_key()))
    results.append(("Google credentials", check_google_credentials()))

    # Test sheets if credentials exist
    if (BASE_DIR / "credentials.json").exists():
        results.append(("Sheets connection", test_sheets_connection()))

    # Setup launchd
    print("\n")
    results.append(("Launchd watcher", setup_launchd()))

    # Summary
    print("\n" + "=" * 50)
    print("    SETUP SUMMARY")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 Setup complete! You're ready to go.")
        print("\nNext steps:")
        print("1. Drop a PDF statement in: ~/finance-tracker/statements/")
        print("2. Run: python ~/finance-tracker/scripts/process_statements.py")
        print("3. View your dashboard (see README for Streamlit Cloud deployment)")
    else:
        print("\n⚠️  Some items need attention. See messages above.")


if __name__ == "__main__":
    main()
