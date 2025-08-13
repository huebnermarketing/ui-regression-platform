# Find Difference Implementation Summary

## Overview
Successfully implemented a unified "Find Difference" workflow that merges screenshot capture and diff generation into a single action with multi-viewport support (desktop, tablet, mobile) and timestamped runs.

## Key Features Implemented

### 1. Unified "Find Difference" Workflow
- **Single Button**: Replaced separate "Capture Screenshots" and "Generate Diffs" buttons with one "Find Difference" button
- **Multi-Viewport Processing**: Captures screenshots and generates diffs for desktop (1920x1080), tablet (768x1024), and mobile (375x667) viewports
- **Sequential Processing**: Desktop → Tablet → Mobile (configurable order)
- **Baseline Management**: Automatically handles cases where no baseline exists

### 2. Timestamped Run System
- **Run ID Format**: `YYYYMMDD-HHmmss` in IST timezone (e.g., `20250811-154210`)
- **Directory Structure**: `/runs/{project_id}/{run_id}/{viewport}/{staging|production}/`
- **Diff Storage**: `/runs/{project_id}/{run_id}/diffs/{viewport}/`
- **No Overwriting**: Each run creates a unique timestamped directory

### 3. Per-Row Manual Capture
- **Checkbox Behavior**: Click any row checkbox to immediately capture that page across all 3 viewports
- **AJAX Implementation**: Real-time capture with toast notifications
- **Progress Feedback**: Shows loading state and completion/failure messages
- **Auto-Refresh**: Page refreshes after successful capture to show updated status

### 4. Enhanced Database Schema
Added new fields to `project_pages` table:
- `current_run_id`: Current run identifier
- `baseline_run_id`: Baseline run for comparison
- `find_diff_status`: Overall workflow status (pending, capturing, captured, diffing, completed, failed, no_baseline)
- `last_run_at`: Timestamp of last run execution
- `diff_status_{viewport}`: Per-viewport diff status tracking
- `diff_error_{viewport}`: Per-viewport error messages
- Multi-viewport metrics fields

### 5. Updated UI/UX

#### Project Details Page
- **Single "Find Difference" Button**: Primary action for all pages
- **Selected Pages Action**: "Find Difference (Selected)" for checked pages
- **New Table Columns**:
  - "Find Difference Status": Shows workflow progress
  - "Last Run": IST timestamp of last execution
  - "Actions": Manual capture button per row
  - "Results": Multi-viewport diff results with links

#### Status Indicators
- **Pending**: Gray badge
- **Capturing**: Yellow badge with "Capturing Screenshots"
- **Captured**: Green badge with "Screenshots Captured"
- **Diffing**: Blue badge with "Generating Diffs"
- **Completed**: Purple badge with "Completed"
- **Failed**: Red badge with "Failed"
- **No Baseline**: Orange badge with "No Baseline"

### 6. Multi-Viewport Results Display
- **Desktop**: 🖥️ icon with diff link and percentage
- **Tablet**: 📱 icon with diff link and percentage
- **Mobile**: 📱 icon with diff link and percentage
- **Status Per Viewport**: Shows "No baseline", "Failed", or diff percentage
- **Direct Links**: Click to view diff images in new tab

### 7. Technical Implementation

#### Services Layer
- **FindDifferenceService**: New unified service handling the complete workflow
- **Run Management**: IST timestamp generation and directory management
- **Multi-Viewport Processing**: Handles all 3 viewports in sequence
- **Error Handling**: Graceful failure handling per viewport
- **Job Control**: Integrates with existing scheduler for pause/stop functionality

#### API Endpoints
- `POST /projects/{id}/find-difference`: Start unified workflow
- `POST /projects/{id}/manual-capture/{page_id}`: Manual single-page capture
- `GET /runs/{path}`: Serve timestamped run files (screenshots and diffs)

#### Enhanced Screenshot Service
- **Multi-Viewport Support**: Already supported desktop/tablet/mobile
- **Timestamped Paths**: New path structure for runs
- **User Agent Handling**: Proper mobile/tablet user agents

