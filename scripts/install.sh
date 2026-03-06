#!/bin/bash -e

# Script Description: Sets up a virtual environment and installs dependencies for the summarizer_service.

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Navigate to the script's directory.  This handles cases where the script is called from elsewhere.
cd "$SCRIPT_DIR" || { echo "Error: Could not change directory to script location." >&2; exit 1; }

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
  echo "Error: python3 is not installed. Please install it before running this script." >&2
  exit 1
fi

# Check if pip is installed
if ! command -v pip &> /dev/null; then
  echo "Error: pip is not installed. Please install it before running this script." >&2
  exit 1
fi


# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv || { echo "Error: Failed to create virtual environment." >&2; exit 1; }
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip || { echo "Error: Failed to upgrade pip." >&2; exit 1; }

# Install requirements
echo "Installing requirements..."
pip install -r summarizer_service/requirements.txt || { echo "Error: Failed to install requirements." >&2; exit 1; }

echo "Setup complete."
echo "To deactivate the environment, run: deactivate"
