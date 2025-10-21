# Gmail OAuth Setup Guide

This guide explains how to set up Gmail OAuth for the Daily Job Search application to enable email notifications.

## Prerequisites

1. A Google Cloud Console project
2. Gmail API enabled
3. OAuth 2.0 credentials configured

## Step 1: Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API:
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click on it and press "Enable"

## Step 2: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. Choose "Web application" as the application type
4. Add authorized redirect URIs:
   - For local development: `http://localhost:5000/gmail-callback`
   - For production: `https://yourdomain.com/gmail-callback`
5. Save the credentials and note down:
   - Client ID
   - Client Secret

## Step 3: Environment Variables

Set the following environment variables:

```bash
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export GOOGLE_REDIRECT_URI="http://localhost:5000/gmail-callback"
```

For production, update the redirect URI to your production domain.

## Step 4: Application Setup

1. Start the application
2. Go to Settings page
3. Click "Authorize Gmail" button
4. Sign in with your Google account
5. Grant permission to send emails
6. Configure notification email address
7. Test the setup with "Send Test Email" button

## Features

- **Gmail OAuth Flow**: Secure authorization without storing passwords
- **Email Notifications**: Automatic job search results via email
- **Custom Recipients**: Send notifications to any email address
- **Test Functionality**: Verify email setup before scheduling searches

## Security Notes

- OAuth credentials are stored securely in the database
- Tokens are automatically refreshed when needed
- Users can revoke access through their Google account settings
- No passwords are stored or transmitted

## Troubleshooting

### Common Issues

1. **"Gmail OAuth not configured"**
   - Check environment variables are set correctly
   - Verify redirect URI matches your configuration

2. **"Invalid state parameter"**
   - Clear browser cookies and try again
   - Ensure redirect URI is correct

3. **"Failed to send test email"**
   - Check Gmail API is enabled in Google Cloud Console
   - Verify OAuth scopes include gmail.send
   - Ensure user has granted necessary permissions

### Debug Steps

1. Check application logs for detailed error messages
2. Verify environment variables are loaded correctly
3. Test OAuth flow manually through Google's OAuth playground
4. Ensure redirect URI is accessible and returns to your application

## API Endpoints

- `GET /gmail-auth` - Start Gmail OAuth flow
- `GET /gmail-callback` - Handle OAuth callback
- `POST /api/save-email-settings` - Save notification email
- `GET /api/gmail-status` - Check OAuth status
- `POST /api/test-email` - Send test email

## Database Schema

The following fields are added to the User model:

- `gmail_credentials` (Text): JSON string of Gmail OAuth credentials
- `notification_email` (String): Email address for notifications

## Production Considerations

1. Use HTTPS for all OAuth redirects
2. Set up proper error handling and logging
3. Implement rate limiting for email sending
4. Consider using a dedicated email service for high volume
5. Monitor OAuth token refresh and handle failures gracefully