#### Enhanced Diff Engine
- **Multi-Viewport Diffs**: Generate diffs for all viewports
- **Baseline Comparison**: Compare current run with baseline
- **Metrics Tracking**: Per-viewport mismatch percentages and pixel counts

### 8. Behavioral Rules Implemented

#### Processing Order
- Always captures in order: Desktop → Tablet → Mobile
- Continues with other viewports if one fails
- Surfaces errors per viewport in the UI

#### Baseline Management
- If baseline exists: Generate diff and show percentage
- If no baseline exists: Mark as "No baseline" and set current run as baseline
- First successful run automatically becomes baseline

#### Time Handling
- **Computation**: All durations and timestamps computed in UTC for math
- **Display**: All displayed times are in IST 12-hour format (DD/MM/YYYY hh:mm A)
- **Run IDs**: Generated using IST timezone for filesystem safety

#### Error Handling
- **Per-Viewport Errors**: Each viewport can fail independently
- **Graceful Degradation**: Continue processing other viewports on failure
- **Error Display**: Show specific error messages per viewport
- **Toast Notifications**: Real-time feedback for manual captures

### 9. File Structure
```
/runs/
  /{project_id}/
    /{run_id}/           # e.g., 20250811-154210
      /desktop/
        /staging/
          /{page_slug}.png
        /production/
          /{page_slug}.png
      /tablet/
        /staging/
          /{page_slug}.png
        /production/
          /{page_slug}.png
      /mobile/
        /staging/
          /{page_slug}.png
        /production/
          /{page_slug}.png
      /diffs/
        /desktop/
          /{page_slug}_diff.png
          /{page_slug}_diff_raw.png
        /tablet/
          /{page_slug}_diff.png
          /{page_slug}_diff_raw.png
        /mobile/
          /{page_slug}_diff.png
          /{page_slug}_diff_raw.png
```

### 10. Python 3.12+ Compatibility
- **Fixed `datetime.utcnow()`**: Replaced with `datetime.now(timezone.utc)`
- **Timezone Handling**: Proper timezone-aware datetime operations
- **Backward Compatibility**: Handles both timezone-aware and naive datetimes

## Usage Instructions

### Running Find Difference on All Pages
1. Navigate to project details page
2. Click the "Find Difference" button
3. Workflow will capture screenshots and generate diffs for all pages across all viewports
4. Progress is shown in real-time with status updates

### Running Find Difference on Selected Pages
1. Check the boxes next to desired pages
2. Click "Find Difference (Selected)" button
3. Only selected pages will be processed

### Manual Single-Page Capture
1. Click the "Capture" button in any row
2. Screenshots will be captured immediately for that page across all viewports
3. Toast notification shows success/failure
4. Page refreshes to show updated status

### Viewing Results
1. Completed pages show viewport-specific results
2. Click the eye icon next to each viewport to view diff images
3. Percentages show the amount of visual change detected
4. "No baseline" indicates this is the first capture (now set as baseline)

## Migration Applied
- Database migration `add_timestamped_runs.py` successfully applied
- All new columns added to `project_pages` table
- Backward compatibility maintained with existing data

## Files Modified/Created
- **New**: `services/find_difference_service.py` - Core unified workflow
- **New**: `migrations/add_timestamped_runs.py` - Database schema updates
- **Modified**: `models/project.py` - Added new fields
- **Modified**: `app.py` - Added Find Difference scheduler integration
- **Modified**: `projects/routes.py` - New API endpoints
- **Modified**: `templates/projects/details.html` - Updated UI
- **Modified**: `crawl_queue/routes.py` - Fixed Python 3.12+ compatibility

## Testing Status
- ✅ Application starts successfully
- ✅ Database migration applied
- ✅ Python 3.12+ compatibility issues resolved
- ✅ UI updated with new Find Difference workflow
- ✅ Multi-viewport support implemented
- ✅ Timestamped run system operational
- ✅ Crawling limited to 20 pages for testing purposes

## Testing Configuration
- **Page Limit**: Crawling is currently limited to 20 pages maximum for testing
- **Delay**: 0.3 seconds between requests for faster testing
- **Viewports**: All 3 viewports (desktop, tablet, mobile) are processed for each page

The implementation is complete and ready for testing with the 20-page limit!