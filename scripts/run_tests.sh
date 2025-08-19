#!/bin/bash

# Exit on error
set -e

# Install test dependencies if not already installed
pip install -r requirements-test.txt

# Run tests with coverage
pytest \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=xml:coverage.xml \
    --cov-report=html:htmlcov \
    tests/

echo "\nCoverage report generated in htmlcov/index.html"

# If running in CI, upload coverage to codecov
if [ "$CI" = "true" ]; then
    bash <(curl -s https://codecov.io/bash)
fi
