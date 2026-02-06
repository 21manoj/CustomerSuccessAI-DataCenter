# Google Sheets API Setup Guide

## Prerequisites
- Google Cloud account
- Python 3.7+
- Access to Google Cloud Console

---

## Step 1: Enable Google Sheets API

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/

2. **Create or Select a Project**
   - Click "Select a project" → "New Project"
   - Name: `dc2s-sheets-sync`
   - Click "Create"

3. **Enable APIs**
   - Go to: APIs & Services → Library
   - Search for "Google Sheets API"
   - Click "Enable"
   - Search for "Google Drive API"
   - Click "Enable"

---

## Step 2: Create Service Account

1. **Navigate to Service Accounts**
   - Go to: APIs & Services → Credentials
   - Click "Create Credentials" → "Service Account"

2. **Fill in Details**
   - Service account name: `dc2s-sync-bot`
   - Service account ID: `dc2s-sync-bot` (auto-filled)
   - Description: `Service account for DC2_S Google Sheets sync`
   - Click "Create and Continue"

3. **Grant Permissions** (Optional)
   - Skip this step for now
   - Click "Continue"

4. **Done**
   - Click "Done"

---

## Step 3: Create Service Account Key

1. **Find Your Service Account**
   - In "APIs & Services → Credentials"
   - Under "Service Accounts", find `dc2s-sync-bot`
   - Click on the email address

2. **Create Key**
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Select "JSON"
   - Click "Create"

3. **Download Credentials**
   - A JSON file will download automatically
   - **IMPORTANT:** Keep this file secure!
   - Rename it to: `google-credentials.json`
   - Move it to your project:
     ```bash
     mv ~/Downloads/dc2s-sync-bot-*.json backend/integrations/google-credentials.json
     ```

4. **Secure the File**
   ```bash
   chmod 600 backend/integrations/google-credentials.json
   
   # Add to .gitignore
   echo "google-credentials.json" >> .gitignore
   ```

---

## Step 4: Get Service Account Email

1. **Open the JSON file**
   ```bash
   cat backend/integrations/google-credentials.json | grep client_email
   ```

2. **Copy the email** (looks like):
   ```
   dc2s-sync-bot@dc2s-sheets-sync.iam.gserviceaccount.com
   ```

3. **Save this email** - you'll need it in Step 5!

---

## Step 5: Share Sheet with Service Account

After creating your Google Sheet:

1. **Open the Google Sheet**
   - Go to the sheet URL

2. **Click "Share"**
   - Top right corner

3. **Add Service Account**
   - Paste the service account email from Step 4
   - Give it "Editor" permissions
   - **UNCHECK** "Notify people"
   - Click "Share"

---

## Step 6: Install Python Dependencies

```bash
cd /Users/manojgupta/CustomerSuccessAI-DataCenter/kpi-dashboard/backend

# Install Google Sheets libraries
pip3 install gspread oauth2client
```

---

## Step 7: Test Authentication

Create a test script:

```bash
cat > test_google_auth.py << 'EOF'
#!/usr/bin/env python3
import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    'integrations/google-credentials.json', scope
)
client = gspread.authorize(creds)

print("✅ Authentication successful!")
print(f"   Service account: {creds.service_account_email}")
print("\nYou can now create and access Google Sheets!")
EOF

chmod +x test_google_auth.py
python3 test_google_auth.py
```

**Expected output:**
```
✅ Authentication successful!
   Service account: dc2s-sync-bot@dc2s-sheets-sync.iam.gserviceaccount.com

You can now create and access Google Sheets!
```

---

## Troubleshooting

### Error: "Insufficient Permission"
**Solution:** Make sure you shared the sheet with the service account email (Step 5)

### Error: "File not found: google-credentials.json"
**Solution:** Check the file path:
```bash
ls -la backend/integrations/google-credentials.json
```

### Error: "gspread.exceptions.APIError: PERMISSION_DENIED"
**Solutions:**
1. Make sure Google Sheets API is enabled (Step 1)
2. Make sure sheet is shared with service account (Step 5)
3. Service account has "Editor" permissions

### Error: "No module named 'gspread'"
**Solution:**
```bash
pip3 install gspread oauth2client
```

---

## Security Best Practices

1. **Never commit credentials to git**
   ```bash
   # Already added to .gitignore
   echo "*.json" >> .gitignore
   echo "google-credentials.json" >> .gitignore
   ```

2. **Restrict service account permissions**
   - Only give access to specific sheets
   - Use "Editor" not "Owner" permissions

3. **Rotate keys periodically**
   - Create new key every 90 days
   - Delete old keys

4. **Monitor API usage**
   - Check Google Cloud Console → APIs & Services → Dashboard
   - Set up quota alerts

---

## API Quotas & Limits

**Google Sheets API limits:**
- Read requests: 300 per minute per project
- Write requests: 300 per minute per project
- Per-user quotas: 60 requests per minute

**Our sync uses:**
- ~10-20 requests per account per sync
- With 10 accounts: ~100-200 requests per sync
- Every 15 minutes: ~400-800 requests/hour
- **Well within limits!** ✅

---

## Next Steps

Once authentication is working:
1. ✅ Generate master Google Sheet (see WEEK2_INTEGRATION_GUIDE.md)
2. ✅ Run sync pipeline
3. ✅ Test with pilot accounts

---

## Quick Reference

**Service Account Email:**
```
dc2s-sync-bot@dc2s-sheets-sync.iam.gserviceaccount.com
```

**Credentials Path:**
```
backend/integrations/google-credentials.json
```

**Test Command:**
```bash
cd backend
python3 test_google_auth.py
```

---

## Support

If you encounter issues:
1. Check troubleshooting section above
2. Verify all steps were completed
3. Check Google Cloud Console for error logs
4. Review API quotas

**Common fix:** Delete and recreate the service account key if authentication fails repeatedly.
