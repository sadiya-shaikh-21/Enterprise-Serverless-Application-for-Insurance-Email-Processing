# environments/dev/outputs.tf - Output values

output "aws_account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "AWS Region used"
  value       = var.aws_region
}

output "console_links" {
  description = "Useful AWS Console links"
  value = <<-EOT
  
  🔗 Useful Links:
  
  S3 Bucket:
  https://s3.console.aws.amazon.com/s3/buckets/${aws_s3_bucket.email_bucket.id}
  
  Lambda Function:
  https://eu-west-1.console.aws.amazon.com/lambda/home?region=eu-west-1#/functions/${aws_lambda_function.email_receiver.function_name}
  
  CloudWatch Logs:
  https://eu-west-1.console.aws.amazon.com/cloudwatch/home?region=eu-west-1#logsV2:log-groups/log-group/%252Faws%252Flambda%252F${aws_lambda_function.email_receiver.function_name}
  EOT
}

# Data source for account ID
data "aws_caller_identity" "current" {}
