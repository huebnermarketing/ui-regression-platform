# Phase 3 - Stage 1: Screenshot Capture System

## 🎯 Overview

This implementation adds automated full-page screenshot capture functionality to the UI regression platform using Playwright (Python). The system captures screenshots for both staging and production URLs of matched pages, preparing them for visual comparison in subsequent stages.

## ✅ Implemented Features

### 1. Screenshot Capture Service
- **File**: `screenshot/screenshot_service.py`
- **Technology**: Playwright with headless Chromium
- **Features**:
  - Full-page screenshot capture
  - Automatic viewport sizing (1920x1080)
  - Network idle wait for dynamic content
  - Error handling and retry logic
  - Job control integration (pause/stop support)

### 2. Database Schema Updates
- **Migration**: `migrations/add_screenshot_fields.py`
- **New Fields in `project_pages` table**:
  - `staging_screenshot_path` (TEXT) - Path to staging screenshot
  - `production_screenshot_path` (TEXT) - Path to production screenshot
- **Updated Status Enum**:
  - `ready_for_screenshot` - Page ready for screenshot capture
  - `screenshot_complete` - Screenshots captured successfully
  - `screenshot_failed` - Screenshot capture failed
  - `diff_generated` - Visual diff has been generated (for Phase 3 Stage 2)

### 3. File Storage System
- **Structure**:
  ```
  screenshots/
  └── {project_id}/
      ├── staging/
      │   └── {slugified_path}.png
      └── production/
          └── {slugified_path}.png
  ```
- **Features**:
  - Automatic directory creation
  - Path slugification for safe filenames
  - Relative path storage in database

### 4. Web Interface Integration
- **New Route**: `/projects/{id}/capture-screenshots` - Trigger screenshot capture
- **Screenshot Serving**: `/screenshots/{path}` - Serve screenshot files with access control
- **UI Updates**:
  - Screenshot capture button in project details
  - Enhanced status badges for screenshot states
  - Screenshot viewing links in page table

### 5. Job System Integration
- **Scheduler Enhancement**: Extended `WorkingCrawlerScheduler` with screenshot jobs
- **Progress Tracking**: Real-time progress updates during capture
- **Job Control**: Pause/resume/stop functionality for screenshot jobs

## 🛠️ Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Run Database Migration
```bash
python migrations/add_screenshot_fields.py
```

### 3. Test Installation
```bash
python test_screenshot_capture.py
```

## 🚀 Usage

### Via Web Interface
1. Navigate to a project with crawled pages
2. Click "Capture Screenshots" button
3. Monitor progress in real-time
4. View screenshots once capture is complete

### Programmatic Usage
```python
from screenshot.screenshot_service import ScreenshotService

# Initialize service
service = ScreenshotService()

# Capture screenshots for a project
successful, failed = service.run_capture_project_screenshots(project_id)

# Capture single page screenshots
success = await service.capture_page_screenshots(page_id)
```

## 📁 File Structure

```
ui-regression-platform/
├── screenshot/
│   ├── __init__.py
│   └── screenshot_service.py          # Main screenshot service
├── migrations/
│   └── add_screenshot_fields.py       # Database migration
├── templates/projects/
│   └── details.html                   # Updated UI with screenshot features
├── projects/
│   └── routes.py                      # Screenshot routes
├── models/
│   └── project.py                     # Updated ProjectPage model
├── screenshots/                       # Screenshot storage directory
│   └── {project_id}/
│       ├── staging/
│       └── production/
├── test_screenshot_capture.py         # Test script
└── requirements.txt                   # Updated with Playwright
```

## 🔧 Configuration

### Screenshot Service Settings
```python
# Default configuration in ScreenshotService
base_screenshot_dir = "screenshots"    # Base directory for screenshots
viewport_size = {"width": 1920, "height": 1080}  # Browser viewport
timeout = 30000                        # Page load timeout (ms)
wait_time = 2000                      # Additional wait for dynamic content (ms)
```

### Playwright Browser Settings
- **Browser**: Chromium (headless mode)
- **Features**: Full-page screenshots, network idle detection
- **Performance**: Optimized for server environments

## 🔍 Error Handling

### Screenshot Capture Errors
- **Network timeouts**: Configurable timeout with graceful failure
- **Page load failures**: Individual page failures don't stop batch processing
- **File system errors**: Automatic directory creation and permission handling
- **Browser crashes**: Isolated browser instances per capture

### Database Error Handling
- **Transaction rollback**: Failed operations don't corrupt database state
- **Status tracking**: Clear status indicators for failed captures
- **Cleanup**: Partial files removed on failure

