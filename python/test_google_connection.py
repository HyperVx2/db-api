#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test Google Workspace Directory API integration."""

import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from db_api_server.google_directory import create_client_from_env


def test_connection():
    """Test Google Workspace API connection."""
    print("Testing Google Workspace Directory API connection...")
    print()
    
    # Check environment variables
    creds_path = os.environ.get('GOOGLE_CREDENTIALS_PATH')
    delegated_user = os.environ.get('GOOGLE_DELEGATED_USER')
    
    print(f"GOOGLE_CREDENTIALS_PATH: {creds_path}")
    print(f"GOOGLE_DELEGATED_USER: {delegated_user}")
    print()
    
    if not creds_path or not delegated_user:
        print("❌ ERROR: Environment variables not set!")
        print()
        print("Please set:")
        print("  export GOOGLE_CREDENTIALS_PATH='/path/to/credentials.json'")
        print("  export GOOGLE_DELEGATED_USER='admin@yourdomain.com'")
        return False
    
    if not os.path.exists(creds_path):
        print(f"❌ ERROR: Credentials file not found: {creds_path}")
        return False
    
    print("✓ Environment variables are set")
    print("✓ Credentials file exists")
    print()
    
    # Try to create client
    try:
        client = create_client_from_env()
        if not client:
            print("❌ ERROR: Failed to create Google API client")
            return False
        
        print("✓ Google API client created successfully")
        print()
        
        # Try to list users (limited to 5 for testing)
        print("Fetching first 5 users from Google Workspace...")
        users = client.list_all_users()
        
        if not users:
            print("⚠ WARNING: No users returned (empty organization or permission issue)")
            return False
        
        print(f"✓ Successfully retrieved {len(users)} users")
        print()
        
        # Display first few users
        print("Sample users:")
        for i, user in enumerate(users[:5], 1):
            print(f"  {i}. {user['primaryEmail']}")
            print(f"     Name: {user['givenName']} {user['familyName']}")
            print(f"     Department: {user['department']}")
            print(f"     External ID: {user['externalId']}")
            print()
        
        print("✅ SUCCESS: Google Workspace API connection is working!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        print()
        print("Common issues:")
        print("  - Domain-wide delegation not configured")
        print("  - Service account doesn't have required scopes")
        print("  - Delegated user is not an admin")
        print("  - API not enabled in Google Cloud Console")
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
