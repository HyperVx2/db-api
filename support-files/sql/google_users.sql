-- Google Workspace Users Sync Tables
-- Creates tables to store synced data from Google Workspace Directory API

-- Main users table
CREATE TABLE IF NOT EXISTS google_users (
    id VARCHAR(255) PRIMARY KEY,
    primary_email VARCHAR(255) UNIQUE NOT NULL,
    given_name VARCHAR(255),
    family_name VARCHAR(255),
    external_id VARCHAR(255),
    department VARCHAR(255),
    org_description VARCHAR(500),
    suspended BOOLEAN DEFAULT FALSE,
    is_admin BOOLEAN DEFAULT FALSE,
    last_login_time DATETIME,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_primary_email (primary_email),
    INDEX idx_external_id (external_id),
    INDEX idx_department (department)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User photos table
CREATE TABLE IF NOT EXISTS google_user_photos (
    user_id VARCHAR(255) PRIMARY KEY,
    photo_data MEDIUMBLOB,
    mime_type VARCHAR(50) DEFAULT 'image/jpeg',
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES google_users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sync log table to track sync operations
CREATE TABLE IF NOT EXISTS google_sync_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sync_type ENUM('full', 'user', 'photo') NOT NULL,
    sync_status ENUM('started', 'completed', 'failed') NOT NULL,
    users_synced INT DEFAULT 0,
    photos_synced INT DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    INDEX idx_sync_status (sync_status),
    INDEX idx_started_at (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
