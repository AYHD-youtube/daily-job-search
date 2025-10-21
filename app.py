#!/usr/bin/env python3
"""
Flask Web Application - Daily Job Search
A multi-user web interface for daily job searching and email notifications.
"""

import os
import json
import logging
import secrets
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import google.auth.transport.requests
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import threading
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///job_search.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'user_credentials'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'https://daily.ayhd.dev/gmail-callback')

# Scopes for Google APIs
SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/customsearch'
]

# Gmail OAuth scopes
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(128))
    google_id = db.Column(db.String(120), unique=True)
    google_credentials = db.Column(db.Text)  # JSON string of credentials
    gmail_credentials = db.Column(db.Text)  # JSON string of Gmail OAuth credentials
    user_oauth_credentials = db.Column(db.Text)  # User-uploaded OAuth credentials JSON
    notification_email = db.Column(db.String(120))  # Email address to send notifications to
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    search_configs = db.relationship('SearchConfig', backref='user', lazy=True, cascade='all, delete-orphan')
    job_results = db.relationship('JobResult', backref='user', lazy=True, cascade='all, delete-orphan')

class SearchConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    keywords = db.Column(db.Text, nullable=False)  # JSON string of keywords
    search_logic = db.Column(db.String(20), default='AND')  # AND, OR, CUSTOM
    custom_logic = db.Column(db.Text, default='')  # Custom search logic
    frequency = db.Column(db.String(20), default='daily')  # daily, hourly, 2hourly, 3hourly, weekdays, weekly, twice_weekly, custom
    custom_frequency = db.Column(db.Text, default='{}')  # JSON string for custom frequency settings
    location_filter = db.Column(db.String(200), default='remote OR "United States"')
    job_sites = db.Column(db.Text, default='[]')  # JSON string of job sites
    max_job_age = db.Column(db.Integer, default=24)  # Maximum job age in hours
    is_active = db.Column(db.Boolean, default=True)
    search_time = db.Column(db.String(10), default='09:00')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_run = db.Column(db.DateTime)

class JobResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    search_config_id = db.Column(db.Integer, db.ForeignKey('search_config.id'))
    title = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(1000), nullable=False)
    snippet = db.Column(db.Text)
    job_site = db.Column(db.String(100))
    keyword = db.Column(db.String(100))
    found_at = db.Column(db.DateTime, default=datetime.utcnow)

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Default job sites
DEFAULT_JOB_SITES = [
    "myworkdayjobs.com",
    "greenhouse.io", 
    "icims.com",
    "taleo.net",
    "lever.co",
    "smartrecruiters.com",
    "jobvite.com",
    "workforcenow.adp.com",
    "successfactors.com",
    "brassring.com",
    "jazzhr.com",
    "breezy.hr",
    "jobdiva.com",
    "bullhorn.com",
    "bamboohr.com"
]

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def get_google_flow():
    """Create Google OAuth flow"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return None
    
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI]
            }
        },
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI
    )
    return flow

def get_google_credentials(user):
    """Get Google credentials for user"""
    if not user.google_credentials:
        return None
    
    try:
        creds_data = json.loads(user.google_credentials)
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
        
        # Refresh if needed
        if creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
            # Save refreshed credentials
            user.google_credentials = creds.to_json()
            db.session.commit()
        
        return creds
    except Exception as e:
        logger.error(f"Error getting credentials for user {user.id}: {e}")
        return None

def get_gmail_flow(user=None):
    """Create Gmail OAuth flow using user's credentials"""
    if user and user.user_oauth_credentials:
        try:
            # Use user's uploaded OAuth credentials
            client_config = json.loads(user.user_oauth_credentials)
            # Use HTTPS redirect URI for production
            redirect_uri = 'https://daily.ayhd.dev/gmail-callback'
            flow = Flow.from_client_config(
                client_config,
                scopes=GMAIL_SCOPES,
                redirect_uri=redirect_uri
            )
            return flow
        except Exception as e:
            logger.error(f"Error creating flow from user credentials: {e}")
            return None
    
    # Fallback to global OAuth credentials if available
    if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
        # Use HTTPS redirect URI for production
        redirect_uri = 'https://daily.ayhd.dev/gmail-callback'
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=GMAIL_SCOPES,
            redirect_uri=redirect_uri
        )
        return flow
    
    return None

def get_gmail_credentials(user):
    """Get Gmail credentials for user"""
    if not user.gmail_credentials:
        return None
    
    try:
        creds_data = json.loads(user.gmail_credentials)
        creds = Credentials.from_authorized_user_info(creds_data, GMAIL_SCOPES)
        
        # Refresh if needed
        if creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
            # Save refreshed credentials
            user.gmail_credentials = creds.to_json()
            db.session.commit()
        
        return creds
    except Exception as e:
        logger.error(f"Error getting Gmail credentials for user {user.id}: {e}")
        return None

