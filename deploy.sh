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

# Stop any running containers
echo "🛑 Stopping any running containers..."
docker-compose down 2>/dev/null || true

# Pull latest changes from GitHub
echo "📥 Pulling latest changes from GitHub..."
git pull origin main

# Check if there are any changes
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Warning: You have uncommitted changes. Consider committing them first."
    echo "   Current changes:"
    git status --short
    echo ""
    read -p "Do you want to continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Deployment cancelled."
        exit 1
    fi
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

# Clean up old Docker images (optional)
echo "🧹 Cleaning up old Docker images..."
docker image prune -f 2>/dev/null || true

# Build the Docker image
echo "🔨 Building Docker image..."
docker-compose build --no-cache

# Start the application
echo "🚀 Starting application..."
docker-compose up -d

# Wait for application to start
echo "⏳ Waiting for application to start..."
sleep 10

# Check if application is running
echo "🔍 Checking application status..."
if curl -f http://localhost:8002/ &> /dev/null; then
    echo "✅ Application is running successfully!"
    echo "🌐 Access your application at: http://localhost:8002"
    echo ""
    echo "📊 Deployment Summary:"
    echo "  ✅ Stopped previous containers"
    echo "  ✅ Pulled latest changes from GitHub"
    echo "  ✅ Built new Docker image"
    echo "  ✅ Started application"
    echo "  ✅ Health check passed"
    echo ""
    echo "📊 Useful commands:"
    echo "  View logs: docker-compose logs -f"
    echo "  Stop app:  docker-compose down"
    echo "  Restart:   docker-compose restart"
    echo "  Update:    ./deploy.sh"
    echo "  Status:    docker-compose ps"
else
    echo "❌ Application failed to start. Check logs with: docker-compose logs"
    echo ""
    echo "🔧 Troubleshooting:"
    echo "  1. Check logs: docker-compose logs -f"
    echo "  2. Check status: docker-compose ps"
    echo "  3. Restart: docker-compose restart"
    echo "  4. Full rebuild: docker-compose down && docker-compose build --no-cache && docker-compose up -d"
    exit 1
fi
