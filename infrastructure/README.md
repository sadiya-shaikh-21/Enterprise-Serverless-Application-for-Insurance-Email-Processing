# Infrastructure as Code with Terraform

This directory contains Terraform configurations for deploying the Insurance Email Processing system to AWS.

## 📁 Structure
infrastructure/
├── modules/ # Reusable components
│ └── lambda/ # Lambda function module
├── environments/ # Environment-specific configs
│ ├── dev/ # Development environment
│ ├── staging/ # Staging environment (empty)
│ └── prod/ # Production environment (empty)
└── versions.tf # Terraform version constraints


## 🚀 Quick Start

### Prerequisites
1. Install Terraform >= 1.5.0
2. Configure AWS credentials:
   ```bash
   aws configure
   # Or set environment variables:
   export AWS_ACCESS_KEY_ID="your_access_key"
   export AWS_SECRET_ACCESS_KEY="your_secret_key"
   export AWS_REGION="eu-west-1"

