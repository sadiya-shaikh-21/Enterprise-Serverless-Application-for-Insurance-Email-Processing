# environments/dev/main.tf - Simple version for dev environment

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "aws" {
  region = "eu-west-1"  # Ireland region
  
  default_tags {
    tags = {
      Environment = "dev"
      Project     = "insurance-email-processing"
      ManagedBy   = "Terraform"
    }
  }
}

provider "random" {}

# Generate random suffix for bucket name
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# S3 Bucket for emails
resource "aws_s3_bucket" "email_bucket" {
  bucket = "insurance-emails-dev-${random_id.bucket_suffix.hex}"
  
  # Allow destroy in dev
  force_destroy = true
  
  tags = {
    Name    = "Email Storage"
    UseCase = "Incoming insurance emails"
  }
}

# Block public access (security)
resource "aws_s3_bucket_public_access_block" "email_bucket" {
  bucket = aws_s3_bucket.email_bucket.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lambda Function
resource "aws_lambda_function" "email_receiver" {
  function_name = "insurance-email-receiver-dev"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  
  # Source code
  filename         = "../../../src/email_receiver/lambda_package.zip"
  source_code_hash = filebase64sha256("../../../src/email_receiver/lambda_package.zip")
  
  # Performance
  timeout     = 30
  memory_size = 128
  
  # Environment variables
  environment {
    variables = {
      ENVIRONMENT = "dev"
      S3_BUCKET   = aws_s3_bucket.email_bucket.id
    }
  }
  
  tags = {
    Function = "Email Receiver"
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_exec" {
  name = "lambda-execution-role-dev"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Attach basic execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Allow S3 to trigger Lambda
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.email_receiver.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.email_bucket.arn
}

# Configure S3 to notify Lambda
resource "aws_s3_bucket_notification" "email_notification" {
  bucket = aws_s3_bucket.email_bucket.id
  
  lambda_function {
    lambda_function_arn = aws_lambda_function.email_receiver.arn
    events              = ["s3:ObjectCreated:*"]
  }
  
  depends_on = [aws_lambda_permission.allow_s3]
}

# Outputs
output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.email_bucket.id
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.email_receiver.function_name
}

output "deployment_instructions" {
  description = "How to test the deployment"
  value = <<-EOT
  
  ✅ DEPLOYMENT COMPLETE!
  
  To test:
  1. Upload a file to S3:
     aws s3 cp test.pdf s3://${aws_s3_bucket.email_bucket.id}/
     
  2. Check Lambda logs in AWS Console
  3. View resources in AWS Console
  
  To destroy:
  terraform destroy
  EOT
}