### Job Control Error Handling
- **Graceful shutdown**: Stop signals properly terminate browser instances
- **Pause/resume**: State preservation during pause operations
- **Progress tracking**: Real-time status updates with error reporting

## 📊 Status Flow

```
pending → crawled → ready_for_screenshot → screenshot_complete → ready_for_diff → diff_generated
                                        → screenshot_failed
```

### Status Descriptions
- **`pending`**: Page not yet crawled
- **`crawled`**: Page discovered and ready for screenshot
- **`ready_for_screenshot`**: Page queued for screenshot capture
- **`screenshot_complete`**: Screenshots captured successfully
- **`screenshot_failed`**: Screenshot capture failed
- **`ready_for_diff`**: Ready for visual comparison (Phase 3 Stage 2)
- **`diff_generated`**: Visual diff has been generated (Phase 3 Stage 2)

## 🧪 Testing

### Automated Tests
```bash
# Run comprehensive test suite
python test_screenshot_capture.py

# Test specific functionality
python -c "from test_screenshot_capture import test_screenshot_service; test_screenshot_service()"
```

### Manual Testing
1. Create a project with staging and production URLs
2. Run crawl to discover pages
3. Trigger screenshot capture
4. Verify screenshots are created and accessible
5. Check database status updates

### Test URLs for Development
- **Staging**: `https://httpbin.org/html`
- **Production**: `https://httpbin.org/html`
- **Complex pages**: Any modern website with dynamic content

## 🔒 Security Considerations

### Access Control
- Screenshot files served only to project owners
- Path validation prevents directory traversal
- User authentication required for all screenshot operations

### File System Security
- Screenshots stored outside web root
- Automatic cleanup of failed captures
- Project-based directory isolation

## 🚀 Performance Optimization

### Browser Management
- Headless mode for server efficiency
- Single browser instance per capture
- Automatic browser cleanup

### File System
- Efficient path slugification
- Minimal file system operations
- Batch processing for multiple pages

### Database
- Bulk status updates where possible
- Efficient queries for ready pages
- Transaction optimization

## 🔮 Future Enhancements

### Phase 3 - Stage 2 Integration
- Visual diff generation using captured screenshots
- Side-by-side comparison interface
- Diff highlighting and annotation

### Advanced Features
- **Responsive screenshots**: Multiple viewport sizes
- **Element-specific capture**: Target specific page elements
- **Screenshot comparison**: Built-in diff algorithms
- **Batch operations**: Bulk screenshot management

### Performance Improvements
- **Parallel processing**: Multiple browser instances
- **Caching**: Screenshot caching and invalidation
- **Compression**: Image optimization for storage

## 📝 API Reference

### ScreenshotService Class

#### Methods
- `capture_screenshot(url, output_path, timeout=30000)` - Capture single screenshot
- `capture_page_screenshots(page_id)` - Capture both staging and production screenshots
- `capture_project_screenshots(project_id, scheduler=None)` - Capture all project screenshots
- `get_screenshot_paths(project_id, page_path)` - Get file paths for screenshots
- `slugify_path(path)` - Convert URL path to safe filename
- `cleanup_project_screenshots(project_id)` - Remove all project screenshots

#### Properties
- `base_screenshot_dir` - Base directory for screenshot storage

### Routes
- `POST /projects/{id}/capture-screenshots` - Start screenshot capture job
- `GET /screenshots/{path}` - Serve screenshot file with access control

## 🐛 Troubleshooting

### Common Issues

#### Playwright Installation
```bash
# If browser installation fails
playwright install --force chromium

# Check installation
playwright --version
```

#### Permission Errors
```bash
# Ensure screenshot directory is writable
chmod 755 screenshots/
```

#### Database Migration Issues
```bash
# Manual migration if script fails
mysql -u username -p database_name < migrations/add_screenshot_fields.sql
```

#### Browser Launch Failures
- Check system dependencies for headless Chrome
- Verify sufficient memory and disk space
- Check firewall settings for outbound connections

### Debug Mode
Enable debug logging by setting environment variable:
```bash
export PLAYWRIGHT_DEBUG=1
```

## 📞 Support

For issues or questions regarding the screenshot capture implementation:

1. Check the test script output: `python test_screenshot_capture.py`
2. Review application logs for error details
3. Verify Playwright installation: `playwright --version`
4. Check database schema: Ensure migration completed successfully

---

**Implementation Status**: ✅ Complete - Ready for Phase 3 Stage 2 (Visual Diff Generation)