def search_jobs_google_api(user, search_config):
    """Search for jobs using Google Custom Search API"""
    try:
        # Get API credentials from user settings
        if not user.google_credentials:
            logger.info(f"No Google credentials for user {user.id}, returning sample data")
            return get_sample_jobs(search_config)
        
        creds_data = json.loads(user.google_credentials)
        api_key = creds_data.get('custom_search_api_key')
        search_engine_id = creds_data.get('search_engine_id')
        
        if not api_key or not search_engine_id:
            logger.info(f"Missing API key or search engine ID for user {user.id}, returning sample data")
            return get_sample_jobs(search_config)
        
        # Build search query
        keywords = json.loads(search_config.keywords)
        job_sites = json.loads(search_config.job_sites) if search_config.job_sites else DEFAULT_JOB_SITES
        
        sites_query = " OR ".join([f"site:{site}" for site in job_sites])
        
        # Build keyword query based on search logic
        search_logic = getattr(search_config, 'search_logic', 'AND')
        if search_logic == 'CUSTOM':
            custom_logic = getattr(search_config, 'custom_logic', '')
            keyword_query = custom_logic if custom_logic else ' OR '.join(keywords)
        elif search_logic == 'OR':
            keyword_query = ' OR '.join(keywords)
        else:  # AND or default
            keyword_query = '"' + ' '.join(keywords) + '"'
        
        query = f'({sites_query}) ({keyword_query}) ("{search_config.location_filter}")'
        
        logger.info(f"Search query: {query}")
        logger.info(f"Search logic: {search_logic}, Keywords: {keywords}, Keyword query: {keyword_query}")
        
        # Use Google Custom Search API with API key
        service = build("customsearch", "v1", developerKey=api_key)
        
        # Determine date restriction based on max_job_age
        max_job_age = getattr(search_config, 'max_job_age', 24)
        date_restrict = None
        
        if max_job_age > 0:
            if max_job_age <= 1:
                date_restrict = 'h'  # Last hour
            elif max_job_age <= 24:
                date_restrict = 'd'  # Last day
            elif max_job_age <= 168:  # 7 days
                date_restrict = 'w'  # Last week
            elif max_job_age <= 720:  # 30 days
                date_restrict = 'm'  # Last month
            # For longer periods, don't use date restriction
        
        # Build search parameters
        search_params = {
            'q': query,
            'cx': search_engine_id,
            'num': 10
        }
        
        if date_restrict:
            search_params['dateRestrict'] = date_restrict
        
        results = service.cse().list(**search_params).execute()
        
        jobs = []
        for item in results.get('items', []):
            jobs.append({
                'title': item.get('title', ''),
                'link': item.get('link', ''),
                'snippet': item.get('snippet', ''),
                'job_site': extract_job_site(item.get('link', '')),
                'keyword': keywords[0] if keywords else '',
                'found_at': datetime.now()
            })
        
        return jobs
        
    except Exception as e:
        logger.error(f"Error searching jobs for user {user.id}: {e}")
        # Return sample data for demonstration
        return get_sample_jobs(search_config)

