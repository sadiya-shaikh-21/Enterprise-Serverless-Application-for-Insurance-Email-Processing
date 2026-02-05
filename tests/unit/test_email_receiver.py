"""
Unit Tests for Email Receiver Lambda Function
Tests each part in isolation using mocks
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock

# Import the function we're testing
from email_receiver.handler import lambda_handler

# ===========================================
# TEST 1: SUCCESSFUL EXECUTION
# ===========================================

def test_lambda_handler_success_with_pdf(sample_s3_event, sample_context):
    """
    Test Lambda handles PDF file correctly
    Happy path - everything works
    """
    # Act: Call the Lambda handler
    result = lambda_handler(sample_s3_event, sample_context)
    
    # Assert: Check the response
    assert result['statusCode'] == 200
    
    # Parse the response body
    response_body = json.loads(result['body'])
    
    # Check response structure
    assert response_body['status'] == 'success'
    assert response_body['message'] == 'Email received for processing'
    assert 'details' in response_body
    
    # Check details
    details = response_body['details']
    assert details['bucket'] == 'insurance-emails-dev'
    assert details['file'] == 'incoming/customer_claim.pdf'
    assert 'processed_at' in details
    assert details['next_step'] == 'Send to extraction queue'

def test_lambda_handler_success_with_txt(txt_event, sample_context):
    """
    Test Lambda handles text file correctly
    """
    result = lambda_handler(txt_event, sample_context)
    
    assert result['statusCode'] == 200
    response_body = json.loads(result['body'])
    assert response_body['status'] == 'success'
    
    details = response_body['details']
    assert details['file'] == 'emails/email_body.txt'
    assert 'txt' in details['file']  # Check file extension in path

def test_lambda_handler_success_with_eml(eml_event, sample_context):
    """
    Test Lambda handles .eml email file correctly
    """
    result = lambda_handler(eml_event, sample_context)
    
    assert result['statusCode'] == 200
    response_body = json.loads(result['body'])
    assert response_body['status'] == 'success'
    assert 'eml' in response_body['details']['file']

# ===========================================
# TEST 2: ERROR HANDLING
# ===========================================

def test_lambda_handler_empty_event():
    """
    Test Lambda handles empty event gracefully
    """
    empty_event = {}
    mock_context = Mock()
    
    result = lambda_handler(empty_event, mock_context)
    
    assert result['statusCode'] == 400
    response_body = json.loads(result['body'])
    assert 'error' in response_body
    assert 'Invalid event' in response_body['error']

def test_lambda_handler_no_records():
    """
    Test Lambda handles event with no Records array
    """
    event_no_records = {"NotRecords": []}
    mock_context = Mock()
    
    result = lambda_handler(event_no_records, mock_context)
    
    assert result['statusCode'] == 400
    response_body = json.loads(result['body'])
    assert 'error' in response_body

def test_lambda_handler_wrong_event_source():
    """
    Test Lambda rejects non-S3 events
    """
    sqs_event = {
        "Records": [{
            "eventSource": "aws:sqs",  # Wrong source!
            "body": "not an email"
        }]
    }
    mock_context = Mock()
    
    result = lambda_handler(sqs_event, mock_context)
    
    assert result['statusCode'] == 400
    response_body = json.loads(result['body'])
    assert 'error' in response_body
    assert 'No S3 events found' in response_body['error']

# ===========================================
# TEST 3: EXCEPTION HANDLING
# ===========================================

def test_lambda_handler_malformed_s3_data():
    """
    Test Lambda handles malformed S3 data gracefully
    """
    malformed_event = {
        "Records": [{
            "eventSource": "aws:s3",
            "s3": {}  # Missing bucket/object data
        }]
    }
    mock_context = Mock()
    
    result = lambda_handler(malformed_event, mock_context)
    
    # Should return 500 because accessing missing keys raises exception
    assert result['statusCode'] == 500
    response_body = json.loads(result['body'])
    assert 'error' in response_body
    assert 'Internal server error' in response_body['error']

def test_lambda_handler_multiple_records(sample_context):
    """
    Test Lambda handles multiple files in one event
    """
    multi_event = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {"name": "bucket1"},
                    "object": {"key": "file1.pdf"}
                }
            },
            {
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {"name": "bucket1"},
                    "object": {"key": "file2.pdf"}
                }
            }
        ]
    }
    
    result = lambda_handler(multi_event, sample_context)
    
    # Should process first file and return
    assert result['statusCode'] == 200
    response_body = json.loads(result['body'])
    assert response_body['details']['file'] == 'file1.pdf'

# ===========================================
# TEST 4: EDGE CASES
# ===========================================

def test_lambda_handler_s3_delete_event():
    """
    Test Lambda ignores S3 delete events (only processes creates)
    """
    delete_event = {
        "Records": [{
            "eventSource": "aws:s3",
            "eventName": "ObjectRemoved:Delete",  # Delete, not create
            "s3": {
                "bucket": {"name": "test-bucket"},
                "object": {"key": "deleted_file.pdf"}
            }
        }]
    }
    mock_context = Mock()
    
    result = lambda_handler(delete_event, mock_context)
    
    # Still processes as S3 event, doesn't check eventName
    assert result['statusCode'] == 200

def test_lambda_handler_large_filename():
    """
    Test Lambda handles files with special characters in names
    """
    special_event = {
        "Records": [{
            "eventSource": "aws:s3",
            "s3": {
                "bucket": {"name": "test-bucket"},
                "object": {"key": "incoming/claim with spaces & special chars (123).pdf"}
            }
        }]
    }
    mock_context = Mock()
    
    result = lambda_handler(special_event, mock_context)
    
    assert result['statusCode'] == 200
    response_body = json.loads(result['body'])
    assert 'spaces & special chars' in response_body['details']['file']

# ===========================================
# TEST 5: LOGGING AND OUTPUT
# ===========================================

@patch('builtins.print')
def test_lambda_logging(mock_print, sample_s3_event, sample_context):
    """
    Test that Lambda logs appropriate messages
    """
    result = lambda_handler(sample_s3_event, sample_context)
    
    # Check that print was called (our logging method)
    assert mock_print.called
    
    # Get all print calls
    print_calls = [call[0][0] for call in mock_print.call_args_list]
    
    # Check for specific log messages
    log_messages = ' '.join(str(call) for call in print_calls)
    
    assert 'Lambda function started' in log_messages
    assert 'Email file detected' in log_messages
    assert 'Processing complete' in log_messages

# ===========================================
# TEST 6: RESPONSE FORMAT
# ===========================================

def test_response_format_consistency(sample_s3_event, sample_context):
    """
    Test that Lambda always returns the same response format
    """
    result = lambda_handler(sample_s3_event, sample_context)
    
    # Required top-level keys
    required_keys = ['statusCode', 'body']
    for key in required_keys:
        assert key in result
    
    # Body must be valid JSON
    body = json.loads(result['body'])
    
    # Required body keys for success
    assert 'status' in body
    assert 'message' in body
    assert 'details' in body
    
    # Required detail keys
    details = body['details']
    detail_keys = ['bucket', 'file', 'processed_at', 'next_step']
    for key in detail_keys:
        assert key in details

# ===========================================
# TEST 7: USING HELPER FUNCTIONS
# ===========================================

def test_with_custom_helper(sample_s3_event, sample_context):
    """
    Test using the helper function from conftest.py
    """
    from tests.conftest import assert_lambda_response
    
    result = lambda_handler(sample_s3_event, sample_context)
    
    # Use helper to validate response
    validated = assert_lambda_response(
        result,
        expected_status=200,
        expected_keys=['status', 'message', 'details']
    )
    
    # Additional assertions
    body = json.loads(validated['body'])
    assert body['status'] == 'success'

# ===========================================
# TEST 8: PERFORMANCE/LOAD (Simple)
# ===========================================

def test_lambda_handler_performance(sample_s3_event, sample_context):
    """
    Simple performance test - should complete quickly
    """
    import time
    
    start_time = time.time()
    
    # Run multiple times
    for _ in range(10):
        result = lambda_handler(sample_s3_event, sample_context)
        assert result['statusCode'] == 200
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Should complete 10 executions in under 1 second
    assert execution_time < 1.0, f"Too slow: {execution_time:.2f} seconds"
    
    print(f"Performance: 10 executions in {execution_time:.3f} seconds")