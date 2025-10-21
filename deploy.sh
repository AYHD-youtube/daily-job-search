#!/bin/bash

# Daily Job Search - Docker Deployment Script
# This script helps you deploy the application on your home server

set -e

echo "🚀 Daily Job Search - Docker Deployment"
echo "======================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating data directories..."
mkdir -p data/{uploads,user_credentials,databases,instance}

# Set proper permissions
echo "🔐 Setting directory permissions..."
chmod -R 755 data/

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from example..."
    cat > .env << EOF
# Flask Configuration
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
DATABASE_URL=sqlite:///instance/job_search.db

# Google OAuth (Optional - for user authentication)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8002/callback

# Production Settings
FLASK_ENV=production
FLASK_APP=app.py
EOF
    echo "✅ Created .env file with secure secret key"
    echo "📝 Please edit .env file to add your Google OAuth credentials"
fi

# Build the Docker image
echo "🔨 Building Docker image..."
docker-compose build

# Start the application
echo "🚀 Starting application..."
docker-compose up -d

# Wait for application to start
echo "⏳ Waiting for application to start..."
sleep 10

# Check if application is running
if curl -f http://localhost:8002/ &> /dev/null; then
    echo "✅ Application is running successfully!"
    echo "🌐 Access your application at: http://localhost:8002"
    echo ""
    echo "📊 Useful commands:"
    echo "  View logs: docker-compose logs -f"
    echo "  Stop app:  docker-compose down"
    echo "  Restart:   docker-compose restart"
    echo "  Update:    git pull && docker-compose build && docker-compose up -d"
else
    echo "❌ Application failed to start. Check logs with: docker-compose logs"
    exit 1
fi
