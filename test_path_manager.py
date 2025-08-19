#!/usr/bin/env python3
"""
Unit tests for PathManager
Tests the new consistent nested folder structure functionality
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import pytz

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.path_manager import PathManager


class TestPathManager(unittest.TestCase):
    """Test cases for PathManager"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.path_manager = PathManager(self.test_dir)
        
        # Test data
        self.project_id = 123
        self.process_timestamp = "20250813-113309"
        self.page_path = "/products/search"
        self.viewport = "desktop"
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def test_generate_process_timestamp(self):
        """Test process timestamp generation"""
        timestamp = self.path_manager.generate_process_timestamp()
        
        # Should match format YYYYMMDD-HHmmss
        self.assertRegex(timestamp, r'^\d{8}-\d{6}$')
        
        # Should be recent (within last minute)
        ist_timezone = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist_timezone)
        timestamp_dt = datetime.strptime(timestamp, '%Y%m%d-%H%M%S')
        timestamp_dt = ist_timezone.localize(timestamp_dt)
        
        time_diff = abs((now - timestamp_dt).total_seconds())
        self.assertLess(time_diff, 60)  # Within 1 minute
    
    def test_slugify_page_name(self):
        """Test page name slugification"""
        test_cases = [
            ("", "home"),
            ("/", "home"),
            ("/products", "products"),
            ("/products/search", "products_search"),
            ("/products/search?q=test", "products_search_q_test"),
            ("/products/category:electronics", "products_category_electronics"),
            ("///multiple///slashes///", "multiple_slashes"),
            ("/special-chars!@#$%^&*()", "special-chars"),
        ]
        
        for input_path, expected in test_cases:
            with self.subTest(input_path=input_path):
                result = self.path_manager.slugify_page_name(input_path)
                self.assertEqual(result, expected)
    
    def test_slugify_long_page_name(self):
        """Test slugification of very long page names"""
        # Create a very long path
        long_path = "/very/long/path/" + "segment/" * 50
        
        result = self.path_manager.slugify_page_name(long_path)
        
        # Should be truncated to reasonable length
        self.assertLessEqual(len(result), 209)  # 200 + 9 for hash
        
        # Should contain hash for uniqueness
        self.assertIn('_', result)
        
        # Should be consistent
        result2 = self.path_manager.slugify_page_name(long_path)
        self.assertEqual(result, result2)
    
    def test_get_project_directory(self):
        """Test project directory path generation"""
        project_dir = self.path_manager.get_project_directory(self.project_id, self.process_timestamp)
        
        expected = Path(self.test_dir) / "123" / "20250813-113309"
        self.assertEqual(project_dir, expected)
    
    def test_get_viewport_directory(self):
        """Test viewport directory path generation"""
        viewport_dir = self.path_manager.get_viewport_directory(
            self.project_id, self.process_timestamp, "desktop"
        )
        
        expected = Path(self.test_dir) / "123" / "20250813-113309" / "Desktop"
        self.assertEqual(viewport_dir, expected)
        
        # Test all viewport types
        viewport_mappings = {
            'desktop': 'Desktop',
            'tablet': 'Tablet',
            'mobile': 'Mobile'
        }
        
        for viewport, folder_name in viewport_mappings.items():
            with self.subTest(viewport=viewport):
                viewport_dir = self.path_manager.get_viewport_directory(
                    self.project_id, self.process_timestamp, viewport
                )
                expected = Path(self.test_dir) / "123" / "20250813-113309" / folder_name
                self.assertEqual(viewport_dir, expected)
    
    def test_get_screenshot_paths(self):
        """Test screenshot path generation"""
        production_path, staging_path, diff_path = self.path_manager.get_screenshot_paths(
            self.project_id, self.process_timestamp, self.page_path, self.viewport
        )
        
        base_dir = Path(self.test_dir) / "123" / "20250813-113309" / "Desktop"
        
        expected_production = base_dir / "products_search-production.png"
        expected_staging = base_dir / "products_search-staging.png"
        expected_diff = base_dir / "products_search-diff.png"
        
        self.assertEqual(production_path, expected_production)
        self.assertEqual(staging_path, expected_staging)
        self.assertEqual(diff_path, expected_diff)
        
        # Directory should be created
        self.assertTrue(base_dir.exists())
    
    def test_get_screenshot_path_by_environment(self):
        """Test getting screenshot path for specific environment"""
        # Test all environments
        environments = ['production', 'staging', 'diff']
        
        for environment in environments:
            with self.subTest(environment=environment):
                path = self.path_manager.get_screenshot_path_by_environment(
                    self.project_id, self.process_timestamp, self.page_path, self.viewport, environment
                )
                
                expected_filename = f"products_search-{environment}.png"
                self.assertEqual(path.name, expected_filename)
                
                expected_dir = Path(self.test_dir) / "123" / "20250813-113309" / "Desktop"
                self.assertEqual(path.parent, expected_dir)
        
        # Test invalid environment
        with self.assertRaises(ValueError):
            self.path_manager.get_screenshot_path_by_environment(
                self.project_id, self.process_timestamp, self.page_path, self.viewport, "invalid"
            )
    
    def test_get_relative_path(self):
        """Test relative path generation"""
        absolute_path = Path(self.test_dir) / "123" / "20250813-113309" / "Desktop" / "home-production.png"
        
        relative_path = self.path_manager.get_relative_path(absolute_path)
        
        expected = "123/20250813-113309/Desktop/home-production.png"
        self.assertEqual(relative_path, expected)
        
        # Test path not relative to base
        external_path = Path("/some/external/path/file.png")
        result = self.path_manager.get_relative_path(external_path)
        expected_external = str(external_path).replace('\\', '/')
        self.assertEqual(result, expected_external)
    
    def test_get_url_path(self):
        """Test URL path generation"""
        relative_path = "123/20250813-113309/Desktop/home-production.png"
        
        url_path = self.path_manager.get_url_path(relative_path)
        
        expected = "/screenshots/123/20250813-113309/Desktop/home-production.png"
        self.assertEqual(url_path, expected)
    
    def test_list_process_runs(self):
        """Test listing process runs for a project"""
        # Create some test directories
        project_dir = Path(self.test_dir) / "123"
        project_dir.mkdir(parents=True)
        
        # Create valid timestamp directories
        valid_timestamps = ["20250813-113309", "20250812-154210", "20250811-090000"]
        for timestamp in valid_timestamps:
            (project_dir / timestamp).mkdir()
        
        # Create invalid directories
        (project_dir / "invalid").mkdir()
        (project_dir / "20250813").mkdir()  # Invalid format
        (project_dir / "not-a-timestamp").mkdir()
        
        # Test listing
        runs = self.path_manager.list_process_runs(123)
        
        # Should return valid timestamps, sorted newest first
        expected = ["20250813-113309", "20250812-154210", "20250811-090000"]
        self.assertEqual(runs, expected)
        
        # Test non-existent project
        runs_empty = self.path_manager.list_process_runs(999)
        self.assertEqual(runs_empty, [])
    
    def test_cleanup_project_screenshots(self):
        """Test project screenshot cleanup"""
        # Create test structure
        project_dir = Path(self.test_dir) / "123"
        
        # Create multiple runs
        timestamps = ["20250813-113309", "20250812-154210", "20250811-090000"]
        for timestamp in timestamps:
            run_dir = project_dir / timestamp / "Desktop"
            run_dir.mkdir(parents=True)
            (run_dir / "test.png").touch()
        
        # Test keeping latest 2 runs
        success = self.path_manager.cleanup_project_screenshots(123, keep_latest=2)
        self.assertTrue(success)
        
        # Should keep only 2 latest runs
        remaining_runs = self.path_manager.list_process_runs(123)
        self.assertEqual(len(remaining_runs), 2)
        self.assertEqual(remaining_runs, ["20250813-113309", "20250812-154210"])
        
        # Test deleting all
        success = self.path_manager.cleanup_project_screenshots(123, keep_latest=0)
        self.assertTrue(success)
        
        # Project directory should be gone
        self.assertFalse(project_dir.exists())
    
    def test_validate_structure(self):
        """Test structure validation"""
        # Test non-existent structure
        result = self.path_manager.validate_structure(123, "20250813-113309")
        self.assertFalse(result['valid'])
        self.assertFalse(result['project_dir_exists'])
        
        # Create partial structure
        project_dir = self.path_manager.get_project_directory(123, "20250813-113309")
        project_dir.mkdir(parents=True)
        
        # Create only desktop viewport
        desktop_dir = self.path_manager.get_viewport_directory(123, "20250813-113309", "desktop")
        desktop_dir.mkdir(parents=True)
        
        result = self.path_manager.validate_structure(123, "20250813-113309")
        self.assertFalse(result['valid'])  # Missing tablet and mobile
        self.assertTrue(result['project_dir_exists'])
        self.assertTrue(result['viewport_dirs']['desktop'])
        self.assertFalse(result['viewport_dirs']['tablet'])
        self.assertFalse(result['viewport_dirs']['mobile'])
        
        # Create complete structure
        for viewport in ['tablet', 'mobile']:
            viewport_dir = self.path_manager.get_viewport_directory(123, "20250813-113309", viewport)
            viewport_dir.mkdir(parents=True)
        
        result = self.path_manager.validate_structure(123, "20250813-113309")
        self.assertTrue(result['valid'])
        self.assertTrue(all(result['viewport_dirs'].values()))
    
    def test_multiple_projects_and_runs(self):
        """Test handling multiple projects and runs"""
        # Create structure for multiple projects and runs
        projects = [123, 456, 789]
        timestamps = ["20250813-113309", "20250812-154210"]
        viewports = ["desktop", "tablet", "mobile"]
        
        for project_id in projects:
            for timestamp in timestamps:
                for viewport in viewports:
                    production_path, staging_path, diff_path = self.path_manager.get_screenshot_paths(
                        project_id, timestamp, "/test-page", viewport
                    )
                    
                    # Create the files
                    production_path.touch()
                    staging_path.touch()
                    diff_path.touch()
        
        # Verify structure
        for project_id in projects:
            runs = self.path_manager.list_process_runs(project_id)
            self.assertEqual(len(runs), 2)
            
            for timestamp in timestamps:
                result = self.path_manager.validate_structure(project_id, timestamp)
                self.assertTrue(result['valid'])
        
        # Test cleanup of specific project
        success = self.path_manager.cleanup_project_screenshots(123, keep_latest=1)
        self.assertTrue(success)
        
        # Project 123 should have only 1 run left
        runs_123 = self.path_manager.list_process_runs(123)
        self.assertEqual(len(runs_123), 1)
        
        # Other projects should be unaffected
        runs_456 = self.path_manager.list_process_runs(456)
        runs_789 = self.path_manager.list_process_runs(789)
        self.assertEqual(len(runs_456), 2)
        self.assertEqual(len(runs_789), 2)
    
    def test_edge_cases(self):
        """Test edge cases and error conditions"""
        # Test with special characters in page path
        special_page = "/products/search?q=test&category=electronics#results"
        production_path, staging_path, diff_path = self.path_manager.get_screenshot_paths(
            self.project_id, self.process_timestamp, special_page, self.viewport
        )
        
        # Should handle special characters gracefully
        self.assertTrue(production_path.name.endswith("-production.png"))
        self.assertTrue(staging_path.name.endswith("-staging.png"))
        self.assertTrue(diff_path.name.endswith("-diff.png"))
        
        # Test with empty page path
        production_path, staging_path, diff_path = self.path_manager.get_screenshot_paths(
            self.project_id, self.process_timestamp, "", self.viewport
        )
        
        # Should use "home" as default
        self.assertEqual(production_path.name, "home-production.png")
        self.assertEqual(staging_path.name, "home-staging.png")
        self.assertEqual(diff_path.name, "home-diff.png")
        
        # Test with case variations in viewport
        for viewport_case in ["Desktop", "DESKTOP", "desktop"]:
            viewport_dir = self.path_manager.get_viewport_directory(
                self.project_id, self.process_timestamp, viewport_case
            )
            # Should always use capitalized folder name
            self.assertTrue(viewport_dir.name == "Desktop")


