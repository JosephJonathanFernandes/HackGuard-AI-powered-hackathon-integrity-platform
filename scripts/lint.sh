#!/bin/bash
set -e

echo "Running Black formatter..."
black src tests

echo "Running tests..."
export PYTHONPATH=src
pytest tests/

echo "All checks passed successfully!"
