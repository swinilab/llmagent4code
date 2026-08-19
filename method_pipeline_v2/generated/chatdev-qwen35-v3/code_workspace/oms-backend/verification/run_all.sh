#!/bin/bash
# Run all NFR verification scripts

set -e

echo "=========================================="
echo "OMS NFR Verification Suite"
echo "=========================================="

# Ensure results directory exists
mkdir -p verification/results

# Start the server in background if not running
echo "Checking server status..."
if ! curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "Starting OMS server..."
    uv run python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 &
    SERVER_PID=$!
    sleep 3
    
    # Wait for server to be ready
    for i in {1..30}; do
        if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
            echo "Server is ready"
            break
        fi
        sleep 1
    done
fi

echo ""
echo "Running NFR 1.1 - Limit Event Response..."
uv run python verification/verify_nfr_1_1.py
echo ""

echo "Running NFR 1.2 - Maintain Multiple copies of Data..."
uv run python verification/verify_nfr_1_2.py
echo ""

echo "Running NFR 2.1 - Exception detection (Timeout)..."
uv run python verification/verify_nfr_2_1.py
echo ""

echo "Running NFR 2.2 - Graceful Degradation..."
uv run python verification/verify_nfr_2_2.py
echo ""

echo "Running NFR 2.3 - State Resynchronization..."
uv run python verification/verify_nfr_2_3.py
echo ""

echo "Running NFR 2.4 - Transactions..."
uv run python verification/verify_nfr_2_4.py
echo ""

echo "=========================================="
echo "Verification Complete"
echo "=========================================="
echo ""
echo "Results saved to verification/results/"
echo ""

# Show summary
echo "Summary:"
for result_file in verification/results/*.json; do
    if [ -f "$result_file" ]; then
        nfr_name=$(basename "$result_file" .json)
        passed=$(python -c "import json; print(json.load(open('$result_file'))['passed'])")
        echo "  $nfr_name: $passed"
    fi
done
