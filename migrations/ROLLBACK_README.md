# Database Rollback Guide

This directory contains rollback scripts to undo all recent database changes made to the crawl jobs system.

## Overview

The following database changes have been made recently and can be rolled back:

1. **Timestamped Runs Support** - Added fields for run tracking and enhanced multi-viewport support
2. **Paused Status** - Added 'paused' status to crawl_jobs ENUM
3. **Screenshot Fields** - Added basic screenshot path fields
4. **Multi-Viewport Fields** - Added desktop/tablet/mobile screenshot and diff fields
5. **Job Type Field** - Added job_type field to crawl_jobs table
6. **Diff Fields** - Added visual diff related fields
7. **Capture and Diff Complete Status** - Added 'capture_and_diff_complete' to project_pages ENUM

## Rollback Scripts

### Individual Rollback Scripts

Each migration has its own rollback script:

- `rollback_timestamped_runs.py` - Removes timestamped run support fields
- `rollback_paused_status.py` - Removes 'paused' status from crawl_jobs
- `rollback_screenshot_fields.py` - Removes basic screenshot fields
- `rollback_multi_viewport_fields.py` - Removes multi-viewport fields
- `rollback_job_type_field.py` - Removes job_type field from crawl_jobs
- `rollback_diff_fields.py` - Removes diff-related fields
- `rollback_capture_and_diff_complete_status.py` - Removes 'capture_and_diff_complete' status

### Master Rollback Script

- `master_rollback_all_changes.py` - Executes all rollback scripts in the correct order

## Usage

### Option 1: Complete Rollback (Recommended)

To undo ALL recent changes at once:

```bash
cd ui-regression-platform/migrations
python master_rollback_all_changes.py
```

### Option 2: Individual Rollbacks

To undo specific changes only:

```bash
cd ui-regression-platform/migrations

# Example: Only rollback job_type field
python rollback_job_type_field.py

# Example: Only rollback multi-viewport fields
python rollback_multi_viewport_fields.py
```

## Rollback Order

If running individual scripts, execute them in this order:

1. `rollback_timestamped_runs.py`
2. `rollback_paused_status.py`
3. `rollback_screenshot_fields.py`
4. `rollback_multi_viewport_fields.py`
5. `rollback_job_type_field.py`
6. `rollback_diff_fields.py`
7. `rollback_capture_and_diff_complete_status.py`

## What Gets Rolled Back

### Tables Affected

- **crawl_jobs table:**
  - Removes `job_type` column
  - Removes 'paused' from status ENUM

- **project_pages table:**
  - Removes all screenshot-related columns
  - Removes all diff-related columns
  - Removes all multi-viewport columns
  - Removes all timestamped run columns
  - Reverts status ENUM to basic values

### Data Handling

- Any records with 'paused' status will be changed to 'pending'
- Any records with 'capture_and_diff_complete' status will be changed to 'diff_generated'
- All other data in removed columns will be lost

## Prerequisites

- MySQL database connection configured in `.env` file
- Python environment with required dependencies
- Database backup (recommended before running rollbacks)

## Environment Variables

Ensure these are set in your `.env` file:

```
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_NAME=ui_diff_dashboard
```

## Safety Features

- Each script checks if columns/values exist before attempting to remove them
- Scripts will skip operations if nothing needs to be rolled back
- Detailed logging shows what changes are being made
- Backup information file is created after successful rollback

## Recovery

If you need to re-apply the changes after rollback:

1. Run the original migration files in reverse order:
   - `add_capture_and_diff_complete_status.py`
   - `add_diff_fields.py`
   - `add_job_type_field_mysql.py`
   - `add_multi_viewport_fields_mysql.py`
   - `add_screenshot_fields.py`
   - `add_paused_status.py`
   - `add_timestamped_runs.py`

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure your database user has ALTER privileges
2. **Connection Errors**: Check your `.env` file database configuration
3. **Column Not Found**: This is normal if the column was already removed
4. **Foreign Key Constraints**: Some rollbacks may fail if there are foreign key dependencies

### Manual Cleanup

If automated rollback fails, you can manually run these SQL commands:

```sql
-- Remove columns from project_pages
ALTER TABLE project_pages DROP COLUMN IF EXISTS current_run_id;
ALTER TABLE project_pages DROP COLUMN IF EXISTS baseline_run_id;
-- ... (add other columns as needed)

-- Remove job_type from crawl_jobs
ALTER TABLE crawl_jobs DROP COLUMN IF EXISTS job_type;

-- Revert ENUM values
ALTER TABLE crawl_jobs MODIFY COLUMN status ENUM('pending', 'running', 'completed', 'failed') NOT NULL DEFAULT 'pending';
ALTER TABLE project_pages MODIFY COLUMN status ENUM('pending', 'crawled', 'ready_for_diff') NOT NULL DEFAULT 'pending';
```

## Verification

After rollback, verify the changes:

```sql
-- Check crawl_jobs table structure
DESCRIBE crawl_jobs;

-- Check project_pages table structure  
DESCRIBE project_pages;

-- Verify ENUM values
SHOW COLUMNS FROM crawl_jobs LIKE 'status';
SHOW COLUMNS FROM project_pages LIKE 'status';
```

## Support

If you encounter issues with the rollback process:

1. Check the error messages in the console output
2. Verify your database connection and permissions
3. Review the `rollback_info.txt` file created after successful rollback
4. Consider running individual rollback scripts to isolate issues