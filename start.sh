#!/bin/bash

# Start the Daily Job Search Flask Application

echo "🚀 Starting Daily Job Search Application..."
echo "📍 Application will be available at: http://localhost:5001"
echo ""

# Activate virtual environment
source venv/bin/activate

# Start the Flask application
python app.py
