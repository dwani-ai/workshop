#!/bin/bash

# List of project directories
projects=(
  "llm-indic-server"
  "indic-translate-server"
  "asr-indic-server"
  "tts-indic-server"
  "docs-indic-server"
  "dwani-server"
  "dwani-workshop"
)

PYTHON_VERSION=python3.10

for project in "${projects[@]}"; do
  echo "Setting up $project..."
  cd "$project" || { echo "Directory $project not found!"; exit 1; }

  # Create virtual environment if it doesn't exist
  if [ ! -d "venv" ]; then
    $PYTHON_VERSION -m venv venv
    echo "Virtual environment created for $project."
  else
    echo "Virtual environment already exists for $project."
  fi

  # Activate the virtual environment
  source venv/bin/activate

  # Install requirements
  if [ -f "requirements.txt" ]; then
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "Requirements installed for $project."
  else
    echo "requirements.txt not found in $project!"
  fi

  # Deactivate the virtual environment
  deactivate

  # Go back to the parent directory
  cd ..
  echo "Done with $project."
  echo "-----------------------------"
done

echo "All projects set up!"
