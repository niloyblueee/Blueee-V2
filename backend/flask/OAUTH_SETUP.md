# Google OAuth Setup Guide

## Quick Start

To enable Gmail, Google Docs, Calendar, and other Google services in Blueee, you need to set up OAuth credentials.

## Step 1: Get OAuth Credentials from Google

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/

2. **Create or Select a Project**
   - Click the project dropdown at the top
   - Click "New Project" or select an existing one
   - Give it a name like "Blueee V2"

3. **Enable Required APIs**
   - Go to "APIs & Services" → "Library"
   - Search and enable these APIs:
     - Gmail API
     - Google Drive API
     - Google Docs API
     - Google Calendar API
     - Google Sheets API
     - Google Tasks API
     - YouTube Data API v3
     - (Any others you want to use)

4. **Create OAuth 2.0 Credentials**
   - Go to "APIs & Services" → "Credentials"
   - Click "+ CREATE CREDENTIALS" → "OAuth client ID"
   - If prompted, configure the OAuth consent screen first:
     - Choose "External" (for personal use)
     - Fill in required fields (app name, user support email, developer email)
     - Under "Scopes", add:
       - `.../auth/gmail.readonly`
       - `.../auth/gmail.send`
       - `.../auth/drive`
       - `.../auth/documents`
       - `.../auth/calendar`
       - `.../auth/spreadsheets`
       - `.../auth/tasks`
       - `.../auth/youtube.readonly`
     - Add your email as a test user
   - Back in Credentials, create OAuth client ID:
     
     **IMPORTANT: Choose the right type based on your setup**
     
     **If Flask serves the frontend (localhost:5000):**
     - Application type: **Desktop app** (recommended for local development)
     - Name: "Blueee Desktop Client"
     - Click "Create"
     
     **OR if you want Web app flow:**
     - Application type: **Web application**
     - Name: "Blueee Web Client"
     - Authorized redirect URIs: `http://localhost:5000/oauth/callback`
     - Click "Create"
     
     ⚠️ **For most users: Use Desktop app** - it's simpler and works automatically

5. **Download the JSON File**
   - Click the download button (⬇️) next to your newly created credential
   - This downloads a file named something like `client_secret_XXXXX.apps.googleusercontent.com.json`

## Step 2: Install the Credentials

### Option A: Use the downloaded file directly (Recommended)

1. Rename the downloaded file to: **`client_secret.json`**
2. Place it in: **`backend/flask/`** directory
3. Done! The file should be at: `backend/flask/client_secret.json`

### Option B: Use environment variable

1. Set the `GOOGLE_OAUTH_CLIENT_SECRET` environment variable to the full path of your JSON file
2. Add to `backend/.env`:
   ```
   GOOGLE_OAUTH_CLIENT_SECRET=/full/path/to/your/client_secret.json
   ```

## Step 3: Verify Setup

1. Start the Flask backend:
   ```bash
   cd backend/flask
   python app.py
   ```

2. **Check the startup logs** - you should see:
   ```
   [flask] Looking for OAuth client secret at: D:\Blueee V2\Blueee-V2\backend\flask\client_secret.json
   [flask] OAuth file exists: True
   ```
   
   ⚠️ If it says `False`, the file is not in the right location!

3. When you first ask Blueee to check Gmail or create a doc:
   - Your browser will open automatically
   - Sign in with your Google account
   - Click "Allow" to grant permissions
   - A token file (`tokens.json`) will be created automatically
   - Future requests will use this token (no need to re-authenticate)

## File Structure

After setup, you should have:
```
backend/flask/
├── app.py
├── client_secret.json       ← OAuth credentials (keep private!)
├── tokens.json              ← Auto-generated after first auth
└── .env
```

**⚠️ Security:**
- Never commit `client_secret.json` to Git (already in `.gitignore`)
- Never commit `tokens.json` to Git (already in `.gitignore`)
- Keep these files private

## Troubleshooting

### "Missing Google OAuth client secret file"
- Make sure `client_secret.json` exists in `backend/flask/` directory
- Check exact location - should be: `D:\Blueee V2\Blueee-V2\backend\flask\client_secret.json`
- **Check Flask startup logs** - it prints the exact path it's looking for
- Or set `GOOGLE_OAUTH_CLIENT_SECRET` env variable to full path
- Restart Flask after adding the file

### Browser doesn't open / "redirect_uri_mismatch" error
- You likely created a **Web application** credential instead of **Desktop app**
- **Fix 1:** Delete the credential and create a new **Desktop app** credential
- **Fix 2:** Or keep Web app and add `http://localhost:8080/` to authorized redirect URIs

### "Invalid client" or "unauthorized_client"
- Your `client_secret.json` is for the wrong credential type
- Check if the file contains `"installed"` (Desktop) or `"web"` (Web app)
- Desktop app file has: `{"installed": {...}}`
- Web app file has: `{"web": {...}}`
- **Recommended:** Use Desktop app for local development

### "Access denied" or "Scope not granted"
- Delete `backend/flask/tokens.json`
- Restart Flask
- Try again - browser will open for re-authentication with new scopes

### "API not enabled"
- Go back to Google Cloud Console
- Enable the missing API in "APIs & Services" → "Library"

### "Quota exceeded"
- Free tier has limits
- Check quota in Google Cloud Console → "APIs & Services" → "Quotas"

## Testing

After setup, try:
- "Check my Gmail" → Should list recent emails
- "Create a Google Doc" → Should create a doc and return ID
- "What's on my calendar today?" → (Once calendar functions added)

## Reference

- Google Cloud Console: https://console.cloud.google.com/
- OAuth 2.0 Scopes: https://developers.google.com/identity/protocols/oauth2/scopes
- Gmail API Docs: https://developers.google.com/gmail/api
- Google Drive API Docs: https://developers.google.com/drive
