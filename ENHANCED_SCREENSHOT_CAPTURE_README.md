# Enhanced Screenshot Capture and Visual Diff Implementation

## Overview

This document describes the enhanced screenshot capture and visual diff functionality that implements accurate snapshots of dynamic pages and reliable storage of visual diffs according to the specified requirements.

## Key Features Implemented

### 1. Load-First Policy

The enhanced screenshot capture now implements a comprehensive load-first policy:

- **Document Ready State**: Waits for `document.readyState === "complete"`
- **Network Idle**: Waits for network to be idle for 2 seconds (configurable)
- **RequestAnimationFrame**: Waits for one requestAnimationFrame tick after idle
- **Progressive Reveal**: Auto-scrolls from top to bottom to trigger lazy-loaded content
- **Settling Time**: Waits additional 1-3 seconds for animations/transitions to settle

### 2. Progressive Reveal with Auto-Scrolling

- **Configurable Step Size**: Default 100px per step (configurable via `SCREENSHOT_SCROLL_STEP_DISTANCE`)
- **Viewport Pausing**: Pauses ~150ms per viewport (configurable via `SCREENSHOT_SCROLL_STEP_PAUSE`)
- **Lazy Loading Trigger**: Ensures all lazy-loaded content (images, iframes, components) is triggered
- **Return to Top**: Scrolls back to top after complete pass

### 3. Dynamic Content Handling

Enhanced handling for various dynamic content types:

- **Animation Control**: Sets `prefers-reduced-motion: reduce` and `animation-play-state: paused`
- **Canvas/Lottie/Video**: Waits for first rendered frame before capture
- **IntersectionObserver**: Forces lazy loading elements to load by removing `loading="lazy"` attributes
- **Data Attributes**: Triggers `data-src` and `data-lazy` attributes

### 4. Device Pixel Ratio (DPR) Support

- **High Quality Capture**: Uses device pixel ratio to preserve detail
- **Consistent Colors**: Ensures consistent color scheme during capture
- **Scale Configuration**: Configurable via `SCREENSHOT_DEVICE_PIXEL_RATIO`

### 5. Find Difference Workflow

Enhanced workflow that properly stores all three artifacts:

- **A (Baseline Image)**: Stored in baseline run directory
- **B (Current Image)**: Stored in current run directory  
- **A_vs_B_diff (Diff/Heatmap)**: Stored in diffs directory within current run

### 6. User Feedback and Logs

Clear status indicators throughout the capture process:

- **Loading**: Document ready state and network idle status
- **Scrolling**: Progressive reveal progress
- **Settling**: Animation/transition settling status
- **Capturing**: Final screenshot capture
- **Diffing**: Visual diff generation progress

## Configuration Options

All configuration options are environment variable based with sensible defaults:

### Screenshot Service Configuration

```bash
# Settling delay (1-3 seconds)
SCREENSHOT_SETTLING_DELAY=2500

# Network idle window (2 seconds)
SCREENSHOT_NETWORK_IDLE_WINDOW=2000

# Auto-scroll step pause (150ms per viewport)
SCREENSHOT_SCROLL_STEP_PAUSE=150

# Auto-scroll step distance (pixels per step)
SCREENSHOT_SCROLL_STEP_DISTANCE=100

# Device pixel ratio for quality
SCREENSHOT_DEVICE_PIXEL_RATIO=1.0

# Whether to wait for dynamic content
SCREENSHOT_WAIT_FOR_DYNAMIC=true
```

### Diff Engine Configuration

```bash
# Per-pixel threshold for differences
DIFF_PER_PIXEL_THRESHOLD=12

# Minimum area for diff regions
DIFF_MIN_DIFF_AREA=24

# Overlay alpha for highlighted diffs
DIFF_OVERLAY_ALPHA=140

# Batch size for processing
DIFF_BATCH_SIZE=15

# Output directory for diffs
DIFF_OUTPUT_DIR=./diffs

# Enable blur for noise reduction
DIFF_ENABLE_BLUR=false

# Blur radius
DIFF_BLUR_RADIUS=0.5

# Enable heatmap visualization
DIFF_HEATMAP=false

# Morphological operations
DIFF_DILATE_ITERATIONS=2
DIFF_ERODE_ITERATIONS=1
```

## Enhanced Workflow

### Screenshot Capture Process

1. **Navigation**: Navigate to target URL
2. **Load-First Policy**: 
   - Wait for document ready state
   - Wait for network idle (2s)
   - Wait for requestAnimationFrame tick
