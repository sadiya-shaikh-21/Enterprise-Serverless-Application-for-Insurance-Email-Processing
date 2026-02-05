#!/bin/bash
# run_tests.sh - Run all tests with nice formatting

set -e  # Exit on error

echo "🧪 Starting Test Suite"
echo "======================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create reports directory
mkdir -p test-reports

echo -e "\n${BLUE}1. Running Unit Tests...${NC}"
pytest tests/unit/ -v --junitxml=test-reports/unit-tests.xml

echo -e "\n${BLUE}2. Running Integration Tests...${NC}"
pytest tests/integration/ -v --junitxml=test-reports/integration-tests.xml

echo -e "\n${BLUE}3. Generating Coverage Report...${NC}"
pytest tests/ --cov=src --cov-report=html --cov-report=xml --cov-report=term

echo -e "\n${BLUE}4. Test Summary${NC}"
echo "======================"

# Count test results
TOTAL_TESTS=$(pytest tests/ --co -q | wc -l)
echo "Total test functions: $TOTAL_TESTS"

# Show coverage percentage if available
if [ -f "coverage.xml" ]; then
    COVERAGE=$(grep -o 'line-rate="[0-9.]*"' coverage.xml | cut -d'"' -f2)
    COVERAGE_PCT=$(echo "$COVERAGE * 100" | bc | xargs printf "%.1f")
    echo -e "Code coverage: ${COVERAGE_PCT}%"
    
    if (( $(echo "$COVERAGE_PCT < 80" | bc -l) )); then
        echo -e "${YELLOW}⚠️  Warning: Coverage below 80%${NC}"
    else
        echo -e "${GREEN}✅ Good coverage!${NC}"
    fi
fi

echo -e "\n${GREEN}✅ All tests completed!${NC}"
echo -e "📊 Reports saved in: test-reports/"
echo -e "📁 Coverage report: htmlcov/index.html"

# Open coverage report in browser (Mac)
if [[ "$OSTYPE" == "darwin"* ]]; then
    open htmlcov/index.html 2>/dev/null || true
fi