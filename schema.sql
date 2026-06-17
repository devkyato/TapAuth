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
    INDEX idx_users_student_no (student_no),
    INDEX idx_users_nfc_code (nfc_code)
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS student_no VARCHAR(64) NOT NULL DEFAULT '' AFTER id;
ALTER TABLE users ADD COLUMN IF NOT EXISTS lastname VARCHAR(100) NOT NULL DEFAULT '' AFTER student_no;
ALTER TABLE users ADD COLUMN IF NOT EXISTS firstname VARCHAR(100) NOT NULL DEFAULT '' AFTER lastname;
ALTER TABLE users ADD COLUMN IF NOT EXISTS middlename VARCHAR(100) NOT NULL DEFAULT '' AFTER firstname;
ALTER TABLE users ADD COLUMN IF NOT EXISTS fullname VARCHAR(255) NOT NULL DEFAULT '' AFTER middlename;
ALTER TABLE users ADD COLUMN IF NOT EXISTS course VARCHAR(100) NOT NULL DEFAULT '' AFTER fullname;
ALTER TABLE users ADD COLUMN IF NOT EXISTS project_type VARCHAR(100) NOT NULL DEFAULT '' AFTER course;
ALTER TABLE users ADD COLUMN IF NOT EXISTS room VARCHAR(100) NOT NULL DEFAULT '' AFTER project_type;
ALTER TABLE users ADD COLUMN IF NOT EXISTS nfc_code VARCHAR(128) NOT NULL DEFAULT '' AFTER room;
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER nfc_code;

CREATE TABLE IF NOT EXISTS user_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nfc_code VARCHAR(128) NOT NULL,
    date_logged TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_logs_nfc_code (nfc_code),
    INDEX idx_user_logs_date_logged (date_logged),
    INDEX idx_user_logs_card_day (nfc_code, date_logged)
);

ALTER TABLE user_logs ADD COLUMN IF NOT EXISTS nfc_code VARCHAR(128) NOT NULL DEFAULT '' AFTER id;
ALTER TABLE user_logs ADD COLUMN IF NOT EXISTS date_logged TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER nfc_code;
CREATE INDEX IF NOT EXISTS idx_users_student_no ON users (student_no);
CREATE INDEX IF NOT EXISTS idx_users_nfc_code ON users (nfc_code);
CREATE INDEX IF NOT EXISTS idx_user_logs_nfc_code ON user_logs (nfc_code);
CREATE INDEX IF NOT EXISTS idx_user_logs_date_logged ON user_logs (date_logged);
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
    numbered_logs.id,
    numbered_logs.nfc_code,
    DATE_FORMAT(numbered_logs.date_logged, '%Y-%m-%d %H:%i:%s') AS date_logged,
    COALESCE(u.student_no, '') AS student_no,
    COALESCE(u.lastname, 'GUEST') AS lastname,
    COALESCE(u.firstname, '') AS firstname,
    COALESCE(u.fullname, 'Guest') AS fullname,
    CASE
        WHEN u.id IS NULL THEN 'GUEST_PENDING'
        WHEN MOD(numbered_logs.tap_number, 2) = 0 THEN 'TAP_OUT'
        ELSE 'TAP_IN'
    END AS status,
    CASE
        WHEN MOD(numbered_logs.tap_number, 2) = 0 THEN 'LOGOUT'
        ELSE 'LOGIN'
    END AS event_type,
    DATE_FORMAT(
        CASE
            WHEN MOD(numbered_logs.tap_number, 2) = 0 THEN numbered_logs.previous_date_logged
            ELSE numbered_logs.date_logged
        END,
        '%Y-%m-%d %H:%i:%s'
    ) AS time_entered,
    CASE
        WHEN MOD(numbered_logs.tap_number, 2) = 0 THEN DATE_FORMAT(numbered_logs.date_logged, '%Y-%m-%d %H:%i:%s')
        ELSE NULL
    END AS time_left,
    CASE
        WHEN MOD(numbered_logs.tap_number, 2) = 0 THEN TIMESTAMPDIFF(SECOND, numbered_logs.previous_date_logged, numbered_logs.date_logged)
        ELSE NULL
    END AS duration_seconds,
    CASE
        WHEN MOD(numbered_logs.tap_number, 2) = 0 THEN TIME_FORMAT(SEC_TO_TIME(TIMESTAMPDIFF(SECOND, numbered_logs.previous_date_logged, numbered_logs.date_logged)), '%H:%i:%s')
        ELSE NULL
    END AS duration_label
FROM (
    SELECT
        l.*,
        ROW_NUMBER() OVER (
            PARTITION BY l.nfc_code, DATE(l.date_logged)
            ORDER BY l.date_logged ASC, l.id ASC
        ) AS tap_number,
        LAG(l.date_logged) OVER (
            PARTITION BY l.nfc_code, DATE(l.date_logged)
            ORDER BY l.date_logged ASC, l.id ASC
        ) AS previous_date_logged
    FROM user_logs l
) numbered_logs
LEFT JOIN users u ON u.nfc_code = numbered_logs.nfc_code;
