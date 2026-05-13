#!/usr/bin/env bash
# Execute every notebook in src/ with nbconvert and fail on the first error.
# Run from the repo root: bash scripts/validate_notebooks.sh
set -euo pipefail

cd "$(dirname "$0")/.."

export AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_DEFAULT_REGION="$AWS_REGION"

notebooks=(
    "src/lab1/01_mantle_fundamentals.ipynb"
    "src/lab2/01_streaming.ipynb"
    "src/lab2/02_tool_calling.ipynb"
    "src/lab2/03_caching_and_stateful.ipynb"
    "src/lab3/01_api_sdk_diff.ipynb"
    "src/lab3/02_auth_security_migration.ipynb"
    "src/lab3/03_tools_and_caching_migration.ipynb"
    "src/lab3/04_perf_eval.ipynb"
    "src/lab4/01_end_to_end_financial_analyzer.ipynb"
)

for nb in "${notebooks[@]}"; do
    echo ""
    echo "=== Executing $nb ==="
    jupyter nbconvert --to notebook --execute --inplace \
        --ExecutePreprocessor.timeout=300 "$nb"
done

echo ""
echo "All notebooks executed cleanly."