def get_sample_jobs(search_config):
    """Return sample job data for demonstration"""
    logger.info(f"Generating sample jobs for search config: {search_config.keywords}")
    keywords = json.loads(search_config.keywords)
    search_logic = getattr(search_config, 'search_logic', 'AND')
    max_job_age = getattr(search_config, 'max_job_age', 24)
    if max_job_age is None:
        max_job_age = 24  # Default to 24 hours if None
    
    # For sample data, we'll create jobs that match the search logic
    if search_logic == 'OR':
        # For OR logic, create jobs with different keywords
        sample_keywords = keywords if keywords else ["Business"]
    else:
        # For AND logic, use the first keyword (or all keywords combined)
        sample_keywords = [keywords[0]] if keywords else ["Business"]
    
    logger.info(f"Using keywords: {sample_keywords}, search logic: {search_logic}, max job age: {max_job_age} hours")
    
    # Create more realistic and varied sample data
    import random
    from datetime import timedelta
    
    # Generate job templates based on search logic
    job_templates = []
    
    if search_logic == 'OR':
        # For OR logic, create jobs with different keywords
        for i, keyword in enumerate(sample_keywords):
            job_templates.extend([
                {
                    'title_template': f'Senior {keyword} Manager',
                    'company': f'TechCorp {i+1} Inc.',
                    'job_site': 'greenhouse.io',
                    'snippet_template': f'We are looking for a Senior {keyword} Manager to join our remote team. Experience with {keyword} required.'
                },
                {
                    'title_template': f'{keyword} Developer',
                    'company': f'CodeCraft {i+1} Solutions',
                    'job_site': 'smartrecruiters.com',
                    'snippet_template': f'We need a {keyword} Developer to join our growing team. Remote-first company with great benefits.'
                },
                {
                    'title_template': f'{keyword} Engineer',
                    'company': f'BuildTech {i+1}',
                    'job_site': 'jobvite.com',
                    'snippet_template': f'Looking for a {keyword} Engineer with strong technical skills. Remote work available.'
                },
                {
                    'title_template': f'{keyword} Analyst',
                    'company': f'DataFlow {i+1} Systems',
                    'job_site': 'lever.co',
                    'snippet_template': f'Join our team as a {keyword} Analyst. Remote work available. Strong analytical skills required.'
                }
            ])
    else:
        # For AND logic, use the first keyword
        keyword = sample_keywords[0]
        job_templates = [
            {
                'title_template': f'Senior {keyword} Manager',
                'company': 'TechCorp Inc.',
                'job_site': 'greenhouse.io',
                'snippet_template': f'We are looking for a Senior {keyword} Manager to join our remote team. Experience with {keyword} required.'
            },
            {
                'title_template': f'{keyword} Analyst',
                'company': 'DataFlow Systems',
                'job_site': 'lever.co',
                'snippet_template': f'Join our team as a {keyword} Analyst. Remote work available. Strong analytical skills required.'
            },
            {
                'title_template': f'Lead {keyword} Specialist',
                'company': 'InnovateLabs',
                'job_site': 'workday.com',
                'snippet_template': f'Lead {keyword} Specialist position. Remote work. 5+ years experience in {keyword} field.'
            },
            {
                'title_template': f'{keyword} Developer',
                'company': 'CodeCraft Solutions',
                'job_site': 'smartrecruiters.com',
                'snippet_template': f'We need a {keyword} Developer to join our growing team. Remote-first company with great benefits.'
            },
            {
                'title_template': f'{keyword} Consultant',
                'company': 'Strategic Partners',
                'job_site': 'icims.com',
                'snippet_template': f'Independent {keyword} Consultant needed for exciting projects. Flexible schedule and remote work.'
            },
            {
                'title_template': f'{keyword} Engineer',
                'company': 'BuildTech',
                'job_site': 'jobvite.com',
                'snippet_template': f'Looking for a {keyword} Engineer with strong technical skills. Remote work available.'
            },
            {
                'title_template': f'{keyword} Coordinator',
                'company': 'ProjectFlow',
                'job_site': 'bamboohr.com',
                'snippet_template': f'{keyword} Coordinator position available. Great opportunity for career growth in {keyword} field.'
            }
        ]
    
    # Vary the number of results based on search logic and keyword popularity
    if search_logic == 'OR':
        # For OR logic, return more results since we're matching any keyword
        num_results = min(len(job_templates), 8)  # More results for OR logic
    else:
        # For AND logic, use keyword popularity
        keyword_variations = {
            'python': 6, 'developer': 5, 'engineer': 5, 'analyst': 4, 'manager': 4,
            'business': 3, 'data': 4, 'software': 5, 'web': 4, 'full': 3
        }
        
        # Determine number of results based on keyword
        num_results = 3  # default
        keyword = sample_keywords[0].lower()
        for key, count in keyword_variations.items():
            if key.lower() in keyword:
                num_results = count
                break
    
    # Randomly select jobs from templates
    selected_jobs = random.sample(job_templates, min(num_results, len(job_templates)))
    
    sample_jobs = []
    for i, template in enumerate(selected_jobs):
        # Add some variation to titles
        title_variations = ['', ' - Remote', ' - Full Time', ' - Contract', ' - Part Time']
        title_suffix = random.choice(title_variations)
        
        # Generate job age within the specified limit
        if max_job_age > 0:
            # Random age within the max_job_age limit (in hours)
            job_age_hours = random.uniform(0, max_job_age)
            job_found_at = datetime.now() - timedelta(hours=job_age_hours)
        else:
            # No age limit - random age up to 7 days
            job_age_hours = random.uniform(0, 168)  # 7 days
            job_found_at = datetime.now() - timedelta(hours=job_age_hours)
        
        sample_jobs.append({
            'title': f"{template['title_template']}{title_suffix}",
            'link': f'https://example.com/job{i+1}',
            'snippet': template['snippet_template'],
            'job_site': template['job_site'],
            'keyword': keyword,
            'found_at': job_found_at
        })
    
    logger.info(f"Generated {len(sample_jobs)} sample jobs for keyword: {keyword} (max age: {max_job_age}h)")
    return sample_jobs

def extract_job_site(url):
    """Extract job site from URL"""
    for site in DEFAULT_JOB_SITES:
        if site in url:
            return site
    return "Unknown"

