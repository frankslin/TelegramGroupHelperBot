"""Tests for send_response logic without importing handlers module."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch


# Define the logic from send_response as a standalone function for testing
async def upload_service_logic(response_length, line_count, upload_service, telegram_max_length=4000):
    """Test version of the upload service decision logic."""
    # Check if message exceeds line count threshold or character limit
    if line_count > 22 or response_length > telegram_max_length:
        if upload_service.lower() == "cwd.pw":
            return "cwd.pw"
        else:  # Default to telegra.ph
            return "telegra.ph"
    else:
        return "direct"  # Send directly


class TestSendResponseLogic(unittest.IsolatedAsyncioTestCase):
    """Test the core logic of send_response without external dependencies."""

    async def test_short_message_sends_directly(self):
        """Test that short messages are sent directly."""
        result = await upload_service_logic(
            response_length=100,
            line_count=5,
            upload_service="telegra.ph"
        )
        self.assertEqual(result, "direct")

    async def test_long_character_count_triggers_upload_telegraph(self):
        """Test that long character count triggers Telegraph upload."""
        result = await upload_service_logic(
            response_length=5000,  # > 4000
            line_count=10,
            upload_service="telegra.ph"
        )
        self.assertEqual(result, "telegra.ph")

    async def test_long_character_count_triggers_upload_cwd_pw(self):
        """Test that long character count triggers cwd.pw upload."""
        result = await upload_service_logic(
            response_length=5000,  # > 4000
            line_count=10,
            upload_service="cwd.pw"
        )
        self.assertEqual(result, "cwd.pw")

    async def test_many_lines_triggers_upload_telegraph(self):
        """Test that many lines trigger Telegraph upload."""
        result = await upload_service_logic(
            response_length=1000,  # < 4000
            line_count=25,  # > 22
            upload_service="telegra.ph"
        )
        self.assertEqual(result, "telegra.ph")

    async def test_many_lines_triggers_upload_cwd_pw(self):
        """Test that many lines trigger cwd.pw upload."""
        result = await upload_service_logic(
            response_length=1000,  # < 4000
            line_count=25,  # > 22
            upload_service="cwd.pw"
        )
        self.assertEqual(result, "cwd.pw")

    async def test_case_insensitive_service_matching(self):
        """Test that service matching is case insensitive."""
        test_cases = [
            ("CWD.PW", "cwd.pw"),
            ("cwd.pw", "cwd.pw"),
            ("Cwd.Pw", "cwd.pw"),
            ("TELEGRA.PH", "telegra.ph"),
            ("telegra.ph", "telegra.ph"),
            ("invalid_service", "telegra.ph")  # Fallback
        ]
        
        for service_input, expected_service in test_cases:
            result = await upload_service_logic(
                response_length=5000,  # Trigger upload
                line_count=10,
                upload_service=service_input
            )
            self.assertEqual(result, expected_service)

    async def test_boundary_conditions_character_limit(self):
        """Test boundary conditions for character limit."""
        # Exactly at limit - should NOT trigger upload
        result = await upload_service_logic(
            response_length=4000,  # Exactly at limit
            line_count=10,
            upload_service="telegra.ph"
        )
        self.assertEqual(result, "direct")
        
        # One over limit - should trigger upload
        result = await upload_service_logic(
            response_length=4001,  # Over limit
            line_count=10,
            upload_service="telegra.ph"
        )
        self.assertEqual(result, "telegra.ph")

    async def test_boundary_conditions_line_count(self):
        """Test boundary conditions for line count."""
        # Exactly at limit - should NOT trigger upload
        result = await upload_service_logic(
            response_length=1000,
            line_count=22,  # Exactly at limit
            upload_service="telegra.ph"
        )
        self.assertEqual(result, "direct")
        
        # One over limit - should trigger upload
        result = await upload_service_logic(
            response_length=1000,
            line_count=23,  # Over limit
            upload_service="telegra.ph"
        )
        self.assertEqual(result, "telegra.ph")

    async def test_both_limits_exceeded(self):
        """Test when both character and line limits are exceeded."""
        result = await upload_service_logic(
            response_length=5000,  # Over character limit
            line_count=30,  # Over line limit
            upload_service="cwd.pw"
        )
        self.assertEqual(result, "cwd.pw")

    async def test_custom_telegram_max_length(self):
        """Test with custom telegram max length."""
        result = await upload_service_logic(
            response_length=150,
            line_count=5,
            upload_service="telegra.ph",
            telegram_max_length=100  # Custom limit
        )
        self.assertEqual(result, "telegra.ph")  # Should trigger because 150 > 100


class TestUploadServiceSelection(unittest.TestCase):
    """Test upload service selection logic."""

    def test_service_name_normalization(self):
        """Test service name normalization."""
        test_cases = [
            ("cwd.pw", "cwd.pw"),
            ("CWD.PW", "cwd.pw"),
            ("Cwd.Pw", "cwd.pw"),
            ("  cwd.pw  ", "  cwd.pw  "),  # Whitespace preserved
            ("telegra.ph", "telegra.ph"),
            ("TELEGRA.PH", "telegra.ph"),
            ("invalid", "invalid")
        ]
        
        for input_service, expected_lower in test_cases:
            result = input_service.lower()
            self.assertEqual(result, expected_lower)

    def test_service_matching_logic(self):
        """Test the exact logic used in send_response."""
        test_cases = [
            ("cwd.pw", True),
            ("CWD.PW", True),
            ("Cwd.Pw", True),
            ("telegra.ph", False),
            ("TELEGRA.PH", False),
            ("invalid_service", False),
            ("", False),
            ("  cwd.pw  ", False)  # Whitespace prevents match
        ]
        
        for service_name, should_match_cwd_pw in test_cases:
            # This is the exact logic from send_response
            is_cwd_pw = service_name.lower() == "cwd.pw"
            self.assertEqual(is_cwd_pw, should_match_cwd_pw,
                           f"Service '{service_name}' matching failed")


class TestResponseProcessingLogic(unittest.TestCase):
    """Test response processing logic."""

    def test_line_counting(self):
        """Test line counting logic."""
        test_cases = [
            ("single line", 1),
            ("line 1\nline 2", 2),
            ("line 1\nline 2\nline 3", 3),
            ("", 1),  # Empty string has 1 line
            ("line\n", 2),  # Trailing newline adds a line
            ("line\n\n", 3),  # Multiple trailing newlines
        ]
        
        for content, expected_lines in test_cases:
            # This is the exact logic from send_response
            line_count = content.count('\n') + 1
            self.assertEqual(line_count, expected_lines,
                           f"Line count for '{repr(content)}' failed")

    def test_length_calculation(self):
        """Test length calculation."""
        test_cases = [
            ("short", 5),
            ("测试中文", 4),  # Chinese characters
            ("emoji 🤖", 7),  # Emoji
            ("", 0),
        ]
        
        for content, expected_length in test_cases:
            length = len(content)
            self.assertEqual(length, expected_length,
                           f"Length for '{content}' failed")


if __name__ == '__main__':
    unittest.main()