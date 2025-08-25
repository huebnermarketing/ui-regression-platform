# UI Regression Platform - Database Structure

## Overview
The UI Regression Platform uses a relational database with three main tables:
1. `users` - For user authentication and management
2. `projects` - For storing project configurations
3. `project_pages` - For tracking individual pages within projects
4. `crawl_jobs` - For tracking crawling and diff jobs

## Table: users
Stores user account information for authentication.

### Columns:
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique user identifier |
| username | String(80) | Unique, Not Null | User's username |
| password_hash | String(255) | Not Null | Hashed password |
| created_at | DateTime | Default: Current UTC time | Account creation timestamp |

## Table: projects
Stores project configurations including URLs and user associations.

### Columns:
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique project identifier |
| name | String(255) | Not Null | Project name |
| staging_url | Text | Not Null | Staging environment URL |
| production_url | Text | Not Null | Production environment URL |
| user_id | Integer | Foreign Key (users.id), Not Null | Owner of the project |
| created_at | DateTime | Default: Current UTC time | Project creation timestamp |
| is_page_restricted | Boolean | Default: False, Not Null | Flag for page restriction mode |

### Relationships:
- One-to-Many with `users` (one user can have many projects)
- One-to-Many with `project_pages` (one project can have many pages)
- One-to-Many with `crawl_jobs` (one project can have many jobs)

## Table: project_pages
Stores information about individual pages within projects, including screenshot and diff data.

### Columns:
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique page identifier |
| project_id | Integer | Foreign Key (projects.id), Not Null | Associated project |
| path | String(767) | Not Null | Page path/URL |
| page_name | String(500) | Nullable | Page title/name |
| staging_url | Text | Not Null | Full staging URL for page |
| production_url | Text | Not Null | Full production URL for page |
| status | Enum | Default: 'pending', Not Null | Page processing status |
| created_at | DateTime | Default: Current UTC time | Page creation timestamp |
| last_crawled | DateTime | Nullable | Last crawl timestamp |
| staging_screenshot_path | Text | Nullable | Legacy staging screenshot path |
| production_screenshot_path | Text | Nullable | Legacy production screenshot path |

### Multi-viewport Screenshot Paths:
| Column | Type | Description |
|--------|------|-------------|
| staging_screenshot_path_desktop | Text | Desktop staging screenshot path |
| staging_screenshot_path_tablet | Text | Tablet staging screenshot path |
| staging_screenshot_path_mobile | Text | Mobile staging screenshot path |
| production_screenshot_path_desktop | Text | Desktop production screenshot path |
| production_screenshot_path_tablet | Text | Tablet production screenshot path |
| production_screenshot_path_mobile | Text | Mobile production screenshot path |

### Legacy Diff Fields:
| Column | Type | Description |
|--------|------|-------------|
| diff_image_path | Text | Legacy highlighted diff image path |
| diff_raw_image_path | Text | Legacy raw diff image path |
| diff_mismatch_pct | Numeric(6,3) | Percentage of changed pixels |
| diff_pixels_changed | Integer | Total changed pixels |
| diff_bounding_boxes | JSON | List of bounding boxes |
| diff_generated_at | DateTime | Diff generation timestamp |
| diff_error | Text | Error message if diff failed |

### Multi-viewport Diff Paths:
| Column | Type | Description |
|--------|------|-------------|
| diff_image_path_desktop | Text | Desktop diff image path |
| diff_image_path_tablet | Text | Tablet diff image path |
| diff_image_path_mobile | Text | Mobile diff image path |
| diff_raw_image_path_desktop | Text | Desktop raw diff image path |
| diff_raw_image_path_tablet | Text | Tablet raw diff image path |
| diff_raw_image_path_mobile | Text | Mobile raw diff image path |

