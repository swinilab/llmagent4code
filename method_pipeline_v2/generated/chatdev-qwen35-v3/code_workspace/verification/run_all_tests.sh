#!/bin/bash
# Run all NFR verification tests
# Usage: ./run_all_tests.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "Running NFR Verification Suite"
echo "=========================================="
echo ""

# Check if server is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "ERROR: Server is not running at http://localhost:8000"
    echo "Please start the server first:"
    echo "  uv run python -m oms_backend.main"
    exit 1
fi

echo "Server is running. Starting tests..."
echo ""

PASSED=0
FAILED=0

run_test() {
    local test_file=$1
    local test_name=$(basename "$test_file" .py)
    
    echo "Running $test_name..."
    if python "$test_file"; then
        PASSED=$((PASSED + 1))
    else
        FAILED=$((FAILED + 1))
    fi
    echo ""
}

# Run all NFR tests
run_test "test_nfr_1_1.py"
run_test "test_nfr_1_2.py"
run_test "test_nfr_2_1.py"
run_test "test_nfr_2_2.py"
run_test "test_nfr_2_3.py"
run_test "test_nfr_2_4.py"

echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""
echo "Results saved to: verification/results/"
echo ""

if [ $FAILED -gt 0 ]; then
    exit 1
fi
exit 0
