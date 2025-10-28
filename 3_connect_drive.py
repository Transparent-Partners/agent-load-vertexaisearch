#!/usr/bin/env python3
"""
Connect Google Drive folder to Vertex AI Search via GCS.
This script syncs files from a Google Drive folder to GCS, then imports them
into Vertex AI Search. Supports incremental sync (only processes new/modified files).
"""

import sys
import json
import os
import argparse
from datetime import datetime, timezone
from io import BytesIO
from google.cloud import storage
from google.cloud import discoveryengine_v1 as discoveryengine
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth import default
from config import (
    PROJECT_ID, LOCATION, DATA_STORE_ID, FOLDER_ID,
    GCS_BUCKET_NAME, SYNC_STATE_FILE,
    get_data_store_client, get_branch_path,
    print_status, print_error, print_success
)

# Supported MIME types for Vertex AI Search
SUPPORTED_MIME_TYPES = [
    'application/pdf',
    'text/plain',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.google-apps.document',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.google-apps.presentation',
    'text/html',
]

def load_sync_state():
    """Load the sync state from file."""
    if os.path.exists(SYNC_STATE_FILE):
        try:
            with open(SYNC_STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print_error(f"Error loading sync state: {e}")
            return {"last_sync": None, "files": {}}
    return {"last_sync": None, "files": {}}

def save_sync_state(state):
    """Save the sync state to file."""
    try:
        with open(SYNC_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        print_status(f"Sync state saved to {SYNC_STATE_FILE}")
    except Exception as e:
        print_error(f"Error saving sync state: {e}")

def initialize_gcs_bucket():
    """Initialize GCS bucket, create if doesn't exist."""
    print_status(f"Initializing GCS bucket: {GCS_BUCKET_NAME}")
    storage_client = storage.Client(project=PROJECT_ID)
    
    try:
        bucket = storage_client.get_bucket(GCS_BUCKET_NAME)
        print_status(f"GCS bucket '{GCS_BUCKET_NAME}' already exists")
        return bucket
    except Exception:
        print_status(f"Creating GCS bucket '{GCS_BUCKET_NAME}'...")
        try:
            # Use US multi-region instead of global
            gcs_location = "US" if LOCATION == "global" else LOCATION
            bucket = storage_client.create_bucket(GCS_BUCKET_NAME, location=gcs_location)
            print_success(f"GCS bucket created: {GCS_BUCKET_NAME} in {gcs_location}")
            return bucket
        except Exception as e:
            print_error(f"Failed to create GCS bucket: {e}")
            sys.exit(1)

def initialize_drive_service():
    """Initialize Google Drive API service."""
    print_status("Initializing Google Drive API...")
    try:
        credentials, _ = default()
        # Set quota project to ensure Drive API works with ADC
        credentials = credentials.with_quota_project(PROJECT_ID)
        service = build('drive', 'v3', credentials=credentials)
        print_success("Drive API initialized")
        return service
    except Exception as e:
        print_error(f"Failed to initialize Drive API: {e}")
        print_error("Make sure the Drive API is enabled in your project")
        sys.exit(1)

def list_drive_files(drive_service, folder_id, page_token=None):
    """List all files in a Google Drive folder recursively."""
    print_status(f"Listing files in Drive folder: {folder_id}")
    
    all_files = []
    query = f"'{folder_id}' in parents and trashed=false"
    
    try:
        while True:
            response = drive_service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name, mimeType, modifiedTime, size)',
                pageToken=page_token,
                supportsAllDrives=True,  # Support Shared Drives
                includeItemsFromAllDrives=True  # Include Shared Drive items
            ).execute()
            
            files = response.get('files', [])
            all_files.extend(files)
            
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        
        print_status(f"Found {len(all_files)} files/folders in Drive")
        return all_files
        
    except Exception as e:
        print_error(f"Error listing Drive files: {e}")
        sys.exit(1)

def is_file_supported(mime_type):
    """Check if file type is supported by Vertex AI Search."""
    # Google Docs will be exported as PDF
    if mime_type.startswith('application/vnd.google-apps'):
        return True
    return mime_type in SUPPORTED_MIME_TYPES

