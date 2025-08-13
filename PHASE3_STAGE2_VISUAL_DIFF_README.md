# Phase 3 - Stage 2: Visual Diff Generation System

## Overview

This document describes the implementation of **Phase 3 - Stage 2: Visual Diff Generation** for the UI regression testing platform. This stage builds upon the screenshot capture system to provide comprehensive visual difference detection and analysis between staging and production environments.

## Features Implemented

### 🎯 Core Visual Diff Engine
- **Image Normalization**: Automatic size matching and format standardization
- **Pixel-Level Comparison**: Advanced difference detection with configurable thresholds
- **Morphological Operations**: Noise reduction through dilation and erosion
- **Bounding Box Detection**: Connected components analysis for diff regions
- **Highlighted Diff Rendering**: Red overlay visualization of differences
- **Raw Diff Visualization**: Grayscale and heatmap diff representations

### 📊 Metrics & Analytics
- **Mismatch Percentage**: Precise calculation of changed pixels
- **Pixel Count**: Total number of different pixels
- **Bounding Boxes**: Coordinates and dimensions of diff regions
- **Largest Region**: Area of the most significant change
- **Generation Timestamps**: Track when diffs were created

### 🔧 Configuration Management
- **Environment Variables**: Configurable thresholds and parameters
- **Batch Processing**: Configurable batch sizes for performance
- **Image Processing Options**: Blur, heatmap, and morphological settings
- **Output Directory**: Customizable diff storage location

### 🚀 Job Integration
- **Background Processing**: Non-blocking diff generation
- **Progress Tracking**: Real-time progress updates
- **Job Control**: Start, pause, resume, and stop operations
- **Error Handling**: Comprehensive error reporting and recovery

### 🌐 Web Interface
- **Generate Diffs Button**: One-click diff generation
- **Diff Viewing**: Direct links to highlighted and raw diff images
- **Status Indicators**: Visual status for each page's diff state
- **Metrics Display**: Percentage changed and region count

## Technical Architecture

### Database Schema

```sql
-- Added to project_pages table
ALTER TABLE project_pages ADD COLUMN diff_image_path TEXT;
ALTER TABLE project_pages ADD COLUMN diff_raw_image_path TEXT;
ALTER TABLE project_pages ADD COLUMN diff_mismatch_pct DECIMAL(6,3);
ALTER TABLE project_pages ADD COLUMN diff_pixels_changed INT;
ALTER TABLE project_pages ADD COLUMN diff_bounding_boxes JSON;
ALTER TABLE project_pages ADD COLUMN diff_generated_at DATETIME;
ALTER TABLE project_pages ADD COLUMN diff_error TEXT;

-- Updated status enum
ALTER TABLE project_pages MODIFY COLUMN status ENUM(
    'pending', 'crawled', 'ready_for_screenshot', 'screenshot_running',
    'screenshot_complete', 'screenshot_failed', 'diff_running',
    'diff_generated', 'diff_failed'
);
```

### Core Components

#### 1. DiffConfig Class
```python
class DiffConfig:
    """Configuration for diff generation"""
    
    def __init__(self):
        # Thresholds and parameters
        self.per_pixel_threshold = int(os.getenv('DIFF_PER_PIXEL_THRESHOLD', '12'))
        self.min_diff_area = int(os.getenv('DIFF_MIN_DIFF_AREA', '24'))
        self.overlay_alpha = int(os.getenv('DIFF_OVERLAY_ALPHA', '140'))
        self.batch_size = int(os.getenv('DIFF_BATCH_SIZE', '15'))
        self.output_dir = os.getenv('DIFF_OUTPUT_DIR', './diffs')
```

#### 2. VisualDiffEngine Class
```python
class VisualDiffEngine:
    """Main visual diff engine for comparing screenshots"""
    
    def normalize_images(self, img1, img2) -> Tuple[Image.Image, Image.Image]
    def compute_diff_mask(self, img1, img2) -> Image.Image
    def extract_bounding_boxes(self, mask) -> List[List[int]]
    def create_highlighted_diff(self, base_image, mask, bounding_boxes) -> Image.Image
    def calculate_metrics(self, mask, bounding_boxes) -> Dict
    def process_page_diff(self, page_id) -> bool
    def process_project_diffs(self, project_id, page_ids=None) -> Tuple[int, int]
```

