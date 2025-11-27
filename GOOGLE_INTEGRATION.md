# Google Workspace Integration Summary

## What's New

db-api now supports syncing and querying Google Workspace user data!

## New Files Added

1. **`python/src/db_api_server/google_directory.py`**
   - Google Workspace Directory API client
   - Handles authentication via service account
   - Fetches user info and photos from Google

2. **`support-files/sql/google_users.sql`**
   - Database schema for storing synced Google users
   - Tables: `google_users`, `google_user_photos`, `google_sync_log`

3. **`GOOGLE_WORKSPACE_SETUP.md`**
   - Complete setup and configuration guide
   - API documentation
   - Troubleshooting tips

4. **`clients/curl/curl.google.sh`**
   - Example curl commands for testing

## New API Endpoints

### Sync Endpoints
- `POST /api/{database}/google/sync` - Sync all users from Google Workspace
- `POST /api/{database}/google/sync/photos` - Sync all user photos

### Query Endpoints
- `GET /api/{database}/google/users` - Get all synced users
- `GET /api/{database}/google/users/{email_or_id}` - Get specific user
- `GET /api/{database}/google/users/{email_or_id}/photo` - Get user photo

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r python/requirements.txt
   ```

2. **Create database tables:**
   ```bash
   mysql -u root -p yourdb < support-files/sql/google_users.sql
   ```

3. **Set up Google service account** (see GOOGLE_WORKSPACE_SETUP.md)

4. **Configure environment variables:**
   ```bash
   export GOOGLE_CREDENTIALS_PATH="/path/to/credentials.json"
   export GOOGLE_DELEGATED_USER="admin@yourdomain.com"
   ```

5. **Run initial sync:**
   ```bash
   curl -X POST http://localhost:8980/api/yourdb/google/sync \
     -u "username:password" \
     -H "X-Host: 127.0.0.1" -H "X-Port: 3306"
   ```

## User Fields Synced

- Primary Email
- Given Name (First Name)
- Family Name (Last Name)
- External ID (Employee ID)
- Department
- Organization Description
- Suspended Status
- Admin Status
- Last Login Time
- User Photo (binary image data)

## Benefits

✅ **Local Caching** - Query user data without hitting Google API rate limits  
✅ **Fast Access** - Sub-second response times for user lookups  
✅ **Photo Storage** - Store and serve user photos directly  
✅ **Sync History** - Track all sync operations in database  
✅ **Scheduled Updates** - Easy to automate with cron/Task Scheduler  

## Next Steps

See **GOOGLE_WORKSPACE_SETUP.md** for detailed configuration instructions.
