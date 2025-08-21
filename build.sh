#!/bin/bash

# Build script for TechZone Portal on Render
# This script ensures Python 3.11 is used and dependencies are installed correctly

echo "=== TechZone Portal Build Script ==="
echo "Current Python version:"
python --version

echo "Current pip version:"
pip --version

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Build completed successfully!"