def send_email_gmail_api(user, subject, content):
    """Send email using Gmail API"""
    try:
        # Get Gmail credentials
        creds = get_gmail_credentials(user)
        if not creds:
            logger.error(f"No Gmail credentials for user {user.id}")
            return False
        
        # Get notification email (use user's email if not set)
        recipient_email = user.notification_email or user.email
        
        # Build Gmail service
        service = build('gmail', 'v1', credentials=creds)
        
        # Create message
        message = create_message(user.email, recipient_email, subject, content)
        
        # Send message
        result = service.users().messages().send(
            userId='me',
            body={'raw': message}
        ).execute()
        
        logger.info(f"Email sent successfully to {recipient_email}: {result.get('id')}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email for user {user.id}: {e}")
        return False

def create_message(sender, to, subject, content):
    """Create email message for Gmail API"""
    import base64
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    msg = MIMEMultipart('alternative')
    msg['From'] = sender
    msg['To'] = to
    msg['Subject'] = subject
    
    html_content = MIMEText(content, 'html')
    msg.attach(html_content)
    
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()

def format_email_content(jobs, config_name):
    """Format job search results into HTML email"""
    if not jobs:
        return "No new jobs found today."
    
    # Group jobs by keyword
    jobs_by_keyword = {}
    for job in jobs:
        keyword = job['keyword']
        if keyword not in jobs_by_keyword:
            jobs_by_keyword[keyword] = []
        jobs_by_keyword[keyword].append(job)
    
    # Build email content
    email_content = f"""
    <h2>Daily Job Search Results - {config_name}</h2>
    <p>Found {len(jobs)} new job postings today!</p>
    """
    
    for keyword, keyword_jobs in jobs_by_keyword.items():
        email_content += f"""
        <h3>Keyword: {keyword} ({len(keyword_jobs)} jobs)</h3>
        <ul>
        """
        
        for job in keyword_jobs:
            email_content += f"""
            <li>
                <strong><a href="{job['link']}" target="_blank">{job['title']}</a></strong><br>
                <em>Site: {job['job_site']}</em><br>
                <small>{job['snippet'][:200]}{'...' if len(job['snippet']) > 200 else ''}</small>
            </li>
            <br>
            """
        
        email_content += "</ul>"
    
    email_content += """
    <hr>
    <p><small>This email was generated automatically by the Daily Job Search Bot.</small></p>
    """
    
    return email_content

def schedule_search_job(config):
    """Schedule a search job based on frequency settings"""
    hour, minute = map(int, config.search_time.split(':'))
    frequency = getattr(config, 'frequency', 'daily')
    
    if frequency == 'daily':
        # Every day at the specified time
        scheduler.add_job(
            run_user_search,
            'cron',
            hour=hour,
            minute=minute,
            args=[config.user_id, config.id],
            id=f"search_{config.id}",
            replace_existing=True
        )
    elif frequency == 'hourly':
        # Every hour at the specified minute
        scheduler.add_job(
            run_user_search,
            'cron',
            minute=minute,
            args=[config.user_id, config.id],
            id=f"search_{config.id}",
            replace_existing=True
        )
    elif frequency == '2hourly':
        # Every 2 hours starting from the specified time
        from datetime import datetime, timedelta
        now = datetime.now()
        start_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if start_time <= now:
            start_time += timedelta(hours=2)
        
        scheduler.add_job(
            run_user_search,
            'interval',
            hours=2,
            start_date=start_time,
            args=[config.user_id, config.id],
            id=f"search_{config.id}",
            replace_existing=True
        )
    elif frequency == '3hourly':
        # Every 3 hours starting from the specified time
        from datetime import datetime, timedelta
        now = datetime.now()
        start_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if start_time <= now:
            start_time += timedelta(hours=3)
        
        scheduler.add_job(
            run_user_search,
            'interval',
            hours=3,
            start_date=start_time,
            args=[config.user_id, config.id],
            id=f"search_{config.id}",
            replace_existing=True
        )
    elif frequency == 'weekdays':
        # Monday to Friday
        scheduler.add_job(
            run_user_search,
            'cron',
            day_of_week='mon-fri',
            hour=hour,
            minute=minute,
            args=[config.user_id, config.id],
            id=f"search_{config.id}",
            replace_existing=True
        )
    elif frequency == 'weekly':
        # Once per week (Monday)
        scheduler.add_job(
            run_user_search,
            'cron',
            day_of_week='mon',
            hour=hour,
            minute=minute,
            args=[config.user_id, config.id],
            id=f"search_{config.id}",
            replace_existing=True
        )
    elif frequency == 'twice_weekly':
        # Monday and Thursday
        scheduler.add_job(
            run_user_search,
            'cron',
            day_of_week='mon,thu',
            hour=hour,
            minute=minute,
            args=[config.user_id, config.id],
            id=f"search_{config.id}",
            replace_existing=True
        )
    elif frequency == 'custom':
        # Custom frequency
        custom_frequency = json.loads(getattr(config, 'custom_frequency', '{}'))
        if custom_frequency and 'days' in custom_frequency:
            days = custom_frequency['days']
            interval = custom_frequency.get('interval', 1)
            
            # Convert day names to APScheduler format
            day_mapping = {
                'monday': 'mon', 'tuesday': 'tue', 'wednesday': 'wed',
                'thursday': 'thu', 'friday': 'fri', 'saturday': 'sat', 'sunday': 'sun'
            }
            day_of_week = ','.join([day_mapping.get(day, day) for day in days])
            
            scheduler.add_job(
                run_user_search,
                'cron',
                day_of_week=day_of_week,
                hour=hour,
                minute=minute,
                args=[config.user_id, config.id],
                id=f"search_{config.id}",
                replace_existing=True
            )
        else:
            # Fallback to daily if custom frequency is invalid
            scheduler.add_job(
                run_user_search,
                'cron',
                hour=hour,
                minute=minute,
                args=[config.user_id, config.id],
                id=f"search_{config.id}",
                replace_existing=True
            )

