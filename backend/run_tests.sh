#!/bin/bash
# Test runner script for DeepAgentStudio backend

set -e  # Exit on error

echo "================================"
echo "DeepAgentStudio Test Suite"
echo "================================"
echo ""

# Check if we're in the backend directory
if [ ! -f "pytest.ini" ]; then
    echo "Error: Must be run from backend directory"
    exit 1
fi

# Parse command line arguments
COVERAGE=false
VERBOSE=false
SPECIFIC_TEST=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage|-c)
            COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --test|-t)
            SPECIFIC_TEST="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: ./run_tests.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -c, --coverage     Generate coverage report"
            echo "  -v, --verbose      Verbose output"
            echo "  -t, --test FILE    Run specific test file"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./run_tests.sh                    # Run all tests"
            echo "  ./run_tests.sh --coverage         # Run with coverage"
            echo "  ./run_tests.sh -t test_auth.py    # Run specific test file"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="pytest"

if [ "$SPECIFIC_TEST" != "" ]; then
    PYTEST_CMD="$PYTEST_CMD tests/$SPECIFIC_TEST"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=app --cov-report=html --cov-report=term-missing"
    echo "Running tests with coverage..."
else
    echo "Running tests..."
fi

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -vv"
fi

echo "Command: $PYTEST_CMD"
echo ""

# Run tests
$PYTEST_CMD

# Print summary
echo ""
echo "================================"
if [ "$COVERAGE" = true ]; then
    echo "Coverage report generated in htmlcov/index.html"
    echo "================================"
fi

echo "Tests completed successfully!"
