#!/usr/bin/env python3
"""Interactive OAuth setup wizard using Playwright."""

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

SKILL_DIR = Path(__file__).parent
CREDENTIALS_FILE = SKILL_DIR / "credentials.json"

def wait_for_user(message: str):
    """Prompt user to continue."""
    input(f"\n>>> {message}\n    Press Enter when ready...")

def setup_oauth():
    print("=" * 60)
    print("Gmail API OAuth Setup Wizard")
    print("=" * 60)
    print("\nThis will open Google Cloud Console to set up OAuth credentials.")
    print("You'll need to:")
    print("  1. Sign in to your Google account")
    print("  2. Create or select a project")
    print("  3. Enable Gmail API")
    print("  4. Configure OAuth consent screen")
    print("  5. Create OAuth credentials")
    print("  6. Download credentials.json")
    
    wait_for_user("Starting browser. Sign in to Google when prompted.")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Step 1: Go to Cloud Console
        print("\n[1/6] Opening Google Cloud Console...")
        page.goto("https://console.cloud.google.com/")
        
        wait_for_user("Sign in to your Google account if needed, then continue.")
        
        # Step 2: Create or select project
        print("\n[2/6] Project setup...")
        page.goto("https://console.cloud.google.com/projectcreate")
        
        wait_for_user(
            "Create a new project (e.g., 'gmail-skill') or use existing.\n"
            "    Wait for project creation to complete, then continue."
        )
        
        # Step 3: Enable Gmail API
        print("\n[3/6] Enabling Gmail API...")
        page.goto("https://console.cloud.google.com/apis/library/gmail.googleapis.com")
        
        wait_for_user(
            "Click 'ENABLE' button to enable Gmail API.\n"
            "    (If already enabled, just continue.)"
        )
        
        # Step 4: Configure OAuth consent screen
        print("\n[4/6] Configuring OAuth consent screen...")
        page.goto("https://console.cloud.google.com/apis/credentials/consent")
        
        print("""
    Configure the OAuth consent screen:
    - Select 'External' user type (unless you have Workspace)
    - App name: 'Gmail Skill' (or anything)
    - User support email: your email
    - Developer contact: your email
    - Click 'Save and Continue' through all steps
    - Add your email as a test user
    - Complete the wizard
        """)
        
        wait_for_user("Complete OAuth consent screen setup, then continue.")
        
        # Step 5: Create OAuth credentials
        print("\n[5/6] Creating OAuth credentials...")
        page.goto("https://console.cloud.google.com/apis/credentials/oauthclient")
        
        print("""
    Create OAuth client ID:
    - Application type: 'Desktop app'
    - Name: 'Gmail Skill Desktop' (or anything)
    - Click 'CREATE'
        """)
        
        wait_for_user("Create the OAuth client, then continue.")
        
        # Step 6: Download credentials
        print("\n[6/6] Downloading credentials...")
        page.goto("https://console.cloud.google.com/apis/credentials")
        
        print(f"""
    Download credentials:
    - Find your OAuth 2.0 Client ID in the list
    - Click the download icon (down arrow) on the right
    - Save the file
    
    After download, I'll help you move it to:
    {CREDENTIALS_FILE}
        """)
        
        wait_for_user("Download the credentials JSON file, then continue.")
        
        # Keep browser open for user to finish
        print("\n" + "=" * 60)
        print("Almost done!")
        print("=" * 60)
        
        # Check common download locations
        downloads = Path.home() / "Downloads"
        cred_files = list(downloads.glob("client_secret*.json"))
        
        if cred_files:
            latest = max(cred_files, key=lambda p: p.stat().st_mtime)
            print(f"\nFound credentials file: {latest}")
            move = input("Move this to skill directory? [Y/n]: ").strip().lower()
            if move != 'n':
                import shutil
                shutil.move(str(latest), str(CREDENTIALS_FILE))
                print(f"Moved to: {CREDENTIALS_FILE}")
        else:
            print(f"\nManually move the downloaded file to:")
            print(f"  {CREDENTIALS_FILE}")
        
        browser.close()
    
    # Verify
    if CREDENTIALS_FILE.exists():
        print("\n" + "=" * 60)
        print("SUCCESS! OAuth credentials configured.")
        print("=" * 60)
        print("\nTest with:")
        print(f"  {SKILL_DIR}/.venv/bin/python {SKILL_DIR}/gmail.py read --limit 3")
        print("\n(First run will open browser for OAuth consent)")
    else:
        print("\n" + "=" * 60)
        print("Credentials file not found.")
        print("=" * 60)
        print(f"\nPlease manually save credentials to: {CREDENTIALS_FILE}")


if __name__ == "__main__":
    setup_oauth()
