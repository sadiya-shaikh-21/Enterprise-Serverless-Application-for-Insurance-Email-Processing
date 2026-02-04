"""
Email Receiver Lambda Function
Processes insurance emails uploaded to S3 bucket
"""

import json
import os
import logging

# Setup logging - messages will appear in AWS CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    AWS Lambda calls this function when triggered
    
    Parameters:
    - event: Contains data about what triggered Lambda (S3 upload info)
    - context: Information about the Lambda execution
    
    Returns:
    - Dictionary with status code and message
    """
    
    print("🎯 Lambda function started!")
    print(f"Event received: {json.dumps(event, indent=2)}")
    
    try:
        # Check if event has Records (S3 events always do)
        if 'Records' not in event:
            print("⚠️ No records found in event")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid event - no records'})
            }
        
        # Process each record (usually just one)
        for record in event['Records']:
            
            # Check if this is from S3
            if record.get('eventSource') == 'aws:s3':
                # Extract bucket and file information
                bucket_name = record['s3']['bucket']['name']
                file_key = record['s3']['object']['key']
                
                print(f"📧 Email file detected!")
                print(f"   Bucket: {bucket_name}")
                print(f"   File: {file_key}")
                print(f"   File type: {file_key.split('.')[-1]}")
                
                # Business logic would go here:
                # 1. Download file from S3
                # 2. Parse email content
                # 3. Extract insurance claim details
                # 4. Send to next processing step
                
                # For now, just log and return success
                message = {
                    'status': 'success',
                    'message': 'Email received for processing',
                    'details': {
                        'bucket': bucket_name,
                        'file': file_key,
                        'processed_at': '2024-02-04',  # Would use datetime in real code
                        'next_step': 'Send to extraction queue'
                    }
                }
                
                print(f"✅ Processing complete: {message}")
                
                return {
                    'statusCode': 200,
                    'body': json.dumps(message)
                }
            else:
                print(f"⚠️ Event not from S3. Source: {record.get('eventSource')}")
        
        # If we get here, no S3 records were found
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'No S3 events found'})
        }
        
    except Exception as error:
        # Catch any unexpected errors
        print(f"❌ ERROR in Lambda: {str(error)}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(error)
            })
        }


# ===========================================
# LOCAL TESTING SECTION
# This only runs when you execute the file locally
# AWS Lambda ignores everything below
# ===========================================
if __name__ == "__main__":
    """
    Test the Lambda function on your computer
    Run: python src/email_receiver/handler.py
    """
    
    print("=" * 50)
    print("🧪 LOCAL TEST: Email Receiver Lambda")
    print("=" * 50)
    
    # Create a fake S3 event (what AWS would send)
    test_event = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "awsRegion": "eu-west-1",
                "eventTime": "2024-02-04T10:00:00Z",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {
                        "name": "insurance-emails-dev",
                        "arn": "arn:aws:s3:::insurance-emails-dev"
                    },
                    "object": {
                        "key": "incoming/claim_12345.pdf",
                        "size": 10245,
                        "eTag": "abc123def456"
                    }
                }
            }
        ]
    }
    
    # Create a fake context (simplified)
    class FakeContext:
        function_name = "email-receiver-test"
        aws_request_id = "test-123"
        memory_limit_in_mb = 128
    
    fake_context = FakeContext()
    
    print("\n1️⃣ Testing with PDF email...")
    result = lambda_handler(test_event, fake_context)
    print(f"Result: {json.dumps(json.loads(result['body']), indent=2)}")
    
    print("\n2️⃣ Testing with different file types...")
    
    # Test with .txt file
    test_event["Records"][0]["s3"]["object"]["key"] = "incoming/email_123.txt"
    result = lambda_handler(test_event, fake_context)
    print(f"Text file result: {result['statusCode']}")
    
    # Test with .eml file (actual email)
    test_event["Records"][0]["s3"]["object"]["key"] = "incoming/customer_query.eml"
    result = lambda_handler(test_event, fake_context)
    print(f"Email file result: {result['statusCode']}")
    
    print("\n3️⃣ Testing error case (no records)...")
    error_event = {}  # Empty event
    result = lambda_handler(error_event, fake_context)
    print(f"Error result: {result['statusCode']}")
    
    print("\n" + "=" * 50)
    print("✅ LOCAL TESTS COMPLETE")
    print("=" * 50)
    print("\nNext: Run this with: python src/email_receiver/handler.py")