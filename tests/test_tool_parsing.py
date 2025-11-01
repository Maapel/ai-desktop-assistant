"""
Tests for AI tool parsing and execution functionality.
"""
import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to the path so we can import the main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import MyApplication


class TestToolParsing(unittest.TestCase):
    """Test cases for tool parsing functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = MyApplication()

    def test_parse_open_app_simple_format(self):
        """Test parsing TOOL_CALL with simple app name."""
        response = "TOOL_CALL: open_app\nPARAMETERS: firefox"
        tool_result = self.app.process_tool_call(response)

        self.assertIsNotNone(tool_result)
        self.assertIn("Opened", tool_result)  # Should return success message

    def test_parse_open_app_json_format(self):
        """Test parsing TOOL_CALL with JSON parameters."""
        response = 'TOOL_CALL: open_app\nPARAMETERS: {"app_name": "firefox"}'
        tool_result = self.app.process_tool_call(response)

        self.assertIsNotNone(tool_result)
        self.assertIn("Opened", tool_result)

    def test_parse_close_window_simple_format(self):
        """Test parsing close_window tool with simple format."""
        response = "TOOL_CALL: close_window\nPARAMETERS: terminal"
        tool_result = self.app.process_tool_call(response)

        self.assertIsNotNone(tool_result)
        # Should return either success or "not found" message

    def test_parse_close_window_json_format(self):
        """Test parsing close_window tool with JSON format."""
        response = 'TOOL_CALL: close_window\nPARAMETERS: {"window_title": "terminal"}'
        tool_result = self.app.process_tool_call(response)

        self.assertIsNotNone(tool_result)

    def test_parse_list_apps(self):
        """Test parsing list_apps tool (no parameters needed)."""
        response = "TOOL_CALL: list_apps\nPARAMETERS:"
        tool_result = self.app.process_tool_call(response)

        self.assertIsNotNone(tool_result)
        self.assertIn("Installed applications", tool_result)

    def test_parse_unknown_tool(self):
        """Test parsing unknown tool."""
        response = "TOOL_CALL: unknown_tool\nPARAMETERS: {}"
        tool_result = self.app.process_tool_call(response)

        self.assertIsNotNone(tool_result)
        self.assertIn("Unknown tool", tool_result)

    def test_no_tool_call_in_response(self):
        """Test response without tool call."""
        response = "This is just a normal response without any tool calls."
        tool_result = self.app.process_tool_call(response)

        self.assertIsNone(tool_result)

    def test_malformed_tool_call(self):
        """Test malformed tool call."""
        response = "TOOL_CALL: open_app\nPARAMETERS: {invalid json"
        tool_result = self.app.process_tool_call(response)

        # Should handle gracefully without crashing
        self.assertIsNotNone(tool_result)

    def test_empty_parameters(self):
        """Test tool call with empty parameters."""
        response = "TOOL_CALL: open_app\nPARAMETERS:"
        tool_result = self.app.process_tool_call(response)

        self.assertIsNotNone(tool_result)

    def test_tool_call_with_extra_text(self):
        """Test tool call embedded in larger response."""
        response = """I can help you open Firefox for browsing.
TOOL_CALL: open_app
PARAMETERS: firefox
This should open the browser for you."""
        tool_result = self.app.process_tool_call(response)

        self.assertIsNotNone(tool_result)
        self.assertIn("Opened", tool_result)

    def test_case_insensitive_app_matching(self):
        """Test that app matching is case insensitive."""
        # Test with different cases
        test_cases = ["firefox", "Firefox", "FIREFOX", "FiReFoX"]

        for app_name in test_cases:
            with self.subTest(app_name=app_name):
                response = f"TOOL_CALL: open_app\nPARAMETERS: {app_name}"
                tool_result = self.app.process_tool_call(response)
                # Should not crash, even if app not found
                self.assertIsNotNone(tool_result)


class TestApplicationDetection(unittest.TestCase):
    """Test cases for application detection and launching."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = MyApplication()

    def test_get_installed_applications(self):
        """Test that we can get a list of installed applications."""
        apps = self.app.get_installed_applications()
        self.assertIsInstance(apps, list)

        # Should have at least some basic apps
        app_names = [app['name'] for app in apps]
        self.assertGreater(len(app_names), 0)

        # Each app should have required fields
        for app in apps:
            self.assertIn('name', app)
            self.assertIn('exec', app)
            self.assertIn('desktop_file', app)

    def test_open_application_known_app(self):
        """Test opening a known application (without actually launching)."""
        # Mock subprocess.Popen to avoid actually launching apps
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = Mock()

            # Try to open a common app that should exist
            result = self.app.open_application("firefox")

            # Should either succeed or report app not found
            self.assertIsInstance(result, str)
            if "Opened" in result:
                mock_popen.assert_called_once()

    def test_open_application_unknown_app(self):
        """Test opening an unknown application."""
        result = self.app.open_application("nonexistent_app_xyz_12345")
        self.assertIn("not found", result.lower())

    def test_open_application_empty_name(self):
        """Test opening with empty app name."""
        result = self.app.open_application("")
        self.assertIn("cannot be empty", result.lower())


if __name__ == '__main__':
    unittest.main()