def run_user_search(user_id, search_config_id):
    """Run job search for a specific user and config"""
    with app.app_context():
        user = db.session.get(User, user_id)
        search_config = db.session.get(SearchConfig, search_config_id)
        
        if not user or not search_config or not search_config.is_active:
            return
        
        # Search for jobs
        jobs = search_jobs_google_api(user, search_config)
        
        if jobs:
            # Save job results
            for job_data in jobs:
                job_result = JobResult(
                    user_id=user.id,
                    search_config_id=search_config.id,
                    title=job_data['title'],
                    link=job_data['link'],
                    snippet=job_data['snippet'],
                    job_site=job_data['job_site'],
                    keyword=job_data['keyword'],
                    found_at=job_data['found_at']
                )
                db.session.add(job_result)
            
            # Update last run time
            search_config.last_run = datetime.utcnow()
            db.session.commit()
            
            # Send email notification
            if user.google_credentials:
                subject = f"Daily Job Search Results - {len(jobs)} new jobs found"
                content = format_email_content(jobs, search_config.name)
                send_email_gmail_api(user, subject, content)

def schedule_user_searches():
    """Schedule all active user searches"""
    active_configs = SearchConfig.query.filter_by(is_active=True).all()
    
    for config in active_configs:
        # Schedule job based on frequency
        schedule_search_job(config)

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        password = request.form['password']
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        # Create new user
        user = User(
            email=email,
            name=name,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        flash('Registration successful!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/google-login')
def google_login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    flow = get_google_flow()
    if not flow:
        flash('Google OAuth not configured', 'error')
        return redirect(url_for('login'))
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    
    session['state'] = state
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    flow = get_google_flow()
    if not flow:
        flash('Google OAuth not configured', 'error')
        return redirect(url_for('login'))
    
    flow.fetch_token(authorization_response=request.url)
    
    if not session.get('state') == request.args.get('state'):
        flash('Invalid state parameter', 'error')
        return redirect(url_for('index'))
    
    credentials = flow.credentials
    user_info_service = build('oauth2', 'v2', credentials=credentials)
    user_info = user_info_service.userinfo().get().execute()
    
    # Check if user exists
    user = User.query.filter_by(google_id=user_info['id']).first()
    
    if not user:
        # Create new user
        user = User(
            google_id=user_info['id'],
            email=user_info['email'],
            name=user_info['name'],
            google_credentials=credentials.to_json()
        )
        db.session.add(user)
        db.session.commit()
    else:
        # Update existing user
        user.google_credentials = credentials.to_json()
        user.last_login = datetime.utcnow()
        db.session.commit()
    
    login_user(user)
    flash('Login successful!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/gmail-auth')
@login_required
def gmail_auth():
    """Start Gmail OAuth flow"""
    flow = get_gmail_flow(current_user)
    if not flow:
        flash('Gmail OAuth not configured. Please upload your credentials.json file first.', 'error')
        return redirect(url_for('settings'))
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    
    session['gmail_state'] = state
    return redirect(authorization_url)

@app.route('/gmail-callback')
@login_required
def gmail_callback():
    """Handle Gmail OAuth callback"""
    flow = get_gmail_flow(current_user)
    if not flow:
        flash('Gmail OAuth not configured. Please upload your credentials.json file first.', 'error')
        return redirect(url_for('settings'))
    
    try:
        flow.fetch_token(authorization_response=request.url)
        
        if not session.get('gmail_state') == request.args.get('state'):
            flash('Invalid state parameter', 'error')
            return redirect(url_for('settings'))
        
        credentials = flow.credentials
        
        # Save Gmail credentials
        current_user.gmail_credentials = credentials.to_json()
        db.session.commit()
        
        flash('Gmail authorization successful! You can now send email notifications.', 'success')
        return redirect(url_for('settings'))
        
    except Exception as e:
        logger.error(f"Gmail OAuth error: {e}")
        flash('Gmail authorization failed. Please try again.', 'error')
        return redirect(url_for('settings'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get user statistics
    total_jobs = JobResult.query.filter_by(user_id=current_user.id).count()
    active_configs = SearchConfig.query.filter_by(user_id=current_user.id, is_active=True).count()
    recent_jobs = JobResult.query.filter_by(user_id=current_user.id)\
        .order_by(JobResult.found_at.desc()).limit(10).all()
    
    return render_template('dashboard.html', 
                         total_jobs=total_jobs,
                         active_configs=active_configs,
                         recent_jobs=recent_jobs)

@app.route('/settings')
@login_required
def settings():
    # Get current API keys from user's google_credentials
    api_keys = {}
    if current_user.google_credentials:
        try:
            creds_data = json.loads(current_user.google_credentials)
            api_keys = {
                'custom_search_api_key': creds_data.get('custom_search_api_key', ''),
                'search_engine_id': creds_data.get('search_engine_id', '')
            }
        except:
            api_keys = {'custom_search_api_key': '', 'search_engine_id': ''}
    else:
        api_keys = {'custom_search_api_key': '', 'search_engine_id': ''}
    
    # Get Gmail status
    gmail_configured = bool(current_user.gmail_credentials)
    oauth_credentials_uploaded = bool(current_user.user_oauth_credentials)
    notification_email = current_user.notification_email or current_user.email
    
    return render_template('settings.html', 
                         api_keys=api_keys,
                         gmail_configured=gmail_configured,
                         oauth_credentials_uploaded=oauth_credentials_uploaded,
                         notification_email=notification_email)

@app.route('/jobs')
@login_required
def jobs():
    """Show all job results organized by search configuration"""
    # Get all search configurations for the user
    search_configs = SearchConfig.query.filter_by(user_id=current_user.id).all()
    
    # Get all job results for the user
    job_results = JobResult.query.filter_by(user_id=current_user.id)\
        .order_by(JobResult.found_at.desc()).all()
    
    # Group jobs by keyword for better organization
    jobs_by_keyword = {}
    for job in job_results:
        keyword = job.keyword
        if keyword not in jobs_by_keyword:
            jobs_by_keyword[keyword] = []
        jobs_by_keyword[keyword].append(job)
    
    return render_template('jobs.html', 
                         search_configs=search_configs,
                         job_results=job_results,
                         jobs_by_keyword=jobs_by_keyword)

@app.route('/api/save-api-keys', methods=['POST'])
@login_required
def save_api_keys():
    data = request.get_json()
    
    # Store API keys in user's google_credentials field for now
    # In production, you'd want a separate settings table
    current_user.google_credentials = json.dumps({
        'custom_search_api_key': data.get('custom_search_api_key', ''),
        'search_engine_id': data.get('search_engine_id', ''),
        'gmail_configured': True
    })
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'API keys saved successfully'})

@app.route('/api/save-email-settings', methods=['POST'])
@login_required
def save_email_settings():
    data = request.get_json()
    
    # Save notification email
    current_user.notification_email = data.get('notification_email', '')
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Email settings saved successfully'})

@app.route('/api/upload-credentials', methods=['POST'])
@login_required
def upload_credentials():
    """Upload user's OAuth credentials file"""
    if 'credentials' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400
    
    file = request.files['credentials']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    if file and file.filename.endswith('.json'):
        try:
            # Read and validate the JSON file
            content = file.read().decode('utf-8')
            credentials_data = json.loads(content)
            
            # Validate that it's a proper OAuth credentials file
            if 'web' not in credentials_data and 'installed' not in credentials_data:
                return jsonify({'success': False, 'message': 'Invalid credentials file format'}), 400
            
            # Save to user's record
            current_user.user_oauth_credentials = content
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Credentials uploaded successfully'})
            
        except json.JSONDecodeError:
            return jsonify({'success': False, 'message': 'Invalid JSON file'}), 400
        except Exception as e:
            logger.error(f"Error uploading credentials: {e}")
            return jsonify({'success': False, 'message': 'Error processing file'}), 500
    
    return jsonify({'success': False, 'message': 'Please upload a .json file'}), 400

@app.route('/api/delete-credentials', methods=['POST'])
@login_required
def delete_credentials():
    """Delete user's OAuth credentials"""
    try:
        # Clear user's OAuth credentials
        current_user.user_oauth_credentials = None
        current_user.gmail_credentials = None  # Also clear Gmail auth tokens
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Credentials deleted successfully'})
        
    except Exception as e:
        logger.error(f"Error deleting credentials: {e}")
        return jsonify({'success': False, 'message': 'Error deleting credentials'}), 500

@app.route('/api/gmail-status')
@login_required
def gmail_status():
    """Check Gmail OAuth status"""
    has_gmail_creds = bool(current_user.gmail_credentials)
    notification_email = current_user.notification_email or current_user.email
    
    return jsonify({
        'gmail_configured': has_gmail_creds,
        'notification_email': notification_email
    })

@app.route('/api/test-email', methods=['POST'])
@login_required
def test_email():
    """Send a test email to verify Gmail configuration"""
    try:
        # Get Gmail credentials
        creds = get_gmail_credentials(current_user)
        if not creds:
            return jsonify({'success': False, 'message': 'Gmail not configured. Please authorize Gmail first.'}), 400
        
        # Get notification email
        recipient_email = current_user.notification_email or current_user.email
        
        # Create test email content
        subject = "Daily Job Search - Test Email"
        content = f"""
        <h2>Test Email from Daily Job Search</h2>
        <p>This is a test email to verify that your Gmail OAuth configuration is working correctly.</p>
        <p><strong>Recipient:</strong> {recipient_email}</p>
        <p><strong>Sent at:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <hr>
        <p><small>If you received this email, your Gmail OAuth setup is working correctly!</small></p>
        """
        
        # Send test email
        success = send_email_gmail_api(current_user, subject, content)
        
        if success:
            return jsonify({'success': True, 'message': f'Test email sent successfully to {recipient_email}'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send test email'}), 500
            
    except Exception as e:
        logger.error(f"Test email error: {e}")
        return jsonify({'success': False, 'message': f'Error sending test email: {str(e)}'}), 500

@app.route('/api/search-configs', methods=['GET', 'POST'])
@login_required
def search_configs():
    if request.method == 'GET':
        configs = SearchConfig.query.filter_by(user_id=current_user.id).all()
        return jsonify([{
            'id': config.id,
            'name': config.name,
            'keywords': json.loads(config.keywords),
            'search_logic': getattr(config, 'search_logic', 'AND'),
            'custom_logic': getattr(config, 'custom_logic', ''),
            'frequency': getattr(config, 'frequency', 'daily'),
            'custom_frequency': json.loads(getattr(config, 'custom_frequency', '{}')),
            'location_filter': config.location_filter,
            'job_sites': json.loads(config.job_sites) if config.job_sites else DEFAULT_JOB_SITES,
            'max_job_age': config.max_job_age,
            'is_active': config.is_active,
            'search_time': config.search_time,
            'last_run': config.last_run.isoformat() if config.last_run else None
        } for config in configs])
    
    elif request.method == 'POST':
        data = request.get_json()
        
        config = SearchConfig(
            user_id=current_user.id,
            name=data['name'],
            keywords=json.dumps(data['keywords']),
            search_logic=data.get('search_logic', 'AND'),
            custom_logic=data.get('custom_logic', ''),
            frequency=data.get('frequency', 'daily'),
            custom_frequency=json.dumps(data.get('custom_frequency', {})),
            location_filter=data.get('location_filter', 'remote OR "United States"'),
            job_sites=json.dumps(data.get('job_sites', DEFAULT_JOB_SITES)),
            max_job_age=data.get('max_job_age', 24),
            is_active=data.get('is_active', True),
            search_time=data.get('search_time', '09:00')
        )
        
        db.session.add(config)
        db.session.commit()
        
        # Schedule the new search
        if config.is_active:
            schedule_search_job(config)
        
        return jsonify({'success': True, 'message': 'Search configuration created successfully'})

@app.route('/api/search-configs/<int:config_id>', methods=['PUT', 'DELETE'])
@login_required
def search_config(config_id):
    config = SearchConfig.query.filter_by(id=config_id, user_id=current_user.id).first()
    
    if not config:
        return jsonify({'success': False, 'message': 'Configuration not found'}), 404
    
    if request.method == 'PUT':
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400
            
            config.name = data['name']
            config.keywords = json.dumps(data['keywords'])
            config.search_logic = data.get('search_logic', 'AND')
            config.custom_logic = data.get('custom_logic', '')
            config.frequency = data.get('frequency', 'daily')
            config.custom_frequency = json.dumps(data.get('custom_frequency', {}))
            config.location_filter = data.get('location_filter', 'remote OR "United States"')
            config.job_sites = json.dumps(data.get('job_sites', DEFAULT_JOB_SITES))
            config.max_job_age = data.get('max_job_age', 24)
            config.is_active = data.get('is_active', True)
            config.search_time = data.get('search_time', '09:00')
            
            db.session.commit()
        except Exception as e:
            logger.error(f"Error updating configuration {config_id}: {e}")
            return jsonify({'success': False, 'message': f'Error updating configuration: {str(e)}'}), 400
        
        # Reschedule job
        scheduler.remove_job(f"search_{config.id}")
        if config.is_active:
            schedule_search_job(config)
        
        return jsonify({'success': True, 'message': 'Configuration updated successfully'})
    
    elif request.method == 'DELETE':
        scheduler.remove_job(f"search_{config.id}")
        db.session.delete(config)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Configuration deleted successfully'})

@app.route('/api/test-search', methods=['POST'])
@login_required
def test_search():
    data = request.get_json()
    logger.info(f"Test search request: {data}")
    
    # Create temporary search config
    temp_config = SearchConfig(
        keywords=json.dumps(data['keywords']),
        search_logic=data.get('search_logic', 'AND'),
        custom_logic=data.get('custom_logic', ''),
        location_filter=data.get('location_filter', 'remote OR "United States"'),
        job_sites=json.dumps(data.get('job_sites', DEFAULT_JOB_SITES)),
        max_job_age=data.get('max_job_age', 24)
    )
    
    logger.info(f"Created temp config with keywords: {temp_config.keywords}")
    
    # Try to use real Google API first, fall back to sample data if not configured or no results
    is_real_search = False
    try:
        jobs = search_jobs_google_api(current_user, temp_config)
        if len(jobs) > 0:
            is_real_search = True
            logger.info(f"Found {len(jobs)} real jobs from Google API")
        else:
            logger.warning("Google API returned 0 results, using sample data")
            jobs = get_sample_jobs(temp_config)
            is_real_search = False
            logger.info(f"Generated {len(jobs)} sample jobs")
    except Exception as e:
        logger.warning(f"Google API search failed, using sample data: {e}")
        jobs = get_sample_jobs(temp_config)
        is_real_search = False
        logger.info(f"Generated {len(jobs)} sample jobs")
    
    # Clear old test results for this user to avoid accumulation
    JobResult.query.filter_by(user_id=current_user.id).delete()
    
    # Save the test results to the database so they appear on the dashboard
    for job in jobs:
        job_result = JobResult(
            user_id=current_user.id,
            title=job['title'],
            link=job['link'],
            snippet=job['snippet'],
            job_site=job['job_site'],
            keyword=job['keyword'],
            found_at=job['found_at']
        )
        db.session.add(job_result)
    
    db.session.commit()
    logger.info(f"Saved {len(jobs)} jobs to database")
    
    return jsonify({
        'success': True, 
        'jobs': jobs,
        'is_real_search': is_real_search,
        'message': f"Found {len(jobs)} jobs using {'real Google search' if is_real_search else 'sample data'}"
    })

@app.route('/api/jobs/<int:job_id>', methods=['DELETE'])
@login_required
def delete_job(job_id):
    """Delete a specific job result"""
    job = JobResult.query.filter_by(id=job_id, user_id=current_user.id).first()
    
    if not job:
        return jsonify({'success': False, 'message': 'Job not found'}), 404
    
    db.session.delete(job)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Job deleted successfully'})

@app.route('/api/migrate-database', methods=['POST'])
def migrate_database():
    """Migrate database schema to add missing columns"""
    try:
        # Check if user_oauth_credentials column exists
        result = db.session.execute("PRAGMA table_info(user)")
        columns = [row[1] for row in result.fetchall()]
        
        migrations_applied = []
        
        if 'user_oauth_credentials' not in columns:
            db.session.execute("ALTER TABLE user ADD COLUMN user_oauth_credentials TEXT")
            db.session.commit()
            migrations_applied.append("Added user_oauth_credentials column")
            
        if 'notification_email' not in columns:
            db.session.execute("ALTER TABLE user ADD COLUMN notification_email VARCHAR(120)")
            db.session.commit()
            migrations_applied.append("Added notification_email column")
        
        if migrations_applied:
            return jsonify({'success': True, 'message': f'Database migration completed: {", ".join(migrations_applied)}'})
        else:
            return jsonify({'success': True, 'message': 'Database is already up to date'})
            
    except Exception as e:
        logger.error(f"Database migration error: {e}")
        return jsonify({'success': False, 'message': f'Migration failed: {str(e)}'}), 500

# Initialize database and schedule jobs
def create_tables():
    db.create_all()
    
    # Add missing columns if they don't exist (for existing databases)
    try:
        # Check if user_oauth_credentials column exists
        result = db.session.execute("PRAGMA table_info(user)")
        columns = [row[1] for row in result.fetchall()]
        
        if 'user_oauth_credentials' not in columns:
            db.session.execute("ALTER TABLE user ADD COLUMN user_oauth_credentials TEXT")
            db.session.commit()
            logger.info("Added user_oauth_credentials column to user table")
            
        if 'notification_email' not in columns:
            db.session.execute("ALTER TABLE user ADD COLUMN notification_email VARCHAR(120)")
            db.session.commit()
            logger.info("Added notification_email column to user table")
            
    except Exception as e:
        logger.error(f"Error updating database schema: {e}")
        # Continue anyway, the columns might already exist
    
    schedule_user_searches()

# Cleanup scheduler on exit
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        schedule_user_searches()
    
    # Get port from environment variable or default to 8002
    port = int(os.environ.get('PORT', 8002))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    app.run(debug=debug, host='0.0.0.0', port=port)