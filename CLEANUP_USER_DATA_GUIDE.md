# User Data Cleanup Script Guide

This guide explains how to use the `cleanup_user_data.py` script to delete all test data for a specific user while preserving the user account.

## What Gets Deleted

The script removes ALL data associated with a user:

### Database Records
- **Projects**: All projects owned by the user
- **Project Pages**: All pages associated with those projects  
- **Crawl Jobs**: All crawl jobs for those projects

### File System Data
- **Screenshots**: All screenshot files in `screenshots/{project_id}/` directories
- **Diffs**: All diff images in `diffs/{project_id}/` directories
- **Runs**: All run data in `runs/{project_id}/` directories
- **Test Screenshots**: All test files in `test_screenshots/{project_id}/` directories

### What Gets Preserved
- **User Account**: Username, password, and login credentials remain intact
- **Other Users' Data**: Only the specified user's data is affected

## Usage

### Basic Usage

```bash
# Clean up by username
python cleanup_user_data.py --username demo

# Clean up by user ID
python cleanup_user_data.py --user-id 1
```

### Dry Run (Recommended First)

Always run a dry run first to see what would be deleted:

```bash
# See what would be deleted without actually deleting
python cleanup_user_data.py --username demo --dry-run
```

### Skip Confirmation

For automated scripts, you can skip the confirmation prompt:

```bash
# Skip confirmation (use with caution!)
python cleanup_user_data.py --username demo --confirm
```

## Examples

### 1. Safe Testing - Dry Run First

```bash
# Step 1: See what would be deleted
python cleanup_user_data.py --username demo --dry-run

# Step 2: If satisfied, run actual cleanup
python cleanup_user_data.py --username demo
```

### 2. Quick Cleanup with Confirmation

```bash
# Direct cleanup (will prompt for confirmation)
python cleanup_user_data.py --username demo
```

### 3. Automated Cleanup

```bash
# For scripts - no prompts
python cleanup_user_data.py --username demo --confirm
```

## Sample Output

### Dry Run Output
```
DRY RUN: Starting cleanup for user: demo (ID: 1)
Created: 2025-08-18 10:30:45
------------------------------------------------------------
DRY RUN MODE - No actual deletions will be performed
Would delete 5 projects:
  - Ecommerce Web (ID: 72)
  - WL (ID: 73)
  - Havis (ID: 74)
  - Collage1 (ID: 75)
  - Continental (ID: 76)
Would delete 66 project pages
Would delete 15 crawl jobs
Would delete 180 files from screenshots/72
Would delete 95 files from screenshots/73
...
```

### Actual Cleanup Output
```
Starting cleanup for user: demo (ID: 1)
Created: 2025-08-18 10:30:45
------------------------------------------------------------
Found 5 projects for user 'demo'

Phase 1: Database cleanup
Deleting 15 crawl jobs...
Deleting 66 project pages...
Deleting 5 projects...
Database cleanup completed successfully!

Phase 2: File system cleanup
Cleaning up screenshots directory...
  Deleting project 72 directory: screenshots/72
    Contains 36 files and 12 subdirectories
  Deleting project 73 directory: screenshots/73
    Contains 19 files and 6 subdirectories
...
File system cleanup completed!
  Total files deleted: 275
  Total directories deleted: 45

============================================================
CLEANUP SUMMARY
============================================================
User: demo
User ID: 1
Cleanup time: 2025-08-18T15:25:30.123456

Database cleanup:
  Projects deleted: 5
  Pages deleted: 66
  Jobs deleted: 15

File system cleanup:
  Files deleted: 275
  Directories deleted: 45

No errors encountered!

User account preserved - login credentials remain intact.
```

## Safety Features

### 1. Confirmation Prompt
The script asks for confirmation before deleting data:
```
WARNING: This will permanently delete ALL data for this user!
Are you sure you want to delete all data for user 'demo'? (yes/no):
```

### 2. Dry Run Mode
Use `--dry-run` to see what would be deleted without making changes.

### 3. Error Handling
The script handles errors gracefully and reports what went wrong.

### 4. User Preservation
The user account is never deleted - only their data.

## Troubleshooting

### User Not Found
```
ERROR: User with username 'nonexistent' not found
```
**Solution**: Check the username spelling or use `--user-id` instead.

### Database Connection Issues
```
ERROR: Database cleanup failed: (pymysql.err.OperationalError) ...
```
**Solution**: Check your database connection settings in `.env` file.

### Permission Issues
```
ERROR: Failed to delete screenshots/72: [Errno 13] Permission denied
```
**Solution**: Run the script with appropriate permissions or check file ownership.

### Partial Cleanup
If the script fails partway through, you can safely run it again. It will only delete what still exists.

## Best Practices

1. **Always run dry-run first**: `--dry-run` shows you exactly what will be deleted
2. **Backup important data**: Although this is for test data, consider backups for production
3. **Check user activity**: Make sure the user isn't currently running jobs
4. **Run during maintenance**: Best to run when the application isn't heavily used
5. **Monitor disk space**: Large cleanups can free significant disk space

## Integration with Development Workflow

### After Testing
```bash
# Clean up test data after development/testing
python cleanup_user_data.py --username testuser --confirm
```

### Before Demo
```bash
# Clean slate for demonstrations
python cleanup_user_data.py --username demo --dry-run
python cleanup_user_data.py --username demo
```

### Automated Testing
```bash
# In CI/CD pipelines
python cleanup_user_data.py --username ci_test_user --confirm
```

## Notes

- The script preserves the user account, so they can immediately start creating new projects
- All foreign key constraints are handled properly (jobs deleted before pages, pages before projects)
- File system cleanup is thorough and removes empty directories
- The script is idempotent - running it multiple times is safe
- Database transactions ensure consistency (rollback on errors)