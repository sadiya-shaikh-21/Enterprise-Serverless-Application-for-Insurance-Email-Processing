"""
pytest configuration file
This file is automatically discovered by pytest
It provides shared test fixtures and setup
"""

import pytest
import sys
import os
import json
from unittest.mock import Mock, MagicMock

# Add src to Python path so we can import our code
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# ===========================================
# FIXTURES - Reusable test components
# ===========================================

@pytest.fixture
def sample_s3_event():
    """
    Provides a realistic S3 event for testing
    Use in tests: def test_something(sample_s3_event):
    """
    return {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "awsRegion": "eu-west-1",
                "eventTime": "2024-02-04T10:00:00Z",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "s3SchemaVersion": "1.0",
                    "configurationId": "testConfigRule",
                    "bucket": {
                        "name": "insurance-emails-dev",
                        "ownerIdentity": {"principalId": "EXAMPLE"},
                        "arn": "arn:aws:s3:::insurance-emails-dev"
                    },
                    "object": {
                        "key": "incoming/customer_claim.pdf",
                        "size": 1024,
                        "eTag": "0123456789abcdef",
                        "versionId": "1",
                        "sequencer": "0A1B2C3D4E5F678901"
                    }
                }
            }
        ]
    }

@pytest.fixture
def sample_context():
    """
    Provides a mock Lambda context object
    """
    context = Mock()
    context.function_name = "email-receiver-dev"
    context.function_version = "$LATEST"
    context.invoked_function_arn = "arn:aws:lambda:eu-west-1:123456789012:function:email-receiver-dev"
    context.memory_limit_in_mb = 128
    context.aws_request_id = "test-request-id-123"
    context.log_group_name = "/aws/lambda/email-receiver-dev"
    context.log_stream_name = "2024/02/04/[$LATEST]abc123def456"
    
    return context

@pytest.fixture
def mock_boto3_client(monkeypatch):
    """
    Mocks AWS boto3 client calls
    Prevents actual AWS API calls during tests
    """
    mock_client = MagicMock()
    
    def mock_return(*args, **kwargs):
        return mock_client
    
    # Patch boto3.client to return our mock
    monkeypatch.setattr("boto3.client", mock_return)
    
    return mock_client

@pytest.fixture
def pdf_event():
    """S3 event for PDF file"""
    return {
        "Records": [{
            "eventSource": "aws:s3",
            "s3": {
                "bucket": {"name": "test-bucket"},
                "object": {"key": "emails/claim_123.pdf"}
            }
        }]
    }

@pytest.fixture
def txt_event():
    """S3 event for text file"""
    return {
        "Records": [{
            "eventSource": "aws:s3",
            "s3": {
                "bucket": {"name": "test-bucket"},
                "object": {"key": "emails/email_body.txt"}
            }
        }]
    }

@pytest.fixture
def eml_event():
    """S3 event for .eml email file"""
    return {
        "Records": [{
            "eventSource": "aws:s3",
            "s3": {
                "bucket": {"name": "test-bucket"},
                "object": {"key": "emails/message.eml"}
            }
        }]
    }

# ===========================================
# TEST HELPERS - Utility functions for tests
# ===========================================

def read_json_file(filepath):
    """Helper to read JSON test data"""
    with open(filepath, 'r') as f:
        return json.load(f)

def assert_lambda_response(response, expected_status=200, expected_keys=None):
    """
    Helper to validate Lambda responses
    
    Args:
        response: Lambda return value
        expected_status: Expected HTTP status code
        expected_keys: List of keys that should be in response body
    """
    assert 'statusCode' in response
    assert response['statusCode'] == expected_status
    
    if 'body' in response:
        body = json.loads(response['body'])
        
        if expected_keys:
            for key in expected_keys:
                assert key in body, f"Missing key in response: {key}"
    
    return response

# ===========================================
# HOOKS - Run code at specific test phases
# ===========================================

def pytest_runtest_setup(item):
    """Runs before each test"""
    print(f"\n🔧 Setting up test: {item.name}")

def pytest_runtest_teardown(item):
    """Runs after each test"""
    print(f"🧹 Cleaning up test: {item.name}")

# ===========================================
# PYTEST CONFIGURATION
# ===========================================

def pytest_collection_modifyitems(config, items):
    """Modify test collection/ordering"""
    # Example: Run unit tests before integration tests
    pass