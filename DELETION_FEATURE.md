# Automatic Deletion Feature

## Overview

The sync script (`3_connect_drive.py`) now automatically detects and handles file deletions from Google Drive. When you remove a file from your Google Drive folder, the next sync will:

1. **Detect** the deletion by comparing Drive files with the sync state
2. **Delete** the file from the GCS bucket
3. **Update** the sync state to remove the deleted file entry
4. **Trigger** a Vertex AI Search import to update the search index

## How It Works

### Detection Logic

```python
def sync_deletions_from_gcs(bucket, sync_state, current_drive_file_ids):
    """Remove files from GCS that no longer exist in Google Drive."""
    
    # Get files that are in sync state but not in current Drive listing
    synced_file_ids = set(sync_state['files'].keys())
    deleted_file_ids = synced_file_ids - current_drive_file_ids
    
    # Delete each file from GCS and update sync state
    for file_id in deleted_file_ids:
        # ... deletion logic ...
```

### Workflow

1. **List Current Drive Files**: Script queries the Drive API for all files in the folder
2. **Compare with Sync State**: Identifies files that were previously synced but no longer exist
3. **Delete from GCS**: Removes the file blobs from the Cloud Storage bucket
4. **Update Sync State**: Removes entries from `drive_sync_state.json`
5. **Import to Vertex AI**: Triggers a new import which updates the search index

## Example Usage

### Scenario: Removing a File

```bash
# Initial state: 17 files in Drive, all synced

# You delete "old_document.pdf" from Google Drive

# Run sync
$ python 3_connect_drive.py

# Output:
# [INFO] Starting file sync from Drive to GCS...
# [INFO] Found 16 files/folders in Drive
# [INFO] Checking for deleted files...
# [INFO] Found 1 files to delete from GCS
# [INFO] Deleted from GCS: old_document.pdf
# [INFO] ✓ Deleted 1 files from GCS
# [INFO] ✓ Sync complete: 0 synced, 16 skipped, 1 deleted, 0 errors
# [INFO] Importing documents from GCS to Vertex AI Search...
# [INFO] ✓ Import operation started successfully
```

### Scenario: Adding and Deleting Files

```bash
# You delete "report_q1.pdf" and add "report_q2.pdf" to Drive

$ python 3_connect_drive.py

# Output:
# [INFO] Found 1 files to delete from GCS
# [INFO] Deleted from GCS: report_q1.pdf
# [INFO] ✓ Deleted 1 files from GCS
# [INFO] New file: report_q2.pdf
# [INFO] Downloading: report_q2.pdf
# [INFO] Uploading to GCS: report_q2.pdf
# [INFO] ✓ Sync complete: 1 synced, 16 skipped, 1 deleted, 0 errors
```

## What Gets Deleted

✅ **Automatically Deleted:**
- Files removed from the Google Drive folder
- Files that existed in a previous sync but are now missing
- Both regular files and exported Google Workspace files (Docs, Slides)

❌ **Not Deleted:**
- Files that were never synced (not in `drive_sync_state.json`)
- Files in GCS from other sources
- Folders (handled separately in Drive traversal)

## Sync State Management

The `drive_sync_state.json` file tracks:

```json
{
  "last_sync": "2024-10-28T12:30:00.123456+00:00",
  "files": {
    "1abc123...": {
      "name": "document.pdf",
      "modified": "2024-10-27T10:15:00.000Z",
      "gcs_path": "gs://bucket-name/document.pdf",
      "mime_type": "application/pdf"
    }
  }
}
```

When a file is deleted from Drive, its entry is removed from the `files` dictionary.

## Vertex AI Search Index Updates

After files are deleted from GCS, the import operation ensures Vertex AI Search updates its index:

- **Reconciliation Mode**: Set to `INCREMENTAL`
- **Auto-generate IDs**: Disabled (uses GCS paths as IDs)
- **Effect**: Files deleted from GCS are removed from the search index

### Note on Index Updates

Vertex AI Search may take a few minutes to fully update the index after an import. During this time:
- Deleted files may still appear in search results briefly
- New files may not be immediately searchable
- Check the Google Cloud Console for import operation status

## Troubleshooting

### Deletion Not Working

**Problem**: Files deleted from Drive still appear in search results

**Solutions**:
1. Check sync state file contains the deleted file
2. Verify the sync ran without errors
3. Check GCS bucket to confirm file was deleted
4. Wait a few minutes for Vertex AI index to update
5. Check import operation status in Cloud Console

### Accidental Deletion

**Problem**: Accidentally deleted file from Drive, need to restore

**Solutions**:
1. Restore the file in Google Drive (use Drive trash/bin)
2. Run sync again: `python 3_connect_drive.py`
3. File will be re-uploaded to GCS and re-indexed

### Sync State Corruption

**Problem**: Sync state is out of sync with actual files

**Solution**: Run a full sync to rebuild state
```bash
python 3_connect_drive.py --full-sync
```

This will:
- Re-scan all Drive files
- Re-upload all files to GCS (overwriting existing)
- Rebuild the sync state from scratch
- NOT delete files (only processes what exists in Drive)

## Performance Considerations

### Large Number of Deletions

If you delete many files at once:
- Each file is deleted individually from GCS
- Sync state is updated for each deletion
- One import operation handles all changes
- Performance scales linearly with number of deletions

### Best Practices

1. **Regular Syncs**: Run sync regularly to keep deletions small and manageable
2. **Batch Deletions**: If deleting many files, consider running sync after all deletions are complete
3. **Monitor Logs**: Check sync output to verify deletions are detected
4. **Backup Sync State**: Keep backups of `drive_sync_state.json` if needed

## Integration with CI/CD

You can automate syncs with deletion handling:

```bash
#!/bin/bash
# sync_drive.sh

cd /path/to/project
source venv/bin/activate

# Run sync (handles additions, modifications, deletions)
python 3_connect_drive.py

# Check exit code
if [ $? -eq 0 ]; then
    echo "Sync completed successfully"
else
    echo "Sync failed"
    exit 1
fi
```

### Cron Example

```cron
# Sync every 6 hours
0 */6 * * * /path/to/sync_drive.sh >> /var/log/drive_sync.log 2>&1
```

## Security Considerations

### Permissions Required

To delete files from GCS, your credentials need:
- `storage.objects.delete` permission on the GCS bucket
- `storage.objects.list` permission to verify deletions

### Audit Trail

All deletions are logged:
- Console output shows each deleted file
- GCS bucket versioning (if enabled) preserves deleted files
- Vertex AI Search import operations are logged in Cloud Logging

## Summary

The automatic deletion feature ensures your Vertex AI Search index stays in sync with your Google Drive folder:

✅ **Adds** new files to the index  
✅ **Updates** modified files in the index  
✅ **Removes** deleted files from the index  

All automatically, with no manual intervention required!

