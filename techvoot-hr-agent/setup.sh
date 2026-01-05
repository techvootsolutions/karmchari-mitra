#!/bin/bash
echo "Setting up Techvoot HR Agent..."

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p logs database/migrations templates static/{css,js,images}

# Copy environment file
cp .env.example .env

# Initialize database
python database.py --init

echo "Setup complete! Run: python app.py"