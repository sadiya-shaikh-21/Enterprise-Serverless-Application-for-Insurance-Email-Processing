# Makefile - Cross-platform friendly (Windows adjusted)
# Type "make [command]" in terminal to run these tasks

.PHONY: help install test clean package

# Default target - shows available commands
help:
	@echo "Available commands:"
	@echo "  make install       - Install Python dependencies"
	@echo "  make test          - Run all tests"
	@echo "  make clean         - Clean up temporary files"
	@echo "  make package       - Package Lambda for local testing"

# Install all dependencies
install:
	python -m venv venv
	venv\Scripts\python -m pip install -r requirements.in

# Run tests
test:
	venv\Scripts\python -m pytest tests/ -v --cov=src --cov-report=html

# Clean up generated files
clean:
	@if exist venv rmdir /s /q venv
	@if exist .coverage del /f /q .coverage
	@if exist htmlcov rmdir /s /q htmlcov
	@if exist __pycache__ rmdir /s /q __pycache__
	@if exist *.zip del /f /q *.zip
	@for /d %%D in (*\__pycache__) do rmdir /s /q "%%D"

# Package Lambda for local testing
package:
	cd src\email_receiver && powershell -Command "Compress-Archive -Path * -DestinationPath lambda_package.zip -Force"

# Run Lambda locally
test-lambda:
	@echo Testing Lambda function locally...
	venv\Scripts\activate && python src\email_receiver\handler.py

# Package just the email_receiver Lambda
package-email-receiver:
	@echo Packaging email_receiver Lambda...
	cd src\email_receiver && powershell -Command "Compress-Archive -Path * -DestinationPath ../../email_receiver.zip -Force"
	@echo Package created: email_receiver.zip
	@powershell -Command "Get-Item email_receiver.zip | Select-Object Length | ForEach-Object { '{0:N2} KB' -f ($_.Length / 1KB) }"

# Testing commands
test-all: test-unit test-integration test-coverage

test-unit:
	@echo Running unit tests...
	venv\Scripts\activate && pytest tests\unit\ -v

test-integration:
	@echo Running integration tests...
	venv\Scripts\activate && pytest tests\integration\ -v

test-coverage:
	@echo Running tests with coverage...
	venv\Scripts\activate && pytest tests\ --cov=src --cov-report=html --cov-report=term

test-fast:
	@echo Running fast tests (no coverage)...
	venv\Scripts\activate && pytest tests\ -xvs

# Clean test artifacts
clean-test:
	@echo Cleaning test artifacts...
	powershell -Command "Remove-Item -Recurse -Force .pytest_cache, htmlcov, .coverage, test-reports -ErrorAction SilentlyContinue"
	powershell -Command "Get-ChildItem -Recurse -Include __pycache__, *.pyc | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"