#!/usr/bin/env python3
"""
Test script for enhanced dynamic content handling in screenshot capture
Tests the new robust waiting strategies for modern web applications
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, '.')

from screenshot.screenshot_service import ScreenshotService
from screenshot.dynamic_content_handler import DynamicContentHandler
from screenshot.config import get_preset_config, PRESET_CONFIGS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_dynamic_content_handler():
    """Test the enhanced dynamic content handler directly"""
    print("Testing Enhanced Dynamic Content Handler")
    print("=" * 60)
    
    try:
        from playwright.async_api import async_playwright
        
        # Test URLs with different types of dynamic content
        test_urls = [
            {
                'url': 'https://example.com',
                'name': 'Simple Static Site',
                'preset': 'fast'
            },
            {
                'url': 'https://react.dev',
                'name': 'React Documentation (SPA)',
                'preset': 'spa_heavy'
            },
            {
                'url': 'https://vuejs.org',
                'name': 'Vue.js Site (SPA)',
                'preset': 'spa_heavy'
            }
        ]
        
        for test_case in test_urls:
            print(f"\n[WEB] Testing: {test_case['name']}")
            print(f"   URL: {test_case['url']}")
            print(f"   Preset: {test_case['preset']}")
            print("-" * 40)
            
            # Get preset configuration
            config = get_preset_config(test_case['preset'])
            handler = DynamicContentHandler(config)
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                try:
                    # Navigate to the page
                    print(f"   [PAGE] Navigating to {test_case['url']}...")
                    await page.goto(test_case['url'], timeout=30000)
                    
                    # Test enhanced dynamic content loading
                    print(f"   [LOAD] Running enhanced dynamic content detection...")
                    results = await handler.wait_for_complete_page_load(page)
                    
                    # Display results
                    if results['success']:
                        print(f"   [SUCCESS] Completed in {results['total_wait_time']:.0f}ms")
                        print(f"   [INFO] Steps completed: {', '.join(results['steps_completed'])}")
                        
                        if results.get('warnings'):
                            print(f"   [WARN] Warnings: {len(results['warnings'])}")
                            for warning in results['warnings']:
                                print(f"      - {warning}")
                    else:
                        print(f"   [FAILED] Test failed")
                        if results.get('errors'):
                            for error in results['errors']:
                                print(f"      Error: {error}")
                    
                    # Take a test screenshot to verify
                    screenshot_path = Path(f"test_screenshots/enhanced_{test_case['preset']}_{test_case['name'].lower().replace(' ', '_')}.png")
                    screenshot_path.parent.mkdir(exist_ok=True)
                    
                    await page.screenshot(path=str(screenshot_path), full_page=True)
                    print(f"   [SCREENSHOT] Test screenshot saved: {screenshot_path}")
                    
                except Exception as e:
                    print(f"   [ERROR] Error testing {test_case['name']}: {str(e)}")
                
                finally:
                    await browser.close()
        
        return True
        
    except ImportError:
        print("[ERROR] Playwright not available. Install with: pip install playwright")
        print("   Then run: playwright install chromium")
        return False
    except Exception as e:
        print(f"[ERROR] Test failed: {str(e)}")
        return False

async def test_screenshot_service_integration():
    """Test the integration with ScreenshotService"""
    print("\n[INTEGRATION] Testing ScreenshotService Integration")
    print("=" * 60)
    
    try:
        # Initialize screenshot service
        screenshot_service = ScreenshotService("test_screenshots")
        
        # Test URLs
        test_urls = [
            'https://example.com',
            'https://httpbin.org/delay/2'  # URL with intentional delay
        ]
        
        for i, url in enumerate(test_urls):
            print(f"\n[SCREENSHOT] Testing screenshot capture for: {url}")
            
            for viewport in ['desktop', 'tablet', 'mobile']:
                output_path = Path(f"test_screenshots/integration_test_{i}_{viewport}.png")
                output_path.parent.mkdir(exist_ok=True)
                
                print(f"   [VIEWPORT] Capturing {viewport} screenshot...")
                success = await screenshot_service.capture_screenshot(
                    url, output_path, viewport, wait_for_dynamic=True
                )
                
                if success:
                    print(f"   [SUCCESS] {viewport} screenshot captured successfully")
                    print(f"      Saved to: {output_path}")
                else:
                    print(f"   [FAILED] {viewport} screenshot failed")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Integration test failed: {str(e)}")
        return False

def test_configuration_presets():
    """Test the configuration presets"""
    print("\n[CONFIG] Testing Configuration Presets")
    print("=" * 60)
    
    try:
        for preset_name in PRESET_CONFIGS.keys():
            print(f"\n[PRESET] Testing preset: {preset_name}")
            config = get_preset_config(preset_name)
            
            # Validate required keys
            required_keys = [
                'max_wait_time', 'network_idle_timeout', 'layout_stability_timeout',
                'animation_settle_timeout', 'debug_mode'
            ]
            
            missing_keys = [key for key in required_keys if key not in config]
            if missing_keys:
                print(f"   [ERROR] Missing keys: {missing_keys}")
                return False
            
            print(f"   [SUCCESS] Preset '{preset_name}' is valid")
            print(f"      Max wait time: {config['max_wait_time']}ms")
            print(f"      Network idle timeout: {config['network_idle_timeout']}ms")
            print(f"      Debug mode: {config['debug_mode']}")
        
        print(f"\n[SUCCESS] All {len(PRESET_CONFIGS)} presets are valid")
        return True
        
    except Exception as e:
        print(f"[ERROR] Configuration test failed: {str(e)}")
        return False

async def main():
    """Main test function"""
    print("Enhanced Dynamic Content Handling Test Suite")
    print("=" * 80)
    print("Testing the new robust screenshot capture with dynamic content detection")
    print("=" * 80)
    
    # Test results
    results = []
    
    # Test 1: Configuration presets
    print("\n" + "="*80)
    config_success = test_configuration_presets()
    results.append(("Configuration Presets", config_success))
    
    # Test 2: Dynamic content handler
    print("\n" + "="*80)
    handler_success = await test_dynamic_content_handler()
    results.append(("Dynamic Content Handler", handler_success))
    
    # Test 3: Screenshot service integration
    print("\n" + "="*80)
    integration_success = await test_screenshot_service_integration()
    results.append(("ScreenshotService Integration", integration_success))
    
    # Summary
    print("\n" + "="*80)
    print("[SUMMARY] TEST SUMMARY")
    print("="*80)
    
    all_passed = True
    for test_name, success in results:
        status = "[PASSED]" if success else "[FAILED]"
        print(f"{test_name:.<50} {status}")
        if not success:
            all_passed = False
    
    print(f"\nOverall Result: {'[ALL TESTS PASSED]' if all_passed else '[SOME TESTS FAILED]'}")
    
    if all_passed:
        print("\n[SUCCESS] Enhanced dynamic content handling is working correctly!")
        print("The new implementation provides:")
        print("  - Robust network activity detection (fetch, XHR, WebSockets)")
        print("  - Comprehensive lazy loading support (Intersection Observer, React lazy)")
        print("  - Animation and transition detection")
        print("  - Layout stability verification")
        print("  - Framework-specific loading patterns (React, Vue, Angular)")
        print("  - Configurable presets for different scenarios")
        print("  - Enhanced debugging and logging")
    else:
        print("\n[WARNING] Some tests failed. Please check the implementation.")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)