#!/bin/bash
# Clean generated files before building a zip for QGIS plugin upload
# This script is not included in pb_tool.cfg and won't be packaged

set -e

echo "Cleaning __pycache__ directories..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

echo "Removing .buildinfo files (Sphinx metadata that triggers secret scanners)..."
find . -name ".buildinfo" -type f -delete 2>/dev/null || true

echo "Removing zip_build directory..."
rm -rf zip_build 2>/dev/null || true

echo "Done."
