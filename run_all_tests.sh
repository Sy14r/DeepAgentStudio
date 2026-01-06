#!/bin/bash
# Complete test runner for DeepAgentStudio

set -e

echo "=========================================="
echo "DeepAgentStudio - Complete Test Suite"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if services are running
echo "Checking Docker services..."
if ! sudo docker-compose ps | grep -q "Up"; then
    echo -e "${RED}Error: Docker services are not running${NC}"
    echo "Starting services..."
    sudo docker-compose up -d --build
    echo "Waiting for services to be healthy..."
    sleep 15
fi

echo -e "${GREEN}✓ Services are running${NC}"
echo ""

# Check backend health
echo "Checking backend health..."
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
else
    echo -e "${YELLOW}Warning: Backend health check failed, but continuing...${NC}"
fi
echo ""

# Run all tests
echo "=========================================="
echo "Running All Tests"
echo "=========================================="
echo ""

sudo docker-compose exec -T backend pytest -v --tb=short 2>&1 | tee test_results.log

# Check if tests passed
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo -e "${GREEN}✓ ALL TESTS PASSED!${NC}"
    echo "=========================================="

    # Run coverage report
    echo ""
    echo "Generating coverage report..."
    sudo docker-compose exec -T backend pytest --cov=app --cov-report=term-missing --cov-report=html 2>&1 | grep -A 20 "coverage"

    echo ""
    echo -e "${GREEN}Coverage report generated at: backend/htmlcov/index.html${NC}"

else
    echo ""
    echo "=========================================="
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo "=========================================="
    echo ""
    echo "Check test_results.log for details"
    exit 1
fi

echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo ""

# Extract test summary from log
grep "passed" test_results.log | tail -1

echo ""
echo -e "${GREEN}Phase 1 verification complete!${NC}"
