#!/bin/bash 

set -uo pipefail  

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

# Exit with non-zero if any command failed
exit_code=$((mypy_exit + ruff_check_exit + ruff_format_exit))

if [ $exit_code -ne 0 ]; then
    echo "One or more checks failed!"
else
    echo "All checks passed!"
fi

echo "Done!"

exit $exit_code
