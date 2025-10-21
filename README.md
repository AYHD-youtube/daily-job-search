# 🚀 Daily Job Search - Automated Job Search & Email Notifications

A powerful Flask web application that automatically searches for jobs on major job sites and sends daily email notifications with the latest job postings. Perfect for job seekers who want to stay updated without manually checking multiple job boards.

## ✨ Features

### 🔍 **Smart Job Search**
- **Multi-site Search**: Searches across 15+ major job sites (Greenhouse, Lever, Workday, etc.)
- **Custom Keywords**: Define your own search terms and combinations
- **Search Logic**: Choose between AND, OR, or custom search patterns
- **Location Filtering**: Target specific locations or remote positions
- **Job Age Filtering**: Only get jobs posted within your specified timeframe

### 📧 **Flexible Email Scheduling**
- **Multiple Frequencies**: Daily, hourly, 2-hourly, 3-hourly, weekdays, weekly, twice-weekly
- **Custom Schedules**: Define your own days and intervals
- **Smart Timing**: Set specific times for email delivery
- **Real-time Results**: Get jobs as soon as they're posted

### 👤 **Multi-User Support**
- **User Authentication**: Secure Google OAuth login
- **Individual Settings**: Each user has their own configurations
- **Personalized Searches**: Custom search settings per user
- **Data Isolation**: Complete privacy between users

### 🎯 **Advanced Features**
- **Google Custom Search API**: Real job search results (not just sample data)
- **Gmail OAuth Integration**: Secure email sending through Gmail API
- **Email Notifications**: Automatic job alerts sent to any email address
- **Test Email Functionality**: Verify email setup before scheduling searches
- **Job Tracking**: View all found jobs with filtering and export options
- **Test Search**: Preview results before setting up automated searches
- **Dashboard**: Beautiful, responsive web interface

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/daily-job-search.git
cd daily-job-search
```

### 2. Set Up Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the project root:
```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///job_search.db

# Google OAuth (Optional - for user authentication)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/callback
```

### 4. Run the Application
```bash
python app.py
```

Visit `http://localhost:5000` to access the application.

## 🔧 Configuration

### Google Custom Search API Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the "Custom Search API"
4. Create credentials (API Key)
5. Create a Custom Search Engine at [cse.google.com](https://cse.google.com/)
6. Add your API key and Search Engine ID in the Settings page

### Gmail OAuth Setup (Optional)
1. Follow the detailed [Gmail OAuth Setup Guide](GMAIL_OAUTH_SETUP.md)
2. Set up Google OAuth credentials in Google Cloud Console
3. Configure environment variables for OAuth
4. Authorize Gmail access through the web interface
5. Test email functionality with the built-in test feature

## 📱 Usage

### Creating Search Configurations
1. **Login** to the application
2. **Go to Dashboard** and click "New Search Configuration"
3. **Configure your search**:
   - Name your configuration
   - Add keywords (comma-separated)
   - Choose search logic (AND/OR/Custom)
   - Set location filter
   - Select job sites
   - Choose frequency and timing
4. **Test your search** to preview results
5. **Save** to activate automated searches

### Managing Searches
- **View all configurations** on the dashboard
- **Edit** existing configurations
- **Test** searches before saving
- **Delete** configurations you no longer need
- **View job results** on the Jobs page

## 🏗️ Project Structure

```
daily-job-search/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── dashboard.html
│   ├── settings.html
│   └── jobs.html
├── static/               # Static files
│   ├── css/
│   └── js/
├── instance/            # Database files
└── uploads/             # User uploads
```

## 🔧 Technical Details

### Built With
- **Flask** - Web framework
- **SQLAlchemy** - Database ORM
- **APScheduler** - Job scheduling
- **Google Custom Search API** - Job search
- **Gmail API** - Email sending
- **Bootstrap 5** - Frontend styling
- **JavaScript** - Frontend interactivity

### Database Schema
- **Users**: User accounts and authentication
- **SearchConfig**: Search configurations and settings
- **JobResult**: Found job postings and metadata

### Scheduling System
- **Cron-based**: For daily, weekly, and custom schedules
- **Interval-based**: For hourly frequencies
- **Smart rescheduling**: Automatic updates when configurations change

## 🚀 Deployment

### Production Setup
1. **Set environment variables**:
   ```bash
   export SECRET_KEY='your-production-secret-key'
   export FLASK_ENV='production'
   ```

2. **Use production server**:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

3. **Set up HTTPS** with Let's Encrypt or your preferred SSL provider

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/yourusername/daily-job-search/issues) page
2. Create a new issue with detailed information
3. Include error messages and steps to reproduce

## 🎯 Roadmap

- [ ] Email templates customization
- [ ] Advanced job filtering
- [ ] Job application tracking
- [ ] Mobile app
- [ ] Team/organization support
- [ ] Analytics and reporting

---

**Happy Job Hunting! 🎉**

*Built with ❤️ for job seekers everywhere*