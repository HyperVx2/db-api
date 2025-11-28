# -*- coding: utf-8 -*-

"""google_directory: Google Workspace Directory API integration."""

import os
import base64
from typing import List, Dict, Optional, Tuple

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Scopes required for Directory API
SCOPES = [
    'https://www.googleapis.com/auth/admin.directory.user.readonly',
    'https://www.googleapis.com/auth/admin.directory.user.security',
]


class GoogleDirectoryClient:
    """Client for Google Workspace Directory API."""

    def __init__(self, credentials_path: str, delegated_user_email: str):
        """Initialize Google Directory API client.
        
        Args:
            credentials_path: Path to service account JSON credentials file
            delegated_user_email: Email of admin user to impersonate
        """
        self.credentials_path = credentials_path
        self.delegated_user_email = delegated_user_email
        self.service = None
        
    def _get_service(self):
        """Get or create Directory API service instance."""
        if self.service is None:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=SCOPES,
                subject=self.delegated_user_email
            )
            self.service = build('admin', 'directory_v1', credentials=credentials)
        return self.service
    
    def list_all_users(self, customer: str = 'my_customer') -> List[Dict]:
        """Retrieve all users from Google Workspace.
        
        Args:
            customer: Customer ID or 'my_customer' for the current domain
            
        Returns:
            List of user dictionaries with selected fields
        """
        service = self._get_service()
        users = []
        page_token = None
        
        try:
            while True:
                results = service.users().list(
                    customer=customer,
                    maxResults=500,
                    orderBy='email',
                    projection='full',
                    pageToken=page_token
                ).execute()
                
                users_page = results.get('users', [])
                for user in users_page:
                    users.append(self._extract_user_fields(user))
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
        except HttpError as error:
            print(f'An error occurred listing users: {error}')
            raise
        
        return users
    
    def get_user(self, user_key: str) -> Optional[Dict]:
        """Get a specific user by email or ID.
        
        Args:
            user_key: User's primary email address or unique ID
            
        Returns:
            User dictionary with selected fields or None if not found
        """
        service = self._get_service()
        
        try:
            user = service.users().get(
                userKey=user_key,
                projection='full'
            ).execute()
            
            return self._extract_user_fields(user)
            
        except HttpError as error:
            if error.resp.status == 404:
                return None
            print(f'An error occurred getting user: {error}')
            raise
    
    def get_user_photo(self, user_key: str) -> Optional[Tuple[bytes, str]]:
        """Get user's photo.
        
        Args:
            user_key: User's primary email address or unique ID
            
        Returns:
            Tuple of (photo_data, mime_type) or None if no photo
        """
        service = self._get_service()
        
        try:
            photo = service.users().photos().get(userKey=user_key).execute()

            photo_data_str = photo.get('photoData', '')
            if not photo_data_str:
                return None

            # Photo data is Base64 encoded per Directory API
            try:
                # Fix padding if needed
                missing_padding = len(photo_data_str) % 4
                if missing_padding:
                    photo_data_str += '=' * (4 - missing_padding)

                photo_bytes = base64.b64decode(photo_data_str)
            except Exception as e:
                print(f'Error decoding photo data for {user_key}: {e}')
                return None

            # Infer MIME if not provided (Directory may omit mimeType)
            mime_type = photo.get('mimeType')
            if not mime_type:
                if len(photo_bytes) >= 2 and photo_bytes[0] == 0xFF and photo_bytes[1] == 0xD8:
                    mime_type = 'image/jpeg'
                elif len(photo_bytes) >= 8 and photo_bytes[:8] == b'\x89PNG\r\n\x1a\n':
                    mime_type = 'image/png'
                elif len(photo_bytes) >= 12 and photo_bytes[:4] == b'RIFF' and photo_bytes[8:12] == b'WEBP':
                    mime_type = 'image/webp'
                else:
                    mime_type = 'application/octet-stream'

            return (photo_bytes, mime_type)
            
        except HttpError as error:
            if error.resp.status == 404:
                return None
            print(f'An error occurred getting user photo: {error}')
            raise
    
    def _extract_user_fields(self, user: Dict) -> Dict:
        """Extract relevant fields from Google user object.
        
        Args:
            user: Full user object from Google API
            
        Returns:
            Dictionary with selected fields
        """
        # Extract name fields
        name = user.get('name', {})
        given_name = name.get('givenName', '')
        family_name = name.get('familyName', '')
        
        # Extract external IDs
        external_ids = user.get('externalIds', [])
        external_id_value = external_ids[0].get('value', '') if external_ids else ''
        
        # Extract organization info (use first organization)
        organizations = user.get('organizations', [])
        org_department = ''
        org_description = ''
        if organizations:
            org = organizations[0]
            org_department = org.get('department', '')
            org_description = org.get('description', '')
        
        return {
            'id': user.get('id', ''),
            'primaryEmail': user.get('primaryEmail', ''),
            'givenName': given_name,
            'familyName': family_name,
            'externalId': external_id_value,
            'department': org_department,
            'orgDescription': org_description,
            'suspended': user.get('suspended', False),
            'isAdmin': user.get('isAdmin', False),
            'lastLoginTime': user.get('lastLoginTime', ''),
        }


def create_client_from_env() -> Optional[GoogleDirectoryClient]:
    """Create GoogleDirectoryClient from environment variables.
    
    Environment variables:
        GOOGLE_CREDENTIALS_PATH: Path to service account JSON file
        GOOGLE_DELEGATED_USER: Email of admin user to impersonate
        
    Returns:
        GoogleDirectoryClient instance or None if env vars not set
    """
    credentials_path = os.environ.get('GOOGLE_CREDENTIALS_PATH')
    delegated_user = os.environ.get('GOOGLE_DELEGATED_USER')
    
    if not credentials_path or not delegated_user:
        return None
    
    if not os.path.exists(credentials_path):
        print(f'Credentials file not found: {credentials_path}')
        return None
    
    return GoogleDirectoryClient(credentials_path, delegated_user)
