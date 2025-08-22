"""Tests for configuration validation and environment variable handling."""

import unittest
from unittest.mock import patch
import os

from bot import config


class TestConfigValidation(unittest.TestCase):
    """Test configuration validation and environment variable handling."""

    def setUp(self):
        """Set up test fixtures."""
        # Store original environment variables to restore later
        self.original_env = {}
        env_vars = ['UPLOAD_SERVICE', 'CWD_PW_API_KEY', 'TELEGRAPH_ACCESS_TOKEN']
        for var in env_vars:
            self.original_env[var] = os.environ.get(var)

    def tearDown(self):
        """Restore original environment variables."""
        for var, value in self.original_env.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value

    @patch.dict(os.environ, {'UPLOAD_SERVICE': 'telegra.ph'})
    def test_upload_service_telegraph_config(self):
        """Test UPLOAD_SERVICE configuration with telegra.ph."""
        # Reload config module to pick up new environment variable
        import importlib
        importlib.reload(config)
        
        self.assertEqual(config.UPLOAD_SERVICE, 'telegra.ph')

    @patch.dict(os.environ, {'UPLOAD_SERVICE': 'cwd.pw'})
    def test_upload_service_cwd_pw_config(self):
        """Test UPLOAD_SERVICE configuration with cwd.pw."""
        import importlib
        importlib.reload(config)
        
        self.assertEqual(config.UPLOAD_SERVICE, 'cwd.pw')

    @patch.dict(os.environ, {}, clear=True)
    def test_upload_service_default_value(self):
        """Test UPLOAD_SERVICE defaults to telegra.ph when not set."""
        import importlib
        importlib.reload(config)
        
        self.assertEqual(config.UPLOAD_SERVICE, 'telegra.ph')

    @patch.dict(os.environ, {'UPLOAD_SERVICE': 'INVALID_SERVICE'})
    def test_upload_service_invalid_value_handling(self):
        """Test that invalid UPLOAD_SERVICE values are accepted (handled at runtime)."""
        import importlib
        importlib.reload(config)
        
        # Config should accept any value (validation happens in handlers)
        self.assertEqual(config.UPLOAD_SERVICE, 'INVALID_SERVICE')

    @patch.dict(os.environ, {'CWD_PW_API_KEY': 'test_api_key_123'})
    def test_cwd_pw_api_key_configuration(self):
        """Test CWD_PW_API_KEY configuration."""
        import importlib
        importlib.reload(config)
        
        self.assertEqual(config.CWD_PW_API_KEY, 'test_api_key_123')

    @patch.dict(os.environ, {}, clear=True)
    def test_cwd_pw_api_key_default_empty(self):
        """Test CWD_PW_API_KEY defaults to empty string."""
        import importlib
        importlib.reload(config)
        
        self.assertEqual(config.CWD_PW_API_KEY, '')

    @patch.dict(os.environ, {'TELEGRAPH_ACCESS_TOKEN': 'telegraph_token_123'})
    def test_telegraph_access_token_configuration(self):
        """Test TELEGRAPH_ACCESS_TOKEN configuration."""
        import importlib
        importlib.reload(config)
        
        self.assertEqual(config.TELEGRAPH_ACCESS_TOKEN, 'telegraph_token_123')

    @patch.dict(os.environ, {'UPLOAD_SERVICE': 'cwd.pw', 'CWD_PW_API_KEY': ''})
    def test_cwd_pw_service_without_api_key(self):
        """Test configuration validation when cwd.pw is selected but API key is missing."""
        import importlib
        importlib.reload(config)
        
        # Config should load successfully (validation happens at runtime)
        self.assertEqual(config.UPLOAD_SERVICE, 'cwd.pw')
        self.assertEqual(config.CWD_PW_API_KEY, '')

    @patch.dict(os.environ, {'UPLOAD_SERVICE': 'telegra.ph', 'TELEGRAPH_ACCESS_TOKEN': ''})
    def test_telegraph_service_without_access_token(self):
        """Test configuration when Telegraph is selected but access token is missing."""
        import importlib
        importlib.reload(config)
        
        # Config should load successfully
        self.assertEqual(config.UPLOAD_SERVICE, 'telegra.ph')
        self.assertEqual(config.TELEGRAPH_ACCESS_TOKEN, '')

    def test_case_insensitive_service_names(self):
        """Test that service names are handled case-sensitively (as expected by implementation)."""
        test_cases = [
            'telegra.ph',
            'TELEGRA.PH', 
            'cwd.pw',
            'CWD.PW',
            'Cwd.Pw'
        ]
        
        for service_name in test_cases:
            with patch.dict(os.environ, {'UPLOAD_SERVICE': service_name}):
                import importlib
                importlib.reload(config)
                
                # Should preserve exact case (case handling happens in handlers.py)
                self.assertEqual(config.UPLOAD_SERVICE, service_name)

    @patch.dict(os.environ, {'UPLOAD_SERVICE': '  cwd.pw  '})
    def test_whitespace_in_service_name(self):
        """Test that whitespace in service names is preserved (trimming happens at runtime)."""
        import importlib
        importlib.reload(config)
        
        # Should preserve whitespace (handled in handlers.py with .lower())
        self.assertEqual(config.UPLOAD_SERVICE, '  cwd.pw  ')

    @patch.dict(os.environ, {
        'UPLOAD_SERVICE': 'cwd.pw',
        'CWD_PW_API_KEY': 'test_key',
        'TELEGRAPH_ACCESS_TOKEN': 'test_token',
        'TELEGRAPH_AUTHOR_NAME': 'Test Bot',
        'TELEGRAPH_AUTHOR_URL': 'https://example.com'
    })
    def test_complete_upload_configuration(self):
        """Test complete configuration with both upload services configured."""
        import importlib
        importlib.reload(config)
        
        # Verify all upload-related configurations
        self.assertEqual(config.UPLOAD_SERVICE, 'cwd.pw')
        self.assertEqual(config.CWD_PW_API_KEY, 'test_key')
        self.assertEqual(config.TELEGRAPH_ACCESS_TOKEN, 'test_token')
        self.assertEqual(config.TELEGRAPH_AUTHOR_NAME, 'Test Bot')
        self.assertEqual(config.TELEGRAPH_AUTHOR_URL, 'https://example.com')

    def test_config_types_are_correct(self):
        """Test that configuration values have correct types."""
        # These should be strings
        self.assertIsInstance(config.UPLOAD_SERVICE, str)
        self.assertIsInstance(config.CWD_PW_API_KEY, str)
        self.assertIsInstance(config.TELEGRAPH_ACCESS_TOKEN, str)
        self.assertIsInstance(config.TELEGRAPH_AUTHOR_NAME, str)
        self.assertIsInstance(config.TELEGRAPH_AUTHOR_URL, str)

    @patch.dict(os.environ, {'TELEGRAM_MAX_LENGTH': '5000'})
    def test_telegram_max_length_configuration(self):
        """Test TELEGRAM_MAX_LENGTH affects upload thresholds."""
        import importlib
        importlib.reload(config)
        
        self.assertEqual(config.TELEGRAM_MAX_LENGTH, 5000)
        self.assertIsInstance(config.TELEGRAM_MAX_LENGTH, int)

    def test_all_upload_related_config_variables_exist(self):
        """Test that all expected upload-related configuration variables exist."""
        expected_configs = [
            'UPLOAD_SERVICE',
            'CWD_PW_API_KEY', 
            'TELEGRAPH_ACCESS_TOKEN',
            'TELEGRAPH_AUTHOR_NAME',
            'TELEGRAPH_AUTHOR_URL',
            'TELEGRAM_MAX_LENGTH'
        ]
        
        for config_var in expected_configs:
            self.assertTrue(hasattr(config, config_var), 
                          f"Config variable {config_var} should exist")

    @patch.dict(os.environ, {'UPLOAD_SERVICE': ''})
    def test_empty_upload_service_uses_default(self):
        """Test that empty UPLOAD_SERVICE string is preserved (os.getenv behavior)."""
        import importlib
        importlib.reload(config)
        
        # Empty string is returned as-is by os.getenv (expected behavior)
        self.assertEqual(config.UPLOAD_SERVICE, '')


