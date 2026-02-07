@echo off
echo Ì¥® Building Lambda packages for Terraform...
echo.

REM Check if in project root
if not exist "requirements.in" (
    echo ‚ùå Error: Not in project root directory!
    echo Please run from: Enterprise-Serverless-Application-for-Insurance-Email-Processing/
    exit /b 1
)

REM Check Python virtual environment
if not exist "venv\" (
    echo ‚ö†Ô∏è  Virtual environment not found.
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.in

REM Build directory
set BUILD_DIR=build
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"

echo.
echo Ì≥¶ Building email_receiver Lambda...

REM Go to source directory
cd src\email_receiver

REM Create requirements.txt if it doesn't exist
if not exist "requirements.txt" (
    echo Creating requirements.txt...
    echo boto3==1.34.0 > requirements.txt
    echo aws-lambda-powertools==2.40.0 >> requirements.txt
)

REM Install dependencies to the current directory
echo Installing Lambda dependencies...
pip install -r requirements.txt -t . --upgrade

REM Create zip file
echo Creating zip package...
powershell -Command "Compress-Archive -Path '*.py', '*.json', '__init__.py' -DestinationPath '..\..\%BUILD_DIR%\email_receiver.zip' -Force"

REM Go back to project root
cd ..\..

REM Copy to Terraform expected location
echo Preparing for Terraform...
if not exist "src\email_receiver" mkdir "src\email_receiver"
copy "%BUILD_DIR%\email_receiver.zip" "src\email_receiver\lambda_package.zip"

echo.
echo ‚úÖ Build complete!
echo Ì≥Å Files created:
echo    - %BUILD_DIR%\email_receiver.zip
echo    - src\email_receiver\lambda_package.zip (for Terraform)
echo.

REM Check if file was created
if exist "src\email_receiver\lambda_package.zip" (
    echo ‚úÖ Ready for Terraform deployment!
    echo Next: cd infrastructure\environments\dev
    echo Then: terraform init
) else (
    echo ‚ùå Build failed!
    exit /b 1
)
