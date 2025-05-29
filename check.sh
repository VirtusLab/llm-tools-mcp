#!/bin/bash 

set -uo pipefail  

# Parse command line arguments
ALSO_TEST=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --also-test)
            ALSO_TEST=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--also-test]"
            exit 1
            ;;
    esac
done

echo "--------------------------------"
echo "Running mypy..."
uv run mypy .
mypy_exit=$?

echo "--------------------------------"
echo "Running ruff check..."
uv run ruff check .
ruff_check_exit=$?

echo "--------------------------------"
echo "Running ruff format..."
uv run ruff format --check .
ruff_format_exit=$?

# Initialize exit code with current checks
exit_code=$((mypy_exit + ruff_check_exit + ruff_format_exit))

# Run tests if --also-test flag is provided
if [ "$ALSO_TEST" = true ]; then
    echo "--------------------------------"
    echo "Running tests..."
    uv run pytest
    test_exit=$?
    exit_code=$((exit_code + test_exit))
fi

# Exit with non-zero if any command failed
if [ $exit_code -ne 0 ]; then
    echo "One or more checks failed!"
else
    echo "All checks passed!"
fi

echo "Done!"

exit $exit_code
