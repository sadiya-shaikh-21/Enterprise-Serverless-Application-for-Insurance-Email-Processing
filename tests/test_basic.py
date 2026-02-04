"""
Basic test to verify our setup works
"""

def test_import_handler():
    """Test that we can import the Lambda handler"""
    try:
        from src.email_receiver.handler import lambda_handler
        assert True, "Import successful"
    except ImportError as e:
        assert False, f"Import failed: {e}"

def test_sample():
    """Sample test - always passes"""
    assert 1 + 1 == 2

if __name__ == "__main__":
    test_import_handler()
    test_sample()
    print("✅ All basic tests passed!")