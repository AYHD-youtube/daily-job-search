# Google API Setup Guide

## Issues Fixed ✅

The application has been updated to handle API errors gracefully and provide sample data when APIs are not properly configured.

## Current Status

- ✅ **Flask Application**: Running successfully on http://localhost:5001
- ✅ **User Registration/Login**: Working
- ✅ **Dashboard**: Functional
- ✅ **Sample Data**: Returns demo job listings when APIs fail
- ⚠️ **Google APIs**: Need proper configuration for real job searching

## Google API Setup (Optional for Demo)

### 1. Google Custom Search API Setup

1. **Go to Google Cloud Console**: https://console.cloud.google.com/
2. **Create a new project** or select existing one
3. **Enable the Custom Search API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Custom Search API"
   - Click "Enable"

4. **Create API Key**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "API Key"
   - Copy the API key

### 2. Custom Search Engine Setup

1. **Go to Google Custom Search**: https://cse.google.com/cse/
2. **Create a new search engine**:
   - Click "Add"
   - Enter job sites in "Sites to search" (one per line):
     ```
     myworkdayjobs.com
     greenhouse.io
     icims.com
     taleo.net
     lever.co
     smartrecruiters.com
     jobvite.com
     workforcenow.adp.com
     successfactors.com
     brassring.com
     jazzhr.com
     breezy.hr
     jobdiva.com
     bullhorn.com
     bamboohr.com
     ```
   - Click "Create"

3. **Get Search Engine ID**:
   - Go to "Setup" > "Basics"
   - Copy the "Search engine ID"

### 3. Configure in Application

1. **Go to Settings** in the web app
2. **Enter your API credentials**:
   - Custom Search API Key: `your-api-key-here`
   - Search Engine ID: `your-search-engine-id-here`
3. **Save settings**
4. **Test the search** to verify it works

## Demo Mode (Current)

The application currently works in **demo mode** and will show sample job listings even without proper API configuration. This allows you to:

- ✅ Test all features
- ✅ See the user interface
- ✅ Create search configurations
- ✅ View sample job results
- ✅ Experience the full workflow

## Next Steps

1. **Test the application** as-is with sample data
2. **Set up Google APIs** if you want real job searching
3. **Configure Gmail API** if you want real email notifications

## Troubleshooting

### If you see API errors:
- The application will automatically fall back to sample data
- Check your API key and search engine ID
- Ensure the Custom Search API is enabled
- Verify your search engine includes the job sites

### If you want to disable sample data:
- Comment out the `return get_sample_jobs(search_config)` line in `app.py`
- The application will return empty results instead

## Production Deployment

For production use, you'll also need to:
1. Set up Gmail API for email notifications
2. Configure proper OAuth credentials
3. Use a production database (PostgreSQL)
4. Set up proper SSL certificates

The application is fully functional for demonstration purposes! 🎉