#### 3. Job Integration
```python
class WorkingCrawlerScheduler:
    def schedule_diff_generation(self, project_id):
        """Start a diff generation job in a background thread"""
    
    def _diff_generation_job(self, project_id, job_id):
        """Background job to generate visual diffs for a project"""
```

### File Structure

```
ui-regression-platform/
├── diff/
│   ├── __init__.py
│   └── diff_engine.py          # Core diff engine implementation
├── diffs/                      # Generated diff images storage
│   └── {project_id}/
│       ├── {slug}_diff.png     # Highlighted diff images
│       └── {slug}_diff_raw.png # Raw diff images
├── migrations/
│   └── add_diff_fields.py      # Database migration
├── templates/projects/
│   └── details.html            # Updated with diff UI
├── projects/
│   └── routes.py               # Added diff routes
├── test_diff_generation.py     # Comprehensive test suite
└── requirements.txt            # Updated with Pillow, NumPy, SciPy
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DIFF_PER_PIXEL_THRESHOLD` | `12` | Pixel difference threshold (0-255) |
| `DIFF_MIN_DIFF_AREA` | `24` | Minimum area for diff regions (pixels) |
| `DIFF_OVERLAY_ALPHA` | `140` | Alpha transparency for red overlay (0-255) |
| `DIFF_BATCH_SIZE` | `15` | Number of pages to process per batch |
| `DIFF_OUTPUT_DIR` | `./diffs` | Directory for storing diff images |
| `DIFF_ENABLE_BLUR` | `false` | Enable Gaussian blur for noise reduction |
| `DIFF_BLUR_RADIUS` | `0.5` | Blur radius for anti-aliasing |
| `DIFF_HEATMAP` | `false` | Enable heatmap visualization |
| `DIFF_DILATE_ITERATIONS` | `2` | Morphological dilation iterations |
| `DIFF_ERODE_ITERATIONS` | `1` | Morphological erosion iterations |

### Example Configuration

```bash
# High sensitivity configuration
export DIFF_PER_PIXEL_THRESHOLD=5
export DIFF_MIN_DIFF_AREA=10
export DIFF_ENABLE_BLUR=true

# Performance configuration
export DIFF_BATCH_SIZE=25
export DIFF_OUTPUT_DIR=/var/diffs

# Visual configuration
export DIFF_OVERLAY_ALPHA=180
export DIFF_HEATMAP=true
```

## API Endpoints

### Generate Diffs
```http
POST /projects/{project_id}/generate-diffs
```
Starts diff generation for all pages with completed screenshots.

### Serve Diff Images
```http
GET /diffs/{project_id}/{filename}
```
Serves diff images with access control verification.

### Project Status
```http
GET /projects/{project_id}/status
```
Returns job status including diff generation progress.

## Usage Guide

### 1. Prerequisites
- Screenshots must be captured for both staging and production
- Pages must have status `screenshot_complete`
- Sufficient disk space for diff images

### 2. Generate Diffs
1. Navigate to project details page
2. Click "Generate Diffs" button
3. Monitor progress in real-time
4. View results in the diff column

### 3. View Diff Results
- **Diff Button**: View highlighted differences with red overlay
- **Raw Button**: View raw difference mask
- **Percentage**: See exact percentage of pixels changed
- **Status**: Monitor diff generation status

### 4. Programmatic Usage
```python
from diff.diff_engine import DiffEngine

# Initialize diff engine
diff_engine = DiffEngine()

# Generate diffs for a project
successful, failed = diff_engine.run_generate_project_diffs(project_id)

print(f"Generated {successful} diffs, {failed} failed")
```

## Algorithm Details

### Image Normalization
1. Convert images to RGBA format
2. Determine maximum dimensions
3. Create white background canvases
4. Paste original images at (0,0)
5. Apply optional Gaussian blur

### Difference Detection
1. Compute absolute pixel differences
2. Convert to grayscale
3. Apply threshold to create binary mask
4. Perform morphological operations:
   - Dilation to close gaps
   - Erosion to clean edges

