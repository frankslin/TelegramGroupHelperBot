"""Tests for upload service error handling and fallback scenarios."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Mock all required modules to avoid import errors
class MockTelegramError:
    class BadRequest(Exception):
        pass

class MockParseMode:
    MARKDOWN = "Markdown"

class MockContextTypes:
    DEFAULT_TYPE = MagicMock()

# Mock all telegram-related modules
sys.modules['telegram'] = MagicMock()
sys.modules['telegram.error'] = MockTelegramError
sys.modules['telegram.constants'] = MagicMock()
sys.modules['telegram.constants'].ParseMode = MockParseMode
sys.modules['telegram.ext'] = MagicMock()
sys.modules['telegram.ext'].ContextTypes = MockContextTypes

# Mock other dependencies
sys.modules['langid'] = MagicMock()
sys.modules['pycountry'] = MagicMock()
sys.modules['markdown'] = MagicMock()
sys.modules['bs4'] = MagicMock()
sys.modules['html2text'] = MagicMock()
sys.modules['requests'] = MagicMock()

# Import after mocking
from bot.handlers import send_response
BadRequest = MockTelegramError.BadRequest


class TestUploadErrorHandling(unittest.IsolatedAsyncioTestCase):
    """Test error handling and fallback scenarios for upload services."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_message = MagicMock()
        self.mock_message.edit_text = AsyncMock()
        
        self.long_response = "This is a very long response. " * 200  # Long enough to trigger upload
        self.test_title = "Test Title"

    @patch('bot.handlers.UPLOAD_SERVICE', 'cwd.pw')
    @patch('bot.handlers.upload_to_cwd_pw_paste')
    async def test_cwd_pw_upload_failure_fallback_to_plain_text(self, mock_cwd_upload):
        """Test fallback to plain text when cwd.pw upload fails."""
        mock_cwd_upload.return_value = None  # Simulate upload failure
        
        await send_response(
            message=self.mock_message,
            response=self.long_response,
            title=self.test_title
        )
        
        # Verify cwd.pw upload was attempted
        mock_cwd_upload.assert_called_once()
        
        # Verify fallback to plain text
        self.mock_message.edit_text.assert_called_once_with(self.long_response)

    @patch('bot.handlers.UPLOAD_SERVICE', 'telegra.ph')
    @patch('bot.handlers.create_telegraph_page')
    async def test_telegraph_failure_fallback_to_plain_text(self, mock_telegraph):
        """Test fallback to plain text when Telegraph creation fails."""
        mock_telegraph.return_value = None  # Simulate upload failure
        
        await send_response(
            message=self.mock_message,
            response=self.long_response,
            title=self.test_title
        )
        
        # Verify Telegraph was attempted
        mock_telegraph.assert_called_once()
        
        # Verify fallback to plain text
        self.mock_message.edit_text.assert_called_once_with(self.long_response)

    @patch('bot.handlers.UPLOAD_SERVICE', 'cwd.pw')
    @patch('bot.handlers.upload_to_cwd_pw_paste')
    async def test_plain_text_fallback_with_bad_request_truncation(self, mock_cwd_upload):
        """Test truncation when plain text fallback also fails with BadRequest."""
        mock_cwd_upload.return_value = None
        
        # Configure mock to raise BadRequest on plain text attempt
        self.mock_message.edit_text.side_effect = [
            BadRequest("Message_too_long"),  # First call fails
            None  # Second call (truncation) succeeds
        ]
        
        await send_response(
            message=self.mock_message,
            response=self.long_response,
            title=self.test_title
        )
        
        # Verify two calls to edit_text: first plain text, then truncated
        self.assertEqual(self.mock_message.edit_text.call_count, 2)
        
        # Check first call was the full response
        first_call = self.mock_message.edit_text.call_args_list[0]
        self.assertEqual(first_call[0][0], self.long_response)
        
        # Check second call was truncated
        second_call = self.mock_message.edit_text.call_args_list[1]
        truncated_text = second_call[0][0]
        self.assertTrue(truncated_text.endswith("...\n\n(Response was truncated due to length)"))
        self.assertTrue(len(truncated_text) < len(self.long_response))

    async def test_formatting_failure_fallback_to_plain_text(self):
        """Test fallback to plain text when markdown formatting fails."""
        
        # Configure mock to fail on formatted text but succeed on plain text
        self.mock_message.edit_text.side_effect = [
            Exception("Markdown parse error"),  # Formatted text fails
            None  # Plain text succeeds
        ]
        
        short_response = "Short response with *invalid markdown"
        
        await send_response(
            message=self.mock_message,
            response=short_response,
            parse_mode=MockParseMode.MARKDOWN
        )
        
        # Verify two attempts: formatted, then plain
        self.assertEqual(self.mock_message.edit_text.call_count, 2)
        
        # Check first call used markdown
        first_call = self.mock_message.edit_text.call_args_list[0]
        self.assertEqual(first_call[1]['parse_mode'], MockParseMode.MARKDOWN)
        
        # Check second call was plain text
        second_call = self.mock_message.edit_text.call_args_list[1]
        self.assertNotIn('parse_mode', second_call[1])

    @patch('bot.handlers.UPLOAD_SERVICE', 'telegra.ph')
    @patch('bot.handlers.create_telegraph_page')
    async def test_double_failure_handling(self, mock_telegraph):
        """Test handling when both upload service and plain text fail."""
        mock_telegraph.return_value = None  # Upload fails
        
        # Plain text also fails with a different error
        self.mock_message.edit_text.side_effect = BadRequest("Network error")
        
        await send_response(
            message=self.mock_message,
            response=self.long_response,
            title=self.test_title
        )
        
        # Verify both attempts were made
        mock_telegraph.assert_called_once()
        self.mock_message.edit_text.assert_called_once_with(self.long_response)

    @patch('bot.handlers.UPLOAD_SERVICE', 'cwd.pw')  
    @patch('bot.handlers.upload_to_cwd_pw_paste')
    async def test_unexpected_too_long_error_triggers_upload_fallback(self, mock_cwd_upload):
        """Test that unexpected 'Message_too_long' errors trigger upload fallback."""
        mock_cwd_upload.return_value = "https://cwd.pw/p/fallback_test"
        
        # Configure formatted text to succeed, but then plain text to fail with too_long
        self.mock_message.edit_text.side_effect = [
            Exception("Some formatting error"),  # Formatted fails
            BadRequest("Message_too_long"),  # Plain text fails due to length
            None  # Final truncated message succeeds
        ]
        
        medium_response = "Medium response " * 50  # Not initially long enough for upload
        
        await send_response(
            message=self.mock_message,
            response=medium_response,
            title=self.test_title
        )
        
        # Should have attempted upload as fallback when plain text failed
        mock_cwd_upload.assert_called_once()

    async def test_error_message_when_all_methods_fail(self):
        """Test error message when all sending methods fail."""
        # Configure all attempts to fail
        self.mock_message.edit_text.side_effect = [
            Exception("Format error"),  # Formatted fails
            BadRequest("Plain text error")  # Plain text fails but not with too_long
        ]
        
        short_response = "Short response"
        
        await send_response(
            message=self.mock_message,
            response=short_response
        )
        
        # Should attempt formatted, then plain, then error message
        self.assertEqual(self.mock_message.edit_text.call_count, 3)
        
        # Check that final call was error message
        final_call = self.mock_message.edit_text.call_args_list[2]
        error_message = final_call[0][0]
        self.assertEqual(error_message, "Error: Failed to format response. Please try again.")

    @patch('bot.handlers.UPLOAD_SERVICE', 'cwd.pw')
    @patch('bot.handlers.upload_to_cwd_pw_paste')
    @patch('bot.handlers.create_telegraph_page') 
    async def test_complex_failure_cascade(self, mock_telegraph, mock_cwd_upload):
        """Test complex failure scenario with multiple fallbacks."""
        # All upload methods fail
        mock_cwd_upload.return_value = None
        mock_telegraph.return_value = None
        
        # Editing also fails in complex ways
        self.mock_message.edit_text.side_effect = [
            Exception("Formatting error"),  # Formatted text fails
            BadRequest("Message_too_long"),  # Plain text fails as too long
            None  # Final truncation succeeds
        ]
        
        await send_response(
            message=self.mock_message,
            response=self.long_response,
            title=self.test_title
        )
        
        # Verify the cascade:
        # 1. Should try cwd.pw upload (configured service)
        mock_cwd_upload.assert_called_once()
        
        # 2. Should try plain text editing (3 times due to the side_effect)
        self.assertEqual(self.mock_message.edit_text.call_count, 3)
        
        # 3. Final call should be truncation
        final_call = self.mock_message.edit_text.call_args_list[2]
        final_text = final_call[0][0]
        self.assertTrue(final_text.endswith("...\n\n(Response was truncated due to length)"))

    @patch('bot.handlers.UPLOAD_SERVICE', 'invalid_service')
    @patch('bot.handlers.create_telegraph_page')
    @patch('bot.handlers.upload_to_cwd_pw_paste')
    async def test_invalid_service_config_fallback(self, mock_cwd_upload, mock_telegraph):
        """Test behavior with invalid upload service configuration."""
        mock_telegraph.return_value = "https://telegra.ph/invalid_config_fallback"
        
        await send_response(
            message=self.mock_message,
            response=self.long_response,
            title=self.test_title
        )
        
        # Should fall back to Telegraph (default behavior)
        mock_telegraph.assert_called_once_with(self.test_title, self.long_response)
        
        # cwd.pw should not be called
        mock_cwd_upload.assert_not_called()
        
        # Should succeed with Telegraph URL
        self.mock_message.edit_text.assert_called_once_with(
            "I have too much to say. Please view it here: https://telegra.ph/invalid_config_fallback"
        )

    @patch('bot.handlers.TELEGRAM_MAX_LENGTH', 100)  # Set very low threshold for testing
    async def test_length_threshold_boundary_conditions(self):
        """Test behavior at the exact boundaries of length thresholds."""
        # Test response exactly at character threshold
        exactly_threshold_response = "x" * 100
        
        with patch('bot.handlers.UPLOAD_SERVICE', 'telegra.ph'), \
             patch('bot.handlers.create_telegraph_page') as mock_telegraph:
            
            mock_telegraph.return_value = "https://telegra.ph/boundary_test"
            
            await send_response(
                message=self.mock_message,
                response=exactly_threshold_response,
                title="Boundary Test"
            )
            
            # At exactly the threshold, should NOT trigger upload (> threshold required)
            mock_telegraph.assert_not_called()
            
            # Should send as normal message
            self.mock_message.edit_text.assert_called_once_with(
                exactly_threshold_response,
                parse_mode=None  # Default parse_mode
            )

    async def test_line_threshold_boundary_conditions(self):
        """Test behavior at the exact boundaries of line count thresholds."""
        # Test response with exactly 22 lines (threshold in code)
        exactly_line_threshold = "line\n" * 22
        
        # Should NOT trigger upload (threshold is > 22 lines)
        await send_response(
            message=self.mock_message,
            response=exactly_line_threshold,
            title="Line Boundary Test"
        )
        
        # Should send as normal message without triggering upload services
        self.mock_message.edit_text.assert_called_once_with(
            exactly_line_threshold,
            parse_mode=None
        )


if __name__ == '__main__':
    unittest.main()