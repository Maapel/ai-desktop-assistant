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
        # Mock subprocess.Popen to avoid launching real applications
        self.popen_patcher = patch('subprocess.Popen')
        self.mock_popen = self.popen_patcher.start()
        self.mock_popen.return_value = Mock()

        # Mock subprocess.run for wmctrl calls
        self.run_patcher = patch('subprocess.run')
        self.mock_run = self.run_patcher.start()
        self.mock_run.return_value = Mock(returncode=0, stdout="0x12345678  0 myhost Terminal\n")

        # Create app instance after mocking is set up
        self.app = MyApplication()

    def tearDown(self):
        """Clean up test fixtures."""
        self.popen_patcher.stop()
        self.run_patcher.stop()

    def test_parse_open_app_simple_format(self):
        """Test parsing TOOL_CALL with simple app name."""
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = Mock()
            response = "TOOL_CALL: open_app\nPARAMETERS: firefox"
            tool_result = self.app.process_tool_call(response)

            self.assertIsNotNone(tool_result)
            self.assertIn("Opened", tool_result)  # Should return success message
            mock_popen.assert_called_once()

    def test_parse_open_app_json_format(self):
        """Test parsing TOOL_CALL with JSON parameters."""
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = Mock()
            response = 'TOOL_CALL: open_app\nPARAMETERS: {"app_name": "firefox"}'
            tool_result = self.app.process_tool_call(response)

            self.assertIsNotNone(tool_result)
            self.assertIn("Opened", tool_result)
            mock_popen.assert_called_once()

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
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = Mock()
            response = """I can help you open Firefox for browsing.
TOOL_CALL: open_app
PARAMETERS: firefox
This should open the browser for you."""
            tool_result = self.app.process_tool_call(response)

            self.assertIsNotNone(tool_result)
            self.assertIn("Opened", tool_result)
            mock_popen.assert_called_once()

    def test_case_insensitive_app_matching(self):
        """Test that app matching is case insensitive."""
        # Test with different cases
        test_cases = ["firefox", "Firefox", "FIREFOX", "FiReFoX"]

        for app_name in test_cases:
            with self.subTest(app_name=app_name):
                with patch('subprocess.Popen') as mock_popen:
                    mock_popen.return_value = Mock()
                    response = f"TOOL_CALL: open_app\nPARAMETERS: {app_name}"
                    tool_result = self.app.process_tool_call(response)
                    # Should not crash, even if app not found
                    self.assertIsNotNone(tool_result)
                    if "Opened" in tool_result:
                        mock_popen.assert_called()


