# Vertex AI Search Programmatic Setup

This repository contains Python scripts to programmatically set up Vertex AI Search with a Google Drive data source, replacing the need for manual console configuration.

## Overview

The scripts create a complete Vertex AI Search setup:
1. **Data Store** - Container for your searchable content
2. **Search Engine** - The search application with enterprise features and LLM integration
3. **Google Drive Connector** - Automatically syncs documents from a Google Drive folder
4. **Search Testing** - Validates the setup works correctly

## Prerequisites

- Google Cloud Project with Vertex AI Search API enabled
- Google Drive folder with documents you want to search
- Authentication configured (`gcloud auth application-default login`)
- Python 3.8+ environment

## Configuration

### **Option 1: Environment Variables (Recommended)**

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your values:
```bash
VERTEX_AI_PROJECT_ID=your-project-id
DRIVE_FOLDER_ID=your-google-drive-folder-id
DATA_STORE_ID=your-data-store-name
ENGINE_ID=your-engine-name
LOCATION=global
```

The scripts will automatically load these values.

### **Option 2: Direct Configuration**

Edit `config.py` to set your specific values:

```python
PROJECT_ID = "your-project-id"
FOLDER_ID = "your-google-drive-folder-id"  # Works with Shared Drives!
DATA_STORE_ID = "your-data-store-name"
ENGINE_ID = "your-engine-name"
```

**Important Notes:**
- ✅ **Shared Drives Supported**: The folder can be in a Shared/Team Drive
- ✅ **Quota Project**: Script automatically sets quota project for Drive API
- ✅ **GCS Location**: Automatically handles location conversion (global → US)
- ✅ **Environment Variables**: Overrides config.py values if set

## Installation

1. Create and activate virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

**Dependencies installed:**
- `google-cloud-discoveryengine` - Vertex AI Search client
- `google-cloud-storage` - GCS operations
- `google-auth` - Authentication
- `google-api-python-client` - Drive API
- `python-dotenv` - Environment variable support

3. Authenticate with Google Cloud (with proper scopes):
```bash
# Important: Include project and Drive scope
gcloud auth application-default login \
  --project=YOUR_PROJECT_ID \
  --scopes=openid,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/drive.readonly
```

4. Enable required APIs:
```bash
gcloud services enable discoveryengine.googleapis.com --project=YOUR_PROJECT_ID
gcloud services enable drive.googleapis.com --project=YOUR_PROJECT_ID
gcloud services enable storage-api.googleapis.com --project=YOUR_PROJECT_ID
```

## Usage

Run the scripts in order:

### 1. Create Data Store
```bash
python 1_create_data_store.py
```
Creates the data store container. Safe to re-run if already exists.

### 2. Create Search Engine
```bash
python 2_create_engine.py
```
Creates the search application with enterprise features and LLM integration. Safe to re-run if already exists.

### 3. Sync Google Drive Files
```bash
python 3_connect_drive.py
```
Syncs files from your Google Drive folder to GCS, then imports them into Vertex AI Search.

**Features:**
- **Incremental sync**: Only processes new/modified files (default)
- **Deletion handling**: Automatically removes files from GCS/Vertex AI when deleted from Drive
- **Full sync option**: Re-process all files with `--full-sync`

```bash
# Incremental sync (recommended)
python 3_connect_drive.py

# Full sync (re-process everything)
python 3_connect_drive.py --full-sync
```

**How Deletion Works:**
- Script compares current Drive files with sync state
- Files removed from Drive are detected and deleted from GCS
- Vertex AI Search automatically updates its index on next import

### 4. Test Search
```bash
python 4_test_search.py
```
Performs test searches to validate the setup is working correctly.

## Required Permissions

### Google Drive Access

Your Application Default Credentials need access to the Google Drive folder:

1. **Using Service Account** (recommended for production):
   - Create a service account in IAM & Admin
   - Download the key JSON file
   - Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable
   - Share your Drive folder with the service account email (Viewer permission)

2. **Using User Account** (for development):
   - Run `gcloud auth application-default login`
   - Ensure you have access to the Drive folder

### GCS Bucket Permissions

The script will automatically create a GCS bucket named `{PROJECT_ID}-vertex-ai-search-docs` if it doesn't exist. Ensure your credentials have:
- `storage.buckets.create` permission (to create bucket)
- `storage.objects.create` permission (to upload files)

### Discovery Engine Permissions

Ensure you have:
- `discoveryengine.dataStores.get` permission
- `discoveryengine.documents.import` permission

## How GCS Sync Works

Instead of using the undocumented `setUpDataConnector` API, we use a reliable GCS-based approach:

