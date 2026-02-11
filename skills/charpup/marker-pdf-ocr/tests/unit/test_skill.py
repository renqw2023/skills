"""
Test Template for TDD+SDD Skills
Copy this file and customize for your skill
"""
import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Import your module
# from lib.your_module import YourClass


# ============================================================================
# UNIT TESTS - Fast, isolated, no external dependencies
# ============================================================================

class TestYourFeature:
    """Unit tests for your feature"""
    
    def test_valid_input(self):
        """TEST: Valid input produces expected output"""
        # Arrange
        # service = YourClass()
        
        # Act
        # result = service.process("valid input")
        
        # Assert
        # assert result['success'] is True
        pytest.skip("Implement this test")
    
    def test_invalid_input_raises_error(self):
        """TEST: Invalid input raises appropriate error"""
        # Arrange
        # service = YourClass()
        
        # Act & Assert
        # with pytest.raises(ValueError):
        #     service.process("")
        pytest.skip("Implement this test")
    
    def test_mock_external_dependency(self):
        """TEST: External dependencies are properly mocked"""
        # with patch('lib.your_module.external_call') as mock_call:
        #     mock_call.return_value = {"mocked": True}
        #     
        #     # Your test code here
        #     
        #     mock_call.assert_called_once()
        pytest.skip("Implement this test")


class TestConfiguration:
    """Tests for configuration and initialization"""
    
    def test_missing_required_config(self):
        """TEST: Missing required config raises error"""
        # with patch.dict(os.environ, {}, clear=True):
        #     with pytest.raises(ValueError):
        #         YourClass()
        pytest.skip("Implement this test")
    
    def test_valid_config_initialization(self):
        """TEST: Valid config initializes successfully"""
        # with patch.dict(os.environ, {'REQUIRED_VAR': 'value'}):
        #     service = YourClass()
        #     assert service.is_initialized
        pytest.skip("Implement this test")


# ============================================================================
# FIXTURES - Reusable test setup
# ============================================================================

@pytest.fixture
def mock_service():
    """Fixture: Creates a mocked service"""
    # service = Mock()
    # service.process.return_value = {"success": True}
    # return service
    pass


@pytest.fixture
def temp_directory(tmp_path):
    """Fixture: Provides a temporary directory"""
    return tmp_path


# ============================================================================
# MARKERS - Use markers to categorize tests
# ============================================================================

@pytest.mark.slow
class TestSlowOperations:
    """Tests that take longer to run"""
    
    def test_large_dataset_processing(self):
        """TEST: Can handle large datasets"""
        pytest.skip("Slow test - implement if needed")


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
