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