class TestApplicationDetection(unittest.TestCase):
    """Test cases for application detection and launching."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock subprocess.Popen to avoid launching real applications
        self.popen_patcher = patch('subprocess.Popen')
        self.mock_popen = self.popen_patcher.start()
        self.mock_popen.return_value = Mock()

        # Mock subprocess.run for wmctrl calls
        self.run_patcher = patch('subprocess.run')
        self.mock_run = self.run_patcher.start()
        self.mock_run.return_value = Mock(returncode=0, stdout="0x12345678  0 myhost Terminal\n")

        self.app = MyApplication()

    def tearDown(self):
        """Clean up test fixtures."""
        self.popen_patcher.stop()
        self.run_patcher.stop()

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
        # Try to open a common app that should exist
        result = self.app.open_application("firefox")

        # Should either succeed or report app not found
        self.assertIsInstance(result, str)
        if "Opened" in result:
            self.mock_popen.assert_called_once()

    def test_open_application_unknown_app(self):
        """Test opening an unknown application."""
        result = self.app.open_application("nonexistent_app_xyz_12345")
        self.assertIn("not found", result.lower())

    def test_open_application_empty_name(self):
        """Test opening with empty app name."""
        result = self.app.open_application("")
        self.assertIn("cannot be empty", result.lower())

    def test_process_tool_call_edge_cases(self):
        """Test various edge cases in tool call processing."""
        # Test malformed JSON parameters
        response = 'TOOL_CALL: open_app\nPARAMETERS: {"app_name": "firefox", "invalid": }'
        result = self.app.process_tool_call(response)
        self.assertIsNotNone(result)  # Should handle gracefully

        # Test parameters with colons
        response = 'TOOL_CALL: open_app\nPARAMETERS: app_name: firefox: extra'
        result = self.app.process_tool_call(response)
        self.assertIsNotNone(result)

        # Test empty tool call
        response = 'TOOL_CALL: \nPARAMETERS: firefox'
        result = self.app.process_tool_call(response)
        self.assertIsNotNone(result)

        # Test tool call without parameters line
        response = 'TOOL_CALL: open_app\nSome other text'
        result = self.app.process_tool_call(response)
        self.assertIsNotNone(result)

        # Test multiple colons in simple format
        response = 'TOOL_CALL: open_app\nPARAMETERS: app_name: firefox: version: 123'
        result = self.app.process_tool_call(response)
        self.assertIsNotNone(result)

    def test_process_tool_call_malformed_responses(self):
        """Test processing of malformed AI responses."""
        # Empty response
        result = self.app.process_tool_call("")
        self.assertIsNone(result)

        # Response without TOOL_CALL
        result = self.app.process_tool_call("This is just normal text")
        self.assertIsNone(result)

        # TOOL_CALL at end of long response
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = Mock()
            long_response = "Here is some text\n" * 100 + "TOOL_CALL: open_app\nPARAMETERS: firefox"
            result = self.app.process_tool_call(long_response)
            self.assertIsNotNone(result)
            mock_popen.assert_called_once()

        # Multiple TOOL_CALL markers
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = Mock()
            response = "TOOL_CALL: open_app\nPARAMETERS: firefox\nTOOL_CALL: close_window\nPARAMETERS: terminal"
            result = self.app.process_tool_call(response)
            self.assertIsNotNone(result)  # Should process first one
            mock_popen.assert_called_once()

    def test_tool_execution_error_handling(self):
        """Test error handling in tool execution."""
        # Test with invalid tool name
        result = self.app.execute_tool("nonexistent_tool", param="value")
        self.assertIn("Unknown tool", result)

        # Test open_app with None parameter
        result = self.app.execute_tool("open_app", app_name=None)
        self.assertIn("cannot be empty", result)

        # Test close_window with None parameter
        result = self.app.execute_tool("close_window", window_title=None)
        self.assertIsInstance(result, str)  # Should handle gracefully

    def test_open_file_browser_tool(self):
        """Test file browser opening functionality."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            # Test with valid path (use existing path)
            result = self.app.open_file_browser("/tmp")
            self.assertIn("Opened file browser", result)
            mock_run.assert_called_with(['xdg-open', '/tmp'], capture_output=True, text=True)

            # Test with empty path (should default to home)
            result = self.app.open_file_browser("")
            self.assertIn("Opened file browser", result)
            # Should call with expanded home directory

    def test_system_info_tool(self):
        """Test system information retrieval."""
        result = self.app.get_system_info()
        self.assertIsInstance(result, str)
        self.assertIn("System Information", result)

        # Should contain some basic info
        lines = result.split('\n')
        self.assertGreater(len(lines), 1)  # Should have header + at least one info line

    def test_parse_open_file_browser(self):
        """Test parsing open_file_browser tool calls."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            response = "TOOL_CALL: open_file_browser\nPARAMETERS: /home/user"
            tool_result = self.app.process_tool_call(response)

            self.assertIsNotNone(tool_result)
            self.assertIn("Opened file browser", tool_result)
            mock_run.assert_called_once()

    def test_parse_system_info(self):
        """Test parsing system_info tool calls."""
        response = "TOOL_CALL: system_info\nPARAMETERS:"
        tool_result = self.app.process_tool_call(response)

        self.assertIsNotNone(tool_result)
        self.assertIn("System Information", tool_result)


if __name__ == '__main__':
    unittest.main()