### Multi-viewport Diff Metrics:
| Column | Type | Description |
|--------|------|-------------|
| diff_mismatch_pct_desktop | Numeric(6,3) | Desktop percentage of changed pixels |
| diff_mismatch_pct_tablet | Numeric(6,3) | Tablet percentage of changed pixels |
| diff_mismatch_pct_mobile | Numeric(6,3) | Mobile percentage of changed pixels |
| diff_pixels_changed_desktop | Integer | Desktop total changed pixels |
| diff_pixels_changed_tablet | Integer | Tablet total changed pixels |
| diff_pixels_changed_mobile | Integer | Mobile total changed pixels |
| diff_bounding_boxes_desktop | Text | Desktop bounding boxes (JSON string) |
| diff_bounding_boxes_tablet | Text | Tablet bounding boxes (JSON string) |
| diff_bounding_boxes_mobile | Text | Mobile bounding boxes (JSON string) |

### Timestamped Run Support:
| Column | Type | Description |
|--------|------|-------------|
| current_run_id | String(20) | Current run ID (YYYYMMDD-HHmmss format) |
| baseline_run_id | String(20) | Baseline run ID for comparison |
| find_diff_status | Enum | Diff processing status |
| last_run_at | DateTime | Last run execution timestamp |

### Per-page Duration Tracking:
| Column | Type | Description |
|--------|------|-------------|
| duration | Numeric(8,3) | Processing duration in seconds |
| processing_started_at | DateTime | Processing start timestamp |
| processing_completed_at | DateTime | Processing completion timestamp |

### Multi-viewport Diff Status Tracking:
| Column | Type | Description |
|--------|------|-------------|
| diff_status_desktop | Enum | Desktop diff status |
| diff_status_tablet | Enum | Tablet diff status |
| diff_status_mobile | Enum | Mobile diff status |

### Error Messages Per Viewport:
| Column | Type | Description |
|--------|------|-------------|
| diff_error_desktop | Text | Desktop diff error message |
| diff_error_tablet | Text | Tablet diff error message |
| diff_error_mobile | Text | Mobile diff error message |

### Constraints:
- Unique constraint on (project_id, path)

## Table: crawl_jobs
Tracks crawling and diff jobs for projects.

### Columns:
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | Primary Key, Auto-increment | Unique job identifier |
| project_id | Integer | Foreign Key (projects.id), Not Null | Associated project |
| status | Enum | Default: 'pending', Not Null | Job status |
| job_number | Integer | Not Null | Incremental job number per project |
| updated_at | DateTime | Default: Current UTC time, Not Null | Last update timestamp |
| job_type | String(20) | Default: 'crawl', Not Null | Type of job |
| total_pages | Integer | Default: 0, Not Null | Total pages in job |
| started_at | DateTime | Nullable | Job start timestamp |
| completed_at | DateTime | Nullable | Job completion timestamp |
| error_message | Text | Nullable | Error message if job failed |
| created_at | DateTime | Default: Current UTC time, Not Null | Job creation timestamp |

### Phase-specific Timestamps:
| Column | Type | Description |
|--------|------|-------------|
| crawl_started_at | DateTime | Crawl phase start timestamp |
| crawl_completed_at | DateTime | Crawl phase completion timestamp |
| fd_started_at | DateTime | Find Difference phase start timestamp |
| fd_completed_at | DateTime | Find Difference phase completion timestamp |

### Relationships:
- Many-to-One with `projects` (many jobs can belong to one project)

## Enum Values

### page_status (for project_pages.status):
- 'pending'
- 'crawled'
- 'ready_for_screenshot'
- 'screenshot_complete'
- 'screenshot_failed'
- 'ready_for_diff'
- 'diff_pending'
- 'diff_running'
- 'diff_generated'
- 'diff_failed'

### find_diff_status (for project_pages.find_diff_status):
- 'pending'
- 'capturing'
- 'captured'
- 'diffing'
- 'finding_difference'
- 'ready'
- 'completed'
- 'failed'
- 'no_baseline'

### crawl_job_status (for crawl_jobs.status):
- 'pending'
- 'Crawling'
- 'Crawled'
- 'Job Failed'
- 'finding_difference'
- 'ready'
- 'diff_failed'

### diff_status_* (for project_pages.diff_status_* columns):
- 'pending'
- 'processing'
- 'completed'
- 'failed'
- 'no_baseline'