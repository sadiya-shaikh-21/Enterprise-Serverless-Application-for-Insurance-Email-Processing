#!/bin/bash
echo "Building Lambda package (simple version)..."

# Create build directory
mkdir -p build

# Package the Lambda
cd src/email_receiver

# Just zip the Python files
zip -r ../../build/email_receiver.zip *.py

# Copy for Terraform
cp ../../build/email_receiver.zip lambda_package.zip

cd ../..

echo ""
echo "âœ… Build complete!"
echo "Files created:"
ls -lh build/email_receiver.zip
ls -lh src/email_receiver/lambda_package.zip
echo ""
echo "í³‹ Next: cd infrastructure/environments/dev"
echo "       terraform init"
