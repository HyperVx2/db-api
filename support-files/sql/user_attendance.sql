-- User Attendance Logging Table
-- Stores user login/attendance records

CREATE TABLE IF NOT EXISTS user_attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    primary_email VARCHAR(255) NOT NULL,
    login_time DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_primary_email (primary_email),
    INDEX idx_login_time (login_time),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
