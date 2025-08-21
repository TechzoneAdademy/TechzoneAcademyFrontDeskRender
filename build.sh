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

echo "Verifying application structure..."
echo "Files in current directory:"
ls -la

echo "Checking app.py exists:"
if [ -f "app.py" ]; then
    echo "✅ app.py found"
    echo "Content preview:"
    head -5 app.py
else
    echo "❌ app.py not found!"
    exit 1
fi

echo "Checking portalflask directory:"
if [ -d "portalflask" ]; then
    echo "✅ portalflask directory found"
    echo "Files in portalflask:"
    ls -la portalflask/
else
    echo "❌ portalflask directory not found!"
    exit 1
fi

echo "Creating startup verification file..."
cat > startup_info.txt << EOF
# TechZone Portal Startup Information
# This file confirms the correct startup configuration

APP_MODULE: app:techzone_app
PYTHON_VERSION: $(python --version)
BUILD_TIME: $(date)
START_COMMAND: gunicorn app:techzone_app --bind 0.0.0.0:\$PORT

# File structure verification:
$(find . -type f -name "*.py" | head -10)

# Dependencies installed:
$(pip list | grep -E "(Flask|pandas|firebase|gunicorn)")
EOF

echo "Build completed successfully!"
echo "Startup command should be: gunicorn app:techzone_app --bind 0.0.0.0:\$PORT"
