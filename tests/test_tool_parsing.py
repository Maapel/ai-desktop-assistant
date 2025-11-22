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

    def test_parse_open_app_json_format(self):
        """Test parsing JSON tool calls for open_app."""
        with patch('subprocess.Popen') as mock_popen:
            mock_popen.return_value = Mock()
            json_response = '{"tool": "open_app", "parameters": {"app_name": "firefox"}}'

            # Mock the AI engine to return this JSON
            with patch.object(self.app, 'ai_engine') as mock_engine:
                mock_engine.query.return_value = json_response

                result = self.app.process_user_input("open firefox")
                self.assertIn("✅ Opened", result)
                self.assertIn("Firefox", result)
                mock_popen.assert_called_once()

    def test_conversational_response(self):
        """Test that pure conversational responses work without tool calls."""
        conversational_response = "I'm doing well, thanks for asking! How can I help you today?"

        # Mock the AI engine to return conversational response (no JSON)
        with patch.object(self.app, 'ai_engine') as mock_engine:
            mock_engine.query.return_value = conversational_response

            result = self.app.process_user_input("how are you")
            self.assertEqual(result, conversational_response)


if __name__ == '__main__':
    unittest.main()
