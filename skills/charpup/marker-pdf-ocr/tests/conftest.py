"""
Pytest configuration and fixtures for Marker PDF OCR tests
"""
import pytest
import os
import tempfile
from pathlib import Path


# Test markers
def pytest_configure(config):
    """Configure custom test markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "acceptance: Acceptance tests")
    config.addinivalue_line("markers", "cloud: Cloud API tests")
    config.addinivalue_line("markers", "local_cpu: Local CPU tests")
    config.addinivalue_line("markers", "local_docker: Local Docker tests")
    config.addinivalue_line("markers", "failover: Failover mechanism tests")
    config.addinivalue_line("markers", "batch: Batch processing tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "quality: Output quality tests")
    config.addinivalue_line("markers", "external_api: Tests requiring external API access")


@pytest.fixture
def test_data_dir():
    """Return path to test data directory"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_pdf_content():
    """Return minimal valid PDF content for testing"""
    return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF content) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000205 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
298
%%EOF"""


@pytest.fixture
def create_sample_pdf(tmp_path, sample_pdf_content):
    """Factory fixture to create sample PDF files"""
    def _create(filename="test.pdf", content=None):
        pdf_path = tmp_path / filename
        pdf_path.write_bytes(content or sample_pdf_content)
        return str(pdf_path)
    return _create


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture to set and cleanup environment variables"""
    def _set_env(vars_dict):
        for key, value in vars_dict.items():
            if value is None:
                monkeypatch.delenv(key, raising=False)
            else:
                monkeypatch.setenv(key, value)
    return _set_env


@pytest.fixture
def clean_temp_files():
    """Cleanup temporary files after test"""
    temp_files = []
    yield temp_files
    # Cleanup
    for file_path in temp_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
