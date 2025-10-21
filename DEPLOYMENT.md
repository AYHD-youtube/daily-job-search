# 🐳 Docker Deployment Guide

This guide will help you deploy the Daily Job Search application using Docker on your home server.

## 📋 Prerequisites

- Docker and Docker Compose installed on your server
- Port 8002 available on your server
- Basic knowledge of Docker and environment variables

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/AYHD-youtube/daily-job-search.git
cd daily-job-search
```

### 2. Create Environment File
Create a `.env` file in the project root:
```bash
# Flask Configuration
SECRET_KEY=your-secret-key-change-this-in-production
DATABASE_URL=sqlite:///instance/job_search.db

# Google OAuth (Optional - for user authentication)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://your-server-ip:8002/callback

# Production Settings
FLASK_ENV=production
FLASK_APP=app.py
```

### 3. Create Data Directories
```bash
mkdir -p data/uploads data/user_credentials data/databases data/instance
```

### 4. Build and Run
```bash
# Build the Docker image
docker-compose build

# Start the application
docker-compose up -d

# Check logs
docker-compose logs -f
```

### 5. Access the Application
Open your browser and go to: `http://your-server-ip:8002`

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `SECRET_KEY` | Flask secret key for sessions | Yes | - |
| `DATABASE_URL` | Database connection string | No | `sqlite:///instance/job_search.db` |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | No | - |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | No | - |
| `GOOGLE_REDIRECT_URI` | OAuth redirect URI | No | `http://localhost:8002/callback` |

### Port Configuration
- **Application Port**: 8002
- **Container Port**: 8002
- **Health Check**: `http://localhost:8002/`

## 📁 Data Persistence

The following directories are mounted for data persistence:

- `./data/uploads` → User uploaded files
- `./data/user_credentials` → OAuth credentials
- `./data/databases` → Database files
- `./data/instance` → Flask instance folder

## 🛠️ Management Commands

### Start the Application
```bash
docker-compose up -d
```

### Stop the Application
```bash
docker-compose down
```

### View Logs
```bash
docker-compose logs -f
```

### Restart the Application
```bash
docker-compose restart
```

### Update the Application
```bash
git pull
docker-compose build
docker-compose up -d
```

### Backup Data
```bash
# Create backup of all data
tar -czf backup-$(date +%Y%m%d).tar.gz data/

# Restore from backup
tar -xzf backup-20240101.tar.gz
```

## 🔒 Security Considerations

### 1. Change Default Secret Key
```bash
# Generate a secure secret key
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Use HTTPS in Production
- Set up a reverse proxy (nginx/traefik)
- Use Let's Encrypt for SSL certificates
- Update `GOOGLE_REDIRECT_URI` to use HTTPS

### 3. Firewall Configuration
```bash
# Allow only necessary ports
ufw allow 8002
ufw deny 22  # If you don't need SSH
```

## 📊 Monitoring

### Health Check
The application includes a health check endpoint:
```bash
curl http://your-server-ip:8002/
```

### Log Monitoring
```bash
# View real-time logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f web
```

### Resource Monitoring
```bash
# Check container stats
docker stats daily-job-search-app

# Check disk usage
docker system df
```

## 🔄 Updates and Maintenance

### Regular Updates
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose build
docker-compose up -d
```

### Database Migrations
The application handles database migrations automatically on startup.

### Backup Strategy
```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
tar -czf /backups/daily-job-search-$DATE.tar.gz data/
find /backups -name "daily-job-search-*.tar.gz" -mtime +7 -delete
```

## 🚨 Troubleshooting

### Common Issues

**1. Port Already in Use**
```bash
# Check what's using port 8002
sudo netstat -tulpn | grep :8002

# Kill the process or change port in docker-compose.yml
```

**2. Permission Issues**
```bash
# Fix directory permissions
sudo chown -R $USER:$USER data/
chmod -R 755 data/
```

**3. Database Issues**
```bash
# Check database files
ls -la data/instance/
ls -la data/databases/

# Reset database (WARNING: This will delete all data)
rm -rf data/instance/* data/databases/*
```

**4. Container Won't Start**
```bash
# Check logs for errors
docker-compose logs web

# Check if all required directories exist
mkdir -p data/{uploads,user_credentials,databases,instance}
```

### Log Analysis
```bash
# View application logs
docker-compose logs web | grep ERROR
docker-compose logs web | grep WARNING

# Monitor resource usage
docker stats daily-job-search-app
```

## 🌐 Reverse Proxy Setup (Optional)

### Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Traefik Configuration
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.daily-job-search.rule=Host(`your-domain.com`)"
  - "traefik.http.routers.daily-job-search.entrypoints=websecure"
  - "traefik.http.routers.daily-job-search.tls.certresolver=letsencrypt"
```

## 📈 Performance Optimization

### Resource Limits
```yaml
# Add to docker-compose.yml
services:
  web:
    # ... existing configuration ...
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

### Database Optimization
- Use PostgreSQL for production (modify DATABASE_URL)
- Enable connection pooling
- Regular database maintenance

## 🎯 Production Checklist

- [ ] Change default SECRET_KEY
- [ ] Set up HTTPS with reverse proxy
- [ ] Configure proper firewall rules
- [ ] Set up automated backups
- [ ] Configure log rotation
- [ ] Set up monitoring and alerting
- [ ] Test disaster recovery procedures
- [ ] Document access credentials
- [ ] Set up SSL certificates
- [ ] Configure Google OAuth properly

---

**Your Daily Job Search application is now ready for production deployment! 🚀**
