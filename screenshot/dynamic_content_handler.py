"""
Enhanced Dynamic Content Handler for Screenshot Capture
Provides robust waiting strategies for modern web applications with complex dynamic content
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from playwright.async_api import Page


class DynamicContentHandler:
    """
    Enhanced handler for waiting for dynamic content to fully load before taking screenshots.
    Addresses modern web application challenges including:
    - API-fetched content (fetch, XHR, WebSockets)
    - Lazy loading (Intersection Observer, React lazy components)
    - Animations and transitions
    - Layout stability detection
    - Framework-specific loading patterns
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the dynamic content handler
        
        Args:
            config: Configuration dictionary with timing and detection settings
        """
        self.logger = logging.getLogger(__name__)
        
        # Default configuration with enhanced settings
        self.config = {
            # Basic timing settings
            'max_wait_time': 30000,  # Maximum total wait time (30s)
            'network_idle_timeout': 3000,  # Network idle timeout (3s)
            'layout_stability_timeout': 2000,  # Layout stability timeout (2s)
            'animation_settle_timeout': 1500,  # Animation settle timeout (1.5s)
            
            # Network activity detection
            'network_check_interval': 100,  # Check network activity every 100ms
            'network_idle_threshold': 500,  # Consider idle after 500ms of no activity
            'max_network_checks': 100,  # Maximum network activity checks
            
            # Lazy loading detection
            'scroll_step_size': 200,  # Pixels to scroll per step
            'scroll_step_delay': 200,  # Delay between scroll steps (ms)
            'lazy_load_trigger_distance': 1000,  # Distance from viewport to trigger lazy loading
            
            # Layout stability
            'layout_check_interval': 100,  # Check layout stability every 100ms
            'layout_stability_threshold': 5,  # Number of stable checks required
            'layout_change_threshold': 1,  # Minimum pixel change to consider unstable
            
            # Animation detection
            'animation_check_interval': 100,  # Check animations every 100ms
            'animation_stability_checks': 10,  # Number of stable checks for animations
            
            # Content type specific timeouts
            'image_load_timeout': 5000,  # Image loading timeout
            'video_load_timeout': 3000,  # Video loading timeout
            'canvas_render_timeout': 2000,  # Canvas rendering timeout
            'font_load_timeout': 3000,  # Font loading timeout
            
            # Framework specific settings
            'react_hydration_timeout': 3000,  # React hydration timeout
            'vue_mount_timeout': 2000,  # Vue mounting timeout
            'angular_bootstrap_timeout': 3000,  # Angular bootstrap timeout
            
            # Debug settings
            'debug_mode': False,  # Enable detailed debug logging
            'screenshot_debug_steps': False,  # Take debug screenshots at each step
        }
        
        # Update with provided config
        if config:
            self.config.update(config)
    
    async def wait_for_complete_page_load(self, page: Page) -> Dict[str, Any]:
        """
        Main method to wait for complete page load with all dynamic content
        
        Args:
            page: Playwright page object
            
        Returns:
            Dict with loading results and metrics
        """
        start_time = asyncio.get_event_loop().time()
        results = {
            'success': False,
            'total_wait_time': 0,
            'steps_completed': [],
            'warnings': [],
            'errors': []
        }
        
        try:
            self.logger.info("🚀 Starting enhanced dynamic content loading...")
            
            # Step 1: Basic page readiness
            await self._wait_for_basic_readiness(page, results)
            
            # Step 2: Enhanced network activity detection
            await self._wait_for_network_idle(page, results)
            
            # Step 3: Trigger and wait for lazy loading
            await self._trigger_and_wait_for_lazy_loading(page, results)
            
            # Step 4: Wait for layout stability
            await self._wait_for_layout_stability(page, results)
            
            # Step 5: Handle animations and transitions
            await self._handle_animations_and_transitions(page, results)
            
            # Step 6: Framework-specific handling
            await self._handle_framework_specific_loading(page, results)
            
            # Step 7: Final content verification
            await self._verify_final_content_state(page, results)
            
            # Step 8: Pause animations for consistent capture
            await self._pause_animations_for_capture(page, results)
            
            results['success'] = True
            results['total_wait_time'] = (asyncio.get_event_loop().time() - start_time) * 1000
            
            self.logger.info(f"✅ Enhanced dynamic content loading completed in {results['total_wait_time']:.0f}ms")
            
        except Exception as e:
            results['errors'].append(f"Dynamic content loading failed: {str(e)}")
            self.logger.error(f"❌ Dynamic content loading failed: {str(e)}")
            
        return results
    
    async def _wait_for_basic_readiness(self, page: Page, results: Dict) -> None:
        """Wait for basic page readiness indicators"""
        self.logger.info("📄 Step 1: Waiting for basic page readiness...")
        
        try:
            # Wait for document ready state
            await page.wait_for_function("document.readyState === 'complete'", timeout=10000)
            self.logger.info("   ✓ Document ready state is complete")
            
            # Wait for initial load event
            await page.wait_for_load_state("load", timeout=10000)
            self.logger.info("   ✓ Load event fired")
            
            # Wait for DOM content loaded
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
            self.logger.info("   ✓ DOM content loaded")
            
            results['steps_completed'].append('basic_readiness')
            
        except Exception as e:
            results['warnings'].append(f"Basic readiness check failed: {str(e)}")
            self.logger.warning(f"   ⚠️ Basic readiness check failed: {str(e)}")
    
    async def _wait_for_network_idle(self, page: Page, results: Dict) -> None:
        """Enhanced network activity detection for modern APIs"""
        self.logger.info("🌐 Step 2: Waiting for network activity to settle...")
        
        try:
            # Install network activity monitor
            await page.evaluate("""
                () => {
                    window._networkActivity = {
                        pendingRequests: 0,
                        lastActivity: Date.now(),
                        requests: [],
                        websockets: []
                    };
                    
                    // Monitor fetch requests
                    const originalFetch = window.fetch;
                    window.fetch = function(...args) {
                        window._networkActivity.pendingRequests++;
                        window._networkActivity.lastActivity = Date.now();
                        window._networkActivity.requests.push({type: 'fetch', url: args[0], start: Date.now()});
                        
                        return originalFetch.apply(this, args).finally(() => {
                            window._networkActivity.pendingRequests--;
                            window._networkActivity.lastActivity = Date.now();
                        });
                    };
                    
                    // Monitor XMLHttpRequest
                    const originalXHROpen = XMLHttpRequest.prototype.open;
                    const originalXHRSend = XMLHttpRequest.prototype.send;
                    
                    XMLHttpRequest.prototype.open = function(...args) {
                        this._url = args[1];
                        return originalXHROpen.apply(this, args);
                    };
                    
                    XMLHttpRequest.prototype.send = function(...args) {
                        window._networkActivity.pendingRequests++;
                        window._networkActivity.lastActivity = Date.now();
                        window._networkActivity.requests.push({type: 'xhr', url: this._url, start: Date.now()});
                        
                        this.addEventListener('loadend', () => {
                            window._networkActivity.pendingRequests--;
                            window._networkActivity.lastActivity = Date.now();
                        });
                        
                        return originalXHRSend.apply(this, args);
                    };
                    
                    // Monitor WebSocket connections
                    const originalWebSocket = window.WebSocket;
                    window.WebSocket = function(...args) {
                        const ws = new originalWebSocket(...args);
                        window._networkActivity.websockets.push(ws);
                        
                        ws.addEventListener('open', () => {
                            window._networkActivity.lastActivity = Date.now();
                        });
                        
                        ws.addEventListener('message', () => {
                            window._networkActivity.lastActivity = Date.now();
                        });
                        
                        return ws;
                    };
                }
            """)
            
            # Wait for network to be idle
            network_idle_start = None
            check_count = 0
            max_checks = self.config['max_network_checks']
            
            while check_count < max_checks:
                network_status = await page.evaluate("""
                    () => {
                        const now = Date.now();
                        const activity = window._networkActivity || {pendingRequests: 0, lastActivity: now};
                        
                        return {
                            pendingRequests: activity.pendingRequests,
                            timeSinceLastActivity: now - activity.lastActivity,
                            totalRequests: activity.requests ? activity.requests.length : 0,
                            activeWebSockets: activity.websockets ? activity.websockets.filter(ws => ws.readyState === 1).length : 0
                        };
                    }
                """)
                
                is_idle = (
                    network_status['pendingRequests'] == 0 and
                    network_status['timeSinceLastActivity'] > self.config['network_idle_threshold'] and
                    network_status['activeWebSockets'] == 0
                )
                
                if is_idle:
                    if network_idle_start is None:
                        network_idle_start = asyncio.get_event_loop().time()
                    elif (asyncio.get_event_loop().time() - network_idle_start) * 1000 >= self.config['network_idle_timeout']:
                        self.logger.info(f"   ✓ Network idle for {self.config['network_idle_timeout']}ms")
                        break
                else:
                    network_idle_start = None
                    if self.config['debug_mode']:
                        self.logger.debug(f"   🔄 Network activity: {network_status['pendingRequests']} pending, "
                                        f"{network_status['timeSinceLastActivity']}ms since last activity")
                
                await asyncio.sleep(self.config['network_check_interval'] / 1000)
                check_count += 1
            
            # Also wait for Playwright's network idle
            await page.wait_for_load_state("networkidle", timeout=self.config['network_idle_timeout'])
            
            results['steps_completed'].append('network_idle')
            
        except Exception as e:
            results['warnings'].append(f"Network idle detection failed: {str(e)}")
            self.logger.warning(f"   ⚠️ Network idle detection failed: {str(e)}")
    
    async def _trigger_and_wait_for_lazy_loading(self, page: Page, results: Dict) -> None:
        """Trigger and wait for lazy loading content"""
        self.logger.info("🔄 Step 3: Triggering and waiting for lazy loading...")
        
        try:
            # Install lazy loading detection
            await page.evaluate("""
                () => {
                    window._lazyLoadingActivity = {
                        observedElements: 0,
                        loadedElements: 0,
                        pendingLoads: 0
                    };
                    
                    // Monitor Intersection Observer usage
                    const originalIntersectionObserver = window.IntersectionObserver;
                    window.IntersectionObserver = function(callback, options) {
                        const observer = new originalIntersectionObserver((entries, obs) => {
                            entries.forEach(entry => {
                                if (entry.isIntersecting) {
                                    window._lazyLoadingActivity.observedElements++;
                                }
                            });
                            callback(entries, obs);
                        }, options);
                        
                        return observer;
                    };
                }
            """)
            
            # Progressive scroll to trigger lazy loading
            await self._progressive_scroll_for_lazy_loading(page)
            
            # Wait for lazy loaded images
            await page.evaluate(f"""
                () => {{
                    return new Promise((resolve) => {{
                        const images = Array.from(document.querySelectorAll('img[loading="lazy"], img[data-src], img[data-lazy]'));
                        const promises = images.map(img => {{
                            if (img.complete && img.naturalWidth > 0) return Promise.resolve();
                            
                            return new Promise(imgResolve => {{
                                const timeout = setTimeout(() => imgResolve(), {self.config['image_load_timeout']});
                                img.addEventListener('load', () => {{
                                    clearTimeout(timeout);
                                    imgResolve();
                                }}, {{ once: true }});
                                img.addEventListener('error', () => {{
                                    clearTimeout(timeout);
                                    imgResolve();
                                }}, {{ once: true }});
                                
                                // Trigger loading if data-src exists
                                if (img.dataset.src && !img.src) {{
                                    img.src = img.dataset.src;
                                }}
                            }});
                        }});
                        
                        Promise.all(promises).then(() => {{
                            // Force any remaining lazy loading
                            images.forEach(img => {{
                                if (img.dataset.src && !img.src) {{
                                    img.src = img.dataset.src;
                                }}
                                img.removeAttribute('loading');
                            }});
                            
                            setTimeout(resolve, 500); // Additional buffer
                        }});
                    }});
                }}
            """)
            
            self.logger.info("   ✓ Lazy loading content triggered and loaded")
            results['steps_completed'].append('lazy_loading')
            
        except Exception as e:
            results['warnings'].append(f"Lazy loading handling failed: {str(e)}")
            self.logger.warning(f"   ⚠️ Lazy loading handling failed: {str(e)}")
    
    async def _progressive_scroll_for_lazy_loading(self, page: Page) -> None:
        """Progressive scroll to trigger all lazy loading"""
        try:
            scroll_info = await page.evaluate(f"""
                () => {{
                    const scrollHeight = document.documentElement.scrollHeight;
                    const viewportHeight = window.innerHeight;
                    const stepSize = {self.config['scroll_step_size']};
                    
                    return {{
                        scrollHeight,
                        viewportHeight,
                        steps: Math.ceil(scrollHeight / stepSize)
                    }};
                }}
            """)
            
            # Scroll progressively to trigger lazy loading
            for step in range(scroll_info['steps']):
                scroll_position = step * self.config['scroll_step_size']
                
                await page.evaluate(f"window.scrollTo(0, {scroll_position})")
                await asyncio.sleep(self.config['scroll_step_delay'] / 1000)
                
                # Check if we've reached the bottom
                current_scroll = await page.evaluate("window.pageYOffset + window.innerHeight")
                if current_scroll >= scroll_info['scrollHeight']:
                    break
            
            # Scroll back to top
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(0.5)
            
        except Exception as e:
            self.logger.warning(f"Progressive scroll failed: {str(e)}")
    
    async def _wait_for_layout_stability(self, page: Page, results: Dict) -> None:
        """Wait for layout to be stable (no DOM changes)"""
        self.logger.info("📐 Step 4: Waiting for layout stability...")
        
        try:
            stable_checks = 0
            required_stable_checks = self.config['layout_stability_threshold']
            
            # Install layout change detection
            await page.evaluate("""
                () => {
                    window._layoutStability = {
                        lastLayoutHash: '',
                        changeCount: 0
                    };
                    
                    function getLayoutHash() {
                        const elements = Array.from(document.querySelectorAll('*')).slice(0, 100); // Sample elements
                        return elements.map(el => {
                            const rect = el.getBoundingClientRect();
                            return `${el.tagName}:${rect.x}:${rect.y}:${rect.width}:${rect.height}`;
                        }).join('|');
                    }
                    
                    window._layoutStability.lastLayoutHash = getLayoutHash();
                }
            """)
            
            while stable_checks < required_stable_checks:
                await asyncio.sleep(self.config['layout_check_interval'] / 1000)
                
                layout_changed = await page.evaluate("""
                    () => {
                        function getLayoutHash() {
                            const elements = Array.from(document.querySelectorAll('*')).slice(0, 100);
                            return elements.map(el => {
                                const rect = el.getBoundingClientRect();
                                return `${el.tagName}:${rect.x}:${rect.y}:${rect.width}:${rect.height}`;
                            }).join('|');
                        }
                        
                        const currentHash = getLayoutHash();
                        const changed = currentHash !== window._layoutStability.lastLayoutHash;
                        
                        if (changed) {
                            window._layoutStability.changeCount++;
                            window._layoutStability.lastLayoutHash = currentHash;
                        }
                        
                        return changed;
                    }
                """)
                
                if layout_changed:
                    stable_checks = 0  # Reset counter
                    if self.config['debug_mode']:
                        self.logger.debug("   🔄 Layout changed, resetting stability counter")
                else:
                    stable_checks += 1
                    if self.config['debug_mode']:
                        self.logger.debug(f"   ✓ Layout stable check {stable_checks}/{required_stable_checks}")
            
            self.logger.info(f"   ✓ Layout stable for {required_stable_checks} consecutive checks")
            results['steps_completed'].append('layout_stability')
            
        except Exception as e:
            results['warnings'].append(f"Layout stability detection failed: {str(e)}")
            self.logger.warning(f"   ⚠️ Layout stability detection failed: {str(e)}")
    
    async def _handle_animations_and_transitions(self, page: Page, results: Dict) -> None:
        """Wait for animations and transitions to complete"""
        self.logger.info("🎬 Step 5: Handling animations and transitions...")
        
        try:
            # Wait for CSS animations and transitions to complete
            await page.evaluate(f"""
                () => {{
                    return new Promise((resolve) => {{
                        let animationCount = 0;
                        let transitionCount = 0;
                        
                        // Count running animations
                        document.getAnimations().forEach(animation => {{
                            if (animation.playState === 'running') {{
                                animationCount++;
                                animation.addEventListener('finish', () => {{
                                    animationCount--;
                                }}, {{ once: true }});
                            }}
                        }});
                        
                        // Monitor for new animations
                        const observer = new MutationObserver(() => {{
                            document.getAnimations().forEach(animation => {{
                                if (animation.playState === 'running') {{
                                    animationCount++;
                                    animation.addEventListener('finish', () => {{
                                        animationCount--;
                                    }}, {{ once: true }});
                                }}
                            }});
                        }});
                        
                        observer.observe(document.body, {{ childList: true, subtree: true }});
                        
                        // Check periodically if animations are done
                        const checkAnimations = () => {{
                            const runningAnimations = document.getAnimations().filter(a => a.playState === 'running').length;
                            
                            if (runningAnimations === 0) {{
                                observer.disconnect();
                                setTimeout(resolve, {self.config['animation_settle_timeout']});
                            }} else {{
                                setTimeout(checkAnimations, {self.config['animation_check_interval']});
                            }}
                        }};
                        
                        // Start checking after a brief delay
                        setTimeout(checkAnimations, 100);
                        
                        // Timeout after max wait time
                        setTimeout(() => {{
                            observer.disconnect();
                            resolve();
                        }}, {self.config['max_wait_time']});
                    }});
                }}
            """)
            
            self.logger.info("   ✓ Animations and transitions completed")
            results['steps_completed'].append('animations_transitions')
            
        except Exception as e:
            results['warnings'].append(f"Animation handling failed: {str(e)}")
            self.logger.warning(f"   ⚠️ Animation handling failed: {str(e)}")
    
    async def _handle_framework_specific_loading(self, page: Page, results: Dict) -> None:
        """Handle framework-specific loading patterns"""
        self.logger.info("⚛️ Step 6: Handling framework-specific loading...")
        
        try:
            # Detect and handle React
            react_ready = await page.evaluate(f"""
                () => {{
                    if (typeof React !== 'undefined' || document.querySelector('[data-reactroot]')) {{
                        return new Promise((resolve) => {{
                            // Wait for React hydration
                            if (window.React && window.React.version) {{
                                // React is present, wait for hydration
                                setTimeout(() => {{
                                    // Check if React components are hydrated
                                    const reactElements = document.querySelectorAll('[data-reactroot] *');
                                    const hydrated = Array.from(reactElements).every(el => 
                                        !el.hasAttribute('data-react-checksum') || el.innerHTML.trim() !== ''
                                    );
                                    resolve(hydrated);
                                }}, {self.config['react_hydration_timeout']});
                            }} else {{
                                resolve(true);
                            }}
                        }});
                    }}
                    return Promise.resolve(true);
                }}
            """)
            
            # Detect and handle Vue
            vue_ready = await page.evaluate(f"""
                () => {{
                    if (typeof Vue !== 'undefined' || document.querySelector('[data-v-]')) {{
                        return new Promise((resolve) => {{
                            setTimeout(() => {{
                                // Check if Vue components are mounted
                                const vueElements = document.querySelectorAll('[data-v-]');
                                const mounted = vueElements.length === 0 || 
                                    Array.from(vueElements).every(el => el.innerHTML.trim() !== '');
                                resolve(mounted);
                            }}, {self.config['vue_mount_timeout']});
                        }});
                    }}
                    return Promise.resolve(true);
                }}
            """)
            
            # Detect and handle Angular
            angular_ready = await page.evaluate(f"""
                () => {{
                    if (typeof ng !== 'undefined' || document.querySelector('[ng-app], [data-ng-app]')) {{
                        return new Promise((resolve) => {{
                            setTimeout(() => {{
                                // Check if Angular is bootstrapped
                                const angularElements = document.querySelectorAll('[ng-app], [data-ng-app]');
                                const bootstrapped = angularElements.length === 0 || 
                                    Array.from(angularElements).every(el => 
                                        el.classList.contains('ng-scope') || el.innerHTML.trim() !== ''
                                    );
                                resolve(bootstrapped);
                            }}, {self.config['angular_bootstrap_timeout']});
                        }});
                    }}
                    return Promise.resolve(true);
                }}
            """)
            
            if react_ready and vue_ready and angular_ready:
                self.logger.info("   ✓ Framework-specific loading completed")
            else:
                self.logger.info("   ⚠️ Some framework components may not be fully loaded")
            
            results['steps_completed'].append('framework_specific')
            
        except Exception as e:
            results['warnings'].append(f"Framework-specific handling failed: {str(e)}")
            self.logger.warning(f"   ⚠️ Framework-specific handling failed: {str(e)}")
    
    async def _verify_final_content_state(self, page: Page, results: Dict) -> None:
        """Final verification of content state"""
        self.logger.info("🔍 Step 7: Final content verification...")
        
        try:
            content_state = await page.evaluate(f"""
                () => {{
                    const state = {{
                        totalImages: 0,
                        loadedImages: 0,
                        totalVideos: 0,
                        loadedVideos: 0,
                        totalCanvases: 0,
                        renderedCanvases: 0,
                        fontsLoaded: false,
                        hasErrors: false
                    }};
                    
                    // Check images
                    const images = document.querySelectorAll('img');
                    state.totalImages = images.length;
                    state.loadedImages = Array.from(images).filter(img => 
                        img.complete && img.naturalWidth > 0
                    ).length;
                    
                    // Check videos
                    const videos = document.querySelectorAll('video');
                    state.totalVideos = videos.length;
                    state.loadedVideos = Array.from(videos).filter(video => 
                        video.readyState >= 2
                    ).length;
                    
                    // Check canvases
                    const canvases = document.querySelectorAll('canvas');
                    state.totalCanvases = canvases.length;
                    state.renderedCanvases = Array.from(canvases).filter(canvas => {{
                        const ctx = canvas.getContext('2d');
                        if (!ctx) return false;
                        const imageData = ctx.getImageData(0, 0, Math.min(canvas.width, 1), Math.min(canvas.height, 1));
                        return imageData.data.some(pixel => pixel !== 0);
                    }}).length;
                    
                    // Check fonts
                    if (document.fonts && document.fonts.ready) {{
                        state.fontsLoaded = document.fonts.status === 'loaded';
                    }} else {{
                        state.fontsLoaded = true; // Assume loaded if API not available
                    }}
                    
                    // Check for JavaScript errors
                    state.hasErrors = window.onerror !== null || window.addEventListener !== null;
                    
                    return state;
                }}
            """)
            
            # Log content state
            self.logger.info(f"   📊 Content state: {content_state['loadedImages']}/{content_state['totalImages']} images, "
                           f"{content_state['loadedVideos']}/{content_state['totalVideos']} videos, "
                           f"{content_state['renderedCanvases']}/{content_state['totalCanvases']} canvases")
            
            if content_state['fontsLoaded']:
                self.logger.info("   ✓ Fonts loaded")
            else:
                self.logger.info("   ⚠️ Fonts may still be loading")
            
            results['content_state'] = content_state
            results['steps_completed'].append('content_verification')
            
        except Exception as e:
            results['warnings'].append(f"Content verification failed: {str(e)}")
            self.logger.warning(f"   ⚠️ Content verification failed: {str(e)}")
    
    async def _pause_animations_for_capture(self, page: Page, results: Dict) -> None:
        """Pause all animations for consistent screenshot capture"""
        self.logger.info("⏸️ Step 8: Pausing animations for capture...")
        
        try:
            await page.evaluate("""
                () => {
                    // Create comprehensive animation pause styles
                    const style = document.createElement('style');
                    style.id = 'screenshot-animation-pause';
                    style.innerHTML = `
                        *, *::before, *::after {
                            animation-play-state: paused !important;
                            animation-duration: 0s !important;
                            animation-delay: 0s !important;
                            transition-duration: 0s !important;
                            transition-delay: 0s !important;
                            transform-origin: center !important;
                        }
                        
                        /* Pause specific animation types */
                        @keyframes * {
                            0%, 100% { animation-play-state: paused !important; }
                        }
                        
                        /* Pause GIFs and videos */
                        img[src*='.gif'], video {
                            animation-play-state: paused !important;
                        }
                        
                        /* Pause CSS transforms that might be animating */
                        [style*="transform"], [style*="opacity"] {
                            transition: none !important;
                        }
                        
                        /* Pause common animation libraries */
                        .animate__animated, .aos-animate, .wow {
                            animation-play-state: paused !important;
                        }
                    `;
                    
                    document.head.appendChild(style);
                    
                    // Pause Web Animations API animations
                    document.getAnimations().forEach(animation => {
                        try {
                            animation.pause();
                        } catch (e) {
                            // Ignore errors for animations that can't be paused
                        }
                    });
                    
                    // Force a reflow to apply styles
                    document.body.offsetHeight;
                }
            """)
            
            # Small delay to ensure styles are applied
            await asyncio.sleep(0.2)
            
            self.logger.info("   ✓ Animations paused for capture")
            results['steps_completed'].append('animation_pause')
            
        except Exception as e:
            results['warnings'].append(f"Animation pausing failed: {str(e)}")
            self.logger.warning(f"   ⚠️ Animation pausing failed: {str(e)}")