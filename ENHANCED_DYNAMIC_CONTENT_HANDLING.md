# Enhanced Dynamic Content Handling for Screenshot Capture

This document describes the enhanced dynamic content handling system that ensures screenshots are only taken after all dynamic elements have fully loaded, animations have stopped, and the layout is stable.

## Overview

The enhanced system addresses the common issue where screenshots are captured before:
- API-fetched content has loaded
- Lazy-loaded images and components have appeared
- Animations and transitions have completed
- Layout has stabilized
- Framework-specific hydration has finished

## Key Features

### 🌐 Enhanced Network Activity Detection
- **Modern API Support**: Monitors fetch(), XMLHttpRequest, and WebSocket connections
- **Intelligent Idle Detection**: Waits for network to be truly idle (no pending requests)
- **Configurable Thresholds**: Customizable idle timeouts and check intervals

### 🔄 Comprehensive Lazy Loading Support
- **Intersection Observer**: Detects and waits for lazy-loaded content
- **Progressive Scrolling**: Automatically scrolls to trigger all lazy loading
- **Framework Support**: Handles React.lazy(), Vue async components, and Angular lazy modules
- **Image Loading**: Waits for all images (including data-src attributes) to load

### 🎬 Animation and Transition Detection
- **CSS Animations**: Detects and waits for CSS animations to complete
- **Web Animations API**: Monitors animations created via JavaScript
- **Transition Detection**: Waits for CSS transitions to finish
- **Animation Pausing**: Pauses all animations for consistent capture

### 📐 Layout Stability Detection
- **DOM Stability**: Monitors for layout changes and waits for stability
- **Reflow Detection**: Detects when elements are still moving or resizing
- **Configurable Thresholds**: Adjustable stability requirements

### ⚛️ Framework-Specific Handling
- **React**: Waits for hydration and component mounting
- **Vue**: Detects Vue app mounting and component readiness
- **Angular**: Waits for Angular bootstrap completion
- **SPA Support**: Enhanced handling for Single Page Applications

## Configuration

### Environment Variables

You can configure the system using environment variables:

```bash
# Basic timing settings
SCREENSHOT_MAX_WAIT_TIME=30000              # Maximum total wait time (30s)
SCREENSHOT_NETWORK_IDLE_TIMEOUT=3000        # Network idle timeout (3s)
SCREENSHOT_LAYOUT_STABILITY_TIMEOUT=2000    # Layout stability timeout (2s)
SCREENSHOT_ANIMATION_SETTLE_TIMEOUT=1500    # Animation settle timeout (1.5s)

# Network activity detection
SCREENSHOT_NETWORK_CHECK_INTERVAL=100       # Check network every 100ms
SCREENSHOT_NETWORK_IDLE_THRESHOLD=500       # Consider idle after 500ms
SCREENSHOT_MAX_NETWORK_CHECKS=100           # Maximum network checks

# Lazy loading detection
SCREENSHOT_SCROLL_STEP_SIZE=200             # Scroll 200px per step
SCREENSHOT_SCROLL_STEP_DELAY=200            # 200ms delay between steps

# Layout stability
SCREENSHOT_LAYOUT_CHECK_INTERVAL=100        # Check layout every 100ms
SCREENSHOT_LAYOUT_STABILITY_THRESHOLD=5     # 5 stable checks required

# Content type timeouts
SCREENSHOT_IMAGE_LOAD_TIMEOUT=5000          # Image loading timeout (5s)
SCREENSHOT_VIDEO_LOAD_TIMEOUT=3000          # Video loading timeout (3s)
SCREENSHOT_CANVAS_RENDER_TIMEOUT=2000       # Canvas rendering timeout (2s)

# Framework specific
SCREENSHOT_REACT_HYDRATION_TIMEOUT=3000     # React hydration timeout (3s)
SCREENSHOT_VUE_MOUNT_TIMEOUT=2000           # Vue mounting timeout (2s)
SCREENSHOT_ANGULAR_BOOTSTRAP_TIMEOUT=3000   # Angular bootstrap timeout (3s)

# Debug settings
SCREENSHOT_DEBUG_MODE=false                 # Enable detailed debug logging
SCREENSHOT_DEBUG_STEPS=false                # Take debug screenshots at each step
```

### Preset Configurations

The system includes preset configurations for different scenarios:

#### Fast (15s max)
```python
# For simple sites with minimal dynamic content
preset = 'fast'
```

#### Balanced (30s max) - Default
```python
# For most modern websites
preset = 'balanced'
```

#### Thorough (60s max)
```python
# For complex sites with heavy dynamic content
preset = 'thorough'
```

#### SPA Heavy (45s max)
```python
# For Single Page Applications with heavy JavaScript
preset = 'spa_heavy'
```

#### E-commerce (40s max)
```python
# For e-commerce sites with lots of images and lazy loading
preset = 'ecommerce'
```

## Usage

### Basic Usage

The enhanced dynamic content handling is automatically enabled when `wait_for_dynamic=True`:

```python
from screenshot.screenshot_service import ScreenshotService

service = ScreenshotService()
success = await service.capture_screenshot(
    url="https://example.com",
    output_path=Path("screenshot.png"),
    viewport="desktop",
    wait_for_dynamic=True  # Enables enhanced handling
)
```

### Using Presets

```python
from screenshot.config import get_preset_config
from screenshot.dynamic_content_handler import DynamicContentHandler

# Use a preset configuration
config = get_preset_config('spa_heavy')
handler = DynamicContentHandler(config)

# Use with Playwright page
results = await handler.wait_for_complete_page_load(page)
```