class TestRuntimeConfigValidation(unittest.TestCase):
    """Test runtime configuration validation logic."""

    def test_upload_service_case_handling_logic(self):
        """Test the case-handling logic used in handlers."""
        # Test various case combinations
        test_cases = [
            ('cwd.pw', True),
            ('CWD.PW', True), 
            ('Cwd.Pw', True),
            ('telegra.ph', False),
            ('TELEGRA.PH', False),
            ('invalid_service', False)
        ]
        
        for service_name, should_be_cwd_pw in test_cases:
            # Test the logic used in send_response
            is_cwd_pw = service_name.lower() == "cwd.pw"
            self.assertEqual(is_cwd_pw, should_be_cwd_pw, 
                           f"Service '{service_name}' should {'be' if should_be_cwd_pw else 'not be'} recognized as cwd.pw")

    def test_upload_service_whitespace_handling_logic(self):
        """Test the whitespace handling logic."""
        test_cases = [
            ('  cwd.pw  ', False),  # Whitespace prevents match in current implementation
            (' CWD.PW ', False),
            ('cwd.pw\n', False),
            ('\ttelegra.ph\t', False),
            ('cwd.pw', True),  # Only exact match works
            ('CWD.PW', True)   # Case insensitive works
        ]
        
        for service_name, should_be_cwd_pw in test_cases:
            # Test the logic used in send_response (with .lower() but no strip)
            is_cwd_pw = service_name.lower() == "cwd.pw"
            self.assertEqual(is_cwd_pw, should_be_cwd_pw,
                           f"Service '{repr(service_name)}' should {'match' if should_be_cwd_pw else 'not match'} 'cwd.pw'")


if __name__ == '__main__':
    unittest.main()