1. **Drive API**: List and download files from your Google Drive folder
2. **Deletion Detection**: Compare current Drive files with sync state to find deleted files
3. **GCS Cleanup**: Remove deleted files from GCS bucket
4. **GCS Upload**: Upload new/modified files to Google Cloud Storage bucket
5. **Import API**: Use the proven ImportDocuments API to import from GCS
6. **Incremental Sync**: Track file modifications to only sync changed files

### Benefits
- ✅ Uses stable, documented APIs
- ✅ Full programmatic control
- ✅ Efficient incremental updates
- ✅ **Automatic deletion handling**
- ✅ Production-ready and scalable
- ✅ Works with all supported file types

### Sync State
The script maintains a `drive_sync_state.json` file that tracks:
- Last sync timestamp
- File IDs and modification times
- GCS paths for each synced file

This enables efficient incremental syncs and deletion detection where only new, modified, or removed files are processed.

## Supported File Types

The sync automatically processes these file types:
- PDF documents (`application/pdf`)
- Plain text files (`text/plain`)
- Microsoft Word documents (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`)
- Microsoft PowerPoint presentations (`application/vnd.openxmlformats-officedocument.presentationml.presentation`)
- Google Docs (`application/vnd.google-apps.document` - exported as PDF)
- Google Slides (`application/vnd.google-apps.presentation` - exported as PDF)
- HTML files (`text/html`)

## Troubleshooting

### Common Issues & Solutions

Based on real-world implementation, here are issues you may encounter and how to resolve them:

#### **Issue 1: "Found 0 files" - Drive API Returns Empty Results**

**Symptoms:**
- Script runs successfully but finds 0 files
- Drive folder definitely contains files
- No error messages, just empty results

**Root Causes & Solutions:**

**A) Quota Project Not Set (Most Common)**
```bash
# Error: "Drive API requires a quota project"
# Solution: Set quota project explicitly
gcloud auth application-default set-quota-project YOUR_PROJECT_ID

# Or re-authenticate with project specified
gcloud auth application-default login --project=YOUR_PROJECT_ID \
  --scopes=openid,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/drive.readonly
```

**B) Shared Drive / Team Drive Not Supported**
```
# Symptom: Folder returns 404 or 0 files, but works in web browser
# Solution: Already fixed in the script with supportsAllDrives=True
# The folder must be in a Shared Drive (check if URL shows team drive structure)
```

**C) Permission/Access Issue**
```
# Ensure the authenticated account has access to the folder
# Check: gcloud auth list
# Make sure that email has Viewer or higher permission on the Drive folder
```

#### **Issue 2: GCS Bucket Creation Fails with "GLOBAL" Location**

**Error:**
```
Project may not create storageClass STANDARD buckets with locationConstraint GLOBAL
```

**Solution:**
Already fixed in the script - it automatically uses "US" multi-region when location is "global". No action needed.

#### **Issue 3: Import Fails with "auto_generate_ids" Error**

**Error:**
```
Field "auto_generate_ids" can only be set when the source is "GcsSource" 
and when the GcsSource.data_schema is `avro`, `custom`, `csv` or `content-with-faq-csv`
```

**Solution:**
Already fixed in the script - uses `auto_generate_ids=False` with `data_schema="content"`. No action needed.

#### **Issue 4: Google Slides/Sheets Download Error**

**Error:**
```
Only files with binary content can be downloaded. Use Export with Docs Editors files.
```

**What This Means:**
- Some Google Workspace files (Slides, Sheets) aren't detected properly by MIME type
- The script tries to download instead of export

**Solution:**
This is expected for certain file types. The script will skip these with an error message but continue syncing other files. If you need these files:
1. Manually export them as PDF from Drive
2. Or update the script to handle more Google Workspace MIME types

#### **Issue 5: Authentication Scopes Insufficient**

**Error:**
```
Request had insufficient authentication scopes
```

**Solution:**
Re-authenticate with proper scopes:
```bash
gcloud auth application-default login \
  --project=YOUR_PROJECT_ID \
  --scopes=openid,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/drive.readonly
```

#### **Issue 6: Drive API Not Enabled**

**Error:**
```
Drive API has not been used in project before or it is disabled
```

**Solution:**
```bash
gcloud services enable drive.googleapis.com --project=YOUR_PROJECT_ID
```

#### **Other Issues**

**"Data store not found"**
- Run `1_create_data_store.py` first

**"Engine not found"**
- Run `2_create_engine.py` after creating the data store

**"No results found" in search**
- Wait for the import to complete (can take several minutes to hours for large datasets)
- Check the Vertex AI Search console for indexing status
- Ensure your Drive folder contains supported file types
- Run the sync script again to check if files were successfully uploaded to GCS
- Check the GCS bucket in the Cloud Console to verify files were uploaded

### Diagnostic Tools

If you encounter issues, use the diagnostic script:

```bash
python diagnose_drive_access.py
```

This will test:
- ✅ Credentials and authentication
- ✅ Drive API access
- ✅ Folder accessibility
- ✅ File listing capabilities

### Monitoring Progress

- **GCS Bucket**: Check Cloud Storage console to verify files uploaded
- **Data Store**: Check in Vertex AI Search → Data Stores
- **Import Status**: Check the "Ingestions" tab in your data store
- **Search Results**: Use `4_test_search.py` to test queries
- **Sync State**: Check `drive_sync_state.json` for incremental sync tracking

### Console Access

You can monitor everything in the Google Cloud Console:
- **GCS Bucket**: Cloud Storage → Buckets → `{project-id}-vertex-ai-search-docs`
- **Data Store**: Vertex AI Search → Data Stores → `chr_project_agent_v2`
- **Ingestions**: Check the "Ingestions" tab for import history
- **Search Testing**: Use the "Search" tab to test queries manually

## Script Details

### Idempotent Design
All scripts are safe to re-run. They check if resources already exist before creating them.

### Error Handling
Each script includes comprehensive error handling and status reporting.

### Configuration
Centralized configuration in `config.py` makes it easy to customize for different projects.

## Lessons Learned & Key Fixes

This implementation went through several iterations to solve real-world issues:

### 1. **Shared Drive Support**
- **Problem**: Regular Drive API calls returned 0 files for Shared Drive folders
- **Solution**: Added `supportsAllDrives=True` and `includeItemsFromAllDrives=True` parameters

### 2. **Quota Project Configuration**
- **Problem**: Drive API requires explicit quota project with Application Default Credentials
- **Solution**: Script sets quota project using `credentials.with_quota_project(PROJECT_ID)`
- **User Action**: Re-authenticate with `--project` flag

### 3. **GCS Location Constraints**
- **Problem**: Can't create GCS buckets with "global" location
- **Solution**: Script automatically converts "global" to "US" multi-region

### 4. **Import Configuration**
- **Problem**: `auto_generate_ids=True` incompatible with `data_schema="content"`
- **Solution**: Use `auto_generate_ids=False` for content schema

### 5. **The Original Problem**
- **Initial Issue**: `setUpDataConnector` API endpoint returned 404
- **Root Cause**: API method doesn't exist or is not publicly available
- **Solution**: Implemented GCS-based sync (Drive → GCS → Vertex AI Search)

## Logging

The scripts use Python's logging module for better observability.

### **Log Levels**
- `INFO` - Normal operations and status messages
- `ERROR` - Errors and failures
- `SUCCESS` - Successful completions (INFO level with ✓ prefix)

### **Log Output**
By default, logs output to console. You can optionally enable file logging:

```python
# In your scripts, before calling functions
from config import setup_logging
setup_logging(log_file='vertex_ai_search.log')
```

Or set in `.env`:
```bash
LOG_FILE=vertex_ai_search.log
LOG_LEVEL=INFO
```

---

## Integration with Other Applications

For teams integrating with this Vertex AI Search instance, see **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** which includes:

- Required IDs and configuration
- Python, JavaScript, and REST API examples
- IAM permission setup
- Quick reference card
- Best practices

**Quick Reference:**
```python
# Serving Config (what you need to search)
serving_config = "projects/transparent-agent-dev/locations/global/collections/default_collection/engines/chr_project_agent_app_v2/servingConfigs/default_config"
```

---

## Next Steps

After successful setup:
1. Monitor the sync progress in the console
2. Test different search queries with `4_test_search.py`
3. Check the GCS bucket to see uploaded files
4. View indexing progress in Vertex AI Search console
5. **Integrate search into your applications** (see [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md))
6. Run incremental syncs regularly to keep data up-to-date
7. Consider scheduling automated syncs (cron job or Cloud Scheduler)

## Project Structure

```
agent-load-vertexaisearch/
├── config.py                    # Configuration with env var support
├── 1_create_data_store.py      # Data store creation
├── 2_create_engine.py          # Search engine creation
├── 3_connect_drive.py          # Drive → GCS → Vertex AI sync
├── 4_test_search.py            # Search testing tool
├── diagnose_drive_access.py    # Diagnostic tool
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
├── .gitignore                  # Git ignore rules
├── README.md                   # This file
├── INTEGRATION_GUIDE.md        # External integration documentation
└── FINAL_SUMMARY.md           # Complete project summary
```

## API Integration

For detailed integration instructions, see **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)**.

Quick example:

```python
from google.cloud import discoveryengine_v1 as discoveryengine

client = discoveryengine.SearchServiceClient()
serving_config = "projects/transparent-agent-dev/locations/global/collections/default_collection/engines/chr_project_agent_app_v2/servingConfigs/default_config"

request = discoveryengine.SearchRequest(
    serving_config=serving_config,
    query="your search query"
)

response = client.search(request=request)
```
