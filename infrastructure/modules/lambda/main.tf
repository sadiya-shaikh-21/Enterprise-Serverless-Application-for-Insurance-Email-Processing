# environments/dev/main.tf - Main configuration for dev environment

# Data sources - get information about existing resources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Generate random suffix for bucket name if not provided
resource "random_id" "bucket_suffix" {
  count = var.s3_bucket_name == "" ? 1 : 0
  
  byte_length = 4
}

# Local values - computed values used in configuration
locals {
  # Generate bucket name if not provided
  bucket_name = var.s3_bucket_name != "" ? var.s3_bucket_name : "${var.project_name}-${var.environment}-${try(random_id.bucket_suffix[0].hex, "emails")}"
  
  # Common tags for all resources
  common_tags = merge(var.additional_tags, {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
    Owner       = "Insurance Team"
    CostCenter  = var.cost_center
    Deployment  = timestamp()
  })
  
  # Lambda source paths
  email_receiver_source = "../../../src/email_receiver/lambda_package.zip"
  
  # Check if source files exist
  source_files_exist = fileexists(local.email_receiver_source)
}

# ===========================================
# S3 BUCKET FOR EMAILS
# ===========================================

resource "aws_s3_bucket" "email_bucket" {
  bucket = local.bucket_name
  
  # Prevent accidental deletion in production
  force_destroy = var.environment == "dev" ? true : false
  
  tags = merge(local.common_tags, {
    Name        = "Email Storage"
    UseCase     = "Incoming insurance emails"
    DataClass   = "Confidential"
  })
}

# Enable versioning (optional)
resource "aws_s3_bucket_versioning" "email_bucket" {
  count = var.enable_s3_versioning ? 1 : 0
  
  bucket = aws_s3_bucket.email_bucket.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Block all public access (security best practice)
resource "aws_s3_bucket_public_access_block" "email_bucket" {
  bucket = aws_s3_bucket.email_bucket.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "email_bucket" {
  bucket = aws_s3_bucket.email_bucket.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ===========================================
# LAMBDA FUNCTIONS USING MODULE
# ===========================================

module "email_receiver_lambda" {
  source = "../../modules/lambda"
  
  # Basic configuration
  function_name = "${var.project_name}-email-receiver-${var.environment}"
  description   = "Receives and processes insurance emails from S3"
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  
  # Source code
  source_path   = local.email_receiver_source
  source_version = "1.0.0-dev"  # In CI/CD, use git commit hash
  
  # Performance
  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory
  
  # Environment variables
  environment_variables = {
    ENVIRONMENT      = var.environment
    S3_BUCKET_NAME   = aws_s3_bucket.email_bucket.id
    AWS_REGION       = var.aws_region
    LOG_LEVEL        = "INFO"
  }
  
  # Logging
  log_retention_days = var.lambda_log_retention
  
  # Tags
  tags = merge(local.common_tags, {
    Component = "lambda"
    Function  = "email-receiver"
  })
  
  # Optional features
  create_alias        = false  # Enable for production
  enable_function_url = false
  
  # Security
  prevent_destroy = false  # Set to true for production
}

# ===========================================
# S3 EVENT NOTIFICATION TO LAMBDA
# ===========================================

# Allow S3 to invoke Lambda
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = module.email_receiver_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.email_bucket.arn
}

# Configure S3 to notify Lambda when files are uploaded
resource "aws_s3_bucket_notification" "email_notification" {
  bucket = aws_s3_bucket.email_bucket.id
  
  lambda_function {
    lambda_function_arn = module.email_receiver_lambda.function_arn
    events              = ["s3:ObjectCreated:*"]
    
    # Filter for specific file types
    filter_suffix = ".pdf"  # Process PDF files
  }
  
  # Wait for Lambda permission to be created
  depends_on = [aws_lambda_permission.allow_s3]
}

# ===========================================
# IAM POLICY FOR S3 ACCESS
# ===========================================

# Additional policy for Lambda to access S3
resource "aws_iam_policy" "lambda_s3_access" {
  name        = "${var.project_name}-s3-access-${var.environment}"
  description = "Allows Lambda to read from S3 email bucket"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowS3ReadAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.email_bucket.arn,
          "${aws_s3_bucket.email_bucket.arn}/*"
        ]
      }
    ]
  })
  
  tags = local.common_tags
}

# Attach S3 policy to Lambda role
resource "aws_iam_role_policy_attachment" "lambda_s3_access" {
  role       = module.email_receiver_lambda.role_name
  policy_arn = aws_iam_policy.lambda_s3_access.arn
}

# ===========================================
# OUTPUTS
# ===========================================

output "account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "region" {
  description = "AWS Region"
  value       = data.aws_region.current.name
}

output "s3_bucket_name" {
  description = "S3 bucket name for emails"
  value       = aws_s3_bucket.email_bucket.id
  sensitive   = false
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.email_bucket.arn
}

output "lambda_function_name" {
  description = "Email receiver Lambda function name"
  value       = module.email_receiver_lambda.function_name
}

output "lambda_function_arn" {
  description = "Email receiver Lambda function ARN"
  value       = module.email_receiver_lambda.function_arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for Lambda"
  value       = module.email_receiver_lambda.cloudwatch_log_group_name
}

output "deployment_instructions" {
  description = "Instructions for testing the deployment"
  value = <<-EOT
  
  ✅ DEPLOYMENT SUCCESSFUL!
  
  Resources created:
  - S3 Bucket: ${aws_s3_bucket.email_bucket.id}
  - Lambda Function: ${module.email_receiver_lambda.function_name}
  
  To test:
  1. Upload a PDF file to the S3 bucket:
     aws s3 cp test.pdf s3://${aws_s3_bucket.email_bucket.id}/incoming/
     
  2. Check Lambda execution:
     - Go to AWS Console → Lambda → ${module.email_receiver_lambda.function_name}
     - Click "Monitor" tab to see invocations
     
  3. View logs:
     - Go to AWS Console → CloudWatch → Log Groups
     - Find: ${module.email_receiver_lambda.cloudwatch_log_group_name}
  
  To destroy (be careful!):
  terraform destroy -var-file="terraform.tfvars"
  
  EOT
}

# ===========================================
# WARNINGS AND VALIDATIONS
# ===========================================

resource "null_resource" "validate_source_files" {
  triggers = {
    always_run = timestamp()
  }
  
  provisioner "local-exec" {
    command = <<-EOT
      echo "========================================"
      echo "Validating source files..."
      echo "========================================"
      
      if [ ! -f "${local.email_receiver_source}" ]; then
        echo "❌ ERROR: Lambda source file not found!"
        echo "File: ${local.email_receiver_source}"
        echo ""
        echo "Please run: ./scripts/build.sh"
        echo "from the project root directory"
        exit 1
      else
        echo "✅ Source file exists: ${local.email_receiver_source}"
        echo "✅ File size: $(du -h "${local.email_receiver_source}" | cut -f1)"
      fi
      
      echo "========================================"
    EOT
  }
}