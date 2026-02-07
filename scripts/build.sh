#!/bin/bash
echo "🔨 Building Lambda packages for Terraform..."
echo "============================================"

# Check if in project root
if [ ! -f "requirements.in" ]; then
    echo "❌ Error: Not in project root directory!"
    echo "Please run from: Enterprise-Serverless-Application-for-Insurance-Email-Processing/"
    exit 1
fi

# Check Python virtual environment
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found."
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate  # Mac/Linux
# On Windows Git Bash: source venv/Scripts/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.in

# Build directory
BUILD_DIR="build"
mkdir -p $BUILD_DIR

echo -e "\n📦 Building email_receiver Lambda..."

cd src/email_receiver

# Create requirements.txt if missing
if [ ! -f "requirements.txt" ]; then
    echo "Creating requirements.txt..."
    echo "boto3==1.34.0" > requirements.txt
    echo "aws-lambda-powertools==2.40.0" >> requirements.txt
fi

# Install dependencies into current dir
pip install -r requirements.txt -t . --upgrade

# Create zip package
zip -r "../../$BUILD_DIR/email_receiver.zip" . \
    -x "*.pyc" \
    -x "__pycache__/*" \
    -x "tests/*" \
    -x "*.git*" \
    -x "*.md" \
    -x "requirements.txt" \
    -x ".DS_Store" \
    -x "test_*.py" \
    -x ".coverage" \
    -x ".pytest_cache/*"

cd ../..

# Copy to Terraform location
mkdir -p src/email_receiver
cp "$BUILD_DIR/email_receiver.zip" "src/email_receiver/lambda_package.zip"

echo -e "\n✅ Build complete!"
echo "📁 Files created:"
echo "   - $BUILD_DIR/email_receiver.zip"
echo "   - src/email_receiver/lambda_package.zip"
echo "📏 Package size: $(du -h $BUILD_DIR/email_receiver.zip | cut -f1)"