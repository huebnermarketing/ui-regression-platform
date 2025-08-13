"""
Configuration settings for enhanced screenshot capture with dynamic content handling
"""

import os
from typing import Dict, Any


class ScreenshotConfig:
    """Configuration class for screenshot capture settings"""
    
    @staticmethod
    def get_dynamic_content_config() -> Dict[str, Any]:
        """
        Get configuration for dynamic content handling
        
        Returns:
            Dict with all dynamic content handling settings
        """
        return {
            # Basic timing settings
            'max_wait_time': int(os.getenv('SCREENSHOT_MAX_WAIT_TIME', '30000')),  # 30 seconds max
            'network_idle_timeout': int(os.getenv('SCREENSHOT_NETWORK_IDLE_TIMEOUT', '3000')),  # 3 seconds
            'layout_stability_timeout': int(os.getenv('SCREENSHOT_LAYOUT_STABILITY_TIMEOUT', '2000')),  # 2 seconds
            'animation_settle_timeout': int(os.getenv('SCREENSHOT_ANIMATION_SETTLE_TIMEOUT', '1500')),  # 1.5 seconds
            
            # Network activity detection
            'network_check_interval': int(os.getenv('SCREENSHOT_NETWORK_CHECK_INTERVAL', '100')),  # 100ms
            'network_idle_threshold': int(os.getenv('SCREENSHOT_NETWORK_IDLE_THRESHOLD', '500')),  # 500ms
            'max_network_checks': int(os.getenv('SCREENSHOT_MAX_NETWORK_CHECKS', '100')),  # 100 checks max
            
            # Lazy loading detection
            'scroll_step_size': int(os.getenv('SCREENSHOT_SCROLL_STEP_SIZE', '200')),  # 200px per step
            'scroll_step_delay': int(os.getenv('SCREENSHOT_SCROLL_STEP_DELAY', '200')),  # 200ms delay
            'lazy_load_trigger_distance': int(os.getenv('SCREENSHOT_LAZY_LOAD_TRIGGER_DISTANCE', '1000')),  # 1000px
            
            # Layout stability
            'layout_check_interval': int(os.getenv('SCREENSHOT_LAYOUT_CHECK_INTERVAL', '100')),  # 100ms
            'layout_stability_threshold': int(os.getenv('SCREENSHOT_LAYOUT_STABILITY_THRESHOLD', '5')),  # 5 stable checks
            'layout_change_threshold': int(os.getenv('SCREENSHOT_LAYOUT_CHANGE_THRESHOLD', '1')),  # 1px minimum change
            
            # Animation detection
            'animation_check_interval': int(os.getenv('SCREENSHOT_ANIMATION_CHECK_INTERVAL', '100')),  # 100ms
            'animation_stability_checks': int(os.getenv('SCREENSHOT_ANIMATION_STABILITY_CHECKS', '10')),  # 10 checks
            
            # Content type specific timeouts
            'image_load_timeout': int(os.getenv('SCREENSHOT_IMAGE_LOAD_TIMEOUT', '5000')),  # 5 seconds
            'video_load_timeout': int(os.getenv('SCREENSHOT_VIDEO_LOAD_TIMEOUT', '3000')),  # 3 seconds
            'canvas_render_timeout': int(os.getenv('SCREENSHOT_CANVAS_RENDER_TIMEOUT', '2000')),  # 2 seconds
            'font_load_timeout': int(os.getenv('SCREENSHOT_FONT_LOAD_TIMEOUT', '3000')),  # 3 seconds
            
            # Framework specific settings
            'react_hydration_timeout': int(os.getenv('SCREENSHOT_REACT_HYDRATION_TIMEOUT', '3000')),  # 3 seconds
            'vue_mount_timeout': int(os.getenv('SCREENSHOT_VUE_MOUNT_TIMEOUT', '2000')),  # 2 seconds
            'angular_bootstrap_timeout': int(os.getenv('SCREENSHOT_ANGULAR_BOOTSTRAP_TIMEOUT', '3000')),  # 3 seconds
            
            # Debug settings
            'debug_mode': os.getenv('SCREENSHOT_DEBUG_MODE', 'false').lower() == 'true',
            'screenshot_debug_steps': os.getenv('SCREENSHOT_DEBUG_STEPS', 'false').lower() == 'true',
        }
    
    @staticmethod
    def get_viewport_config() -> Dict[str, Dict[str, int]]:
        """
        Get viewport configurations
        
        Returns:
            Dict with viewport settings
        """
        return {
            'desktop': {
                'width': int(os.getenv('SCREENSHOT_DESKTOP_WIDTH', '1920')),
                'height': int(os.getenv('SCREENSHOT_DESKTOP_HEIGHT', '1080'))
            },
            'tablet': {
                'width': int(os.getenv('SCREENSHOT_TABLET_WIDTH', '768')),
                'height': int(os.getenv('SCREENSHOT_TABLET_HEIGHT', '1024'))
            },
            'mobile': {
                'width': int(os.getenv('SCREENSHOT_MOBILE_WIDTH', '375')),
                'height': int(os.getenv('SCREENSHOT_MOBILE_HEIGHT', '667'))
            }
        }
    
    @staticmethod
    def get_browser_config() -> Dict[str, Any]:
        """
        Get browser configuration settings
        
        Returns:
            Dict with browser settings
        """
        return {
            'headless': os.getenv('SCREENSHOT_HEADLESS', 'true').lower() == 'true',
            'device_pixel_ratio': float(os.getenv('SCREENSHOT_DEVICE_PIXEL_RATIO', '1.0')),
            'timeout': int(os.getenv('SCREENSHOT_TIMEOUT', '30000')),  # 30 seconds
            'wait_for_dynamic': os.getenv('SCREENSHOT_WAIT_FOR_DYNAMIC', 'true').lower() == 'true',
            'browser_args': [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
        }


# Preset configurations for different scenarios
PRESET_CONFIGS = {
    'fast': {
        'max_wait_time': 15000,  # 15 seconds
        'network_idle_timeout': 1500,  # 1.5 seconds
        'layout_stability_timeout': 1000,  # 1 second
        'animation_settle_timeout': 500,  # 0.5 seconds
        'scroll_step_delay': 100,  # 100ms
        'layout_stability_threshold': 3,  # 3 checks
        'debug_mode': False
    },
    'balanced': {
        'max_wait_time': 30000,  # 30 seconds
        'network_idle_timeout': 3000,  # 3 seconds
        'layout_stability_timeout': 2000,  # 2 seconds
        'animation_settle_timeout': 1500,  # 1.5 seconds
        'scroll_step_delay': 200,  # 200ms
        'layout_stability_threshold': 5,  # 5 checks
        'debug_mode': False
    },
    'thorough': {
        'max_wait_time': 60000,  # 60 seconds
        'network_idle_timeout': 5000,  # 5 seconds
        'layout_stability_timeout': 3000,  # 3 seconds
        'animation_settle_timeout': 3000,  # 3 seconds
        'scroll_step_delay': 300,  # 300ms
        'layout_stability_threshold': 10,  # 10 checks
        'debug_mode': True
    },
    'spa_heavy': {
        # For Single Page Applications with heavy JavaScript
        'max_wait_time': 45000,  # 45 seconds
        'network_idle_timeout': 4000,  # 4 seconds
        'layout_stability_timeout': 3000,  # 3 seconds
        'animation_settle_timeout': 2000,  # 2 seconds
        'react_hydration_timeout': 5000,  # 5 seconds
        'vue_mount_timeout': 4000,  # 4 seconds
        'angular_bootstrap_timeout': 5000,  # 5 seconds
        'scroll_step_delay': 250,  # 250ms
        'layout_stability_threshold': 8,  # 8 checks
        'debug_mode': False
    },
    'ecommerce': {
        # For e-commerce sites with lots of images and lazy loading
        'max_wait_time': 40000,  # 40 seconds
        'network_idle_timeout': 3500,  # 3.5 seconds
        'layout_stability_timeout': 2500,  # 2.5 seconds
        'animation_settle_timeout': 2000,  # 2 seconds
        'image_load_timeout': 8000,  # 8 seconds for product images
        'scroll_step_delay': 300,  # 300ms for lazy loading
        'layout_stability_threshold': 6,  # 6 checks
        'debug_mode': False
    }
}


def get_preset_config(preset_name: str) -> Dict[str, Any]:
    """
    Get a preset configuration
    
    Args:
        preset_name: Name of the preset ('fast', 'balanced', 'thorough', 'spa_heavy', 'ecommerce')
        
    Returns:
        Dict with preset configuration
    """
    base_config = ScreenshotConfig.get_dynamic_content_config()
    preset = PRESET_CONFIGS.get(preset_name, {})
    
    # Merge preset with base config
    base_config.update(preset)
    return base_config