### Bounding Box Extraction
1. Label connected components
2. Find bounding rectangles
3. Filter by minimum area
4. Return as [x, y, width, height] arrays

### Metrics Calculation
```python
{
    'diff_pixels_changed': int,      # Total different pixels
    'diff_mismatch_pct': float,      # Percentage changed
    'diff_bounding_boxes': list,     # Bounding box coordinates
    'largest_region_area': int       # Largest diff region area
}
```

## Performance Considerations

### Optimization Strategies
- **Batch Processing**: Process multiple pages in batches
- **Memory Management**: Process images individually to avoid memory issues
- **Disk I/O**: Efficient file handling with proper cleanup
- **Database Transactions**: Batch database updates

### Scaling Recommendations
- Use SSD storage for diff images
- Configure appropriate batch sizes based on memory
- Monitor disk space usage
- Consider image compression for storage

## Testing

### Run Test Suite
```bash
cd ui-regression-platform
python test_diff_generation.py
```

### Test Coverage
- ✅ Configuration management
- ✅ Image normalization
- ✅ Diff mask computation
- ✅ Bounding box extraction
- ✅ Metrics calculation
- ✅ Highlighted diff rendering
- ✅ Database integration
- ✅ Job orchestration
- ✅ Error handling
- ✅ File management

### Test Results
```
🧪 Starting Phase 3 Stage 2: Visual Diff Generation Tests
============================================================
=== Testing Diff Configuration ===
✓ Default configuration values correct
✓ Environment variable overrides working

=== Testing Visual Diff Engine ===
✓ Loaded test images: (800, 600) and (800, 600)
✓ Image normalization: (800, 600)
✓ Diff mask computation: 15234 different pixels detected
✓ Bounding box extraction: 4 regions found
✓ Metrics calculation: 3.17% changed
✓ Highlighted diff creation
✓ Raw diff creation

=== Testing Database Integration ===
✓ Created test project: 1
✓ Created test page: 1
✓ Page diff processing successful
✓ Database fields updated:
  - Status: diff_generated
  - Mismatch: 3.17%
  - Changed pixels: 15234
  - Bounding boxes: 4
✓ Diff image files created successfully

✅ All diff generation tests passed successfully!
```

## Troubleshooting

### Common Issues

#### 1. Missing Dependencies
```bash
pip install Pillow==10.1.0 numpy==1.24.3 scipy==1.11.4
```

#### 2. Permission Errors
```bash
chmod 755 diffs/
chown -R www-data:www-data diffs/
```

#### 3. Memory Issues
- Reduce `DIFF_BATCH_SIZE`
- Process smaller images
- Monitor system memory usage

#### 4. No Differences Detected
- Check `DIFF_PER_PIXEL_THRESHOLD` setting
- Verify screenshot quality
- Review image normalization

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable detailed diff engine logging
logger = logging.getLogger('diff.diff_engine')
logger.setLevel(logging.DEBUG)
```

## Security Considerations

### Access Control
- Diff images are served with project ownership verification
- File paths are validated to prevent directory traversal
- User authentication required for all diff operations

### File Security
- Diff images stored outside web root
- Proper file permissions (644 for files, 755 for directories)
- Regular cleanup of old diff images

## Future Enhancements

### Planned Features
- **Diff History**: Track diff changes over time
- **Diff Annotations**: Add comments and notes to diff regions
- **Automated Alerts**: Notify when significant changes detected
- **Diff Comparison**: Compare diffs across different time periods
- **Export Options**: PDF reports and CSV metrics export

### Performance Improvements
- **Parallel Processing**: Multi-threaded diff generation
- **Image Caching**: Cache normalized images
- **Progressive Diffs**: Generate diffs incrementally
- **Compression**: Optimize diff image storage

## Conclusion

Phase 3 - Stage 2 successfully implements a comprehensive visual diff generation system that:

- ✅ Provides accurate pixel-level difference detection
- ✅ Generates highlighted and raw diff visualizations
- ✅ Calculates detailed metrics and analytics
- ✅ Integrates seamlessly with the job system
- ✅ Offers extensive configuration options
- ✅ Includes comprehensive error handling
- ✅ Provides an intuitive web interface

The system is production-ready and provides a solid foundation for advanced UI regression testing workflows.