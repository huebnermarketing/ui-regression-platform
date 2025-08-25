# UI Diff Dashboard - Database Schema (MySQL)

## Overview
The UI Diff Dashboard uses a MySQL database with five main tables:
1. `users` - For user authentication and management
2. `projects` - For storing project configurations
3. `project_pages` - For tracking individual pages within projects
4. `crawl_jobs` - For tracking crawling and diff jobs
5. `alembic_version` - For database migration version tracking

## Table: users
Stores user account information for authentication.

### Columns:
| Column | Type | Null | Key | Default | Extra |
|--------|------|------|-----|---------|-------|
| id | int | NO | PRI | None | auto_increment |
| username | varchar(80) | NO | UNI | None | |
| password_hash | varchar(255) | NO | | None | |
| created_at | datetime | YES | | None | |

## Table: projects
Stores project configurations including URLs and user associations.

### Columns:
| Column | Type | Null | Key | Default | Extra |
|--------|------|------|-----|---------|-------|
| id | int | NO | PRI | None | auto_increment |
| user_id | int | NO | MUL | None | |
| name | varchar(255) | NO | | None | |
| staging_url | text | NO | | None | |
| production_url | text | NO | | None | |
| status | enum('active','paused') | YES | | None | |
| created_at | datetime | YES | | None | |
| updated_at | datetime | YES | | None | |
| is_page_restricted | tinyint(1) | NO | | 0 | |

### Foreign Keys:
- `user_id` references `users.id`

## Table: project_pages
Stores information about individual pages within projects, including screenshot and diff data.

### Columns:
| Column | Type | Null | Key | Default | Extra |
|--------|------|------|-----|---------|-------|
| id | int | NO | PRI | None | auto_increment |
| project_id | int | NO | MUL | None | |
| path | varchar(767) | NO | | None | |
| page_name | varchar(500) | YES | | None | |
| staging_url | text | NO | | None | |
| production_url | text | NO | | None | |
| status | enum('pending','crawled','ready_for_screenshot','screenshot_complete','screenshot_failed','ready_for_diff','diff_pending','diff_running','diff_generated','diff_failed') | NO | | None | |
| created_at | datetime | YES | | None | |
| last_crawled | datetime | YES | | None | |
| staging_screenshot_path | text | YES | | None | |
| production_screenshot_path | text | YES | | None | |

### Multi-viewport Screenshot Paths:
| Column | Type | Null | Key | Default | Extra |
|--------|------|------|-----|---------|-------|
| staging_screenshot_path_desktop | text | YES | | None | |
| staging_screenshot_path_tablet | text | YES | | None | |
| staging_screenshot_path_mobile | text | YES | | None | |
| production_screenshot_path_desktop | text | YES | | None | |
| production_screenshot_path_tablet | text | YES | | None | |
| production_screenshot_path_mobile | text | YES | | None | |

### Legacy Diff Fields:
| Column | Type | Null | Key | Default | Extra |
|--------|------|------|-----|---------|-------|
| diff_image_path | text | YES | | None | |
| diff_raw_image_path | text | YES | | None | |
| diff_mismatch_pct | decimal(6,3) | YES | | None | |
| diff_pixels_changed | int | YES | | None | |
| diff_bounding_boxes | json | YES | | None | |
| diff_generated_at | datetime | YES | | None | |
| diff_error | text | YES | | None | |

### Multi-viewport Diff Paths:
| Column | Type | Null | Key | Default | Extra |
|--------|------|------|-----|---------|-------|
| diff_image_path_desktop | text | YES | | None | |
| diff_image_path_tablet | text | YES | | None | |
| diff_image_path_mobile | text | YES | | None | |
| diff_raw_image_path_desktop | text | YES | | None | |
| diff_raw_image_path_tablet | text | YES | | None | |
| diff_raw_image_path_mobile | text | YES | | None | |

### Multi-viewport Diff Metrics:
| Column | Type | Null | Key | Default | Extra |
|--------|------|------|-----|---------|-------|
| diff_mismatch_pct_desktop | decimal(6,3) | YES | | None | |
| diff_mismatch_pct_tablet | decimal(6,3) | YES | | None | |
| diff_mismatch_pct_mobile | decimal(6,3) | YES | | None | |
| diff_pixels_changed_desktop | int | YES | | None | |
| diff_pixels_changed_tablet | int | YES | | None | |
| diff_pixels_changed_mobile | int | YES | | None | |
| diff_bounding_boxes_desktop | text | YES | | None | |
| diff_bounding_boxes_tablet | text | YES | | None | |
| diff_bounding_boxes_mobile | text | YES | | None | |

### Timestamped Run Support:
| Column | Type | Null | Key | Default | Extra |
|--------|------|------|-----|---------|-------|
| current_run_id | varchar(20) | YES | | None | |
| baseline_run_id | varchar(20) | YES | | None | |
| find_diff_status | enum('pending','capturing','captured','diffing','finding_difference','ready','completed','failed','no_baseline') | NO | | None | |
| last_run_at | datetime | YES | | None | |

### Per-page Duration Tracking:
| Column | Type | Null | Key | Default | Extra |
|--------|------|------|-----|---------|-------|
| duration | decimal(8,3) | YES | | None | |
| processing_started_at | datetime | YES | | None | |
| processing_completed_at | datetime | YES | | None | |

### Multi-viewport Diff Status Tracking:
| Column | Type | Null | Key | Default | Extra |
|--------|------|------|-----|---------|-------|
| diff_status_desktop | enum('pending','processing','completed','failed','no_baseline') | NO | | None | |
| diff_status_tablet | enum('pending','processing','completed','failed','no_baseline') | NO | | None | |
| diff_status_mobile | enum('pending','processing','completed','failed','no_baseline') | NO | | None | |

### Error Messages Per Viewport:
| Column | Type | Null | Key | Default | Extra |
|--------|------|------|-----|---------|-------|
| diff_error_desktop | text | YES | | None | |
| diff_error_tablet | text | YES | | None | |
| diff_error_mobile | text | YES | | None | |

### Foreign Keys:
- `project_id` references `projects.id`

## Table: crawl_jobs
Tracks crawling and diff jobs for projects.

### Columns:
| Column | Type | Null | Key | Default | Extra |
|--------|------|------|-----|---------|-------|
| id | int | NO | PRI | None | auto_increment |
| project_id | int | NO | MUL | None | |
| status | enum('pending','Crawling','Crawled','Job Failed','finding_difference','ready','diff_failed') | NO | | None | |
| job_number | int | NO | | None | |
| updated_at | datetime | NO | | None | |
| job_type | varchar(20) | NO | | None | |
| total_pages | int | NO | | None | |
| started_at | datetime | YES | | None | |
| completed_at | datetime | YES | | None | |
| error_message | text | YES | | None | |
| created_at | datetime | NO | | None | |

### Phase-specific Timestamps:
| Column | Type | Null | Key | Default | Extra |
|--------|------|------|-----|---------|-------|
| crawl_started_at | datetime | YES | | None | |
| crawl_completed_at | datetime | YES | | None | |
| fd_started_at | datetime | YES | | None | |
| fd_completed_at | datetime | YES | | None | |

### Foreign Keys:
- `project_id` references `projects.id`

## Table: alembic_version
Tracks the current version of the database schema for migrations.

### Columns:
| Column | Type | Null | Key | Default | Extra |
|--------|------|------|-----|---------|-------|
| version_num | varchar(32) | NO | PRI | None | |