class TestPathManagerIntegration(unittest.TestCase):
    """Integration tests for PathManager with real file operations"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.path_manager = PathManager(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
    
    def test_full_workflow(self):
        """Test complete workflow from creation to cleanup"""
        project_id = 123
        process_timestamp = "20250813-113309"
        page_path = "/products/search"
        
        # Step 1: Create screenshots for all viewports
        for viewport in ['desktop', 'tablet', 'mobile']:
            production_path, staging_path, diff_path = self.path_manager.get_screenshot_paths(
                project_id, process_timestamp, page_path, viewport
            )
            
            # Simulate creating screenshot files
            production_path.touch()
            staging_path.touch()
            
            # Verify files exist
            self.assertTrue(production_path.exists())
            self.assertTrue(staging_path.exists())
            
            # Simulate creating diff file
            diff_path.touch()
            self.assertTrue(diff_path.exists())
        
        # Step 2: Validate structure
        result = self.path_manager.validate_structure(project_id, process_timestamp)
        self.assertTrue(result['valid'])
        
        # Step 3: List runs
        runs = self.path_manager.list_process_runs(project_id)
        self.assertEqual(runs, [process_timestamp])
        
        # Step 4: Create another run
        process_timestamp2 = "20250814-120000"
        for viewport in ['desktop', 'tablet', 'mobile']:
            production_path, staging_path, diff_path = self.path_manager.get_screenshot_paths(
                project_id, process_timestamp2, page_path, viewport
            )
            production_path.touch()
            staging_path.touch()
            diff_path.touch()
        
        # Should have 2 runs now
        runs = self.path_manager.list_process_runs(project_id)
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs, [process_timestamp2, process_timestamp])  # Newest first
        
        # Step 5: Cleanup old runs
        success = self.path_manager.cleanup_project_screenshots(project_id, keep_latest=1)
        self.assertTrue(success)
        
        # Should have only 1 run left
        runs = self.path_manager.list_process_runs(project_id)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs, [process_timestamp2])
        
        # Step 6: Complete cleanup
        success = self.path_manager.cleanup_project_screenshots(project_id, keep_latest=0)
        self.assertTrue(success)
        
        # Project should be completely removed
        runs = self.path_manager.list_process_runs(project_id)
        self.assertEqual(runs, [])


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)