def download_drive_file(drive_service, file_id, mime_type):
    """Download a file from Google Drive."""
    try:
        # Export Google Docs as PDF
        if mime_type == 'application/vnd.google-apps.document':
            request = drive_service.files().export_media(
                fileId=file_id,
                mimeType='application/pdf'
            )
        elif mime_type == 'application/vnd.google-apps.presentation':
            request = drive_service.files().export_media(
                fileId=file_id,
                mimeType='application/pdf'
            )
        else:
            request = drive_service.files().get_media(
                fileId=file_id,
                supportsAllDrives=True  # Support Shared Drives
            )
        
        file_buffer = BytesIO()
        downloader = MediaIoBaseDownload(file_buffer, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        file_buffer.seek(0)
        return file_buffer
        
    except Exception as e:
        print_error(f"Error downloading file {file_id}: {e}")
        return None

def upload_to_gcs(bucket, file_buffer, gcs_path, mime_type):
    """Upload a file to GCS."""
    try:
        # Adjust mime type for exported Google Docs
        if mime_type.startswith('application/vnd.google-apps'):
            mime_type = 'application/pdf'
            if not gcs_path.endswith('.pdf'):
                gcs_path = gcs_path + '.pdf'
        
        blob = bucket.blob(gcs_path)
        blob.upload_from_file(file_buffer, content_type=mime_type)
        print_status(f"Uploaded to GCS: gs://{bucket.name}/{gcs_path}")
        return f"gs://{bucket.name}/{gcs_path}"
        
    except Exception as e:
        print_error(f"Error uploading to GCS: {e}")
        return None

def sync_deletions_from_gcs(bucket, sync_state, current_drive_file_ids):
    """Remove files from GCS that no longer exist in Google Drive."""
    print_status("Checking for deleted files...")
    
    # Get files that are in sync state but not in current Drive listing
    synced_file_ids = set(sync_state['files'].keys())
    deleted_file_ids = synced_file_ids - current_drive_file_ids
    
    deleted_count = 0
    cleaned_count = 0  # Files removed from sync state but already deleted from GCS
    
    if deleted_file_ids:
        print_status(f"Found {len(deleted_file_ids)} files to delete from GCS")
        
        for file_id in deleted_file_ids:
            file_info = sync_state['files'][file_id]
            file_name = file_info['name']
            gcs_path = file_info['gcs_path']
            
            try:
                # Extract blob name from GCS URI
                # Format: gs://bucket-name/blob-name
                blob_name = gcs_path.split(f"gs://{bucket.name}/")[1]
                
                # Delete from GCS
                blob = bucket.blob(blob_name)
                if blob.exists():
                    blob.delete()
                    print_status(f"Deleted from GCS: {file_name}")
                    deleted_count += 1
                else:
                    # File already deleted from GCS, just clean up sync state
                    print_status(f"Cleaning sync state for already-deleted file: {file_name}")
                    cleaned_count += 1
                
                # Remove from sync state regardless
                del sync_state['files'][file_id]
                
            except Exception as e:
                print_error(f"Error deleting {file_name} from GCS: {e}")
        
        if deleted_count > 0:
            print_success(f"Deleted {deleted_count} files from GCS")
        if cleaned_count > 0:
            print_success(f"Cleaned {cleaned_count} orphaned entries from sync state")
    else:
        print_status("No deleted files found")
    
    return deleted_count + cleaned_count  # Return total changes made

def sync_files_to_gcs(drive_service, bucket, folder_id, sync_state, full_sync=False):
    """Sync files from Drive to GCS (incremental or full)."""
    print_status("Starting file sync from Drive to GCS...")
    
    # List all files in Drive
    drive_files = list_drive_files(drive_service, folder_id)
    
    # Track current Drive file IDs for deletion detection
    current_drive_file_ids = {f['id'] for f in drive_files if f['mimeType'] != 'application/vnd.google-apps.folder'}
    
    # Handle deletions first
    deleted_count = sync_deletions_from_gcs(bucket, sync_state, current_drive_file_ids)
    
    synced_count = 0
    skipped_count = 0
    error_count = 0
    
    for file in drive_files:
        file_id = file['id']
        file_name = file['name']
        mime_type = file['mimeType']
        modified_time = file['modifiedTime']
        
        # Skip folders
        if mime_type == 'application/vnd.google-apps.folder':
            continue
        
        # Skip unsupported file types
        if not is_file_supported(mime_type):
            print_status(f"Skipping unsupported file type: {file_name} ({mime_type})")
            skipped_count += 1
            continue
        
        # Check if file needs to be synced
        if not full_sync and file_id in sync_state['files']:
            if sync_state['files'][file_id]['modified'] == modified_time:
                print_status(f"Skipping unchanged file: {file_name}")
                skipped_count += 1
                continue
        
        # Download from Drive
        print_status(f"Syncing: {file_name}")
        file_buffer = download_drive_file(drive_service, file_id, mime_type)
        
        if file_buffer is None:
            error_count += 1
            continue
        
        # Upload to GCS
        gcs_path = file_name
        gcs_uri = upload_to_gcs(bucket, file_buffer, gcs_path, mime_type)
        
        if gcs_uri:
            # Update sync state
            sync_state['files'][file_id] = {
                'name': file_name,
                'modified': modified_time,
                'gcs_path': gcs_uri,
                'mime_type': mime_type
            }
            synced_count += 1
        else:
            error_count += 1
    
    print_success(f"Sync complete: {synced_count} synced, {skipped_count} skipped, {deleted_count} deleted, {error_count} errors")
    return synced_count, deleted_count

def import_from_gcs_to_vertex_ai(bucket):
    """Import documents from GCS to Vertex AI Search."""
    print_status("Importing documents from GCS to Vertex AI Search...")
    
    # Check if data store exists
    try:
        ds_client = get_data_store_client()
        from config import get_data_store_path
        ds_client.get_data_store(name=get_data_store_path())
    except Exception as e:
        print_error(f"Data store not found: {e}")
        print_error("Please run 1_create_data_store.py first")
        sys.exit(1)
    
    # Initialize document client
    doc_client = discoveryengine.DocumentServiceClient()
    
    # Get branch path
    branch_path = get_branch_path()
    
    # Create import request
    gcs_uri = f"gs://{bucket.name}/*"
    
    request = discoveryengine.ImportDocumentsRequest(
        parent=branch_path,
        reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
        auto_generate_ids=False,  # Can't use with content schema
        gcs_source=discoveryengine.GcsSource(
            input_uris=[gcs_uri],
            data_schema="content"
        )
    )
    
    try:
        print_status(f"Starting import from {gcs_uri}...")
        operation = doc_client.import_documents(request=request)
        
        print_status(f"Import operation started: {operation.operation.name}")
        print_status("Waiting for import to complete (this may take several minutes)...")
        
        # Wait for operation to complete
        result = operation.result(timeout=600)  # 10 minute timeout
        
        print_success("Import completed successfully!")
        print_status(f"Import result: {result}")
        
        return True
        
    except Exception as e:
        print_error(f"Import failed: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Sync Google Drive files to Vertex AI Search via GCS'
    )
    parser.add_argument(
        '--full-sync',
        action='store_true',
        help='Perform full sync (re-sync all files, ignoring sync state)'
    )
    args = parser.parse_args()
    
    print_status("Starting Google Drive to Vertex AI Search sync...")
    print_status(f"Project: {PROJECT_ID}")
    print_status(f"Location: {LOCATION}")
    print_status(f"Data Store: {DATA_STORE_ID}")
    print_status(f"Drive Folder ID: {FOLDER_ID}")
    print_status(f"GCS Bucket: {GCS_BUCKET_NAME}")
    print_status(f"Sync Mode: {'FULL' if args.full_sync else 'INCREMENTAL'}")
    
    try:
        # Load sync state
        sync_state = load_sync_state()
        if args.full_sync:
            print_status("Full sync requested - resetting sync state")
            sync_state = {"last_sync": None, "files": {}}
        
        # Initialize GCS bucket
        bucket = initialize_gcs_bucket()
        
        # Initialize Drive service
        drive_service = initialize_drive_service()
        
        # Sync files from Drive to GCS
        synced_count, deleted_count = sync_files_to_gcs(
            drive_service,
            bucket,
            FOLDER_ID,
            sync_state,
            full_sync=args.full_sync
        )
        
        if synced_count > 0 or deleted_count > 0:
            # Update and save sync state after successful GCS operations
            sync_state['last_sync'] = datetime.now(timezone.utc).isoformat()
            save_sync_state(sync_state)
            print_status("Sync state saved")
            
            # Import from GCS to Vertex AI Search
            import_success = import_from_gcs_to_vertex_ai(bucket)
            
            if import_success:
                print_success("Drive sync completed successfully!")
                print_status("Documents are now being indexed in Vertex AI Search")
                print_status("Check the console for indexing progress")
            else:
                print_error("Import to Vertex AI Search failed")
                print_error("Note: GCS sync was successful and state was saved")
                sys.exit(1)
        else:
            print_status("No new files to sync and no deletions detected")
            print_success("Drive sync completed - all files are up to date")
        
    except KeyboardInterrupt:
        print_error("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
