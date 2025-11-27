# Google Workspace Directory API Integration

## Overview

This integration adds Google Workspace Directory API support to db-api, allowing you to sync user information and photos from Google Workspace into your MySQL database for local querying.

## Features

- **User Sync**: Sync all Google Workspace users to local database
- **Photo Sync**: Sync user profile photos to local database
- **Query APIs**: Query synced user data without hitting Google API rate limits
- **Sync Logging**: Track sync operations and history

## Setup

### 1. Create Google Cloud Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project
3. Enable the **Admin SDK API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Admin SDK API"
   - Click "Enable"

4. Create a Service Account:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Name: `db-api-directory-sync`
   - Role: None required (we'll use domain-wide delegation)
   - Click "Done"

5. Create Service Account Key:
   - Click on the created service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose JSON format
   - Download and save as `google-credentials.json`

### 2. Enable Domain-Wide Delegation

1. In the service account details page:
   - Click "Show Domain-Wide Delegation"
   - Enable "Enable Google Workspace Domain-wide Delegation"
   - Copy the "Client ID" (numeric)

2. Configure in Google Workspace Admin Console:
   - Go to [admin.google.com](https://admin.google.com)
   - Navigate to: Security > Access and data control > API controls
   - Click "Manage Domain Wide Delegation"
   - Click "Add new"
   - Paste the Client ID
   - Add OAuth Scopes:
     ```
     https://www.googleapis.com/auth/admin.directory.user.readonly
     https://www.googleapis.com/auth/admin.directory.user.security
     ```
   - Click "Authorize"

### 3. Configure Environment Variables

Set the following environment variables:

```bash
# Path to service account JSON credentials file
export GOOGLE_CREDENTIALS_PATH="/path/to/google-credentials.json"

# Email of a Google Workspace admin user (for delegation)
export GOOGLE_DELEGATED_USER="admin@yourdomain.com"
```

**Windows (PowerShell):**
```powershell
$env:GOOGLE_CREDENTIALS_PATH="C:\path\to\google-credentials.json"
$env:GOOGLE_DELEGATED_USER="admin@yourdomain.com"
```

### 4. Create Database Tables

Run the SQL schema to create required tables:

```bash
mysql -u username -p database_name < support-files/sql/google_users.sql
```

Or execute the SQL directly:
- `google_users` - Stores synced user data
- `google_user_photos` - Stores user profile photos
- `google_sync_log` - Tracks sync operations

### 5. Install Dependencies

```bash
cd python
pip install -r requirements.txt
```

## API Endpoints

### Sync Operations

#### Sync All Users
```http
POST /api/{database}/google/sync
Authorization: Basic username:password
X-Host: 127.0.0.1
X-Port: 3306
```

**Response:**
```json
{
  "status": 201,
  "message": "Sync completed",
  "users_synced": 150
}
```

#### Sync All Photos
```http
POST /api/{database}/google/sync/photos
Authorization: Basic username:password
X-Host: 127.0.0.1
X-Port: 3306
```

**Response:**
```json
{
  "status": 201,
  "message": "Photo sync completed",
  "photos_synced": 145
}
```

### Query Operations

#### Get All Users
```http
GET /api/{database}/google/users?limit=100
Authorization: Basic username:password
X-Host: 127.0.0.1
X-Port: 3306
```

**Response:**
```json
[
  {
    "id": "1234567890",
    "primaryEmail": "john.doe@company.com",
    "givenName": "John",
    "familyName": "Doe",
    "externalId": "EMP001",
    "department": "Engineering",
    "orgDescription": "Software Development",
    "suspended": false,
    "isAdmin": false,
    "lastLoginTime": "2025-11-27T10:30:00+00:00",
    "syncedAt": "2025-11-27T12:00:00+00:00"
  }
]
```

#### Get Specific User
```http
GET /api/{database}/google/users/{email_or_id}
Authorization: Basic username:password
X-Host: 127.0.0.1
X-Port: 3306
```

**Response:**
```json
{
  "id": "1234567890",
  "primaryEmail": "john.doe@company.com",
  "givenName": "John",
  "familyName": "Doe",
  "externalId": "EMP001",
  "department": "Engineering",
  "orgDescription": "Software Development",
  "suspended": false,
  "isAdmin": false,
  "lastLoginTime": "2025-11-27T10:30:00+00:00",
  "syncedAt": "2025-11-27T12:00:00+00:00"
}
```

#### Get User Photo
```http
GET /api/{database}/google/users/{email_or_id}/photo
Authorization: Basic username:password
X-Host: 127.0.0.1
X-Port: 3306
```

**Response:** Binary image data (JPEG/PNG)

## User Data Fields

The following fields are synced from Google Workspace:

| Field | Google API Path | Description |
|-------|----------------|-------------|
| `id` | `id` | Unique Google user ID |
| `primaryEmail` | `primaryEmail` | Primary email address |
| `givenName` | `name.givenName` | First name |
| `familyName` | `name.familyName` | Last name |
| `externalId` | `externalIds[0].value` | Employee ID or external identifier |
| `department` | `organizations[0].department` | Department name |
| `orgDescription` | `organizations[0].description` | Organization description |
| `suspended` | `suspended` | Account suspension status |
| `isAdmin` | `isAdmin` | Admin privileges status |
| `lastLoginTime` | `lastLoginTime` | Last login timestamp |

## Scheduled Sync

To keep data up-to-date, set up periodic sync using cron or Task Scheduler.

### Linux/Mac (cron)
```bash
# Sync users daily at 2 AM
0 2 * * * curl -X POST -u username:password \
  -H "X-Host: 127.0.0.1" -H "X-Port: 3306" \
  http://localhost:8980/api/mydb/google/sync

# Sync photos weekly on Sunday at 3 AM
0 3 * * 0 curl -X POST -u username:password \
  -H "X-Host: 127.0.0.1" -H "X-Port: 3306" \
  http://localhost:8980/api/mydb/google/sync/photos
```

### Windows (Task Scheduler)
Create a PowerShell script `sync-google-users.ps1`:
```powershell
$base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("username:password"))
$headers = @{
    "Authorization" = "Basic $base64Auth"
    "X-Host" = "127.0.0.1"
    "X-Port" = "3306"
}

# Sync users
Invoke-RestMethod -Uri "http://localhost:8980/api/mydb/google/sync" `
    -Method POST -Headers $headers

# Sync photos (optional)
# Invoke-RestMethod -Uri "http://localhost:8980/api/mydb/google/sync/photos" `
#     -Method POST -Headers $headers
```

Schedule with Task Scheduler to run daily.

## Troubleshooting

### Error: "Google API not configured"
- Verify environment variables are set correctly
- Ensure credentials file exists at specified path
- Restart the application after setting environment variables

### Error: "Google credentials not configured"
- Check that `GOOGLE_CREDENTIALS_PATH` points to valid JSON file
- Verify `GOOGLE_DELEGATED_USER` is set to an admin email

### Error: "403 Forbidden" or "Not Authorized"
- Verify domain-wide delegation is properly configured
- Check that the correct OAuth scopes are authorized
- Ensure delegated user has admin privileges

### Error: "401 Unauthorized" during API calls
- Check database credentials in request headers
- Verify Basic authentication is properly formatted

### Sync fails silently
- Check `google_sync_log` table for error messages:
  ```sql
  SELECT * FROM mydb.google_sync_log ORDER BY started_at DESC LIMIT 10;
  ```

## Performance Considerations

- **User Sync**: Syncing 1000 users typically takes 10-20 seconds
- **Photo Sync**: Photos are bandwidth-intensive; sync during off-hours
- **Rate Limits**: Google Directory API has generous limits, but large organizations should monitor usage
- **Storage**: Photos average 10-50 KB each; plan database storage accordingly

## Security Notes

- Store `google-credentials.json` securely with restricted file permissions
- Use environment variables instead of hardcoding credentials
- Rotate service account keys periodically
- Monitor sync logs for unauthorized access attempts
- Consider encrypting photos in database if sensitive

## Example Integration

### JavaScript/React Client
```javascript
// Fetch all users
const response = await fetch('http://localhost:8980/api/mydb/google/users', {
  headers: {
    'Authorization': 'Basic ' + btoa('username:password'),
    'X-Host': '127.0.0.1',
    'X-Port': '3306'
  }
});
const users = await response.json();

// Display user photo
const photoUrl = `http://localhost:8980/api/mydb/google/users/${email}/photo`;
```

### Python Client
```python
import requests
from requests.auth import HTTPBasicAuth

# Sync users
response = requests.post(
    'http://localhost:8980/api/mydb/google/sync',
    auth=HTTPBasicAuth('username', 'password'),
    headers={'X-Host': '127.0.0.1', 'X-Port': '3306'}
)
print(response.json())

# Get users
response = requests.get(
    'http://localhost:8980/api/mydb/google/users',
    auth=HTTPBasicAuth('username', 'password'),
    headers={'X-Host': '127.0.0.1', 'X-Port': '3306'}
)
users = response.json()
```