### Custom Configuration

```python
from screenshot.dynamic_content_handler import DynamicContentHandler

# Custom configuration
config = {
    'max_wait_time': 45000,  # 45 seconds
    'network_idle_timeout': 4000,  # 4 seconds
    'debug_mode': True,
    'scroll_step_delay': 300  # Slower scrolling for heavy sites
}

handler = DynamicContentHandler(config)
```

## How It Works

The enhanced system follows an 8-step process:

### Step 1: Basic Page Readiness
- Waits for `document.readyState === 'complete'`
- Ensures DOM content is loaded
- Waits for initial load event

### Step 2: Network Activity Detection
- Monitors fetch(), XMLHttpRequest, and WebSocket activity
- Waits for all pending requests to complete
- Ensures network is idle for the specified timeout

### Step 3: Lazy Loading Trigger
- Progressively scrolls through the page
- Triggers Intersection Observer callbacks
- Forces loading of data-src images
- Waits for all lazy-loaded content

### Step 4: Layout Stability
- Monitors DOM layout changes
- Waits for elements to stop moving/resizing
- Ensures layout is stable for required duration

### Step 5: Animation and Transition Handling
- Detects running CSS animations
- Monitors Web Animations API
- Waits for all animations to complete

### Step 6: Framework-Specific Loading
- Detects React, Vue, Angular applications
- Waits for framework-specific loading patterns
- Handles hydration and mounting processes

### Step 7: Final Content Verification
- Verifies all images are loaded
- Checks canvas elements are rendered
- Ensures fonts are loaded
- Validates video elements

### Step 8: Animation Pausing
- Pauses all animations for consistent capture
- Applies CSS to stop transitions
- Ensures stable visual state

## Debugging

### Enable Debug Mode

```bash
export SCREENSHOT_DEBUG_MODE=true
```

This provides detailed logging of each step:

```
🚀 Starting enhanced dynamic content loading...
📄 Step 1: Waiting for basic page readiness...
   ✓ Document ready state is complete
   ✓ Load event fired
   ✓ DOM content loaded
🌐 Step 2: Waiting for network activity to settle...
   🔄 Network activity: 2 pending, 150ms since last activity
   ✓ Network idle for 3000ms
🔄 Step 3: Triggering and waiting for lazy loading...
   ✓ Lazy loading content triggered and loaded
📐 Step 4: Waiting for layout stability...
   ✓ Layout stable for 5 consecutive checks
🎬 Step 5: Handling animations and transitions...
   ✓ Animations and transitions completed
⚛️ Step 6: Handling framework-specific loading...
   ✓ Framework-specific loading completed
🔍 Step 7: Final content verification...
   📊 Content state: 15/15 images, 2/2 videos, 1/1 canvases
   ✓ Fonts loaded
⏸️ Step 8: Pausing animations for capture...
   ✓ Animations paused for capture
✅ Enhanced dynamic content loading completed in 8450ms
```

### Debug Screenshots

```bash
export SCREENSHOT_DEBUG_STEPS=true
```

This takes screenshots at each major step for analysis.

## Testing

Run the test suite to validate the implementation:

```bash
python test_enhanced_dynamic_content.py
```

This tests:
- Configuration presets
- Dynamic content handler functionality
- Screenshot service integration
- Real-world scenarios

## Performance Impact

The enhanced system adds wait time but ensures accuracy:

- **Fast preset**: ~5-15 seconds additional wait
- **Balanced preset**: ~10-30 seconds additional wait
- **Thorough preset**: ~20-60 seconds additional wait

The trade-off is between speed and accuracy. For regression testing, accuracy is typically more important than speed.

## Troubleshooting

### Common Issues

1. **Screenshots still incomplete**
   - Try the 'thorough' preset
   - Increase `max_wait_time`
   - Enable debug mode to see what's happening

2. **Too slow for CI/CD**
   - Use the 'fast' preset
   - Reduce timeout values
   - Consider running tests in parallel

3. **Framework not detected**
   - Check framework-specific timeout settings
   - Enable debug mode to see detection logs
   - Add custom detection logic if needed

### Custom Framework Support

To add support for a new framework:

```python
# In _handle_framework_specific_loading method
custom_ready = await page.evaluate("""
    () => {
        if (typeof MyFramework !== 'undefined') {
            return new Promise((resolve) => {
                // Custom framework detection logic
                MyFramework.onReady(() => resolve(true));
                setTimeout(() => resolve(false), 5000);
            });
        }
        return Promise.resolve(true);
    }
""")
```

## Migration from Old System

The new system is backward compatible. To migrate:

1. **No code changes required** - existing calls work automatically
2. **Optional**: Set environment variables for fine-tuning
3. **Optional**: Use presets for specific scenarios
4. **Optional**: Enable debug mode during migration

## Best Practices

1. **Choose appropriate presets** based on your application type
2. **Enable debug mode** during initial setup
3. **Monitor performance** and adjust timeouts as needed
4. **Test with real content** not just demo pages
5. **Use CI/CD environment variables** for different environments

## Conclusion

The enhanced dynamic content handling system provides robust, reliable screenshot capture for modern web applications. It automatically handles the complexities of dynamic content loading while remaining configurable for specific needs.

For most users, simply enabling `wait_for_dynamic=True` will provide significantly improved screenshot accuracy with no additional configuration required.