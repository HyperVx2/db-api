# Google Workspace API Integration - Quick Test

# Test the endpoints after setup

## 1. First, create the database tables
# Run: mysql -u root -p yourdb < support-files/sql/google_users.sql

## 2. Set environment variables (adjust paths for your system)
# Linux/Mac:
export GOOGLE_CREDENTIALS_PATH="/path/to/google-credentials.json"
export GOOGLE_DELEGATED_USER="admin@yourdomain.com"

# Windows PowerShell:
$env:GOOGLE_CREDENTIALS_PATH="C:\path\to\google-credentials.json"
$env:GOOGLE_DELEGATED_USER="admin@yourdomain.com"

## 3. Start the server
cd python
python -m db_api_server.server

## 4. Test sync (replace credentials and database name)
curl -X POST http://localhost:8980/api/yourdb/google/sync \
  -u "username:password" \
  -H "X-Host: 127.0.0.1" \
  -H "X-Port: 3306"

## 5. Test get users
curl http://localhost:8980/api/yourdb/google/users \
  -u "username:password" \
  -H "X-Host: 127.0.0.1" \
  -H "X-Port: 3306"

## 6. Test get specific user
curl http://localhost:8980/api/yourdb/google/users/user@domain.com \
  -u "username:password" \
  -H "X-Host: 127.0.0.1" \
  -H "X-Port: 3306"

## 7. Test sync photos
curl -X POST http://localhost:8980/api/yourdb/google/sync/photos \
  -u "username:password" \
  -H "X-Host: 127.0.0.1" \
  -H "X-Port: 3306"

## 8. Test get photo (in browser or save to file)
curl http://localhost:8980/api/yourdb/google/users/user@domain.com/photo \
  -u "username:password" \
  -H "X-Host: 127.0.0.1" \
  -H "X-Port: 3306" \
  -o user_photo.jpg
