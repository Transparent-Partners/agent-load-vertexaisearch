#!/usr/bin/env python3
"""
Diagnostic script to test Drive API access and folder permissions.
"""

import sys
from google.auth import default
from googleapiclient.discovery import build
from config import PROJECT_ID, FOLDER_ID, print_status, print_error, print_success

def test_drive_access():
    """Test Drive API access and permissions."""
    print_status("=== Drive API Diagnostic Tool ===\n")
    
    # Initialize credentials
    print_status("Step 1: Loading credentials...")
    try:
        credentials, project = default()
        credentials = credentials.with_quota_project(PROJECT_ID)
        print_success(f"Credentials loaded (Project: {project})")
        print_status(f"Using quota project: {PROJECT_ID}\n")
    except Exception as e:
        print_error(f"Failed to load credentials: {e}")
        return False
    
    # Initialize Drive service
    print_status("Step 2: Initializing Drive API service...")
    try:
        service = build('drive', 'v3', credentials=credentials)
        print_success("Drive API service initialized\n")
    except Exception as e:
        print_error(f"Failed to initialize Drive API: {e}")
        return False
    
    # Test: List accessible files
    print_status("Step 3: Testing general Drive access (list your files)...")
    try:
        results = service.files().list(
            pageSize=5,
            fields="files(id, name, mimeType)"
        ).execute()
        files = results.get('files', [])
        
        if files:
            print_success(f"Drive API is working! Found {len(files)} files:")
            for file in files:
                print_status(f"  - {file['name']} ({file['id']})")
        else:
            print_status("No files found in your Drive (or limited access)")
        print()
    except Exception as e:
        print_error(f"Failed to list files: {e}\n")
        return False
    
    # Test: Access specific folder
    print_status(f"Step 4: Testing access to folder ID: {FOLDER_ID}...")
    try:
        folder = service.files().get(
            fileId=FOLDER_ID,
            fields="id, name, mimeType, capabilities, permissions, owners"
        ).execute()
        
        print_success("✅ Folder is accessible!")
        print_status(f"Folder Name: {folder.get('name')}")
        print_status(f"Folder ID: {folder.get('id')}")
        print_status(f"MIME Type: {folder.get('mimeType')}")
        
        # Check capabilities
        caps = folder.get('capabilities', {})
        print_status(f"\nPermissions:")
        print_status(f"  - Can List Children: {caps.get('canListChildren', False)}")
        print_status(f"  - Can Read: {caps.get('canRead', False)}")
        print_status(f"  - Can Download: {caps.get('canDownload', False)}")
        
        # Check owners
        owners = folder.get('owners', [])
        if owners:
            print_status(f"\nFolder Owners:")
            for owner in owners:
                print_status(f"  - {owner.get('emailAddress', 'Unknown')}")
        
        print()
        
    except Exception as e:
        print_error(f"❌ Cannot access folder: {e}")
        print_error("\nPossible reasons:")
        print_error("1. Folder ID is incorrect")
        print_error("2. Folder is not shared with your account (drankine@transparent.partners)")
        print_error("3. Folder is in a different Google account")
        print_error("4. Folder has been deleted")
        print()
        return False
    
    # Test: List files in folder
    print_status(f"Step 5: Listing files in folder {FOLDER_ID}...")
    try:
        results = service.files().list(
            q=f"'{FOLDER_ID}' in parents and trashed=false",
            pageSize=100,
            fields="files(id, name, mimeType, modifiedTime, size)"
        ).execute()
        
        files = results.get('files', [])
        print_success(f"Found {len(files)} files/folders")
        
        if files:
            print_status("\nFiles in folder:")
            for file in files[:10]:  # Show first 10
                size = file.get('size', 'N/A')
                print_status(f"  - {file['name']} ({file['mimeType']}) - {size} bytes")
            
            if len(files) > 10:
                print_status(f"  ... and {len(files) - 10} more files")
        else:
            print_status("Folder is empty")
        
        print()
        
    except Exception as e:
        print_error(f"Failed to list files in folder: {e}\n")
        return False
    
    print_success("=== All tests passed! ===")
    return True

if __name__ == "__main__":
    success = test_drive_access()
    sys.exit(0 if success else 1)

