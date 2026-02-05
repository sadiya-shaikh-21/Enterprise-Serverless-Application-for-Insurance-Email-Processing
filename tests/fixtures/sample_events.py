"""
Sample events for testing
Real-world S3 events that Lambda might receive
"""

SAMPLE_S3_PUT_EVENT = {
    "Records": [
        {
            "eventVersion": "2.1",
            "eventSource": "aws:s3",
            "awsRegion": "eu-west-1",
            "eventTime": "2024-02-04T10:00:00Z",
            "eventName": "ObjectCreated:Put",
            "userIdentity": {
                "principalId": "AWS:AROA3NSJNVJ6Y5P4P7RKI:email-receiver-dev"
            },
            "requestParameters": {
                "sourceIPAddress": "54.240.197.233"
            },
            "responseElements": {
                "x-amz-request-id": "D2B5B5F5C3E4F5A2",
                "x-amz-id-2": "EXgKp7WDFc8sQqvOcg4mj/B5u5Y6LvU2wMWb9VpC8JzQ/7fXhGXoE8aC6pR4Dd8N8rT9sK5nJ7g="
            },
            "s3": {
                "s3SchemaVersion": "1.0",
                "configurationId": "EmailProcessor",
                "bucket": {
                    "name": "insurance-emails-production",
                    "ownerIdentity": {
                        "principalId": "A3NL1KOZZKExample"
                    },
                    "arn": "arn:aws:s3:::insurance-emails-production"
                },
                "object": {
                    "key": "incoming/2024/02/04/customer_claim_12345.pdf",
                    "size": 512345,
                    "eTag": "0123456789abcdef0123456789abcdef",
                    "sequencer": "0055AED6DCD90281E5"
                }
            }
        }
    ]
}

SAMPLE_S3_COPY_EVENT = {
    "Records": [
        {
            "eventVersion": "2.1",
            "eventSource": "aws:s3",
            "awsRegion": "us-east-1",
            "eventTime": "2024-02-04T11:30:00Z",
            "eventName": "ObjectCreated:Copy",
            "userIdentity": {
                "principalId": "AWS:AROA3NSJNVJ6Y5P4P7RKI:email-processor"
            },
            "requestParameters": {
                "sourceIPAddress": "52.46.137.41"
            },
            "responseElements": {
                "x-amz-request-id": "7B6B7B8B9B0B1B",
                "x-amz-id-2": "d2B5b5f5c3e4f5a2EXgKp7WDFc8sQqvOcg4mj/B5u5Y6LvU2wMWb9VpC8JzQ/7fXhGXoE8aC6pR4"
            },
            "s3": {
                "s3SchemaVersion": "1.0",
                "configurationId": "EmailCopyRule",
                "bucket": {
                    "name": "insurance-archive",
                    "ownerIdentity": {
                        "principalId": "A3NL1KOZZKExample"
                    },
                    "arn": "arn:aws:s3:::insurance-archive"
                },
                "object": {
                    "key": "processed/claim_12345_20240204.pdf",
                    "size": 512345,
                    "eTag": "fedcba9876543210fedcba9876543210",
                    "versionId": "HkNDgUqXZzF1T.example.5p7WDFc8sQqvOcg",
                    "sequencer": "0055BEE6DCD90281E5"
                }
            }
        }
    ]
}

SAMPLE_MULTIPLE_FILES_EVENT = {
    "Records": [
        {
            "eventSource": "aws:s3",
            "s3": {
                "bucket": {"name": "insurance-emails"},
                "object": {"key": "incoming/claim1.pdf"}
            }
        },
        {
            "eventSource": "aws:s3",
            "s3": {
                "bucket": {"name": "insurance-emails"},
                "object": {"key": "incoming/claim2.pdf"}
            }
        },
        {
            "eventSource": "aws:s3",
            "s3": {
                "bucket": {"name": "insurance-emails"},
                "object": {"key": "incoming/policy_update.docx"}
            }
        }
    ]
}

# File type variations
FILE_TYPE_EVENTS = {
    "pdf": {
        "Records": [{
            "eventSource": "aws:s3",
            "s3": {
                "bucket": {"name": "test-bucket"},
                "object": {"key": "document.pdf"}
            }
        }]
    },
    "docx": {
        "Records": [{
            "eventSource": "aws:s3",
            "s3": {
                "bucket": {"name": "test-bucket"},
                "object": {"key": "report.docx"}
            }
        }]
    },
    "txt": {
        "Records": [{
            "eventSource": "aws:s3",
            "s3": {
                "bucket": {"name": "test-bucket"},
                "object": {"key": "email.txt"}
            }
        }]
    },
    "eml": {
        "Records": [{
            "eventSource": "aws:s3",
            "s3": {
                "bucket": {"name": "test-bucket"},
                "object": {"key": "message.eml"}
            }
        }]
    },
    "jpg": {
        "Records": [{
            "eventSource": "aws:s3",
            "s3": {
                "bucket": {"name": "test-bucket"},
                "object": {"key": "scan.jpg"}
            }
        }]
    }
}

# Error case events
ERROR_EVENTS = {
    "missing_bucket": {
        "Records": [{
            "eventSource": "aws:s3",
            "s3": {
                "object": {"key": "file.pdf"}  # Missing bucket
            }
        }]
    },
    "missing_key": {
        "Records": [{
            "eventSource": "aws:s3",
            "s3": {
                "bucket": {"name": "test-bucket"}
                # Missing object key
            }
        }]
    },
    "empty_object": {
        "Records": [{
            "eventSource": "aws:s3",
            "s3": {}  # Empty s3 object
        }]
    }
}

# Helper function to get event by file type
def get_event_for_filetype(file_type):
    """Get a test event for specific file type"""
    return FILE_TYPE_EVENTS.get(file_type.lower(), FILE_TYPE_EVENTS["pdf"])

# Helper to create custom event
def create_custom_event(bucket="test-bucket", key="test.pdf", event_name="ObjectCreated:Put"):
    """Create a custom S3 event"""
    return {
        "Records": [{
            "eventSource": "aws:s3",
            "eventName": event_name,
            "s3": {
                "bucket": {"name": bucket},
                "object": {"key": key}
            }
        }]
    }