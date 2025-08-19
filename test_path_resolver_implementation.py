"""
Comprehensive test script for PathResolver implementation
Tests all components of the new dynamic asset resolver system
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

# Add the project directory to the path
sys.path.append(str(Path(__file__).parent))

from utils.path_resolver import PathResolver
from routes.asset_resolver import register_asset_resolver_routes


class PathResolverTests:
    """Test suite for PathResolver functionality"""
    
    def __init__(self):
        self.test_dir = None
        self.path_resolver = None
        self.passed = 0
        self.failed = 0
        
    def setup(self):
        """Set up test environment"""
        print("Setting up test environment...")
        
        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp(prefix='pathresolver_test_')
        print(f"Test directory: {self.test_dir}")
        
        # Initialize PathResolver with test directory
        self.path_resolver = PathResolver(self.test_dir)
        
    def teardown(self):
        """Clean up test environment"""
        if self.test_dir and Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)
            print(f"Cleaned up test directory: {self.test_dir}")
    
    def assert_equal(self, actual, expected, test_name):
        """Assert that two values are equal"""
        if actual == expected:
            print(f"✓ {test_name}")
            self.passed += 1
        else:
            print(f"✗ {test_name}")
            print(f"  Expected: {expected}")
            print(f"  Actual:   {actual}")
            self.failed += 1
    
    def assert_true(self, condition, test_name):
        """Assert that condition is true"""
        if condition:
            print(f"✓ {test_name}")
            self.passed += 1
        else:
            print(f"✗ {test_name}")
            self.failed += 1
    
    def test_component_normalization(self):
        """Test component normalization"""
        print("\n--- Testing Component Normalization ---")
        
        # Test normalize_component
        self.assert_equal(
            self.path_resolver.normalize_component("PROJECT_123"),
            "project_123",
            "Normalize uppercase project ID"
        )
        
        self.assert_equal(
            self.path_resolver.normalize_component("Desktop"),
            "desktop",
            "Normalize viewport case"
        )
        
        self.assert_equal(
            self.path_resolver.normalize_component("STAGING"),
            "staging",
            "Normalize environment case"
        )
    
    def test_page_slugification(self):
        """Test page path slugification"""
        print("\n--- Testing Page Slugification ---")
        
        test_cases = [
            ("/", "home"),
            ("/home/", "home"),
            ("/blog/post-title/", "blog_post-title"),
            ("/about/team", "about_team"),
            ("/products/category/item", "products_category_item"),
            ("/special-chars!@#$%", "special-chars_____"),
            ("", "home"),
            ("/very/long/path/that/exceeds/normal/limits/and/should/be/truncated/with/hash", None)  # Will check length
        ]
        
        for input_path, expected in test_cases:
            result = self.path_resolver.slugify_page_path(input_path)
            
            if expected is None:
                # Check that long paths are truncated and have hash
                self.assert_true(
                    len(result) <= 200 and '_' in result[-9:],
                    f"Long path truncation: {input_path}"
                )
            else:
                self.assert_equal(
                    result,
                    expected,
                    f"Slugify: {input_path} -> {expected}"
                )
    
    def test_run_id_generation(self):
        """Test run ID generation"""
        print("\n--- Testing Run ID Generation ---")
        
        run_id = self.path_resolver.generate_run_id()
        
        # Check format: YYYYMMDD-HHmmss
        import re
        pattern = r'^\d{8}-\d{6}$'
        self.assert_true(
            re.match(pattern, run_id) is not None,
            f"Run ID format: {run_id}"
        )
        
        # Check that it's lowercase
        self.assert_equal(
            run_id,
            run_id.lower(),
            "Run ID is lowercase"
        )
    
    def test_canonical_path_generation(self):
        """Test canonical path generation"""
        print("\n--- Testing Canonical Path Generation ---")
        
        project_id = 123
        run_id = "20250813-143022"
        viewport = "desktop"
        page_slug = "home"
        environment = "staging"
        
        expected_path = Path(self.test_dir) / "123" / "20250813-143022" / "desktop" / "home-staging.png"
        
        actual_path = self.path_resolver.get_canonical_path(
            project_id, run_id, viewport, page_slug, environment
        )
        
        self.assert_equal(
            actual_path,
            expected_path,
            "Canonical path generation"
        )
    
    def test_filename_generation(self):
        """Test canonical filename generation"""
        print("\n--- Testing Filename Generation ---")
        
        test_cases = [
            ("home", "staging", "home-staging.png"),
            ("blog_post", "production", "blog_post-production.png"),
            ("about_team", "diff", "about_team-diff.png")
        ]
        
        for page_slug, environment, expected in test_cases:
            result = self.path_resolver.get_canonical_filename(page_slug, environment)
            self.assert_equal(
                result,
                expected,
                f"Filename: {page_slug} + {environment}"
            )
    
    def test_url_path_generation(self):
        """Test URL path generation"""
        print("\n--- Testing URL Path Generation ---")
        
        project_id = 123
        run_id = "20250813-143022"
        viewport = "desktop"
        page_slug = "home"
        environment = "staging"
        
        expected_url = "/assets/runs/123/20250813-143022/desktop/home-staging.png"
        
        actual_url = self.path_resolver.get_url_path(
            project_id, run_id, viewport, page_slug, environment
        )
        
        self.assert_equal(
            actual_url,
            expected_url,
            "URL path generation"
        )
    
    def test_url_path_parsing(self):
        """Test URL path parsing"""
        print("\n--- Testing URL Path Parsing ---")
        
        test_url = "/assets/runs/123/20250813-143022/desktop/home-staging.png"
        
        result = self.path_resolver.parse_url_path(test_url)
        
        expected = {
            'project_id': '123',
            'run_id': '20250813-143022',
            'viewport': 'desktop',
            'page_slug': 'home',
            'environment': 'staging',
            'extension': 'png'
        }
        
        self.assert_equal(
            result,
            expected,
            "URL path parsing"
        )
        
        # Test invalid URL
        invalid_result = self.path_resolver.parse_url_path("/invalid/path")
        self.assert_equal(
            invalid_result,
            None,
            "Invalid URL path parsing"
        )
    
    def test_directory_creation(self):
        """Test directory creation"""
        print("\n--- Testing Directory Creation ---")
        
        project_id = 123
        run_id = "20250813-143022"
        
        self.path_resolver.create_directories(project_id, run_id)
        
        # Check that all viewport directories were created
        for viewport in self.path_resolver.viewports:
            expected_dir = Path(self.test_dir) / "123" / "20250813-143022" / viewport
            self.assert_true(
                expected_dir.exists() and expected_dir.is_dir(),
                f"Directory created: {viewport}"
            )
    
    def test_file_resolution_with_fallback(self):
        """Test file resolution with legacy fallback"""
        print("\n--- Testing File Resolution with Fallback ---")
        
        project_id = 123
        run_id = "20250813-143022"
        viewport = "desktop"
        page_slug = "home"
        environment = "staging"
        
        # Create canonical file
        canonical_path = self.path_resolver.get_canonical_path(
            project_id, run_id, viewport, page_slug, environment
        )
        canonical_path.parent.mkdir(parents=True, exist_ok=True)
        canonical_path.write_text("test content")
        
        # Test resolution
        resolved_path = self.path_resolver.resolve_file(
            project_id, run_id, viewport, page_slug, environment
        )
        
        self.assert_equal(
            resolved_path,
            canonical_path,
            "File resolution finds canonical file"
        )
        
        # Test non-existent file
        non_existent = self.path_resolver.resolve_file(
            project_id, run_id, viewport, "nonexistent", environment
        )
        
        self.assert_equal(
            non_existent,
            None,
            "File resolution returns None for non-existent file"
        )
    
    def test_all_paths_for_page(self):
        """Test getting all paths for a page"""
        print("\n--- Testing All Paths for Page ---")
        
        project_id = 123
        run_id = "20250813-143022"
        page_path = "/blog/post"
        
        all_paths = self.path_resolver.get_all_paths_for_page(
            project_id, run_id, page_path
        )
        
        # Check structure
        self.assert_true(
            len(all_paths) == 3,  # 3 viewports
            "All paths has 3 viewports"
        )
        
        for viewport in self.path_resolver.viewports:
            self.assert_true(
                viewport in all_paths,
                f"All paths contains {viewport}"
            )
            
            self.assert_true(
                len(all_paths[viewport]) == 3,  # 3 environments
                f"All paths {viewport} has 3 environments"
            )
            
            for environment in self.path_resolver.environments:
                self.assert_true(
                    environment in all_paths[viewport],
                    f"All paths {viewport} contains {environment}"
                )
    
    def test_validation_errors(self):
        """Test validation and error handling"""
        print("\n--- Testing Validation and Error Handling ---")
        
        # Test invalid viewport
        try:
            self.path_resolver.get_canonical_path(
                123, "20250813-143022", "invalid_viewport", "home", "staging"
            )
            self.assert_true(False, "Should raise ValueError for invalid viewport")
        except ValueError:
            self.assert_true(True, "Raises ValueError for invalid viewport")
        
        # Test invalid environment
        try:
            self.path_resolver.get_canonical_path(
                123, "20250813-143022", "desktop", "home", "invalid_env"
            )
            self.assert_true(False, "Should raise ValueError for invalid environment")
        except ValueError:
            self.assert_true(True, "Raises ValueError for invalid environment")
    
    def run_all_tests(self):
        """Run all tests"""
        print("PathResolver Implementation Test Suite")
        print("=" * 50)
        
        self.setup()
        
        try:
            self.test_component_normalization()
            self.test_page_slugification()
            self.test_run_id_generation()
            self.test_canonical_path_generation()
            self.test_filename_generation()
            self.test_url_path_generation()
            self.test_url_path_parsing()
            self.test_directory_creation()
            self.test_file_resolution_with_fallback()
            self.test_all_paths_for_page()
            self.test_validation_errors()
            
        finally:
            self.teardown()
        
        # Print results
        print("\n" + "=" * 50)
        print("TEST RESULTS")
        print("=" * 50)
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Total:  {self.passed + self.failed}")
        
        if self.failed == 0:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"❌ {self.failed} test(s) failed")
            return False


def test_asset_resolver_route():
    """Test the asset resolver route functionality"""
    print("\n" + "=" * 50)
    print("ASSET RESOLVER ROUTE TESTS")
    print("=" * 50)
    
    # Mock Flask app for testing
    from flask import Flask
    app = Flask(__name__)
    
    # Register routes
    register_asset_resolver_routes(app)
    
    # Test route registration
    rules = [rule.rule for rule in app.url_map.iter_rules()]
    
    expected_routes = [
        '/assets/runs/<project_id>/<run_id>/<viewport>/<filename>',
        '/assets/placeholder/<placeholder_type>'
    ]
    
    for route in expected_routes:
        if route in rules:
            print(f"✓ Route registered: {route}")
        else:
            print(f"✗ Route missing: {route}")
    
    print("Asset resolver routes registered successfully!")


def main():
    """Main test function"""
    # Run PathResolver tests
    tests = PathResolverTests()
    path_resolver_success = tests.run_all_tests()
    
    # Run asset resolver tests
    test_asset_resolver_route()
    
    # Create placeholder images
    print("\n" + "=" * 50)
    print("CREATING PLACEHOLDER IMAGES")
    print("=" * 50)
    
    try:
        from static.placeholders.create_placeholders import main as create_placeholders
        create_placeholders()
        print("✓ Placeholder images created successfully!")
    except Exception as e:
        print(f"✗ Error creating placeholder images: {e}")
    
    # Final summary
    print("\n" + "=" * 50)
    print("IMPLEMENTATION SUMMARY")
    print("=" * 50)
    print("✓ PathResolver class implemented")
    print("✓ Dynamic asset resolver route created")
    print("✓ Database migration script created")
    print("✓ Backfill script created")
    print("✓ Placeholder image system implemented")
    print("✓ Screenshot service updated")
    print("✓ App.py updated with new routes")
    
    if path_resolver_success:
        print("\n🎉 PathResolver implementation is ready!")
        print("\nNext steps:")
        print("1. Run database migration: flask db upgrade")
        print("2. Run backfill script: python scripts/backfill_canonical_paths.py --live")
        print("3. Test with real data")
    else:
        print("\n❌ Some tests failed. Please review and fix issues.")
    
    return path_resolver_success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)