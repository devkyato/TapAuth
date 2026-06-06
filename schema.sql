CREATE DATABASE IF NOT EXISTS airhub_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE airhub_db;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_no VARCHAR(64) NOT NULL,
    lastname VARCHAR(100) NOT NULL,
    firstname VARCHAR(100) NOT NULL,
    middlename VARCHAR(100) NOT NULL DEFAULT '',
    fullname VARCHAR(255) NOT NULL,
    course VARCHAR(100) NOT NULL,
    project_type VARCHAR(100) NOT NULL,
    room VARCHAR(100) NOT NULL,
    nfc_code VARCHAR(128) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_student_no (student_no),
    INDEX idx_users_nfc_code (nfc_code)
);

CREATE TABLE IF NOT EXISTS user_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nfc_code VARCHAR(128) NOT NULL,
    date_logged TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(32) NOT NULL DEFAULT 'nfc',
    tap_type ENUM('TAP_IN','TAP_OUT') NOT NULL DEFAULT 'TAP_IN',
    guest_name VARCHAR(255) NULL,
    INDEX idx_user_logs_nfc_code (nfc_code),
    INDEX idx_user_logs_date_logged (date_logged),
    INDEX idx_user_logs_card_day (nfc_code, date_logged)
);


ALTER TABLE user_logs ADD COLUMN IF NOT EXISTS guest_name VARCHAR(255) NULL AFTER source;
ALTER TABLE user_logs ADD COLUMN IF NOT EXISTS tap_type ENUM('TAP_IN','TAP_OUT') NOT NULL DEFAULT 'TAP_IN' AFTER source;
CREATE INDEX IF NOT EXISTS idx_user_logs_card_day ON user_logs (nfc_code, date_logged);

CREATE TABLE IF NOT EXISTS firebase_sync_queue (
    id INT AUTO_INCREMENT PRIMARY KEY,
    record_type ENUM('user','log') NOT NULL,
    record_id INT NOT NULL,
    attempts INT NOT NULL DEFAULT 0,
    last_error TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    synced_at TIMESTAMP NULL DEFAULT NULL,
    UNIQUE KEY uniq_firebase_sync_record (record_type, record_id),
    INDEX idx_firebase_sync_pending (synced_at, updated_at)
);
CREATE OR REPLACE VIEW user_logs_info AS
SELECT
    l.id,
    l.nfc_code,
    l.date_logged,
    CASE
        WHEN u.id IS NULL AND NULLIF(l.guest_name, '') IS NOT NULL THEN 'GUEST'
        WHEN u.id IS NULL THEN 'GUEST_PENDING'
        ELSE l.tap_type
    END AS status,
    COALESCE(u.fullname, NULLIF(l.guest_name, ''), 'Guest') AS fullname
FROM user_logs l
LEFT JOIN users u ON u.nfc_code = l.nfc_code;