3. **Progressive Reveal**:
   - Auto-scroll from top to bottom
   - Pause at each viewport (~150ms)
   - Trigger lazy-loaded content
4. **Settling**:
   - Wait for animations/transitions (1-3s)
   - Pause animations and transitions
   - Handle canvas/video/Lottie elements
5. **Capture**: Take full-page screenshot at device pixel ratio

### Find Difference Process

1. **Capture Screenshots**: For all viewports (desktop, tablet, mobile)
2. **Generate Diffs**: Compare with baseline images
3. **Store Artifacts**:
   - Baseline images (A)
   - Current images (B)
   - Diff images (A_vs_B_diff)
4. **Calculate Metrics**: Mismatch percentage, changed pixels, bounding boxes
5. **Update Status**: Per-viewport status tracking

## File Structure

```
/runs/
  /{project_id}/
    /{run_id}/                    # e.g., 20250812-120641
      /screenshots/
        /staging/
          /desktop/{page_slug}.png
          /tablet/{page_slug}.png
          /mobile/{page_slug}.png
        /production/
          /desktop/{page_slug}.png
          /tablet/{page_slug}.png
          /mobile/{page_slug}.png
      /diffs/
        /desktop/
          /{page_slug}_diff.png     # Highlighted diff
          /{page_slug}_diff_raw.png # Raw diff visualization
        /tablet/
          /{page_slug}_diff.png
          /{page_slug}_diff_raw.png
        /mobile/
          /{page_slug}_diff.png
          /{page_slug}_diff_raw.png
```

## Status Indicators

### Screenshot Capture Status

- **Loading**: Waiting for document ready state and network idle
- **Scrolling**: Progressive reveal in progress
- **Settling**: Waiting for animations/transitions to settle
- **Capturing**: Taking final screenshot

### Find Difference Status

- **Capturing**: Screenshots being captured
- **Captured**: Screenshots captured successfully
- **Diffing**: Visual diffs being generated
- **Completed**: All processing completed successfully
- **Failed**: Processing failed with error details
- **No Baseline**: No baseline exists (current run becomes baseline)
- **No Changes**: No visual differences detected

## Error Handling

Enhanced error handling with specific error messages:

- **Missing Screenshots**: "Current run screenshots not found"
- **Missing Baseline**: "Baseline screenshots not found"
- **Image Size Mismatch**: "Images have different sizes"
- **Storage Failure**: "Failed to save diff images"
- **Processing Error**: Detailed error messages with context

## Acceptance Criteria Met

✅ **Snapshots include content that previously appeared only after scrolling or animation**
- Progressive reveal with auto-scrolling triggers all lazy-loaded content
- Animation settling ensures stable capture state

✅ **"Find difference" results in three saved artifacts (A, B, and the diff) every time**
- Baseline images (A) stored in baseline run directory
- Current images (B) stored in current run directory
- Diff images stored in diffs directory with highlighted and raw versions

✅ **UI confirms whether the diff was generated and stored**
- Clear status indicators throughout the process
- Success/failure confirmation with detailed error messages
- Per-viewport status tracking for multi-viewport support

## Usage Examples

### Manual Screenshot Capture

```python
from screenshot.screenshot_service import ScreenshotService

service = ScreenshotService()
success = await service.capture_screenshot(
    url="https://example.com",
    output_path=Path("screenshot.png"),
    viewport="desktop",
    wait_for_dynamic=True
)
```

### Find Difference Workflow

```python
from services.find_difference_service import FindDifferenceService

service = FindDifferenceService()
successful, failed, run_id = await service.run_find_difference(
    project_id=1,
    page_ids=[1, 2, 3]  # Optional: specific pages
)
```

## Performance Considerations

- **Configurable Timeouts**: All wait times are configurable
- **Batch Processing**: Diff generation processes pages in configurable batches
- **Resource Cleanup**: Automatic cleanup of partial files on failure
- **Memory Management**: Efficient image processing with proper resource disposal

## Browser Compatibility

- **Chromium-based**: Uses Playwright with Chromium for consistent rendering
- **User Agents**: Proper mobile/tablet user agents for responsive testing
- **Headless Mode**: Runs in headless mode with stability optimizations

This enhanced implementation provides reliable, accurate screenshot capture and visual diff generation that handles modern web applications with dynamic content, lazy loading, and animations.